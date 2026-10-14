"""Explicit user authority for mechanical gates and the fixed M3 continuation.

This supplements, rather than qualifies, provider evidence. The ordinary native
receipt/reply/runtime validators still establish genuine successful qualification.
Only stdlib is used so the trusted native admission boundary can repeat checks.
"""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

REVIEWED_SOURCE = 'e59da1e101e7763d85fe0d3198c2994c0709d8dc176472260b6a16e8f0ac0a8e'
REVIEWED_COMMIT = 'f66eac36d247b8e8c0067ca96194ed8e89747d4a'
REVIEWED_LAUNCH = 'f93cecd2e881bda6feac876e9346ffaa53051ff4661430282eedef1d3bfb0687'
INSTRUCTION_SHA = '5041950d266dab3339fc643cd3f8e0ec35b1c2925ea83464e469bde2b8e1ef6d'
REVIEW_SHA = '764429151e8bed3d76087423720aefb8b22e939235dd299d96c3c49963408154'
ARCHIVE = 'resources/evidence/archive/m3-user-continuation-e59'
DOCUMENT = 'm3-auto-run-after-qualification-20261013.md'
COPY_PATH = 'instructions_between_agents/archive/m3b-user-authorization/' + DOCUMENT
CAPTURE_DOCUMENT = 'm3-event-capture-disposition-20261013.md'
CAPTURE_SHA = '1c7ad0cec61cc6564553f6b8ddbf123e4b25863039e201d6e7a79ecc5c56eb66'
CAPTURE_LIMIT = 33554432
GATES = {'real_path_review', 'protocol_review', 'experiment_authorization'}
PROBES = {'config','environment','home','network','oracle','own_package','private_state','process','readonly','session','sibling','source','symlink','temp'}
GATE_FUNCTIONS = {
    'src/intentlineage/experiment_execution.py': {'validate_execution_decision'},
    'src/intentlineage/experiment_chatgpt.py': {'validate_chatgpt_qualification_review','validate_chatgpt_qualification'},
    'src/intentlineage/_reference/chatgpt_boundary.py': {'_admission'},
}


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _hash(path):
    path=Path(path)
    for p in [path,*path.parents]:
        if p.is_symlink() or getattr(p.lstat(),'st_file_attributes',0)&0x400:
            raise ValueError('Authority/source path link refused')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate authority key')
            result[k]=v
        return result
    def bad(value):raise ValueError('Nonfinite authority value')
    value=json.loads(Path(path).read_bytes(),object_pairs_hook=pairs,parse_constant=bad)
    _digest(value)
    return value


def _protected_ast(raw,names):
    tree=ast.parse(raw)
    found=set()
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name=='chatgpt_qualification_contract':
            # Exactly the two brief-hash expressions and one local import may
            # change; input, model, settings, limits and framing stay protected.
            node.body=[x for x in node.body if not (isinstance(x,ast.ImportFrom) and
                x.module=='experiment_user_authorization' and x.level==1 and
                len(x.names)==1 and x.names[0].name=='qualification_brief_sha256' and x.names[0].asname is None)]
            for call in ast.walk(node):
                if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='qualification_brief_sha256':
                    if [ast.dump(x) for x in call.args]!=[ast.dump(x) for x in ast.parse('f(brief, ROOT)',mode='eval').body.args] or call.keywords:
                        raise ValueError('Brief gate invocation changed')
                    call.func=ast.Name(id='file_hash',ctx=ast.Load());call.args=call.args[:1]
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
            found.add(node.name)
            node.body=[ast.Pass()]
    if found!=names:raise ValueError('Gate function membership changed')
    return ast.dump(tree,include_attributes=False)


def _campaign_ast(raw):
    tree=ast.parse(raw);changed=0
    for node in ast.walk(tree):
        if not isinstance(node,ast.Compare) or len(node.ops)!=1:continue
        expected=ast.parse("record.get('kind')",mode='eval').body
        if ast.dump(node.left)!=ast.dump(expected):continue
        if isinstance(node.ops[0],ast.In) and isinstance(node.comparators[0],ast.Set):
            values={getattr(x,'value',None) for x in node.comparators[0].elts}
            if values=={'observed_overseer_decision','observed_user_authorization'}:
                node.ops=[ast.Eq()];node.comparators=[ast.Constant('observed_overseer_decision')];changed+=1
    if changed>1:raise ValueError('Unexpected campaign gate changes')
    return ast.dump(tree,include_attributes=False)


