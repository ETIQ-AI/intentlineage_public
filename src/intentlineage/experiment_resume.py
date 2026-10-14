"""Explicit controller-owned continuation; reuse the existing reviewer machinery.

Authority functions remain stdlib-only for the native gate. Retained calls are
immutable observations, not resumable model sessions or a fresh call allowance.
"""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

FORMAT = 'm3b-chatgpt-function-protocol.2'
POLICY = 'm3-response-policy.1'
ARCHIVE = 'resources/evidence/archive/m3-response-base-6392862'
BRIEF_SHA = '47641495bef60c8dc2a19cacd9886492db2f6e86c36a5bdb6540b1769373b510'
BASE_SHA = 'f5df2dadd1cb1f13dbbc37ab3765f06b94768a852ef5d317dd68b979e757192b'
OLD_SOURCE_COMMIT = '6392862925ff1803ac784e34a6f58d36be80bcf9'
OLD_ROOT = '.tmp/actual-m3-function-campaign-950570701c5444acbe45b3d706be6ad2'
OLD_PROTOCOL = 'bc033ba73edab345a362002cb5351681a5419058be54bbe76d775e7f0bc67f04'
OLD_CAMPAIGN_PROTOCOL = 'e2301e63d71b07976f6b46cd0b8ecf21184e4d92f8000af53469a8f3746ee5dc'
OLD_QUALIFICATION = '76a14f2724f60dc270aabca4c880f972d4bc818a67dd3b523804cdb35748d70b'
OLD_BUNDLE = '6fb50d8513260decf165a5ccb02c078d8ede29df7c89c0bc601aabdd512c9b8f'
MANIFEST = 'resources/protocol/m3-response-continuation.json'
CEILING = 198
RETAINED = 79
ALLOWED = {
 'src/intentlineage/review_runner.py': {'_Session.__init__','_Session.review','_Session.finish','run_review_session','reconsider_same_evidence','_run_control','_ReplaySession.__init__','_ReplaySession.record_call','replay_session','run_review_matrix','replay_matrix'},
 'src/intentlineage/experiment_chatgpt.py': {'validate_chatgpt_protocol','chatgpt_qualification_request','chatgpt_qualification_contract','run_chatgpt_invocation','validate_chatgpt_call_files','collect_chatgpt_response','ChatGPTReviewerTransport.__call__','qualify_chatgpt_provider','validate_chatgpt_qualification'},
 'src/intentlineage/experiment_function.py': {'source_authorization','qualification_contract','authorize_launch','frozen_candidate','user_record','validate_user_record','validate_protocol','verify_m2_extension'},
 'src/intentlineage/experiment_protocol.py': {'validate_execution_protocol'},
 'src/intentlineage/experiment_qualification.py': {'validate_provider_qualification'},
 'src/intentlineage/experiment_user_authorization.py': {'user_campaign_record','validate_user_campaign_record'},
 'src/intentlineage/experiment_campaign.py': {'run_campaign','replay_campaign','inspect_incomplete_campaign'},
 'src/intentlineage/experiment_scoring.py': {'rows_from_units','_outcome','score_rows'},
 'src/intentlineage/experiment_execution.py': {'validate_empirical_unit'},
 'scripts/m3b.py': {'main'},
}

def digest(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def load(path):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ValueError('Duplicate continuation key')
            d[k]=v
        return d
    def constant(v):raise ValueError('Nonfinite continuation value')
    value=json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=constant)
    digest(value);return value

def hashfile(path):
    path=Path(path)
    for p in [path,*path.parents]:
        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Continuation link escape')
    with path.open('rb') as f:
        h=hashlib.sha256()
        while b:=f.read(2**20):h.update(b)
    return h.hexdigest()

def functions(root):
    spec=importlib.util.spec_from_file_location('intentlineage.function_authority',Path(root)/'src/intentlineage/experiment_function.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify_baseline(root):
    root=Path(root);manifest=load(root/ARCHIVE/'source-manifest.json')
    if digest(manifest)!=BASE_SHA:raise ValueError('Historical baseline source seal changed')
    for name,sha in manifest.items():
        if hashfile(root/ARCHIVE/'source'/name)!=sha:raise ValueError('Historical baseline source bytes changed: '+name)
    return BASE_SHA

def protected(raw,names):
    tree=ast.parse(raw);spans=[];found=set()
    def visit(body,prefix=''):
        for n in body:
            if isinstance(n,ast.ClassDef):visit(n.body,prefix+n.name+'.')
            elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and prefix+n.name in names:
                found.add(prefix+n.name);spans.append((n.lineno-1,n.end_lineno))
                n.args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[])
                n.body=[ast.Pass()];n.returns=None
    visit(tree.body)
    if found!=names:raise ValueError('Registered response function missing')
    lines=raw.decode().replace('\r\n','\n').splitlines(keepends=True)
    for a,b in sorted(spans,reverse=True):lines[a:b]=['<authorized-response-function>\n']
    return ast.dump(tree,include_attributes=False),''.join(lines)

