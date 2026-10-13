"""Existing serial M2 campaign with explicit synthetic/recorded/actual gates."""
from copy import deepcopy
import importlib.metadata
import json
from pathlib import Path
import platform
import random
import shutil
import sys

from .native_capture import ROOT,digest,file_hash,load_native
from .artifact_views import _validate_catalogue
from .review_runner import run_review_matrix,replay_matrix,SESSION_VERSION,MATRIX_VERSION
from .experiment_history import validate_historical_binding,replay_historical_session
from .review_batches import validate_plan
from .experiment_faults import write
from .experiment_isolation import IsolatedMockProvider,OfflineSandbox,_check_tree
from .experiment_scoring import score_rows,rows_from_units,receipt_usage
from .experiment_execution import validate_execution_contract


def schedule(case_ids,*,repeats=1,seed=17):
    ids=sorted(case_ids)
    if not ids or len(ids)!=len(set(ids)) or any(not isinstance(i,str) or not i for i in ids):
        raise ValueError('Schedule needs unique nonempty opaque case IDs')
    if type(repeats) is not int or repeats<1 or type(seed) is not int or seed<0:
        raise ValueError('Schedule repeats/seed invalid')
    result=[{'case_id':i,'repeat_id':r,'unit_id':digest({'case':i,'repeat':r,'seed':seed})[:20]}
            for i in ids for r in range(1,repeats+1)]
    random.Random(seed).shuffle(result)
    return result


def environment():
    pins={}
    for line in (ROOT/'requirements.txt').read_text(encoding='utf-8').splitlines():
        if '==' in line and not line.lstrip().startswith('#'):
            name,pin=line.split('==',1);pin=pin.split(';',1)[0].strip()
            actual=importlib.metadata.version(name.strip())
            if actual!=pin:raise ValueError('Unverified dependency pin: '+name)
            pins[name.strip()]=actual
    return {'python_version':platform.python_version(),'platform':platform.platform(),
            'interpreter':sys.executable,'requirements_sha256':file_hash(ROOT/'requirements.txt'),
            'verified_pins':pins}


def validate_bank_selection(bank):
    """Verify actual captured/source bindings before staging any reviewer invocation."""
    bankroot=Path(bank['root']).resolve();_check_tree(bankroot)
    original=json.loads((bankroot/'bank.json').read_bytes())
    if original.get('bank_sha256')!=digest({k:v for k,v in original.items() if k!='bank_sha256'}):
        raise ValueError('Fault-bank integrity mismatch')
    if not bank['cases'] or any(c not in original['cases'] for c in bank['cases']):
        raise ValueError('Selected qualification differs from bank')
    for name,key in [('runtime.json','runtime_sha256'),('inventory.json','inventory_sha256'),
                     ('source-manifest.json','source_manifest_sha256')]:
        if file_hash(bankroot/name)!=original[key]:raise ValueError('Bank source/input hash mismatch: '+name)
    sources=json.loads((bankroot/'source-manifest.json').read_bytes())
    for relative,expected in sources.items():
        path=(bankroot/'source-snapshot'/relative).resolve()
        if not path.is_relative_to(bankroot/'source-snapshot') or file_hash(path)!=expected:
            raise ValueError('Bank source snapshot hash mismatch')
    # A delivered dependency correction must not silently reuse old interpretations/views.
    dependencies=['src/intentlineage/'+name+'.py' for name in ['native_capture','artifact_views',
        'evidence_inventory','evidence_packages','extraction','prompt_compiler','source_scope',
        'prompt_dispatch','native_workflow','payment']]
    dependencies+=['src/intentlineage/_reference/artifact_operations.py','src/intentlineage/_reference/native_graph.py']
    for relative in dependencies:
        if sources.get(relative)!=file_hash(ROOT/relative):raise ValueError('Stale M1 source dependency: '+relative)
    for record in bank['cases']:
        folder=(bankroot/record['directory']).resolve()
        if not folder.is_relative_to(bankroot):raise ValueError('Case directory escapes bank')
        if file_hash(folder/'entry.py')!=record['source_sha256']:
            raise ValueError('Injected entry source hash mismatch')
        if json.loads((folder/'controller/qualification.json').read_bytes())!=record:
            raise ValueError('Qualification integrity mismatch')
        if 'function_registry_sha256' in record and file_hash(folder/'controller/function-registry.json')!=record['function_registry_sha256']:
            raise ValueError('Immutable function semantic/provenance registry changed')
        if file_hash(folder/'capture/native-capture.json')!=record['native_capture_sha256']:
            raise ValueError('Native capture hash mismatch')
        packet=load_native(folder/'capture/scan-result.json')
        if packet['entry_file_hash']!=record['source_sha256'] or digest(packet)!=record['capture_sha256']:
            raise ValueError('Actual source/capture binding mismatch')
        for relative,expected in packet['adapter_sources'].items():
            if file_hash(ROOT/relative)!=expected:raise ValueError('Stale native adapter source: '+relative)
        cat=json.loads((folder/'controller/catalogue.json').read_bytes());_validate_catalogue(cat)
        if cat['capture_sha256']!=record['capture_sha256']:raise ValueError('Catalogue capture integrity mismatch')
        for witness in record['native_witnesses']:
            artifact=cat['artifacts'][witness['artifact_ref']]
            if artifact['native_ids']!=witness['native_ids'] or artifact['artifact_value_sha256']!=witness['artifact_value_sha256']:
                raise ValueError('Mechanical native witness mismatch')
        plan=json.loads((folder/'controller/review-plan.json').read_bytes());validate_plan(plan)
        if plan['plan_sha256']!=record['review_plan_sha256'] or len(plan['endpoint']['job_inputs'])!=3:
            raise ValueError('Complete source-bound pipeline input plan mismatch')
    return original


