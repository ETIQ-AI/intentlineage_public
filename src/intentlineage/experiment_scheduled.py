"""User-bound scheduled-call readiness over the existing native campaign.

Authority helpers stay stdlib-only for the native gate. No reviewer/assessor,
transport, isolation policy, alternate scheduler or qualification is implemented.
"""
import ast
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path

FORMAT='m3b-chatgpt-scheduled-protocol.1'
MODE='m3-scheduled-readiness.1'
ARCHIVE='resources/evidence/archive/m3-single-parent-00276e9'
BRIEF='developer_m3-direct-start-20261014.md'
BRIEF_SHA='f6a39d5f514f4a35bb0a1a0066fe01e8318cc980c8d40381f2676257a8e14427'
ASSESSMENT_SHA='d0fd94300a87c2a683a59bbeba55326215d2140c8cbfb9bcd220987b566f658d'
PARENT_SOURCE='de0585a16fd4b84a92184290708e05b68f2618b0d3040a3aeb50b784f57acfb3'
PARENT_PROTOCOL='92f2fa94b64579f5d3428e0ec01089bd1748f286c3f6a7b254f60513babf8e51'
BANK='3494aea100d7ff651bacceb3542c509e7b52414b3c8e775c2c1c0d77b5af071a'
STARTUP_POLICY='Exact first scheduled E then first H; content-invalid ends its arm; technical failure stops; no repeat/replacement/extra qualification.'
ALLOWED={
 'src/intentlineage/experiment_execution.py':{'validate_execution_contract','validate_empirical_unit'},
 'src/intentlineage/experiment_protocol.py':{'validate_execution_protocol'},
 'src/intentlineage/experiment_preflight.py':{'execution_preflight'},
 'src/intentlineage/experiment_chatgpt.py':{'validate_chatgpt_protocol','run_chatgpt_invocation','ChatGPTProviderFactory.__init__','ChatGPTProviderFactory.verify','ChatGPTProviderFactory.inspect_runtime','ChatGPTProviderFactory.stage_qualification','ChatGPTReviewerTransport.__init__','ChatGPTReviewerTransport.__call__'},
 'src/intentlineage/_reference/chatgpt_boundary.py':{'_admission'},
 'src/intentlineage/review_runner.py':{'_Session.record_call'},
 'src/intentlineage/experiment_campaign.py':{'run_campaign','replay_campaign','inspect_incomplete_campaign'},
 'scripts/m3b.py':{'main'},
}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def load(path):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('Duplicate scheduled-mode key')
            d[k]=v
        return d
    def constant(v):raise ValueError('Nonfinite scheduled-mode value')
    value=json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=constant);digest(value);return value


def hashfile(path):
    path=Path(path)
    for p in [path,*path.parents]:
        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Scheduled authority/source link refused')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected(raw,names):
    tree=ast.parse(raw);spans=[];found=set()
    def visit(body,prefix=''):
        for n in body:
            if isinstance(n,ast.ClassDef):visit(n.body,prefix+n.name+'.')
            elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and prefix+n.name in names:
                found.add(prefix+n.name);spans.append((n.lineno-1,n.end_lineno))
                n.args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]);n.body=[ast.Pass()];n.returns=None
    visit(tree.body)
    if found!=names:raise ValueError('Registered scheduled-mode function missing')
    lines=raw.decode().replace('\r\n','\n').splitlines(keepends=True)
    for a,b in sorted(spans,reverse=True):lines[a:b]=['<scheduled-gate-function>\n']
    return ast.dump(tree,include_attributes=False),''.join(lines)