def source_authorization(root):
    root=Path(root);f=functions(root);main=root.parent.parent/'instructions_between_agents'
    verify_baseline(root)
    if hashfile(main/'developer_m3-response-failure-and-resume-20261013.md')!=BRIEF_SHA or hashfile(root/ARCHIVE/'response-brief.md')!=BRIEF_SHA:
        raise ValueError('Actual response/continuation authority changed')
    for name,sha in [('m3-function-review-brief-20261013.md',f.BRIEF_SHA),('m3-auto-run-after-qualification-20261013.md','5041950d266dab3339fc643cd3f8e0ec35b1c2925ea83464e469bde2b8e1ef6d'),('m3b-qualification-code-overseer-review.md',f.REVIEW_SHA),('m3-event-capture-disposition-20261013.md',f.CAPTURE_SHA)]:
        if hashfile(main/name)!=sha:raise ValueError('Historical actual authority changed')
    baseline=load(root/ARCHIVE/'source-manifest.json')
    files=list((root/'src/intentlineage').rglob('*.py'))+[root/n for n in ['scripts/m3b.py','scripts/audit_m3b.py','scripts/audit_m3b_execution.py','scripts/capture_m1_v4.py','requirements.txt']]
    current={p.relative_to(root).as_posix():hashfile(p) for p in sorted(files)}
    if set(current)-set(baseline)!={'src/intentlineage/review_failures.py','src/intentlineage/experiment_resume.py'} or set(baseline)-set(current):
        raise ValueError('Response source membership drift')
    for name,sha in baseline.items():
        if current[name]==sha:continue
        if name not in ALLOWED or protected((root/ARCHIVE/'source'/name).read_bytes(),ALLOWED[name])!=protected((root/name).read_bytes(),ALLOWED[name]):
            raise ValueError('Unrelated reviewer/pipeline/isolation/source change: '+name)
    return {'issued_by':'user','scope':'controller-response-policy-and-exact-retained-continuation','instruction_sha256':BRIEF_SHA,
            'reviewed_source_sha256':'e59da1e101e7763d85fe0d3198c2994c0709d8dc176472260b6a16e8f0ac0a8e',
            'reviewed_commit':'f66eac36d247b8e8c0067ca96194ed8e89747d4a','reviewed_launch_sha256':'f93cecd2e881bda6feac876e9346ffaa53051ff4661430282eedef1d3bfb0687',
            'protected_base_source_sha256':BASE_SHA,'controller_source_sha256':digest(current),
            'configuration_disposition':{'issued_by':'overseer','scope':'native-event-capture-bound-amendment','sha256':f.CAPTURE_SHA,'max_output_bytes':33554432}}

def candidate(root):
    root=Path(root);p=deepcopy(functions(root).profile(root)['candidate']);p['format_version']=FORMAT;p['response_policy']=POLICY
    p['continuation']={'format_version':'m3-response-continuation.1','instruction_sha256':BRIEF_SHA,
        'original_source_commit':OLD_SOURCE_COMMIT,'original_source_sha256':BASE_SHA,
        'original_protocol_sha256':OLD_PROTOCOL,'original_campaign_protocol_sha256':OLD_CAMPAIGN_PROTOCOL,
        'original_qualification_sha256':OLD_QUALIFICATION,'original_bundle_sha256':OLD_BUNDLE,
        'manifest_path':MANIFEST,'manifest_sha256':digest(load(root/MANIFEST)) if (root/MANIFEST).exists() else None,
        'retained_charges':RETAINED,'ceiling':CEILING,'remaining_allowance':CEILING-RETAINED,
        'reviewer_inputs_changed':False,'reviewer_conversation_resume':False}
    return p

def qualification_request(root,index):return functions(root).qualification_request(root,index)

def validate_protocol(p,*,require_frozen=False):
    from intentlineage.native_capture import ROOT
    from intentlineage.experiment_chatgpt import validate_chatgpt_protocol,CHATGPT_FORMAT,draft_chatgpt_protocol
    expected=candidate(ROOT);expected['status']=p['status'];expected['bindings']=deepcopy(p['bindings']);expected['reviewer']=deepcopy(p['reviewer'])
    if p!=expected:raise ValueError('Exact amended protocol/continuation changed')
    old=functions(ROOT).profile(ROOT)['candidate'];reviewer=deepcopy(p['reviewer']);reviewer['client_effective_model']=None
    if reviewer!=old['reviewer'] or p['reviewer']['client_effective_model'] not in {None,'gpt-5.5'}:raise ValueError('Reviewer model/settings/input drift')
    if p['bindings']['controller_source_sha256'] not in {None,source_authorization(ROOT)['controller_source_sha256']}:raise ValueError('Amended source changed')
    base=deepcopy(p);base.pop('response_policy');base.pop('continuation');base.pop('function_review');base['format_version']=CHATGPT_FORMAT
    original=draft_chatgpt_protocol()
    for key in ['prompts','matrix','common_evidence']:base[key]=deepcopy(original[key])
    result=validate_chatgpt_protocol(base,require_frozen=require_frozen);result['protocol_sha256']=digest(p);return result

def qualification_contract(root,p):
    expected=candidate(root);expected['bindings']=deepcopy(p['bindings'])
    if p!=expected:raise ValueError('Exact draft amended qualification candidate required')
    if not p['continuation']['manifest_sha256']:raise ValueError('Validated retained continuation manifest required before qualification')
    if p['bindings']['controller_source_sha256']!=source_authorization(root)['controller_source_sha256']:raise ValueError('Amended qualification source missing')
    f=functions(root);records=f.request_records(root)
    return {'scope':'chatgpt-function-provider-qualification','data_class':'empirical','user_brief_sha256':BRIEF_SHA,
        'reviewer':deepcopy(p['reviewer']),'limits':deepcopy(p['limits']),'observability':deepcopy(p['observability']),
        'function_review':deepcopy(p['function_review']),'profile_sha256':f.PROFILE_SHA,
        'qualification_inputs':[deepcopy(r) for r,request in records],
        'response_policy':POLICY,'continuation':deepcopy(p['continuation']),
        'transport_framing':'unchanged native reply_json envelope and original M2 schema plus declared concise checks'}