def inspect_incomplete_campaign(root):
    """Retain interrupted staging/attempts; never infer missing replies or scores."""
    root=Path(root).resolve();_check_tree(root)
    protocol=json.loads((root/'protocol.json').read_bytes())
    if protocol.get('format_version')=='m3b-campaign-protocol.2':
        from .experiment_resume import inspect_interrupted_continuation
        return inspect_interrupted_continuation(root)
    if protocol.get('protocol_sha256')=='e2301e63d71b07976f6b46cd0b8ecf21184e4d92f8000af53469a8f3746ee5dc':
        from .experiment_resume import inspect_retained_parent
        return inspect_retained_parent(root)
    if protocol.get('protocol_sha256')!=digest({k:v for k,v in protocol.items() if k!='protocol_sha256'}):
        raise ValueError('Incomplete protocol integrity mismatch')
    extended=protocol.get('format_version')=='m3b-campaign-protocol.1'
    data_class=protocol.get('data_class') if extended else None
    if extended:
        if data_class not in {'recorded_contract','empirical'} or protocol.get('synthetic') is not (data_class!='empirical') or protocol.get('live_allowed') is not (data_class=='empirical'):
            raise ValueError('Incomplete execution provenance mismatch')
        if data_class=='empirical':validate_execution_contract(**protocol['execution_contract'],evidence_root=root)
    elif protocol.get('synthetic') is not True or protocol.get('live_allowed') is not False:
        raise ValueError('Incomplete M3A export requires synthetic-only scope')
    truth=json.loads((root/'truth.json').read_bytes())
    if digest(truth)!=protocol['truth_sha256']:raise ValueError('Incomplete truth integrity mismatch')
    design={item['unit_id']:item for item in protocol['schedule']}
    if len(design)!=len(protocol['schedule']):raise ValueError('Duplicate unit schedule')
    completed=[];interrupted=[];calls=[];unknown=[]
    for folder in (root/'units').glob('*'):
        if folder.name not in design:raise ValueError('Unknown staged unit')
        if (folder/'unit.json').exists() and (folder/'matrix.json').exists():completed.append(folder.name)
        else:interrupted.append(folder.name)
        for invocation in folder.glob('*/calls/*/invocation'):
            call_path=invocation.parent/'call.json'
            if call_path.exists():calls.append(json.loads(call_path.read_bytes()))
            else:unknown.append(invocation.relative_to(root).as_posix())
    result={'synthetic':data_class!='empirical','incomplete':True,'protocol_sha256':protocol['protocol_sha256'],
        'completed_units':completed,'interrupted_units':interrupted,
        'unstaged_units':sorted(set(design)-set(completed)-set(interrupted)),
        'calls_recorded':len(calls),'logical_calls_known':sum(bool(c['charged_reasoning']) for c in calls),
        'unknown_attempts':len(unknown),'unknown_invocations':unknown,'score':None,
        'limits':['Interrupted invocations have unknown charging/results; no session resumes and no semantic score is manufactured.']}
    if extended:result.update(data_class=data_class,empirical_admissible=False)
    return result