def source_authorization(root):
    root=Path(root);arc=root/ARCHIVE;main=root.parent.parent/'instructions_between_agents'
    if hashfile(main/BRIEF)!=BRIEF_SHA or hashfile(arc/'direct-start-brief.md')!=BRIEF_SHA:raise ValueError('Actual direct-start user authority changed')
    if hashfile(main/'m3-single-review-overseer-assessment-20261014.md')!=ASSESSMENT_SHA or hashfile(arc/'overseer-assessment.md')!=ASSESSMENT_SHA:raise ValueError('Reviewed parent assessment changed')
    baseline=load(arc/'source-manifest.json')
    if digest(baseline)!=PARENT_SOURCE or len(baseline)!=62:raise ValueError('Reviewed parent source seal changed')
    files=list((root/'src/intentlineage').rglob('*.py'))+[root/n for n in ['scripts/m3b.py','scripts/audit_m3b.py','scripts/audit_m3b_execution.py','scripts/capture_m1_v4.py','requirements.txt']]
    current={p.relative_to(root).as_posix():hashfile(p) for p in sorted(files)}
    if set(current)-set(baseline)!={'src/intentlineage/experiment_scheduled.py'} or set(baseline)-set(current):raise ValueError('Scheduled extension source membership drift')
    for name,sha in baseline.items():
        old=arc/'source'/name
        if hashfile(old)!=sha:raise ValueError('Reviewed parent source bytes changed: '+name)
        if current[name]==sha:continue
        if name not in ALLOWED or protected(old.read_bytes(),ALLOWED[name])!=protected((root/name).read_bytes(),ALLOWED[name]):
            raise ValueError('Unrelated scientific/native/isolation source change: '+name)
    parent=load(arc/'parent-profile.json')
    if digest(parent['candidate'])!=PARENT_PROTOCOL or parent['bank_sha256']!=BANK:raise ValueError('Reviewed parent protocol/bank changed')
    return {'issued_by':'user','instruction_sha256':BRIEF_SHA,'parent_source_sha256':PARENT_SOURCE,
        'parent_protocol_sha256':PARENT_PROTOCOL,'parent_commit':'00276e9085628784e9105405198844bdb0665594',
        'controller_source_sha256':digest(current)}


def setup_record(path):
    from .experiment_qualification import REQUIRED_PROBES,runtime_identity
    record=load(path);raw=record['raw'];result=raw.get('result') or {};t=result.get('transport') or {}
    if (record.get('provider_review_calls')!=0 or result.get('provider_review_calls')!=0 or result.get('logical_turns')!=0
        or result.get('metadata_only') is not True or raw.get('exit_code')!=0 or t.get('exit_code')!=0
        or t.get('timed_out') or t.get('failure') or result.get('credential_leak') is not False
        or set(result.get('probes',{}))!=REQUIRED_PROBES or any(v is not True for v in result['probes'].values())
        or result.get('fresh_state_before_canaries') is not True):raise ValueError('Actual no-turn native setup unavailable')
    events=[json.loads(line) for line in base64.b64decode(t['stdout_base64']).splitlines() if line.strip()]
    models=next(e['result']['data'] for e in events if e.get('id')==3)
    account=next(e['result']['account'] for e in events if e.get('id')==2)
    if account.get('type')!='chatgpt' or 'gpt-5.5' not in {m.get('model') for m in models}:raise ValueError('Existing ChatGPT gpt-5.5 metadata unavailable')
    if any(e.get('method') in {'turn/started','turn/completed'} for e in events):raise ValueError('No-turn setup includes reviewer inference')
    return {'format_version':'m3-no-turn-setup.1','inspection_sha256':hashfile(path),
        'inspection_path':Path(path).resolve().relative_to(Path(__file__).resolve().parents[2]).as_posix(),'runtime':runtime_identity(raw['runtime']),
        'cli':deepcopy(raw['cli']),'public_network_runtime':deepcopy(raw['public_network_runtime']),
        'available_models':sorted({m['model'] for m in models}),'authentication':'chatgpt','review_calls':0,
        'account_access_basis':'supported client metadata; effective served client identity remains pending scheduled turns'}