def authorize_launch(root,contract,decision):
    binding=source_authorization(root)
    if decision.get('issued_by')!='overseer' or decision.get('status')!='approved' or decision.get('synthetic') is not False or decision.get('controller_source_sha256')!=binding['reviewed_source_sha256'] or decision.get('qualification_launch_sha256')!=binding['reviewed_launch_sha256']:
        raise ValueError('Actual original reviewed ancestry differs')
    p=candidate(root);p['bindings']['controller_source_sha256']=binding['controller_source_sha256']
    if contract!=qualification_contract(root,p):raise ValueError('Exact amended qualification contract differs')
    return {**binding,'authorized_launch_sha256':digest(contract),'profile_sha256':functions(root).PROFILE_SHA}

def frozen_candidate(root,q):
    p=candidate(root);p['status']='frozen';p['reviewer']=deepcopy(q['reviewer'])
    p['bindings'].update(controller_source_sha256=source_authorization(root)['controller_source_sha256'],qualification_sha256=q['qualification_sha256'],model_metadata=deepcopy(q['model_metadata']))
    return p

def user_record(root,p,q,gate):
    if gate not in {'real_path_review','protocol_review','experiment_authorization'}:raise ValueError('Unknown response gate')
    binding=source_authorization(root)
    if q.get('qualified') is not True or q.get('synthetic') is not False or q.get('data_class')!='empirical' or q.get('controller_source_sha256')!=binding['controller_source_sha256'] or q.get('qualification_sha256')!=digest({k:v for k,v in q.items() if k!='qualification_sha256'}):raise ValueError('Genuine corrected-source qualification required')
    if p!=frozen_candidate(root,q):raise ValueError('Exact amended continuation protocol required')
    expected=deepcopy(functions(root).profile(root)['candidate']['reviewer']);expected['client_effective_model']='gpt-5.5'
    if q['reviewer']!=expected or len(q['calls'])!=2 or len({c['thread_id'] for c in q['calls']})!=2 or [c['request_sha256'] for c in q['calls']]!=[r['request_sha256'] for r in functions(root).profile(root)['qualification_requests']]:raise ValueError('Fixed fresh endpoint/function qualification changed')
    if len(q['probes'])!=14 or any(v is not True for v in q['probes'].values()) or q['history_policy']!='none' or q['fresh_sessions'] is not True:raise ValueError('Native qualification controls/history missing')
    return {'kind':'observed_user_authorization','issued_by':'user','status':'authorized','synthetic':False,'scope':'exact-retained-response-policy-continuation',
        'gate':gate,'path':ARCHIVE+'/response-brief.md','sha256':BRIEF_SHA,'controller_source_sha256':binding['controller_source_sha256'],
        'protected_base_source_sha256':BASE_SHA,'protocol_sha256':digest(p),'qualification_sha256':q['qualification_sha256'],
        'continuation_manifest_sha256':p['continuation']['manifest_sha256']}

def validate_user_record(root,record,gate,p,q,evidence_root):
    try:return record==user_record(root,p,q,gate) and hashfile(Path(evidence_root)/ARCHIVE/'response-brief.md')==BRIEF_SHA
    except (ValueError,OSError,KeyError,TypeError):return False

def admit_calls(rows,*,ceiling):
    keys=set();ids=set();charged=0
    for r in rows:
        if type(r['charged_reasoning']) is not bool or type(r['attempt']) is not int or r['attempt']<1 or r['arm'] not in {'E','H','A','R-H','R-A'} or not isinstance(r['provider_call_id'],str) or not r['provider_call_id']:raise ValueError('Invalid call identity/charge provenance')
        key=(r['case_id'],r['arm'],r['attempt']);identity=r['provider_call_id']
        if key in keys or identity in ids:raise ValueError('Duplicate/conflicting retained call identity')
        keys.add(key);ids.add(identity);charged+=bool(r['charged_reasoning'])
        if charged>ceiling:raise ValueError('Retained calls exceed cumulative ceiling')
    return {'charged_calls':charged,'calls':len(rows),'identities':sorted(ids)}

class ContinuationBudget:
    def __init__(self,*,ceiling,retained_charges):
        if type(ceiling) is not int or type(retained_charges) is not int or retained_charges<0 or ceiling<retained_charges:raise ValueError('Invalid cumulative budget')
        self.ceiling=ceiling;self.used=retained_charges
    @property
    def remaining(self):return self.ceiling-self.used
    def charge(self):
        if self.remaining<=0:raise RuntimeError('Cumulative campaign ceiling exhausted')
        self.used+=1


def parent_bundle(root):
    p=Path(root)/'evidence/actual-function-campaign-launch-950570701c5444acbe45b3d706be6ad2/bundle-manifest.json'
    m=load(p)
    if m.get('bundle_sha256')!=OLD_BUNDLE or digest({k:v for k,v in m.items() if k!='bundle_sha256'})!=OLD_BUNDLE:
        raise ValueError('Exact preserved parent bundle required')
    return m