def replay_campaign(root):
    root=Path(root)
    result=json.loads((root/'campaign.json').read_bytes())
    if result.get('format_version')=='m3b-campaign.2':
        from .experiment_resume import replay_continuation
        return replay_continuation(root)
    if result.get('campaign_sha256')!=digest({k:v for k,v in result.items() if k!='campaign_sha256'}):
        raise ValueError('Campaign integrity mismatch')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-{'campaign.json'}
    if actual!=set(result['files']):raise ValueError('Campaign exact file set mismatch')
    for relative,expected in result['files'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or path.is_symlink() or file_hash(path)!=expected:
            raise ValueError('Campaign file hash mismatch: '+relative)
    protocol=json.loads((root/'protocol.json').read_bytes())
    if protocol.get('protocol_sha256')!=digest({k:v for k,v in protocol.items() if k!='protocol_sha256'}) or protocol['protocol_sha256']!=result['protocol_sha256']:
        raise ValueError('Campaign protocol integrity mismatch')
    extended=result['format_version']=='m3b-campaign.1'
    data_class=result.get('data_class') if extended else None
    historical=result['format_version'] in {'m3a-campaign.1','m3a-campaign.2'}
    if historical:
        if protocol['format_version'] not in {'m3a-protocol.1','m3a-protocol.2'}:
            raise ValueError('Current protocol cannot use historical replay')
        validate_historical_binding(root,protocol)
    elif extended:
        if protocol['format_version']!='m3b-campaign-protocol.1' or data_class not in {'recorded_contract','empirical'} or protocol.get('data_class')!=data_class:
            raise ValueError('Execution campaign provenance/version mismatch')
        if result.get('synthetic') is not (data_class!='empirical') or protocol.get('synthetic') is not result['synthetic'] or result.get('empirical_admissible') is not (data_class=='empirical'):
            raise ValueError('Execution campaign labels changed')
        from .review_function import SESSION_VERSION as FUNCTION_SESSION,MATRIX_VERSION as FUNCTION_MATRIX
        function_mode=protocol.get('execution_contract',{}).get('protocol',{}).get('format_version')=='m3b-chatgpt-function-protocol.1'
        expected_session=FUNCTION_SESSION if function_mode else SESSION_VERSION;expected_matrix=FUNCTION_MATRIX if function_mode else MATRIX_VERSION
        if protocol.get('usage_version')!=expected_session or protocol.get('matrix_version')!=expected_matrix or result['score']['format_version']!='m3b-score.1':
            raise ValueError('Execution requires exact corrected 4.2 policy')
        if data_class=='empirical':validate_execution_contract(**protocol['execution_contract'],evidence_root=root)
        elif protocol.get('provider_identity',{}).get('kind')!='m3b-offline-fake':
            raise ValueError('Recorded campaign requires its bound explicit fake identity')
    elif result['format_version']!='m3a-campaign.3' or protocol['format_version']!='m3a-protocol.3' or protocol.get('usage_version')!=SESSION_VERSION or protocol.get('matrix_version')!=MATRIX_VERSION or result['score']['format_version']!='m3a-score.2':
        raise ValueError('Current campaign requires corrected 4.2 policy and scoring versions')
    legacy=result['score']['format_version']=='m3a-score.1'
    for unit in result['units']:
        folder=root/unit['directory'];matrix=json.loads((folder/'matrix.json').read_bytes())
        if matrix.get('matrix_sha256')!=digest({k:v for k,v in matrix.items() if k!='matrix_sha256'}) or matrix!=unit['matrix']:
            raise ValueError('Matrix integrity mismatch')
        cat=json.loads((root/'inputs'/unit['case_id']/'controller/catalogue.json').read_bytes())
        if not historical:
            if replay_matrix(folder,catalogue=cat)!=matrix:raise ValueError('Matrix policy replay mismatch')
        else:
            if matrix['format_version']!='m2-matrix.4.0':raise ValueError('Historical matrix version mismatch')
            for arm,session in matrix['sessions'].items():
                if session.get('status')!='not_run' and replay_historical_session(folder/arm)!=session:
                    raise ValueError('Historical session replay mismatch')
        for paired in matrix['paired_counts'].values():
            if not paired['matched']:raise ValueError('Actual logical calls not matched')
    score=score_rows(result['truth'],rows_from_units(result['units'],legacy=legacy,historical=historical,data_class=data_class,evidence_root=root),
                     format_version=result['score']['format_version'],data_class=data_class)
    if score!=result['score']:raise ValueError('Score replay mismatch')
    # Every invocation has a real qualified receipt, including transport retries.
    for unit in result['units']:
        for arm,session in unit['matrix']['sessions'].items():
            for call in session.get('calls',[]):
                receipt=json.loads((root/unit['directory']/arm/'calls'/f"{call['attempt']:04d}"/'invocation/isolation-receipt.json').read_bytes())
                if not receipt['qualified'] or not all(receipt['probes'].values()) or receipt['receipt_sha256']!=digest({k:v for k,v in receipt.items() if k!='receipt_sha256'}):
                    raise ValueError('Isolation receipt integrity mismatch')
                if data_class=='empirical':
                    if receipt.get('data_class')!='empirical' or receipt.get('request_sha256')!=call['request_sha256']:
                        raise ValueError('Actual call isolation binding changed')
                elif protocol.get('provider_identity',{}).get('kind')=='m3b-offline-fake':
                    from .experiment_qualification import validate_qualification
                    validate_qualification(receipt,request_sha256=call['request_sha256'])
    return {**result,'historical':True,'current_42_qualified':False,'replay_scope':'Frozen-source historical structural/accounting audit only'} if historical else result


def run_campaign(bank,output_dir,*,mode='synthetic',repeats=None,seed=None,resume=False,
                 max_calls=None,max_operations=None,reasoning_retries=None,transport_retries=None,fixtures=None,
                 provider_factory=None,execution_contract=None):
    if mode=='empirical' and (execution_contract or {}).get('protocol',{}).get('format_version')=='m3b-chatgpt-function-protocol.2':
        if resume or any(v is not None for v in [repeats,seed,max_calls,max_operations,reasoning_retries,transport_retries]) or fixtures:raise ValueError('Explicit amended continuation forbids overrides/resume')
        from .experiment_resume import run_continuation
        return run_continuation(bank,output_dir,provider_factory=provider_factory,execution_contract=execution_contract)
    extended=mode in {'recorded_contract','empirical'}
    data_class=mode if extended else None
    context=None;max_disclosure_bytes=100000;policy='question_driven'
    if mode=='empirical':
        context=validate_execution_contract(**(execution_contract or {}))
        frozen=context['protocol']
        for name,actual,expected in [('repeats',repeats,frozen['repeats']),('seed',seed,frozen['scheduling']['seed']),
            ('max_calls',max_calls,frozen['A']['max_calls']),('max_operations',max_operations,frozen['A']['max_operations']),
            ('reasoning_retries',reasoning_retries,frozen['retry']['reasoning_retries']),('transport_retries',transport_retries,frozen['retry']['transport_retries'])]:
            if actual is not None and actual!=expected:raise ValueError('Actual campaign overrides frozen protocol: '+name)
        repeats=frozen['repeats'];seed=frozen['scheduling']['seed'];max_calls=frozen['A']['max_calls'];max_operations=frozen['A']['max_operations']
        reasoning_retries=frozen['retry']['reasoning_retries'];transport_retries=frozen['retry']['transport_retries']
        max_disclosure_bytes=frozen['A']['max_disclosure_bytes'];policy=frozen['selection_policy']
        if fixtures:raise ValueError('Synthetic fixtures cannot enter empirical campaign')
        from .experiment_transport import HumanProviderFactory
        from .experiment_chatgpt import ChatGPTProviderFactory
        if frozen['reviewer']['authentication']!='chatgpt' or type(provider_factory) is not ChatGPTProviderFactory:
            raise ValueError('Actual campaign requires qualified ChatGPT cached-login transport')
    elif mode not in {'synthetic','recorded_contract'}:
        raise ValueError('M3A only runs explicit synthetic fixtures; M3B owns live integration')
    if mode=='recorded_contract' and provider_factory is None:raise ValueError('Recorded contract requires explicit offline transport')
    repeats=1 if repeats is None else repeats;seed=17 if seed is None else seed
    max_calls=5 if max_calls is None else max_calls;max_operations=2 if max_operations is None else max_operations
    reasoning_retries=0 if reasoning_retries is None else reasoning_retries;transport_retries=0 if transport_retries is None else transport_retries
    if provider_factory is not None and mode!='empirical':
        from .experiment_transport import OfflineProviderFactory
        if type(provider_factory) is not OfflineProviderFactory:
            raise ValueError('Only the explicit offline fake provider factory is allowed')
        if fixtures:raise ValueError('Choose one explicit synthetic provider fixture mechanism')
        provider_factory.verify()
    root=Path(output_dir).resolve()
    bankroot=Path(bank['root']).resolve()
    original=validate_bank_selection(bank)
    if context:
        if original['bank_sha256']!=frozen['population']['bank_sha256'] or {c['case_id'] for c in bank['cases']}!=set(frozen['population']['case_ids']):
            raise ValueError('Actual population/bank differs from frozen protocol')
    selected=deepcopy(bank['cases']);truth=[{k:c[k] for k in ['case_id','pair_id','kind','qualified','target_element_ids','capture_sha256']} for c in selected]
    inventory_ids=[e['element_id'] for e in json.loads((bankroot/'inventory.json').read_bytes())['elements']]
    for record in truth:record['inventory_element_ids']=inventory_ids[:]
    design=schedule([c['case_id'] for c in selected],repeats=repeats,seed=seed)
    clean_pairs={c['pair_id'] for c in selected if c['kind']=='clean' and c['qualified']}
    if any(c['qualified'] and c['kind'] in {'persistent','repaired'} and c['pair_id'] not in clean_pairs for c in selected):
        raise ValueError('Selected qualified faults require their matched clean control')
    controller_sources={p.relative_to(ROOT).as_posix():file_hash(p) for p in (ROOT/'src/intentlineage').rglob('*.py')}
    for name in ['requirements.txt','scripts/m3a.py','scripts/capture_m1_v4.py','resources/evidence/m3a-m2-interface.json']:
        controller_sources[name]=file_hash(ROOT/name)
    interface=json.loads((ROOT/'resources/evidence/m3a-m2-interface.json').read_bytes())
    from .review_function import SESSION_VERSION as FUNCTION_SESSION,MATRIX_VERSION as FUNCTION_MATRIX
    function_mode=bool(context and frozen.get('format_version')=='m3b-chatgpt-function-protocol.1')
    protocol={'format_version':'m3a-protocol.3','synthetic':mode!='empirical','model':frozen['reviewer']['model'] if context else 'synthetic-m2-stub',
        'settings':deepcopy(frozen['reviewer']['settings']) if context else {},'schedule':design,'truth_sha256':digest(truth),'bank_sha256':original['bank_sha256'],
        'max_calls':max_calls,'max_operations':max_operations,'max_disclosure_bytes':max_disclosure_bytes,
        'history_policy':'none','reasoning_retries':reasoning_retries,'transport_retries':transport_retries,
        'retry_policy':'Only positively confirmed transport failures are uncharged; malformed charged reasoning retries count.',
        'fixtures':deepcopy(fixtures or {}),'m1_status':'accepted 7178692 within tested scope',
        'm2_status':interface['status'],'usage_version':FUNCTION_SESSION if function_mode else SESSION_VERSION,'matrix_version':FUNCTION_MATRIX if function_mode else MATRIX_VERSION,
        'm2_interface':interface,
        'provider_transport':'human-qualified' if context else 'disabled','live_allowed':mode=='empirical','controller_sources':controller_sources}
    if provider_factory is not None:protocol['provider_identity']=provider_factory.identity
    if extended:
        protocol.update(format_version='m3b-campaign-protocol.1',data_class=data_class)
        if context:protocol['execution_contract']={k:deepcopy(context[k]) for k in ['protocol','gates','qualification']}
    protocol['protocol_sha256']=digest(protocol)
    if root.exists():
        if not resume:raise ValueError('Campaign requires fresh output or explicit read-only restart')
        saved=json.loads((root/'protocol.json').read_bytes())
        if saved!=protocol:raise ValueError('Restart protocol differs from frozen protocol')
        if (root/'campaign.json').exists():return replay_campaign(root)
    else:
        root.mkdir(parents=True);write(root/'protocol.json',protocol)
        write(root/'environment.json',environment())
        write(root/'truth.json',truth)
        if context:
            provider_factory.stage_qualification(root)
            for record in context['gates'].values():
                if type(record) is dict and record.get('kind') in {'observed_overseer_decision','observed_user_authorization'}:
                    target=root/record['path'];target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes((ROOT/record['path']).read_bytes())
        for relative,expected in controller_sources.items():
            dest=root/'controller-source'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((ROOT/relative).read_bytes())
            if file_hash(dest)!=expected:raise ValueError('Controller source changed during freeze')
        for name in ['source-manifest.json','source-snapshot','runtime.json','inventory.json']:
            source=bankroot/name;dest=root/'inputs'/name
            if source.is_dir():shutil.copytree(source,dest)
            else:dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
        for case in selected:
            source=bankroot/case['directory'];_check_tree(source)
            shutil.copytree(source,root/'inputs'/case['case_id'])
    runtime=provider_factory.inspect_runtime() if context else OfflineSandbox().inspect_runtime();write_runtime=root/'sandbox-runtime.json'
    if not write_runtime.exists():write(write_runtime,runtime)
    elif json.loads(write_runtime.read_bytes())!=runtime:raise ValueError('Sandbox runtime changed on restart')
    units=[]
    for item in design:
        directory='units/'+item['unit_id'];folder=root/directory
        if folder.exists():
            # Completed units can be replayed. Interrupted calls never resume.
            if not (folder/'unit.json').exists() or not (folder/'matrix.json').exists():
                raise ValueError('Interrupted unit retained as incomplete; rerun only as a new campaign/repeat')
            unit=json.loads((folder/'unit.json').read_bytes())
            matrix=json.loads((folder/'matrix.json').read_bytes())
            if matrix!=unit['matrix'] or matrix['matrix_sha256']!=digest({k:v for k,v in matrix.items() if k!='matrix_sha256'}):
                raise ValueError('Restart matrix integrity mismatch')
            cat=json.loads((root/'inputs'/item['case_id']/'controller/catalogue.json').read_bytes())
            if replay_matrix(folder,catalogue=cat)!=matrix:raise ValueError('Restart matrix policy replay mismatch')
            units.append(unit)
            continue
        case_folder=root/'inputs'/item['case_id']
        plan=json.loads((case_folder/'controller/review-plan.json').read_bytes());validate_plan(plan)
        if context and (plan['batch_count']!=frozen['H']['batch_counts'][item['case_id']] or plan['batch_size']!=frozen['H']['batch_size'] or plan['max_request_bytes']!=frozen['H']['max_request_bytes']):
            raise ValueError('Actual qualified H batching differs from frozen protocol')
        catalogue=json.loads((case_folder/'controller/catalogue.json').read_bytes())
        if max_calls<plan['batch_count']:raise ValueError('Frozen budget cannot cover H starting batches')
        providers={}
        def factory(arm):
            provider=provider_factory(arm) if provider_factory is not None else IsolatedMockProvider(adaptive=arm=='A',fixtures=(fixtures or {}).get(arm,()))
            providers[arm]=provider
            return provider
        write(root/'starts'/(item['unit_id']+'.json'),{**item,'protocol_sha256':protocol['protocol_sha256'],
              'review_plan_sha256':plan['plan_sha256'],'session_resume_allowed':False})
        matrix=run_review_matrix(plan,catalogue,provider_factory=factory,output_dir=folder,
            model=protocol['model'],settings=protocol['settings'],max_calls=max_calls,
            max_operations=max_operations,max_disclosure_bytes=max_disclosure_bytes,policy=policy,
            reasoning_retries=reasoning_retries,transport_retries=transport_retries,provider_mode='qualified_human' if context else 'mock')
        qualified=all(len(providers[a].receipts)==len(s.get('calls',[])) for a,s in matrix['sessions'].items() if a in providers)
        if not qualified:
            write(folder/'incomplete-isolation.json',{'status':'incomplete','synthetic':True,'reason':'Unqualified attempt; no scoring admissible'})
            raise ValueError('Isolation unavailable for one or more calls; campaign failed closed')
        unit={**item,'directory':directory,'matrix':matrix,'synthetic':mode!='empirical','isolation_qualified':qualified,
              'H_batch_count':plan['batch_count'],'A_max_logical_calls':max_calls}
        if extended:
            unit.update(data_class=data_class,provenance={'kind':'qualified-actual-provider' if context else 'recorded-contract-fixture',
                'provider_identity_sha256':digest(provider_factory.identity)})
        write(folder/'unit.json',unit);units.append(unit)
    result={'format_version':'m3b-campaign.1' if extended else 'm3a-campaign.3','synthetic':mode!='empirical','hosted_calls':sum(c['charged_reasoning'] for u in units for s in u['matrix']['sessions'].values() for c in s.get('calls',[])) if context else 0,
        'isolation_qualified':all(u['isolation_qualified'] for u in units),
        'scope':'Actual human-launched reviewer within qualified frozen protocol' if context else 'offline command boundary only; hosted provider transport unqualified',
        'protocol_sha256':protocol['protocol_sha256'],'units':units,'truth':truth,
        'score':score_rows(truth,rows_from_units(units,data_class=data_class,evidence_root=root),format_version='m3b-score.1' if extended else 'm3a-score.2',data_class=data_class),
        'scheduled_units':len(design),'completed_units':len(units),
        'incomplete_review_sessions':sum(s['status']=='incomplete' for u in units for s in u['matrix']['sessions'].values()),
        'limits':['All reviewer outputs and scores are synthetic plumbing demonstrations, not empirical findings.',
                  'Accepted M1 is integrated; M2 acceptance, actual model/CLI and provider transport remain M3B gates.']}
    if extended:
        result.update(data_class=data_class,empirical_admissible=mode=='empirical')
        result['limits'][0]='Actual results remain bounded by qualified protocol, coverage and dependent-case limitations.' if context else 'Recorded contract fixtures are not empirical results.'
    result['files']={p.relative_to(root).as_posix():file_hash(p) for p in root.rglob('*') if p.is_file()}
    result['campaign_sha256']=digest(result);write(root/'campaign.json',result)
    return result