def startup_requests(protocol,root=None):
    from .review_single import build_request
    root=Path(root or Path(__file__).resolve().parents[2]);mode=protocol['execution_mode'];item=mode['schedule'][0]
    bank=root/protocol['single_review']['bank_path'];plan=load(bank.parent/item['case_id']/'controller/review-plan.json')
    records=[]
    for arm,e in [('E',plan['endpoint']),('H',plan['batches'][0])]:
        q=build_request(e,model=protocol['reviewer']['model'],settings=protocol['reviewer']['settings'])
        records.append({'arm':arm,'unit_id':item['unit_id'],'case_id':item['case_id'],'request_sha256':digest(q),
            'evidence_sha256':q['evidence']['evidence_sha256'],'assessment_contract':q['contract_version']})
    return records


def freeze(inspection):
    from .native_capture import ROOT
    from .experiment_campaign import validate_bank_selection
    root=ROOT;parent=load(root/ARCHIVE/'parent-profile.json');p=deepcopy(parent['candidate']);setup=setup_record(inspection)
    binding=source_authorization(root);bank=load(root/p['single_review']['bank_path']);validate_bank_selection(bank)
    if setup['cli']['native_elf'] is not True or setup['cli']['binary_sha256']!=p['reviewer']['cli_sha256'] or setup['cli']['version']!=p['reviewer']['cli_version']:raise ValueError('Pinned native Linux CLI changed')
    p.update(format_version=FORMAT,status='frozen');p['limits']['qualification_max_calls']=0
    p['bindings']['controller_source_sha256']=binding['controller_source_sha256']
    p['bindings']['model_metadata']={'source_kind':'codex-app-server-model-list','authentication':'chatgpt',
        'models':setup['available_models'],'inspection_sha256':setup['inspection_sha256'],
        'public_network_runtime':setup['public_network_runtime'],'account_access_basis':setup['account_access_basis']}
    p['reviewer']['model_metadata_sha256']=digest(p['bindings']['model_metadata'])
    p['execution_mode']={'format_version':MODE,'qualification_calls':0,'charged_call_ceiling':198,
        'instruction_sha256':BRIEF_SHA,'parent_source_sha256':PARENT_SOURCE,'parent_protocol_sha256':PARENT_PROTOCOL,
        'schedule':deepcopy(parent['schedule']),'setup':setup,'backend_served_model':None,
        'startup_policy':STARTUP_POLICY,
        'startup_requests':[],'assessment_validity_separate':True,'protocol_changes_after_inference':'forbidden'}
    p['execution_mode']['startup_requests']=startup_requests(p)
    validate_protocol(p);return p