def build_continuation_manifest(root,*,evidence_root=None):
    from intentlineage.experiment_chatgpt import validate_chatgpt_call_files
    from intentlineage.experiment_qualification import REQUIRED_PROBES,assert_runtime_matches
    from intentlineage.review_runner import replay_matrix,replay_session
    from intentlineage.review_failures import assessment_failure
    from intentlineage.review_usage import aggregate_usage
    root=Path(root);tree=Path(evidence_root) if evidence_root is not None else root/OLD_ROOT
    expected={n.removeprefix('campaign/'):v for n,v in parent_bundle(root)['files'].items()}
    actual={p.relative_to(tree).as_posix() for p in tree.rglob('*') if p.is_file()}
    if actual!=set(expected):raise ValueError('Retained exact membership differs')
    for name,sha in expected.items():
        if hashfile(tree/name)!=sha:raise ValueError('Retained evidence changed: '+name)
    protocol=load(tree/'protocol.json')
    if protocol['protocol_sha256']!=OLD_CAMPAIGN_PROTOCOL or digest({k:v for k,v in protocol.items() if k!='protocol_sha256'})!=OLD_CAMPAIGN_PROTOCOL:raise ValueError('Original campaign protocol changed')
    execution=protocol['execution_contract'];original=execution['protocol'];q=execution['qualification']
    if digest(original)!=OLD_PROTOCOL or q['qualification_sha256']!=OLD_QUALIFICATION or digest({k:v for k,v in q.items() if k!='qualification_sha256'})!=OLD_QUALIFICATION or q['controller_source_sha256']!=BASE_SHA or q.get('qualified') is not True or q.get('synthetic') is not False:raise ValueError('Retained genuine qualification/source differs')
    if original['reviewer']!=q['reviewer'] or original['reviewer']['model']!='gpt-5.5' or original['reviewer']['settings']!=functions(root).profile(root)['candidate']['reviewer']['settings']:raise ValueError('Retained model/settings differ')
    if len(q['calls'])!=2 or len({c['thread_id'] for c in q['calls']})!=2 or set(q['probes'])!=REQUIRED_PROBES or any(v is not True for v in q['probes'].values()):raise ValueError('Retained native qualification missing')
    for c in q['calls']:
        invocation=tree/q['artifact_directory']/c['directory'];request=load(invocation/'evidence/request.json');launch=load(invocation/'launch-receipt.json')
        facts=validate_chatgpt_call_files(invocation,request,launch,limits=original['limits'],historical_source=BASE_SHA)
        if not facts['complete'] or facts['facts']['logical_turns']!=1:raise ValueError('Retained qualification no longer verifies')
    design={s['unit_id']:s for s in protocol['schedule']};rows=[];calls=[];sessions=[];native=[]
    for folder in sorted(tree.glob('units/*/*')):
        if not folder.is_dir():continue
        path=folder/'session.json'
        if not path.exists():raise ValueError('Retained partial invocation cannot be resumed')
        item=design[folder.parent.name];s=load(path);cat=load(tree/'inputs'/item['case_id']/'controller/catalogue.json')
        terminal=None
        for c in s['calls']:
            callfolder=folder/'calls'/f"{c['attempt']:04d}";request=load(callfolder/'request.json');launch=load(callfolder/'invocation/launch-receipt.json')
            if c!=load(callfolder/'call.json') or request['model']!=q['reviewer']['model'] or request['settings']!=q['reviewer']['settings'] or launch['qualification_sha256']!=OLD_QUALIFICATION:raise ValueError('Retained ordered request/model/qualification changed')
            isolation=load(callfolder/'invocation/isolation-receipt.json')
            if isolation['qualified'] is not True or set(isolation['probes'])!=REQUIRED_PROBES or any(v is not True for v in isolation['probes'].values()) or isolation['probes']!=launch['raw_events']['result']['probes'] or launch['raw_events']['result']['credential_leak'] is not False:raise ValueError('Retained native isolation missing')
            assert_runtime_matches(q['runtime'],launch['runtime'])
            facts=validate_chatgpt_call_files(callfolder/'invocation',request,launch,limits=original['limits'],historical_source=BASE_SHA)
            response=load(callfolder/'invocation/output/real-transport-response.json')
            if facts['facts']!=response['native_client_facts'] or facts['charging']!=response['charging'] or c['usage_observation']!=facts['facts']['usage_observation']:raise ValueError('Retained raw/facts/usage provenance differs')
            classification=None
            if not facts['complete']:
                wire=(callfolder/'invocation/output/reply.json').read_text(encoding='utf-8')
                classification=assessment_failure(wire,request,facts['facts'],charging=facts['charging'],probes=isolation['probes'])
                if classification is None or item['case_id']!='case-006' or folder.name!='A' or c['attempt']!=5:raise ValueError('Non-content or unexpected retained failure')
                terminal='invalid_response'
            rows.append({'case_id':item['case_id'],'arm':folder.name,'attempt':c['attempt'],'provider_call_id':c['provider_call_id'],'request_sha256':c['request_sha256'],'charged_reasoning':c['charged_reasoning']})
            calls.append(c)
            native.append({**rows[-1],'call_file_sha256':hashfile(callfolder/'call.json'),'raw_reply_sha256':c['raw_reply_sha256'],
                           'usage_observation':deepcopy(c['usage_observation']),'classification':classification,'source_sha256':BASE_SHA,'native_facts_sha256':digest(facts['facts'])})
        sessions.append({**item,'arm':folder.name,'directory':folder.relative_to(tree).as_posix(),'session_sha256':s['session_sha256'],
                         'logical_calls':s['logical_calls'],'terminal_outcome':terminal,'call_ids':[c['provider_call_id'] for c in s['calls']]})
        # Complete matrices replay once below; partial-case sessions replay here.
        if not (folder.parent/'matrix.json').exists() and replay_session(folder,catalogue=cat)!=s:raise ValueError('Retained session policy differs')
    units=[]
    for path in sorted(tree.glob('units/*/unit.json')):
        u=load(path);cat=load(tree/'inputs'/u['case_id']/'controller/catalogue.json')
        if replay_matrix(path.parent,catalogue=cat)!=u['matrix']:raise ValueError('Retained matrix policy differs')
        units.append({'unit_id':u['unit_id'],'case_id':u['case_id'],'directory':u['directory'],'unit_file_sha256':hashfile(path),'matrix_sha256':u['matrix']['matrix_sha256']})
    admitted=admit_calls(rows,ceiling=CEILING)
    if admitted['charged_calls']!=RETAINED or len(native)!=RETAINED or len(units)!=2 or len(sessions)!=13 or sum(c['classification'] is not None for c in native)!=1:raise ValueError('Exact retained continuation boundary differs')
    result={'format_version':'m3-response-continuation.1','instruction_sha256':BRIEF_SHA,'parent_bundle_sha256':OLD_BUNDLE,
        'parent_protocol_sha256':OLD_PROTOCOL,'parent_campaign_protocol_sha256':OLD_CAMPAIGN_PROTOCOL,
        'parent_source_sha256':BASE_SHA,'parent_qualification_sha256':OLD_QUALIFICATION,'original_directory':OLD_ROOT,
        'files':expected,'schedule':protocol['schedule'],'calls':native,'sessions':sessions,'units':units,
        'charged_calls':RETAINED,'cumulative_ceiling':CEILING,'remaining_allowance':CEILING-RETAINED,
        'accounting':aggregate_usage(calls),'reviewer_history_reused':False,'reviewer_inputs_changed':False}
    return result


