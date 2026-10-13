"""User-bound function-review profile; stdlib authority can run in native gate.

Heavy existing harness imports occur only inside host validation functions. No
provider, selector, parallel runner or independent scorer is implemented here.
"""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

FORMAT='m3b-chatgpt-function-protocol.1'
BRIEF='m3-function-review-brief-20261013.md'
BRIEF_SHA='a16a6be3f2402c0fb0c9ee070fb9ef2b8e37d84338d1709c359e2e392fa0793b'
COMPLETION_SHA='93d0284e31f84f9014243913c9f893ca64e5485d9a0b026d378ae171a0e0bcfe'
BASE='resources/evidence/archive/m3-function-base-378c855'
BASE_SHA='7d6639fff31ac840ee65cb3b8be622b4c5592d2fec61f81f837b306b20b508d9'
PROFILE='resources/protocol/m3-function-profile.json'
PROFILE_SHA='8701657b4a8c8ea0351ea30cf5cdb1c75b16a0e586771bac29132047049ac6ae'
REVIEW_SHA='764429151e8bed3d76087423720aefb8b22e939235dd299d96c3c49963408154'
CAPTURE_SHA='1c7ad0cec61cc6564553f6b8ddbf123e4b25863039e201d6e7a79ecc5c56eb66'
FUNCTIONS={
 'src/intentlineage/review_runner.py':{'_Session.__init__','_Session.review','_Session.finish','_run_treatment','replay_session','run_review_matrix','replay_matrix'},
 'src/intentlineage/experiment_chatgpt.py':{'validate_chatgpt_protocol','chatgpt_event_facts','chatgpt_qualification_request','chatgpt_qualification_contract','run_chatgpt_invocation','qualify_chatgpt_provider','validate_chatgpt_qualification'},
 'src/intentlineage/experiment_protocol.py':{'validate_execution_protocol'},
 'src/intentlineage/experiment_qualification.py':{'validate_provider_qualification'},
 'src/intentlineage/experiment_campaign.py':{'run_campaign','replay_campaign','validate_bank_selection'},
 'src/intentlineage/experiment_scoring.py':{'rows_from_units','_outcome'},
 'src/intentlineage/experiment_user_authorization.py':{'validate_source_authorization','capture_authorized_launch','qualification_brief_sha256','_fixed_binding','user_campaign_record','validate_user_campaign_record'},
 'scripts/m3b.py':{'main'},
 'scripts/audit_m3b.py':{'audit_sources'},
 'scripts/audit_m3a.py':{'audit'},
}


def _digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _hash(path):
 path=Path(path)
 for p in [path,*path.parents]:
  if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:raise ValueError('Function authority/source link refused')
 return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Duplicate function contract key')
   d[k]=v
  return d
 def nonfinite(v):raise ValueError('Nonfinite contract')
 value=json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=nonfinite);_digest(value);return value


def profile(root):
 value=_load(Path(root)/PROFILE)
 if _digest(value)!=PROFILE_SHA:raise ValueError('Exact function profile/input/bank policy changed')
 return value


def _protected(raw,names):
 tree=ast.parse(raw);found=set();spans=[]
 def visit(body,prefix=''):
  for n in body:
   if isinstance(n,ast.ClassDef):visit(n.body,prefix+n.name+'.')
   elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and prefix+n.name in names:
    found.add(prefix+n.name);spans.append((n.body[0].lineno-1,n.end_lineno));n.body=[ast.Pass()]
 visit(tree.body)
 if found!=names:raise ValueError('Function extension membership changed')
 lines=raw.decode().replace('\r\n','\n').splitlines(keepends=True)
 for first,last in sorted(spans,reverse=True):lines[first:last]=['<authorized-function-body>\n']
 return ast.dump(tree,include_attributes=False),''.join(lines)