def validate_native_protocol(root,p):
    root=Path(root);parent=load(root/ARCHIVE/'parent-profile.json');expected=deepcopy(parent['candidate'])
    if not isinstance(p,dict) or p.get('format_version')!=FORMAT or p.get('status')!='frozen':raise ValueError('Explicit frozen scheduled-readiness protocol required')
    binding=source_authorization(root);mode=p.get('execution_mode') or {};setup=mode.get('setup') or {}
    if set(mode)!={'format_version','qualification_calls','charged_call_ceiling','instruction_sha256','parent_source_sha256','parent_protocol_sha256',
        'schedule','setup','backend_served_model','startup_policy','startup_requests','assessment_validity_separate','protocol_changes_after_inference'}:
        raise ValueError('Closed scheduled startup mode required')
    if set(setup)!={'format_version','inspection_sha256','inspection_path','runtime','cli','public_network_runtime','available_models','authentication','review_calls','account_access_basis'}:
        raise ValueError('Closed observed no-turn setup required')
    expected.update(format_version=FORMAT,status='frozen');expected['limits']['qualification_max_calls']=0
    expected['bindings']['controller_source_sha256']=binding['controller_source_sha256']
    expected['bindings']['model_metadata']=deepcopy(p['bindings']['model_metadata'])
    expected['reviewer']['model_metadata_sha256']=digest(p['bindings']['model_metadata'])
    expected['execution_mode']=deepcopy(mode)
    if p!=expected:raise ValueError('Frozen source/bank/model/settings/scientific protocol drift')
    if (mode.get('format_version')!=MODE or mode.get('qualification_calls')!=0 or mode.get('charged_call_ceiling')!=198
        or mode.get('instruction_sha256')!=BRIEF_SHA or mode.get('parent_source_sha256')!=PARENT_SOURCE
        or mode.get('parent_protocol_sha256')!=PARENT_PROTOCOL or mode.get('schedule')!=parent['schedule']
        or mode.get('backend_served_model') is not None or mode.get('assessment_validity_separate') is not True
        or mode.get('protocol_changes_after_inference')!='forbidden' or mode.get('startup_policy')!=STARTUP_POLICY or setup.get('review_calls')!=0
        or setup.get('authentication')!='chatgpt' or 'gpt-5.5' not in setup.get('available_models',[])
        or setup.get('cli',{}).get('binary_sha256')!=p['reviewer']['cli_sha256']):raise ValueError('Scheduled startup policy/setup/bounds drift')
    original=load(root/setup['inspection_path'])
    if hashfile(root/setup['inspection_path'])!=setup['inspection_sha256'] or original.get('provider_review_calls')!=0:raise ValueError('Bound no-turn metadata evidence changed')
    raw=original['raw']
    if setup.get('runtime')!=raw['runtime'] or setup.get('cli')!=raw['cli'] or setup.get('public_network_runtime')!=raw['public_network_runtime']:
        raise ValueError('Frozen no-turn runtime/CLI/network identity drift')
    events=[json.loads(line) for line in base64.b64decode(raw['result']['transport']['stdout_base64']).splitlines() if line.strip()]
    models=next(e['result']['data'] for e in events if e.get('id')==3)
    if setup['available_models']!=sorted({m['model'] for m in models}):raise ValueError('No-turn available model observation differs')
    metadata=p['bindings']['model_metadata']
    if metadata!={'source_kind':'codex-app-server-model-list','authentication':'chatgpt','models':setup['available_models'],
        'inspection_sha256':setup['inspection_sha256'],'public_network_runtime':setup['public_network_runtime'],'account_access_basis':setup['account_access_basis']}:
        raise ValueError('Frozen no-turn model metadata differs')
    if p['bindings']['qualification_sha256'] is not None or p['reviewer']['client_effective_model'] is not None:raise ValueError('Scheduled mode cannot fabricate qualification/served identity')
    return binding


def validate_protocol(p,*,require_frozen=False):
    from .native_capture import ROOT
    from .experiment_campaign import validate_bank_selection
    validate_native_protocol(ROOT,p)
    if p['execution_mode']['startup_requests']!=startup_requests(p):raise ValueError('Exact scheduled startup request drift')
    bank=load(ROOT/p['single_review']['bank_path']);validate_bank_selection(bank)
    if bank['bank_sha256']!=BANK or any(not c['qualified'] for c in bank['cases']):raise ValueError('Reviewed mechanical bank unavailable')
    return {'valid':True,'ready':True,'protocol_sha256':digest(p),'qualification_calls':0,
        'runtime_ready':False,'served_model_identity':'pending append-only scheduled observations'}


def authority(root,p):
    binding=validate_native_protocol(root,p)
    return {**binding,'kind':'observed_user_authorization','scope':'scheduled-call-readiness-direct-start',
        'path':ARCHIVE+'/direct-start-brief.md','sha256':BRIEF_SHA,'protocol_sha256':digest(p),'bank_sha256':BANK,
        'charged_call_ceiling':198,'separate_qualification_calls':0}


def validate_native_context(root,context):
    if set(context)!={'protocol','gates','qualification'} or context['qualification'] is not None:raise ValueError('Scheduled mode forbids fabricated/separate qualification')
    p=context['protocol']
    if context['gates']!={'direct_start':authority(root,p)}:raise ValueError('Actual source-bound user execution authority differs')
    return True