def validate_retained_manifest(root,manifest,*,evidence_root=None):
    actual=build_continuation_manifest(root,evidence_root=evidence_root)
    if actual!=manifest:raise ValueError('Retained continuation manifest conflicts with immutable evidence')
    return {'valid':True,'manifest_sha256':digest(manifest),'retained_charges':RETAINED,'remaining_allowance':CEILING-RETAINED}


def terminal_outcomes(manifest,item):
    return {s['arm']:s['terminal_outcome'] for s in manifest['sessions'] if s['unit_id']==item['unit_id']}


def write_cost_checkpoint(root,item,costs):
    from intentlineage.experiment_faults import write
    write(Path(root)/'cost-checkpoints'/(item['unit_id']+'.json'),costs)


def validate_session_reference(item,arm,session,reference,manifest,*,plan_sha256):
    if session['arm']!=arm or session['plan_sha256']!=plan_sha256 or reference['session_sha256']!=session['session_sha256']:
        raise ValueError('Session arm/plan/identity binding differs')
    retained=[s for s in manifest['sessions'] if s['unit_id']==item['unit_id'] and s['case_id']==item['case_id'] and s['arm']==arm]
    if reference['phase']=='retained':
        if len(retained)!=1 or reference['directory']!='retained/campaign/'+retained[0]['directory'] or reference['session_sha256']!=retained[0]['session_sha256']:
            raise ValueError('Retained reference relabels or conflicts with an admitted observation')
    elif reference['phase']=='new':
        if retained:raise ValueError('Admitted retained observation cannot be redone')
        if not any(s['unit_id']==item['unit_id'] and s['case_id']==item['case_id'] for s in manifest['schedule']):raise ValueError('New case outside frozen schedule')
        partial=any(s['unit_id']==item['unit_id'] for s in manifest['sessions'])
        expected='units/'+item['unit_id']+('/' if partial else '/new/')+arm
        if reference['directory']!=expected:raise ValueError('New arm directory differs from continuation boundary')
    else:raise ValueError('Unknown session source phase')
    return True


def validate_composite_unit(unit,evidence_root,*,historical_source=None):
    from intentlineage.experiment_execution import validate_empirical_unit
    root=Path(evidence_root);p=load(root/'protocol.json');manifest=load(root/'continuation-manifest.json')
    if historical_source is not None:
        from intentlineage.completed_replay import assert_unit_bound
        assert_unit_bound(unit,root,historical_source)
    if digest(manifest)!=p['execution_contract']['protocol']['continuation']['manifest_sha256']:raise ValueError('Composite retained manifest binding differs')
    if unit.get('synthetic') is not False or unit.get('data_class')!='empirical' or unit.get('provenance',{}).get('kind')!='continued-qualified-actual-provider':raise ValueError('Composite unit provenance missing')
    from intentlineage.experiment_chatgpt import validate_chatgpt_call_files
    plan=load(root/'inputs'/unit['case_id']/'controller/review-plan.json')
    if set(unit['matrix']['sessions'])!={'E','H','A','R-H','R-A'}:raise ValueError('Composite scheduled arms differ')
    for arm,s in unit['matrix']['sessions'].items():
        ref=unit['session_sources'][arm]
        validate_session_reference(unit,arm,s,ref,manifest,plan_sha256=plan['plan_sha256'])
        folder=(root/ref['directory']).resolve()
        if not folder.is_relative_to(root.resolve()) or load(folder/'session.json')!=s:raise ValueError('Composite arm source/summary differs')
        old=ref['phase']=='retained'
        for c in s['calls']:
            inv=folder/'calls'/f"{c['attempt']:04d}"/'invocation';request=load(inv/'evidence/request.json');launch=load(inv/'launch-receipt.json')
            facts=validate_chatgpt_call_files(inv,request,launch,limits=p['execution_contract']['protocol']['limits'],historical_source=BASE_SHA if old else historical_source)
            expected=qhash=OLD_QUALIFICATION if old else p['execution_contract']['qualification']['qualification_sha256']
            if launch['qualification_sha256']!=expected or request['model']!='gpt-5.5' or request['settings']!=p['settings']:raise ValueError('Composite qualification/model lineage differs')
            response=load(inv/'output/real-transport-response.json')
            if response['native_client_facts']!=facts['facts'] or c['usage_observation']!=facts['facts']['usage_observation']:raise ValueError('Composite raw/usage facts differ')
    return True