def validate_source_authorization(root):
    """Only the actual user brief authorizes these narrowly located gate changes."""
    if (Path(root)/'src/intentlineage/experiment_function.py').exists():
        import importlib.util
        spec=importlib.util.spec_from_file_location('function_authority',Path(root)/'src/intentlineage/experiment_function.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.source_authorization(root)
    root=Path(root).resolve(strict=True);archive=root/ARCHIVE
    main=root.parent.parent/'instructions_between_agents'
    if _hash(main/DOCUMENT)!=INSTRUCTION_SHA or _hash(archive/'user-instruction.md')!=INSTRUCTION_SHA:
        raise ValueError('Actual user instruction missing or changed')
    if _hash(main/'m3b-qualification-code-overseer-review.md')!=REVIEW_SHA or _hash(archive/'qualification-review.md')!=REVIEW_SHA:
        raise ValueError('Actual reviewed qualification lineage changed')
    baseline=_load(archive/'source-manifest.json')
    if _digest(baseline)!=REVIEWED_SOURCE:raise ValueError('Reviewed source manifest changed')
    files=list((root/'src/intentlineage').rglob('*.py'))
    files += [root/n for n in ['scripts/m3b.py','scripts/audit_m3b.py','scripts/audit_m3b_execution.py','scripts/capture_m1_v4.py','requirements.txt']]
    current={p.relative_to(root).as_posix():_hash(p) for p in sorted(files)}
    if set(current)-set(baseline) not in (set(),{'src/intentlineage/experiment_user_authorization.py'}) or set(baseline)-set(current):
        raise ValueError('Controller source membership changed outside user gate')
    for name,sha in baseline.items():
        old=archive/'source'/name
        if _hash(old)!=sha:raise ValueError('Reviewed source snapshot altered')
        if current[name]==sha:continue
        original=old.read_bytes();actual=(root/name).read_bytes()
        if name in GATE_FUNCTIONS:
            if _protected_ast(original,GATE_FUNCTIONS[name])==_protected_ast(actual,GATE_FUNCTIONS[name]):continue
        elif name=='src/intentlineage/experiment_campaign.py':
            if _campaign_ast(original)==_campaign_ast(actual):continue
        raise ValueError('Protected client/input/isolation/validation/source behavior changed: '+name)
    contract=_load(archive/'qualification-launch-contract.json')
    if _digest(contract)!=REVIEWED_LAUNCH:raise ValueError('Reviewed launch contract changed')
    candidate=_load(archive/'qualification-settings.json')
    if _digest(candidate)!='a49e7eb1e03a4cb7e7363fa3ed60e124d1075de31bc49172f415675a81663ab0':
        raise ValueError('Fixed candidate changed')
    return {'issued_by':'user','scope':'mechanical-gate-adaptation','instruction_sha256':INSTRUCTION_SHA,
            'reviewed_commit':REVIEWED_COMMIT,'reviewed_source_sha256':REVIEWED_SOURCE,
            'reviewed_launch_sha256':REVIEWED_LAUNCH,'controller_source_sha256':_digest(current),
            'configuration_disposition':capture_disposition_record(root)}


def capture_disposition_record(root):
    """Observe the actual technical disposition; never issue a new approval."""
    root=Path(root)
    main=root.parent.parent/'instructions_between_agents'/CAPTURE_DOCUMENT
    copy_path=ARCHIVE+'/capture-disposition.md'
    if _hash(main)!=CAPTURE_SHA or _hash(root/copy_path)!=CAPTURE_SHA:
        raise ValueError('Actual recorded capture-bound disposition missing or changed')
    return {'kind':'observed_overseer_decision','issued_by':'overseer','synthetic':False,
            'scope':'native-event-capture-bound-amendment','status':'observed_configuration_disposition',
            'path':copy_path,'sha256':CAPTURE_SHA,'provenance':CAPTURE_DOCUMENT,'max_output_bytes':CAPTURE_LIMIT}


def capture_authorized_launch(root,contract,decision):
    if contract.get('scope')=='chatgpt-single-provider-qualification':
        root=Path(root)
        files=list((root/'src/intentlineage').rglob('*.py'))+[root/n for n in ['scripts/m3b.py','scripts/audit_m3b.py','scripts/audit_m3b_execution.py','scripts/capture_m1_v4.py','requirements.txt']]
        current=_digest({p.relative_to(root).as_posix():_hash(p) for p in sorted(files)})
        if (decision.get('format_version')!='m3b-qualification-code-review.1' or decision.get('issued_by')!='overseer'
            or decision.get('status')!='approved' or decision.get('synthetic') is not False
            or decision.get('controller_source_sha256')!=current or contract.get('controller_source_sha256')!=current
            or decision.get('qualification_launch_sha256')!=_digest(contract)):
            raise ValueError('New exact single-review Overseer qualification decision required')
        return {'issued_by':'overseer','controller_source_sha256':current,'authorized_launch_sha256':_digest(contract)}
    if contract.get('scope')=='chatgpt-function-provider-qualification':
        import importlib.util
        spec=importlib.util.spec_from_file_location('function_authority',Path(root)/'src/intentlineage/experiment_function.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.authorize_launch(root,contract,decision)
    binding=validate_source_authorization(root)
    if (decision.get('format_version')!='m3b-qualification-code-review.1' or decision.get('issued_by')!='overseer'
        or decision.get('status')!='approved' or decision.get('synthetic') is not False
        or decision.get('commit')!=REVIEWED_COMMIT or decision.get('controller_source_sha256')!=REVIEWED_SOURCE
        or decision.get('qualification_launch_sha256')!=REVIEWED_LAUNCH):
        raise ValueError('Original reviewed source/launch decision differs')
    expected=_load(Path(root)/ARCHIVE/'qualification-launch-contract.json')
    expected['limits']['max_output_bytes']=CAPTURE_LIMIT
    if contract!=expected:raise ValueError('Capture disposition authorizes only exactly 32 MiB amendment')
    return {**binding['configuration_disposition'],'reviewed_launch_sha256':REVIEWED_LAUNCH,
            'authorized_launch_sha256':_digest(contract),'controller_source_sha256':binding['controller_source_sha256']}


def qualification_brief_sha256(path,root):
    original='e777cf27d9c136102960717290f9444e8004300e5bce78539a15f3db7490f89b'
    actual=_hash(path)
    if actual=='93d0284e31f84f9014243913c9f893ca64e5485d9a0b026d378ae171a0e0bcfe':
        if _hash(Path(root)/'resources/evidence/archive/m3-function-base-378c855/completion-brief.md')!=actual:raise ValueError('Exact function completion amendment changed')
        validate_source_authorization(root)
        return original
    if actual==original:return original
    amended='df7bf4f37e947a11d0073aab9658a9f7695112d416594747b68a7b9f9ed13744'
    archive=Path(root)/ARCHIVE
    capture_amended='15eda15969c5fe2dd96bf7c16d86096ff39a4237890d653cb015eb5be9f7ce5a'
    if actual==capture_amended:
        if _hash(archive/'completion-brief-capture-override.md')!=capture_amended or _hash(archive/'completion-brief-user-override.md')!=amended or _hash(archive/'completion-brief-reviewed.md')!=original:
            raise ValueError('Exact capture amendment brief lineage changed')
        validate_source_authorization(root)
        return original
    if actual!=amended or _hash(archive/'completion-brief-reviewed.md')!=original or _hash(archive/'completion-brief-user-override.md')!=amended:
        raise ValueError('Completion brief drift outside exact user amendment')
    validate_source_authorization(root)
    return original


def _fixed_binding(root,protocol,qualification):
    authority=validate_source_authorization(root);q=qualification
    if type(q) is not dict or q.get('format_version')!='m3b-chatgpt-qualification.1' or q.get('data_class')!='empirical' or q.get('synthetic') is not False or q.get('qualified') is not True:
        raise ValueError('Successful real qualification required')
    if q.get('qualification_sha256')!=_digest({k:v for k,v in q.items() if k!='qualification_sha256'}):
        raise ValueError('Qualification seal changed')
    if q.get('controller_source_sha256')!=authority['controller_source_sha256']:
        raise ValueError('Qualified source changed')
    if q.get('history_policy')!='none' or q.get('fresh_sessions') is not True or q.get('credential_model_access')!='denied' or q.get('model_command_network')!='denied':
        raise ValueError('Qualification isolation/history controls missing')
    if set(q.get('probes',{}))!=PROBES or any(v is not True for v in q['probes'].values()):
        raise ValueError('Qualification native controls missing')
    calls=q.get('calls',[])
    if len(calls)!=2 or len({c.get('thread_id') for c in calls})!=2 or any(not c.get('thread_id') or c.get('logical_calls')!=1 or c.get('request_sha256')!='f719f047431f22b02451406a78e5f98585d6d7cbbf93e826a49e83c0374fdf8b' for c in calls):
        raise ValueError('Two fresh real-endpoint qualification calls required')
    expected=_load(Path(root)/ARCHIVE/'qualification-settings.json')
    expected['limits']['max_output_bytes']=CAPTURE_LIMIT
    expected['status']='frozen'
    expected['bindings']['controller_source_sha256']=authority['controller_source_sha256']
    expected['bindings']['qualification_sha256']=q['qualification_sha256']
    expected['reviewer']['client_effective_model']='gpt-5.5'
    if protocol!=expected or q.get('reviewer')!=expected['reviewer'] or q.get('model_metadata')!=expected['bindings']['model_metadata']:
        raise ValueError('Fixed campaign source/bank/model/settings/bounds changed')
    return authority


def _record(root,protocol,qualification,gate):
    if gate not in GATES:raise ValueError('Unknown user continuation gate')
    authority=_fixed_binding(root,protocol,qualification)
    return {'kind':'observed_user_authorization','issued_by':'user','synthetic':False,
            'status':'authorized','scope':'user-authorized-fixed-m3','gate':gate,
            'path':COPY_PATH,'sha256':INSTRUCTION_SHA,'provenance':DOCUMENT,
            'controller_source_sha256':authority['controller_source_sha256'],
            'reviewed_source_sha256':REVIEWED_SOURCE,'reviewed_commit':REVIEWED_COMMIT,
            'configuration_disposition':authority['configuration_disposition'],
            'protocol_sha256':_digest(protocol),'qualification_sha256':qualification['qualification_sha256']}


def user_campaign_record(root,protocol,qualification,gate):
    if protocol.get('format_version') in {'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}:
        import importlib.util
        spec=importlib.util.spec_from_file_location('function_authority',Path(root)/'src/intentlineage/experiment_function.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.user_record(root,protocol,qualification,gate)
    record=_record(root,protocol,qualification,gate)
    target=Path(root)/COPY_PATH;target.parent.mkdir(parents=True,exist_ok=True)
    original=Path(root)/ARCHIVE/'user-instruction.md'
    if target.exists():
        if _hash(target)!=INSTRUCTION_SHA:raise ValueError('Archived user authority changed')
    else:
        with target.open('xb') as stream:stream.write(original.read_bytes())
    return record


def validate_user_campaign_record(root,record,gate,protocol,qualification,*,evidence_root):
    if protocol.get('format_version') in {'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}:
        import importlib.util
        spec=importlib.util.spec_from_file_location('function_authority',Path(root)/'src/intentlineage/experiment_function.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.validate_user_record(root,record,gate,protocol,qualification,evidence_root)
    try:
        return (record==_record(root,protocol,qualification,gate) and _hash(Path(evidence_root)/COPY_PATH)==INSTRUCTION_SHA
                and _hash(Path(evidence_root)/ARCHIVE/'capture-disposition.md')==CAPTURE_SHA)
    except (ValueError,OSError,KeyError,TypeError):return False