def validate_execution_contract(protocol,gates,qualification,*,evidence_root=None):
    from .native_capture import ROOT
    validate_protocol(protocol);validate_native_context(ROOT,{'protocol':protocol,'gates':gates,'qualification':qualification})
    if evidence_root is not None and Path(evidence_root)!=ROOT:
        if hashfile(Path(evidence_root)/gates['direct_start']['path'])!=BRIEF_SHA:raise ValueError('Exported actual user authority differs')
    return {'protocol':deepcopy(protocol),'gates':deepcopy(gates),'qualification':None,
        'check':{'ready':True,'execution_mode':MODE,'runtime_ready':False},'protocol_sha256':digest(protocol)}


def check_technical_observation(p,response,launch,isolation,call):
    from .experiment_qualification import REQUIRED_PROBES,assert_runtime_matches
    facts=response.get('native_client_facts') or {}
    classified=(response.get('failure') or {}).get('classification') or {}
    if (response.get('data_class')!='empirical' or response.get('mocked') is not False or response.get('synthetic') is not False
        or response.get('charging')!='unknown_or_charged' or facts.get('logical_turns')!=1
        or facts.get('client_effective_model')!='gpt-5.5' or facts.get('effective_reasoning_effort')!='low'
        or facts.get('usage_observation',{}).get('complete') is not True or facts['usage_observation'].get('errors')
        or isolation.get('qualified') is not True or set(isolation.get('probes',{}))!=REQUIRED_PROBES
        or any(v is not True for v in isolation['probes'].values()) or launch.get('controller_source_sha256')!=p['bindings']['controller_source_sha256']
        or launch.get('frozen_protocol_sha256')!=digest(p) or launch.get('qualification_sha256') is not None
        or launch.get('limits')!=p['limits'] or launch.get('model')!='gpt-5.5' or launch.get('settings')!={'reasoning_effort':'low'}
        or call.get('charged_reasoning') is not True or call.get('provider_call_id')!=launch.get('provider_call_id')):raise ValueError('Unverified native startup charging/usage/identity/isolation')
    assert_runtime_matches(p['execution_mode']['setup']['runtime'],launch['runtime'])
    valid=facts.get('complete') is True and call.get('failure_kind') is None
    if not valid:
        if set(facts.get('errors',[]))!={'Malformed/unbound native reply'} or classified.get('kind')!='invalid_response' or call.get('failure_kind')!='invalid_response':raise ValueError('Native technical failure cannot establish readiness')
    return {'technical_ready':True,'assessment_valid':valid,'framing_decode_checked':True,
        'client_effective_model':'gpt-5.5','backend_served_model':None,'reasoning_effort':'low',
        'usage_complete':True,'native_probes_verified':True,'qualification':False,
        'assessment_failure':deepcopy(call.get('failure')),'provider_attempts':None,'monetary_cost':None}