def replay_composite_unit(root,unit,*,historical_source=None):
    from intentlineage.review_runner import replay_session
    from intentlineage.review_failures import assert_not_hard_failure
    root=Path(root);cat=load(root/'inputs'/unit['case_id']/'controller/catalogue.json')
    validate_composite_unit(unit,root,historical_source=historical_source)
    for arm,s in unit['matrix']['sessions'].items():
        ref=unit['session_sources'][arm]
        if replay_session(root/ref['directory'],catalogue=cat)!=s:raise ValueError('Composite session policy replay differs')
        if ref['phase']=='new':assert_not_hard_failure(s)
    m=unit['matrix']
    if m['matrix_sha256']!=digest({k:v for k,v in m.items() if k!='matrix_sha256'}):raise ValueError('Composite matrix seal differs')
    for control,paired in [('R-H','H'),('R-A','A')]:
        a=m['sessions'][control];b=m['sessions'][paired];expected={'control':a['logical_calls'],'paired':b['logical_calls'],'matched':a['logical_calls']==b['logical_calls']}
        if m['paired_counts'][control]!=expected or (not expected['matched'] and m['terminal_outcomes'][control]!='invalid_response'):raise ValueError('Composite neutral pairing differs')
    return unit


def run_continuation(bank,output_dir,*,provider_factory,execution_contract):
    from intentlineage.native_capture import ROOT
    from intentlineage.experiment_campaign import validate_bank_selection,environment
    from intentlineage.experiment_execution import validate_execution_contract
    from intentlineage.experiment_faults import write
    from intentlineage.review_runner import run_review_matrix,reconsider_same_evidence
    from intentlineage.review_failures import assert_not_hard_failure
    from intentlineage.experiment_scoring import rows_from_units,score_rows
    from intentlineage.experiment_chatgpt import ChatGPTProviderFactory
    import shutil
    context=validate_execution_contract(**execution_contract);p=context['protocol']
    if p['format_version']!=FORMAT or type(provider_factory) is not ChatGPTProviderFactory:raise ValueError('Actual amended provider/protocol required')
    root=Path(output_dir).resolve()
    if root.exists():raise ValueError('Continuation needs a fresh output; no reviewer resumes')
    manifest=load(ROOT/MANIFEST)
    validate_retained_manifest(ROOT,manifest)
    original=validate_bank_selection(bank)
    if original['bank_sha256']!=p['population']['bank_sha256']:raise ValueError('Continuation bank changed')
    root.mkdir(parents=True)
    write(root/'continuation-manifest.json',manifest)
    shutil.copytree(ROOT/OLD_ROOT,root/'retained/campaign')
    parent=load(root/'retained/campaign/protocol.json')
    protocol={'format_version':'m3b-campaign-protocol.2','data_class':'empirical','synthetic':False,'live_allowed':True,
        'model':p['reviewer']['model'],'settings':deepcopy(p['reviewer']['settings']),'schedule':manifest['schedule'],
        'truth_sha256':parent['truth_sha256'],'bank_sha256':parent['bank_sha256'],
        'execution_contract':{k:deepcopy(context[k]) for k in ['protocol','gates','qualification']},
        'provider_identity':provider_factory.identity,'response_policy':POLICY,'history_policy':'none',
        'retained_charges':RETAINED,'cumulative_ceiling':CEILING,'remaining_allowance':CEILING-RETAINED,
        'parent_protocol_sha256':OLD_PROTOCOL,'parent_campaign_protocol_sha256':OLD_CAMPAIGN_PROTOCOL,
        'controller_source_sha256':context['protocol']['bindings']['controller_source_sha256']}
    protocol['protocol_sha256']=digest(protocol);write(root/'protocol.json',protocol)
    shutil.copytree(root/'retained/campaign/inputs',root/'inputs')
    shutil.copyfile(root/'retained/campaign/truth.json',root/'truth.json')
    write(root/'environment.json',environment());provider_factory.stage_qualification(root)
    for record in context['gates'].values():
        if type(record) is dict and record.get('kind') in {'observed_overseer_decision','observed_user_authorization'}:
            target=root/record['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/record['path']).read_bytes())
    budget=ContinuationBudget(ceiling=CEILING,retained_charges=RETAINED)
    new_rows=[];units=[]
    def factory(arm):
        provider=provider_factory(arm)
        def call(request,invocation):
            if budget.remaining<=0:raise RuntimeError('Cumulative campaign ceiling exhausted before inference')
            # Reserve conservatively; release only a proven uncharged transport.
            from intentlineage.review_runner import TransportFailure
            budget.charge()
            try:return provider(request,invocation)
            except TransportFailure:
                budget.used-=1;raise
        return call
    for item in manifest['schedule']:
        directory='units/'+item['unit_id'];folder=root/directory;folder.mkdir(parents=True)
        cat=load(root/'inputs'/item['case_id']/'controller/catalogue.json');plan=load(root/'inputs'/item['case_id']/'controller/review-plan.json')
        retained=[s for s in manifest['sessions'] if s['unit_id']==item['unit_id']]
        sessions={s['arm']:load(root/'retained/campaign'/s['directory']/'session.json') for s in retained}
        refs={s['arm']:{'phase':'retained','directory':'retained/campaign/'+s['directory'],'session_sha256':s['session_sha256']} for s in retained}
        outcomes=terminal_outcomes(manifest,item)
        if not sessions:
            m=run_review_matrix(plan,cat,provider_factory=factory,output_dir=folder/'new',model=protocol['model'],settings=protocol['settings'],
                max_calls=p['A']['max_calls'],max_operations=p['A']['max_operations'],max_disclosure_bytes=p['A']['max_disclosure_bytes'],
                policy=p['selection_policy'],reasoning_retries=0,transport_retries=p['retry']['transport_retries'],provider_mode='qualified_human',response_policy=POLICY)
            sessions=m['sessions'];refs={a:{'phase':'new','directory':directory+'/new/'+a,'session_sha256':s['session_sha256']} for a,s in sessions.items()}
            outcomes={a:s.get('terminal_outcome') for a,s in sessions.items()}
        else:
            if set(sessions) not in ({'E','H','A','R-H','R-A'},{'E','H','A'}):raise ValueError('Unexpected retained continuation boundary')
            for arm,paired in [('R-H','H'),('R-A','A')]:
                if arm in sessions:continue
                s=reconsider_same_evidence(plan,arm=arm,logical_calls=sessions[paired]['logical_calls'],provider=factory(arm),
                    output_dir=folder/arm,model=protocol['model'],settings=protocol['settings'],transport_retries=p['retry']['transport_retries'],response_policy=POLICY)
                assert_not_hard_failure(s);sessions[arm]=s;refs[arm]={'phase':'new','directory':directory+'/'+arm,'session_sha256':s['session_sha256']};outcomes[arm]=s.get('terminal_outcome')
        m={'format_version':'m3-composite-matrix.1','response_policy':POLICY,'plan_sha256':plan['plan_sha256'],'model':protocol['model'],'settings':protocol['settings'],
            'sessions':sessions,'terminal_outcomes':outcomes,'session_sources':refs,
            'paired_counts':{c:{'control':sessions[c]['logical_calls'],'paired':sessions[a]['logical_calls'],'matched':sessions[c]['logical_calls']==sessions[a]['logical_calls']} for c,a in [('R-H','H'),('R-A','A')]}}
        m['matrix_sha256']=digest(m);write(folder/'matrix.json',m)
        unit={**item,'directory':directory,'matrix':m,'session_sources':refs,'data_class':'empirical','synthetic':False,'isolation_qualified':True,
              'provenance':{'kind':'continued-qualified-actual-provider','amended_protocol_sha256':digest(p),'parent_protocol_sha256':OLD_PROTOCOL,'continuation_manifest_sha256':digest(manifest)}}
        write(folder/'unit.json',unit);units.append(unit)
        for arm,s in sessions.items():
            if refs[arm]['phase']=='new':new_rows.extend({**c,'case_id':item['case_id'],'arm':arm} for c in s['calls'])
        write_cost_checkpoint(root,item,{'retained_charges':RETAINED,'new_charged_calls':sum(c['charged_reasoning'] for c in new_rows),'cumulative_charges':budget.used,'remaining_allowance':budget.remaining})
    admitted=admit_calls([{**c,'case_id':c['case_id'],'arm':c['arm']} for c in manifest['calls']]+new_rows,ceiling=CEILING)
    if admitted['charged_calls']!=budget.used:raise ValueError('Cumulative charge ledger does not reconcile')
    truth=load(root/'truth.json');score=score_rows(truth,rows_from_units(units,data_class='empirical',evidence_root=root),format_version='m3b-score.1',data_class='empirical')
    result={'format_version':'m3b-campaign.2','data_class':'empirical','synthetic':False,'empirical_admissible':True,'execution_finished':True,
        'protocol_sha256':protocol['protocol_sha256'],'parent_protocol_sha256':OLD_PROTOCOL,'continuation_manifest_sha256':digest(manifest),
        'retained_charged_calls':RETAINED,'new_charged_calls':budget.used-RETAINED,'hosted_calls':budget.used,
        'units':units,'truth':truth,'score':score,'scheduled_units':6,'completed_units':len(units),
        'invalid_response_arms':sum(o=='invalid_response' for u in units for o in u['matrix']['terminal_outcomes'].values()),
        'isolation_qualified':True,'scientific_complete':False,'limits':['Execution completion does not establish complete semantic coverage or acceptance.','Six dependent variants of one pair; invalid responses and incomplete pairs remain explicit.']}
    result['files']={p.relative_to(root).as_posix():hashfile(p) for p in root.rglob('*') if p.is_file()}
    result['campaign_sha256']=digest(result);write(root/'campaign.json',result);return result


def inspect_retained_parent(tree):
    from intentlineage.native_capture import ROOT
    manifest=build_continuation_manifest(ROOT,evidence_root=tree)
    completed=[u['unit_id'] for u in manifest['units']]
    interrupted=sorted({s['unit_id'] for s in manifest['sessions']}-set(completed))
    return {'synthetic':False,'incomplete':True,'protocol_sha256':OLD_CAMPAIGN_PROTOCOL,
        'completed_units':completed,'interrupted_units':interrupted,
        'unstaged_units':sorted({s['unit_id'] for s in manifest['schedule']}-set(completed)-set(interrupted)),
        'calls_recorded':RETAINED,'logical_calls_known':RETAINED,'unknown_attempts':0,'unknown_invocations':[],
        'score':None,'limits':['Interrupted invocations have unknown charging/results; no session resumes and no semantic score is manufactured.'],
        'data_class':'empirical','empirical_admissible':False}


def inspect_interrupted_continuation(tree):
    from intentlineage.experiment_execution import validate_execution_contract
    tree=Path(tree);p=load(tree/'protocol.json');validate_execution_contract(**p['execution_contract'],evidence_root=tree)
    if p['protocol_sha256']!=digest({k:v for k,v in p.items() if k!='protocol_sha256'}):raise ValueError('Interrupted amended protocol seal differs')
    manifest=load(tree/'continuation-manifest.json')
    if digest(manifest)!=p['execution_contract']['protocol']['continuation']['manifest_sha256']:raise ValueError('Interrupted retained-manifest binding differs')
    completed=[u.name for u in tree.glob('units/*') if (u/'unit.json').exists()]
    interrupted=[u.name for u in tree.glob('units/*') if not (u/'unit.json').exists()]
    new_calls=[load(c) for c in tree.glob('units/**/calls/*/call.json')]
    unknown=[i.relative_to(tree).as_posix() for i in tree.glob('units/**/calls/*/invocation') if not (i.parent/'call.json').exists()]
    count=sum(c['charged_reasoning'] for c in new_calls)
    if RETAINED+count>CEILING:raise ValueError('Interrupted cumulative ceiling exceeded')
    return {'data_class':'empirical','synthetic':False,'empirical_admissible':False,'incomplete':True,'protocol_sha256':p['protocol_sha256'],
        'completed_units':completed,'interrupted_units':interrupted,'unstaged_units':sorted({s['unit_id'] for s in manifest['schedule']}-set(completed)-set(interrupted)),
        'retained_calls':RETAINED,'new_calls_recorded':len(new_calls),'calls_recorded':RETAINED+len(new_calls),'logical_calls_known':RETAINED+count,
        'unknown_attempts':len(unknown),'unknown_invocations':unknown,'score':None,
        'limits':['Unknown staged attempts remain unknown; no reviewer conversation resumes or fabricated score.']}


def replay_continuation(tree):
    from intentlineage.native_capture import ROOT
    from intentlineage.experiment_execution import validate_execution_contract
    from intentlineage.experiment_scoring import rows_from_units,score_rows
    tree=Path(tree);result=load(tree/'campaign.json')
    if result['campaign_sha256']!=digest({k:v for k,v in result.items() if k!='campaign_sha256'}):raise ValueError('Amended campaign seal differs')
    actual={p.relative_to(tree).as_posix() for p in tree.rglob('*') if p.is_file()}-{'campaign.json'}
    if actual!=set(result['files']):raise ValueError('Amended campaign exact membership differs')
    for name,sha in result['files'].items():
        if hashfile(tree/name)!=sha:raise ValueError('Amended campaign evidence hash differs: '+name)
    p=load(tree/'protocol.json')
    if p['protocol_sha256']!=digest({k:v for k,v in p.items() if k!='protocol_sha256'}) or p['protocol_sha256']!=result['protocol_sha256']:raise ValueError('Amended campaign protocol differs')
    validate_execution_contract(**p['execution_contract'],evidence_root=tree)
    manifest=load(tree/'continuation-manifest.json')
    validate_retained_manifest(ROOT,manifest,evidence_root=tree/'retained/campaign')
    if result['scheduled_units']!=6 or result['completed_units']!=6 or [u['unit_id'] for u in result['units']]!=[s['unit_id'] for s in manifest['schedule']]:raise ValueError('Amended campaign schedule coverage differs')
    rows=[]
    for unit in result['units']:
        folder=tree/unit['directory']
        if load(folder/'unit.json')!=unit or load(folder/'matrix.json')!=unit['matrix']:raise ValueError('Amended unit/matrix file differs')
        replay_composite_unit(tree,unit)
        for arm,s in unit['matrix']['sessions'].items():
            rows.extend({**c,'case_id':unit['case_id'],'arm':arm} for c in s['calls'])
    admitted=admit_calls(rows,ceiling=CEILING)
    if admitted['charged_calls']!=result['hosted_calls'] or result['retained_charged_calls']!=RETAINED or result['new_charged_calls']!=admitted['charged_calls']-RETAINED:raise ValueError('Amended cumulative accounting differs')
    truth=load(tree/'truth.json')
    if truth!=result['truth'] or digest(truth)!=p['truth_sha256']:raise ValueError('Amended truth binding differs')
    score=score_rows(truth,rows_from_units(result['units'],data_class='empirical',evidence_root=tree),format_version='m3b-score.1',data_class='empirical')
    if score!=result['score']:raise ValueError('Amended actual score does not recompute')
    if sum(o=='invalid_response' for u in result['units'] for o in u['matrix']['terminal_outcomes'].values())!=result['invalid_response_arms']:raise ValueError('Invalid-response coverage differs')
    return result