def source_authorization(root):
 if (Path(root)/'resources/evidence/archive/m3-response-base-6392862').exists():
  import importlib.util
  spec=importlib.util.spec_from_file_location("response_authority",Path(root)/"src/intentlineage/experiment_resume.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.source_authorization(root)
 root=Path(root);main=root.parent.parent/'instructions_between_agents';archive=root/BASE
 if _hash(main/BRIEF)!=BRIEF_SHA or _hash(archive/'function-brief.md')!=BRIEF_SHA:raise ValueError('Actual function-review user instruction changed')
 if _hash(main/'m3b-qualification-code-overseer-review.md')!=REVIEW_SHA:raise ValueError('Original reviewed ancestry changed')
 if _hash(main/'m3-event-capture-disposition-20261013.md')!=CAPTURE_SHA:raise ValueError('Capture disposition changed')
 if _hash(main/'m3-auto-run-after-qualification-20261013.md')!='5041950d266dab3339fc643cd3f8e0ec35b1c2925ea83464e469bde2b8e1ef6d':raise ValueError('Actual automatic continuation changed')
 baseline=_load(archive/'source-manifest.json')
 if _digest(baseline)!=BASE_SHA:raise ValueError('Exact pre-extension source snapshot changed')
 files=list((root/'src/intentlineage').rglob('*.py'))+[root/n for n in ['scripts/m3b.py','scripts/audit_m3b.py','scripts/audit_m3b_execution.py','scripts/capture_m1_v4.py','requirements.txt']]
 current={p.relative_to(root).as_posix():_hash(p) for p in sorted(files)}
 if set(current)-set(baseline)!={'src/intentlineage/review_function.py','src/intentlineage/experiment_function.py'} or set(baseline)-set(current):raise ValueError('Function extension source membership drift')
 for name,sha in baseline.items():
  old=archive/'source'/name
  if _hash(old)!=sha:raise ValueError('Original source archive changed')
  if current[name]==sha:continue
  if name not in FUNCTIONS or _protected(old.read_bytes(),FUNCTIONS[name])!=_protected((root/name).read_bytes(),FUNCTIONS[name]):
   raise ValueError('Unrelated pipeline/auth/isolation/schema/usage source change: '+name)
 return {'issued_by':'user','scope':'versioned-one-function-review-extension','instruction_sha256':BRIEF_SHA,
  'reviewed_source_sha256':'e59da1e101e7763d85fe0d3198c2994c0709d8dc176472260b6a16e8f0ac0a8e',
  'protected_base_source_sha256':BASE_SHA,'reviewed_commit':'f66eac36d247b8e8c0067ca96194ed8e89747d4a',
  'reviewed_launch_sha256':'f93cecd2e881bda6feac876e9346ffaa53051ff4661430282eedef1d3bfb0687',
  'controller_source_sha256':_digest(current),
  'configuration_disposition':{'issued_by':'overseer','scope':'native-event-capture-bound-amendment','sha256':CAPTURE_SHA,'max_output_bytes':33554432}}


def request_records(root):
 value=profile(root);result=[]
 for r in value['qualification_requests']:
  if _hash(Path(root)/r['request_path'])!=r['request_file_sha256'] or _hash(Path(root)/r['controller_evidence_path'])!=r['controller_evidence_file_sha256']:raise ValueError('Bound function qualification input changed')
  request=_load(Path(root)/r['request_path'])
  if _digest(request)!=r['request_sha256']:raise ValueError('Bound endpoint/function request changed')
  result.append((r,request))
 return result


def verify_m2_extension(root):
 """Verify accepted bytes separately from the explicit current runner extension."""
 root=Path(root);interface=_load(root/'resources/evidence/m3a-m2-interface.json')
 record=interface['function_review_extension'];name='src/intentlineage/review_runner.py'
 binding=source_authorization(root)
 expected={'issued_by':'user','instruction_sha256':BRIEF_SHA,'path':name,
  'accepted_sha256':interface['files'][name],'archive':BASE+'/source/'+name,
  'current_sha256':_hash(root/name),'session_version':'m3-function-session.1',
  'matrix_version':'m3-function-matrix.1','original_formats_preserved':True}
 if (root/'resources/evidence/archive/m3-response-base-6392862').exists():
  from .experiment_resume import BRIEF_SHA as RESPONSE_BRIEF
  expected.update(instruction_sha256=RESPONSE_BRIEF,session_version='m3-function-session.2',matrix_version='m3-function-matrix.2')
 if record!=expected or _hash(root/record['archive'])!=record['accepted_sha256']:raise ValueError('Accepted/current M2 extension provenance differs')
 for path,sha in interface['files'].items():
  if path!=name and _hash(root/path)!=sha:raise ValueError('Other accepted M2 source changed: '+path)
 return record


def qualification_request(root,index):
 from .review_function import build_request
 r,request=request_records(root)[index]
 evidence=_load(Path(root)/r['controller_evidence_path'])
 rebuilt=build_request(evidence,model=request['model'],settings=request['settings'],allow_opening=False)
 if rebuilt!=request:raise ValueError('Compact qualification view/guidance replay differs')
 return request


def qualification_contract(root,protocol):
 if protocol.get('format_version')=='m3b-chatgpt-function-protocol.2':
  import importlib.util
  spec=importlib.util.spec_from_file_location("response_authority",Path(root)/"src/intentlineage/experiment_resume.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.qualification_contract(root,protocol)
 p=profile(root)['candidate'];actual=deepcopy(protocol);actual['bindings']['controller_source_sha256']=None
 if actual!=p:raise ValueError('Exact updated qualification model/settings/bounds differ')
 if protocol['bindings']['controller_source_sha256']!=source_authorization(root)['controller_source_sha256']:raise ValueError('Exact function qualification source binding missing')
 records=request_records(root)
 return {'scope':'chatgpt-function-provider-qualification','data_class':'empirical','user_brief_sha256':BRIEF_SHA,
  'reviewer':deepcopy(p['reviewer']),'limits':deepcopy(p['limits']),'observability':deepcopy(p['observability']),
  'function_review':deepcopy(p['function_review']),'profile_sha256':PROFILE_SHA,
  'qualification_inputs':[deepcopy(r) for r,request in records],
  'transport_framing':'unchanged native reply_json envelope and original M2 schema plus declared concise checks'}


def authorize_launch(root,contract,decision):
 if contract.get('response_policy'):
  import importlib.util
  spec=importlib.util.spec_from_file_location("response_authority",Path(root)/"src/intentlineage/experiment_resume.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.authorize_launch(root,contract,decision)
 binding=source_authorization(root)
 if (decision.get('issued_by')!='overseer' or decision.get('status')!='approved' or decision.get('synthetic') is not False
  or decision.get('controller_source_sha256')!=binding['reviewed_source_sha256'] or decision.get('qualification_launch_sha256')!=binding['reviewed_launch_sha256']):raise ValueError('Actual original reviewed source/decision differs')
 p=deepcopy(profile(root)['candidate']);p['bindings']['controller_source_sha256']=binding['controller_source_sha256']
 if contract!=qualification_contract(root,p):raise ValueError('Function qualification inputs/guidance/settings drift')
 return {**binding,'authorized_launch_sha256':_digest(contract),'profile_sha256':PROFILE_SHA}


def frozen_candidate(root,qualification):
 if (Path(root)/'resources/protocol/m3-response-continuation.json').exists():
  import importlib.util
  spec=importlib.util.spec_from_file_location("response_authority",Path(root)/"src/intentlineage/experiment_resume.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.frozen_candidate(root,qualification)
 p=deepcopy(profile(root)['candidate']);p['status']='frozen';p['reviewer']=deepcopy(qualification['reviewer'])
 p['bindings'].update(controller_source_sha256=source_authorization(root)['controller_source_sha256'],qualification_sha256=qualification['qualification_sha256'],model_metadata=deepcopy(qualification['model_metadata']))
 return p


def user_record(root,protocol,qualification,gate):
 if protocol.get('format_version')=='m3b-chatgpt-function-protocol.2':
  import importlib.util
  spec=importlib.util.spec_from_file_location("response_authority",Path(root)/"src/intentlineage/experiment_resume.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.user_record(root,protocol,qualification,gate)
 if gate not in {'real_path_review','protocol_review','experiment_authorization'}:raise ValueError('Unknown function campaign gate')
 binding=source_authorization(root);q=qualification;p=profile(root)['candidate']
 if (type(q) is not dict or q.get('qualified') is not True or q.get('synthetic') is not False or q.get('data_class')!='empirical'
  or q.get('controller_source_sha256')!=binding['controller_source_sha256'] or q.get('qualification_sha256')!=_digest({k:v for k,v in q.items() if k!='qualification_sha256'})):
  raise ValueError('Actual new qualification/source/seal required')
 if protocol!=frozen_candidate(root,q):raise ValueError('Exact fixed function campaign changed')
 expected=deepcopy(p['reviewer']);expected['client_effective_model']='gpt-5.5'
 if q.get('reviewer')!=expected or q.get('model_metadata')!=p['bindings']['model_metadata']:raise ValueError('Fixed model/CLI/settings changed')
 calls=q.get('calls',[])
 if len(calls)!=2 or len({c.get('thread_id') for c in calls})!=2 or [c.get('request_sha256') for c in calls]!=[r['request_sha256'] for r in profile(root)['qualification_requests']]:raise ValueError('Distinct endpoint/function fresh qualification required')
 if any(c.get('logical_calls')!=1 for c in calls) or not all(q.get('probes',{}).values()) or len(q.get('probes',{}))!=14 or q.get('history_policy')!='none':raise ValueError('Qualification counters/native controls missing')
 if q.get('fresh_sessions') is not True or q.get('credential_model_access')!='denied' or q.get('model_command_network')!='denied':raise ValueError('Fresh credential/tool/network separation missing')
 return {'kind':'observed_user_authorization','issued_by':'user','status':'authorized','synthetic':False,
  'scope':'user-authorized-fixed-function-m3','gate':gate,'path':BASE+'/function-brief.md','sha256':BRIEF_SHA,
  'controller_source_sha256':binding['controller_source_sha256'],'protected_base_source_sha256':BASE_SHA,
  'profile_sha256':PROFILE_SHA,'protocol_sha256':_digest(protocol),'qualification_sha256':q['qualification_sha256']}


def validate_user_record(root,record,gate,protocol,qualification,evidence_root):
 if protocol.get('format_version')=='m3b-chatgpt-function-protocol.2':
  import importlib.util
  spec=importlib.util.spec_from_file_location("response_authority",Path(root)/"src/intentlineage/experiment_resume.py")
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  return module.validate_user_record(root,record,gate,protocol,qualification,evidence_root)
 try:return record==user_record(root,protocol,qualification,gate) and _hash(Path(evidence_root)/BASE/'function-brief.md')==BRIEF_SHA
 except (ValueError,OSError,KeyError,TypeError):return False


def validate_protocol(protocol,*,require_frozen=False):
 if protocol.get('format_version')=='m3b-chatgpt-function-protocol.2':
  from .experiment_resume import validate_protocol as validate_response_protocol
  return validate_response_protocol(protocol,require_frozen=require_frozen)
 from .native_capture import ROOT
 from .experiment_chatgpt import validate_chatgpt_protocol,CHATGPT_FORMAT,draft_chatgpt_protocol
 p=profile(ROOT)['candidate'];expected=deepcopy(p)
 expected['status']=protocol['status'];expected['bindings']=deepcopy(protocol['bindings']);expected['reviewer']=deepcopy(protocol['reviewer'])
 if protocol!=expected:raise ValueError('Function protocol policy/population/budget changed')
 reviewer=deepcopy(protocol['reviewer']);reviewer['client_effective_model']=None
 if reviewer!=p['reviewer'] or protocol['reviewer']['client_effective_model'] not in {None,'gpt-5.5'}:raise ValueError('Exact function reviewer/model/settings changed')
 if protocol['bindings']['model_metadata']!=p['bindings']['model_metadata']:raise ValueError('Exact model metadata changed')
 if protocol['bindings']['controller_source_sha256'] not in {None,source_authorization(ROOT)['controller_source_sha256']}:raise ValueError('Function protocol source drift')
 # Reuse existing eligibility, CLI/model/auth/settings/bounds/dependency checks.
 base=deepcopy(protocol);base.pop('function_review');base['format_version']=CHATGPT_FORMAT
 original=draft_chatgpt_protocol()
 for key in ['prompts','matrix','common_evidence']:base[key]=deepcopy(original[key])
 check=validate_chatgpt_protocol(base,require_frozen=require_frozen)
 check['protocol_sha256']=_digest(protocol)
 return check