class Progress:
    """Append-only admission, cost and readiness journal around existing calls."""
    def __init__(self,root,p):
        self.root=Path(root);self.p=deepcopy(p);self.charged_calls=0;self.startup_observations=[];self.pending={};self.ids=set();self.threads=set();self.events=[]
        if not (self.root/'protocol.json').is_file() or load(self.root/'protocol.json')['execution_contract']['protocol']!=p:raise ValueError('Campaign must be frozen on disk before inference')

    def interrupt(self,reason):
        from .review_runner import _write
        target=self.root/'progress/interruption.json'
        if not target.exists():_write(target,{'reason':reason,'charged_calls_recorded':self.charged_calls,
            'charge_basis':'Controller conservatively charges unknown completed attempts; raw provenance/usage remain explicit.',
            'pending_invocations':list(self.pending),'startup_observations':self.startup_observations,'resume_review_history':False})

    def before_call(self,arm,request,invocation):
        from .review_runner import _write
        if self.charged_calls+len(self.pending)>=198:raise ValueError('Cumulative198 campaign ceiling exhausted')
        if self.startup_observations!=[] and len(self.startup_observations)<2:
            expected=self.p['execution_mode']['startup_requests'][1]
        elif not self.startup_observations:expected=self.p['execution_mode']['startup_requests'][0]
        else:expected=None
        if expected and (arm!=expected['arm'] or digest(request)!=expected['request_sha256']):raise ValueError('Startup must be exact scheduled E then H')
        path=Path(invocation).parent.relative_to(self.root).as_posix()
        if path in self.pending or any(e['directory']==path for e in self.events):raise ValueError('Repeated scheduled invocation')
        event={'phase':'admitted_before_inference','arm':arm,'directory':path,'request_sha256':digest(request),
            'frozen_protocol_sha256':digest(self.p),'charged_calls_before':self.charged_calls,'sequence':len(self.events)+1}
        self.pending[path]=event;self.events.append(event);_write(self.root/'progress'/f"{len(self.events):04d}-admission.json",event)

    def after_call(self,folder,call):
        from .review_runner import _write
        from .experiment_chatgpt import validate_chatgpt_call_files
        path=Path(folder).relative_to(self.root).as_posix();admitted=self.pending.pop(path,None)
        if not admitted:raise ValueError('Unadmitted/repeated campaign call')
        if call['charged_reasoning']:self.charged_calls+=1
        event={'phase':'recorded_call','directory':path,'arm':admitted['arm'],'call_file_sha256':hashfile(Path(folder)/'call.json'),
            'charged_calls':self.charged_calls,'charged_reasoning':call['charged_reasoning'],'provider_call_id':call['provider_call_id'],
            'usage_observation':deepcopy(call['usage_observation']),'failure':deepcopy(call['failure'])}
        _write(self.root/'progress'/f"{len(self.events):04d}-cost.json",event)
        if self.charged_calls>198:raise ValueError('Cumulative campaign ceiling exceeded')
        if not call['charged_reasoning']:return
        inv=Path(folder)/'invocation';request=load(inv/'evidence/request.json');launch=load(inv/'launch-receipt.json')
        response=load(inv/'output/real-transport-response.json');isolation=load(inv/'isolation-receipt.json')
        checked=validate_chatgpt_call_files(inv,request,launch,limits=self.p['limits'])
        if checked['facts']!=response['native_client_facts'] or call['usage_observation']!=response['usage_observation']:raise ValueError('Native campaign receipt/usage binding differs')
        observation=check_technical_observation(self.p,response,launch,isolation,call)
        commands=load(inv/'output/client-requests.json');thread=next(c['params']['threadId'] for c in commands if c['method']=='turn/start')
        if thread in self.threads or call['provider_call_id'] in self.ids:raise ValueError('Native reviewer reused thread/call identity')
        self.threads.add(thread);self.ids.add(call['provider_call_id'])
        if len(self.startup_observations)<2:
            expected=self.p['execution_mode']['startup_requests'][len(self.startup_observations)]
            if expected['arm']!=admitted['arm'] or expected['request_sha256']!=call['request_sha256']:raise ValueError('Startup observation order/request differs')
            receipt={**observation,**expected,'directory':path,'call_file_sha256':hashfile(Path(folder)/'call.json'),
                'provider_call_id':call['provider_call_id'],'thread_id':thread,'launch_sha256':digest(launch),
                'response_sha256':digest(response),'startup_index':len(self.startup_observations)+1,
                'campaign_charge_included_once':True,'usage_observation':deepcopy(call['usage_observation'])}
            self.startup_observations.append(receipt);_write(self.root/'startup'/f'{len(self.startup_observations):04d}.json',receipt)
        print(f"Recorded {self.charged_calls}/198 charged calls: {admitted['arm']} {call['failure_kind'] or 'valid'}; startup {len(self.startup_observations)}/2",flush=True)


def verify_progress(root,*,complete=False):
    from .experiment_chatgpt import validate_chatgpt_call_files
    root=Path(root);p=load(root/'protocol.json')['execution_contract']['protocol'];receipts=[load(f) for f in sorted((root/'startup').glob('*.json'))]
    costs=[load(f) for f in sorted((root/'progress').glob('*-cost.json'))];admissions=[load(f) for f in sorted((root/'progress').glob('*-admission.json'))]
    seen=set();calls=[];threads=set();running=0
    if len({a['directory'] for a in admissions})!=len(admissions) or any(a['frozen_protocol_sha256']!=digest(p) for a in admissions):raise ValueError('Admission journal source/order differs')
    for cost in costs:
        folder=root/cost['directory'];call=load(folder/'call.json')
        if hashfile(folder/'call.json')!=cost['call_file_sha256'] or cost['directory'] in seen:raise ValueError('Campaign cost journal duplicate/binding differs')
        seen.add(cost['directory']);calls.append(call)
        running+=call['charged_reasoning']
        admitted=next((a for a in admissions if a['directory']==cost['directory']),None)
        if (not admitted or admitted['request_sha256']!=call['request_sha256'] or admitted['arm']!=cost['arm']
            or cost['charged_calls']!=running or cost['charged_reasoning']!=call['charged_reasoning'] or cost['usage_observation']!=call['usage_observation']
            or cost['failure']!=call['failure']):raise ValueError('Exact admission/charge/usage journal binding differs')
    charged=sum(c['charged_reasoning'] for c in calls)
    if charged>198 or (costs and costs[-1]['charged_calls']!=charged):raise ValueError('Campaign cumulative cost journal differs')
    for index,r in enumerate(receipts):
        folder=root/r['directory'];call=load(folder/'call.json');inv=folder/'invocation'
        request=load(inv/'evidence/request.json');launch=load(inv/'launch-receipt.json');response=load(inv/'output/real-transport-response.json');isolation=load(inv/'isolation-receipt.json')
        facts=validate_chatgpt_call_files(inv,request,launch,limits=p['limits'])
        observation=check_technical_observation(p,response,launch,isolation,call)
        commands=load(inv/'output/client-requests.json');actual_thread=next(c['params']['threadId'] for c in commands if c['method']=='turn/start')
        expected=p['execution_mode']['startup_requests'][index]
        if (any(r[k]!=v for k,v in expected.items()) or any(r[k]!=v for k,v in observation.items())
            or r['call_file_sha256']!=hashfile(folder/'call.json') or r['thread_id']!=actual_thread or r['thread_id'] in threads
            or r['directory'] not in seen or r['launch_sha256']!=digest(launch) or r['response_sha256']!=digest(response)
            or r['provider_call_id']!=call['provider_call_id'] or r['startup_index']!=index+1 or r['campaign_charge_included_once'] is not True
            or r['usage_observation']!=call['usage_observation']):
            raise ValueError('Startup readiness/validity journal differs')
        if facts['facts']!=response['native_client_facts']:raise ValueError('Startup raw native facts differ')
        threads.add(r['thread_id'])
    if len(receipts)>2 or (complete and len(receipts)!=2):raise ValueError('Exactly two scheduled readiness observations required')
    # Literal unit/arm pattern avoids treating saved source fixtures as calls.
    recorded={f.parent.relative_to(root).as_posix() for f in (root/'units').glob('*/*/calls/*/call.json')}
    if recorded!=seen:raise ValueError('Unjournaled or invented campaign call records')
    if complete and len(admissions)!=len(costs):raise ValueError('Complete campaign has pending/unknown admitted invocations')
    return {'charged_calls':charged,'startup_observations':len(receipts),'technical_ready':len(receipts)==2,
        'assessment_validity':[r['assessment_valid'] for r in receipts],'separate_qualification_calls':0,'pending_attempts':len(list((root/'progress').glob('*-admission.json')))-len(costs)}
