"""Bound provider-control-plane contracts; no reviewer loop or assessor."""
from copy import deepcopy
import json
from pathlib import Path
import re

from .native_capture import ROOT, digest, file_hash
from .review_contract import canonical_bytes, _strict_load
from .experiment_protocol import MODEL_ALLOWLIST
from .review_provider import extract_usage, _usage_candidates
from .review_usage import normalize_usage

DECISION_FILES={
    'real_path_review':'m3b-real-path-overseer-review.md',
    'protocol_review':'m3b-protocol-overseer-review.md',
    'experiment_authorization':'m3b-campaign-overseer-release.md',
}

EXECUTION_BRIEF_SHA256='2cb7a4941ca85e6de362ab36f19f54a07225875c62fadbee402326ed00fce78a'


def controller_sources():
    files=list((ROOT/'src/intentlineage').rglob('*.py'))
    files+=[ROOT/'scripts/m3b.py',ROOT/'scripts/audit_m3b.py',ROOT/'scripts/audit_m3b_execution.py',ROOT/'scripts/capture_m1_v4.py',ROOT/'requirements.txt']
    return {p.relative_to(ROOT).as_posix():file_hash(p) for p in sorted(files)}


def controller_source_digest():
    return digest(controller_sources())


def validate_provider_request(body, own_request, *, max_output_tokens):
    """One frozen own prompt/model; broker imposes the actual API output cap.

    Credentials remain in the human's control plane. This validator neither
    contacts the API nor treats an arbitrary declaration as a qualified launch.
    """
    if type(body) is not dict or type(max_output_tokens) is not int or max_output_tokens<1:
        raise ValueError('Provider body/output limit must be explicit')
    if own_request['model'] not in MODEL_ALLOWLIST['api_key'] or body.get('model')!=own_request['model']:
        raise ValueError('Provider request model differs from the eligible frozen model')
    if body.get('reasoning',{}).get('effort')!=own_request['settings'].get('reasoning_effort'):
        raise ValueError('Provider reasoning settings differ from the sealed request')
    if body.get('tools') not in (None,[]) or body.get('stream') is not True:
        raise ValueError('Only streamed assessment without provider tools is admissible')
    if any(body.get(key) is not None for key in ['previous_response_id','conversation']):
        raise ValueError('Provider inherited/resumed conversation is forbidden')
    inputs=body.get('input')
    if type(inputs) is not list:raise ValueError('Provider input must be explicit messages')
    messages=[m for m in inputs if type(m) is dict and m.get('role')=='user']
    if len(messages)!=1 or any(type(m) is not dict or m.get('role') not in {'user','system','developer'} for m in inputs):
        raise ValueError('Exactly one fresh user request; no prior answers or tool results')
    content=messages[0].get('content')
    if type(content) is list:
        if any(type(p) is not dict or p.get('type')!='input_text' or type(p.get('text')) is not str for p in content):
            raise ValueError('Only the sealed textual request is allowed')
        content='\n'.join(p['text'] for p in content)
    expected=canonical_bytes(own_request).decode('utf-8')
    if type(content) is not str or content.count(expected)!=1:
        raise ValueError('Provider prompt is not bound to the own sealed request')
    bounded=deepcopy(body);bounded.update(max_output_tokens=max_output_tokens,store=False)
    return bounded


def validate_execution_decision(record,gate,protocol,qualification,*,evidence_root=ROOT):
    """Require the actual separate Overseer checkout's recognized Markdown.

    Developer JSON/booleans and arbitrary paths cannot issue authority. Future
    decisions use the documented fenced contract with exact source/protocol/probe
    bindings; missing external documents leave a real gate naturally closed.
    """
    if gate not in DECISION_FILES or type(record) is not dict:return False
    single=protocol.get('format_version')=='m3b-chatgpt-single-protocol.1'
    if single and record.get('kind')=='observed_user_authorization':return False
    if record.get('kind')=='observed_user_authorization':
        from .experiment_user_authorization import validate_user_campaign_record
        return validate_user_campaign_record(ROOT,record,gate,protocol,qualification,evidence_root=evidence_root)
    try:
        filename=DECISION_FILES[gate].replace('m3b-','m3-single-') if single else DECISION_FILES[gate]
        authority=ROOT.parent.parent/'instructions_between_agents'/filename
        expected_path='instructions_between_agents/archive/m3b-execution-decisions/'+filename
        if record.get('kind')!='observed_overseer_decision' or record.get('path')!=expected_path:return False
        from .experiment_isolation import _check_tree
        _check_tree(authority)
        copied=Path(evidence_root)/expected_path;_check_tree(copied)
        if authority.is_symlink() or copied.is_symlink():return False
        if file_hash(authority)!=record.get('sha256') or file_hash(copied)!=record['sha256']:return False
        blocks=re.findall(r'```intentlineage-overseer-decision\r?\n(.*?)\r?\n```',authority.read_text(encoding='utf-8'),re.S)
        if len(blocks)!=1:return False
        decision=_strict_load(blocks[0])
        if decision.get('format_version')!='m3b-overseer-decision.1' or decision.get('gate')!=gate:return False
        if decision.get('issued_by')!='overseer' or decision.get('status')!='approved' or decision.get('synthetic') is not False:return False
        if decision.get('controller_source_sha256')!=controller_source_digest():return False
        if decision.get('protocol_sha256')!=digest(protocol):return False
        if decision.get('qualification_sha256')!=(qualification or {}).get('qualification_sha256'):return False
        if decision.get('scope')!='actual-provider-campaign' or decision.get('commit')!=record.get('commit'):return False
        # The human decision must refer to an actual existing reviewed ancestor.
        import subprocess
        if subprocess.run(['git','merge-base','--is-ancestor',decision['commit'],'HEAD'],cwd=ROOT,capture_output=True).returncode:return False
        return True
    except (KeyError,ValueError,OSError,TypeError):return False


def validate_execution_contract(protocol=None,gates=None,qualification=None,*,evidence_root=ROOT):
    if type(protocol) is dict and protocol.get('format_version')=='m3b-chatgpt-scheduled-protocol.1':
        from .experiment_scheduled import validate_execution_contract as scheduled
        return scheduled(protocol,gates,qualification,evidence_root=evidence_root)
    from .experiment_preflight import execution_preflight
    check=execution_preflight(protocol,gates,qualification,evidence_root=evidence_root)
    if not check['ready']:
        raise ValueError('Execution protocol/qualification/authority release missing: '+', '.join(check['blockers']))
    return {'protocol':deepcopy(protocol),'gates':deepcopy(gates),'qualification':deepcopy(qualification),
            'check':check,'protocol_sha256':digest(protocol)}


def provider_event_facts(raw,status,own_request,expected_actual_model):
    """Bind streamed transport facts; all token interpretation is accepted M2."""
    models=[];usage=[];errors=[];completed=[];events=[]
    if len(raw)>8*1024*1024:errors.append('Provider response exceeded bounded raw capture')
    try:lines=raw.decode('utf-8').splitlines()
    except UnicodeError:lines=[];errors.append('Invalid provider event encoding')
    for line in lines:
        if not line.startswith('data: '):continue
        if line[6:]=='[DONE]':continue
        try:
            event=_strict_load(line[6:]);events.append(event);response=event.get('response',{})
            if response.get('model'):models.append(response['model'])
            if response.get('usage') is not None:usage.append(response['usage'])
            if event.get('type') in {'error','response.failed','response.incomplete'}:errors.append(event['type'])
            if event.get('type')=='response.completed':completed.append(response)
            items=response.get('output',[])+([event['item']] if 'item' in event else [])
            if any(item.get('type') not in {'message','reasoning'} for item in items):errors.append('Unexpected provider tool/command output')
        except (ValueError,TypeError,AttributeError):errors.append('Malformed provider event')
    if expected_actual_model is None:
        if any(model not in MODEL_ALLOWLIST['api_key'] or not (model==own_request['model'] or model.startswith(own_request['model']+'-20')) for model in models):
            errors.append('Actual provider model exceeds ceiling or differs from requested family')
    elif any(model!=expected_actual_model for model in models):errors.append('Actual provider model differs')
    if len(completed)!=1 or completed[0].get('status')!='completed':errors.append('Exact provider completion unavailable')
    if len(set(models))!=1:errors.append('Unknown or mixed actual provider model')
    if status!=200:errors.append('Provider HTTP failure')
    observation=extract_usage(events)
    if observation['usage_observation']['errors']:errors.append('Malformed/conflicting raw API usage')
    return {'actual_models':models,'usage_raw':usage,'errors':errors,'completion_events':len(completed),
        'observed_actual_model':models[0] if models and len(set(models))==1 else None,
        'usage_observation':observation['usage_observation']}


class CredentialBroker:
    """One bound CLI-to-provider exchange, outside the reviewer namespace.

    This is credential/transport mediation, not a model runner. An injected
    upstream is supported only as explicitly recorded test data. Actual requests
    require a validated release; the human qualification bootstrap is separate.
    No credential/header is persisted into reviewer or exported evidence.
    """
    def __init__(self,own_request,*,api_key,output_dir,max_output_tokens,max_input_bytes,
                 recorded_contract=False,upstream=None,execution_contract=None,qualification_contract=None,
                 max_input_tokens=None,token_counter=None):
        if type(recorded_contract) is not bool or type(api_key) is not str or not api_key:
            raise ValueError('Explicit private provider credential and scope required')
        for value in [max_output_tokens,max_input_bytes]:
            if type(value) is not int or value<1:raise ValueError('Explicit provider limits required')
        if recorded_contract:
            if not callable(upstream):raise ValueError('Recorded broker requires an explicit local fixture upstream')
        else:
            if upstream is not None:raise ValueError('Injected/fake upstream cannot become empirical')
            if execution_contract is not None:validate_execution_contract(**execution_contract)
            elif qualification_contract is not None:validate_qualification_launch_contract(qualification_contract)
            else:raise ValueError('Actual broker requires qualification launch or campaign authority')
        self.own_request=deepcopy(own_request);self._key=api_key;self._upstream=upstream
        self.root=Path(output_dir);self.root.mkdir(parents=True,exist_ok=False)
        self.max_output_tokens=max_output_tokens;self.max_input_bytes=max_input_bytes
        if max_input_tokens is not None and (type(max_input_tokens) is not int or max_input_tokens<1):raise ValueError('Invalid provider input token limit')
        if token_counter is not None and not recorded_contract:raise ValueError('Injected token counts cannot qualify an actual provider')
        if recorded_contract and max_input_tokens is not None and not callable(token_counter):
            raise ValueError('Recorded token budgets require an explicit local counter; no hosted fallback')
        if not recorded_contract and max_input_tokens is None:raise ValueError('Actual provider requires a pre-reasoning input token cap')
        self.max_input_tokens=max_input_tokens;self._token_counter=token_counter
        self.recorded_contract=recorded_contract;self.forwarded_requests=0;self.received_requests=0
        self.expected_actual_model=(execution_contract or {}).get('protocol',{}).get('reviewer',{}).get('actual_model') or own_request['model']
        self.failure=None;self.timeout_seconds=120;self.quarantine_dir=None

    def _fetch(self,payload,headers):
        import urllib.request
        # TLS certificate/hostname verification uses the stdlib default context.
        # No custom destination, redirect, inherited proxy or credential logging.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        request=urllib.request.Request('https://api.openai.com/v1/responses',data=canonical_bytes(payload),headers=headers,method='POST')
        try:
            with opener.open(request,timeout=self.timeout_seconds) as response:
                return {'status':response.status,'body':response.read(8*1024*1024+1)}
        except urllib.error.HTTPError as error:
            return {'status':error.code,'body':error.read()}

    def _count_tokens(self,payload,headers):
        import urllib.request
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        supported={'model','input','instructions','tools','tool_choice','text','truncation','parallel_tool_calls','reasoning'}
        body={k:v for k,v in payload.items() if k in supported}
        request=urllib.request.Request('https://api.openai.com/v1/responses/input_tokens',
            data=canonical_bytes(body),headers=headers,method='POST')
        with opener.open(request,timeout=min(30,self.timeout_seconds)) as response:
            raw=response.read(65537)
            if len(raw)>65536:raise ValueError('Provider token control-plane response exceeds bound')
            value=_strict_load(raw)
        (self.root/'input-token-count.bin').write_bytes(raw)
        if value.get('object')!='response.input_tokens' or type(value.get('input_tokens')) is not int or value['input_tokens']<0:
            raise ValueError('Actual provider input token count unavailable')
        return value['input_tokens']

    def forward(self,body):
        self.received_requests+=1
        if self.forwarded_requests:
            self.failure='Internal provider retry/request quota exceeded'
            raise ValueError(self.failure)
        bounded=validate_provider_request(body,self.own_request,max_output_tokens=self.max_output_tokens)
        data=canonical_bytes(bounded)
        if len(data)>self.max_input_bytes:raise ValueError('Provider input/context byte budget exceeded before reasoning')
        if self._key.encode() in data:raise ValueError('Credential leaked into provider request')
        from .review_runner import _write
        headers={'Authorization':'Bearer '+self._key,'Content-Type':'application/json','Accept':'text/event-stream'}
        if self.max_input_tokens is not None:
            count=self._token_counter(bounded) if self.recorded_contract and self._token_counter else self._count_tokens(bounded,headers)
            if type(count) is not int or count<0:raise ValueError('Invalid provider input token observation')
            _write(self.root/'input-token-count.json',{'data_class':'recorded_contract' if self.recorded_contract else 'empirical',
                'input_tokens':count,'provider_body_sha256':digest(bounded),'model_review_calls':0,'scope':'provider control-plane budget precheck'})
            if count>self.max_input_tokens:raise ValueError('Provider input token budget exceeded before reasoning')
        _write(self.root/'request.json',{'data_class':'recorded_contract' if self.recorded_contract else 'empirical',
            'own_request_sha256':digest(self.own_request),'cli_body':deepcopy(body),'provider_body':bounded,
            'provider_body_sha256':digest(bounded),'credential_location':'outside reviewer namespace; never exported'})
        self.forwarded_requests=1 # Any uncertain network completion is charged conservatively.
        try: result=(self._upstream or self._fetch)(bounded,headers)
        except Exception as error:
            self.failure=type(error).__name__
            _write(self.root/'failure.json',{'data_class':'recorded_contract' if self.recorded_contract else 'empirical',
                'reason':self.failure,'forwarded_requests':1,'charging':'unknown_or_charged'})
            raise
        if type(result) is not dict or type(result.get('status')) is not int or type(result.get('body')) is not bytes:
            raise ValueError('Provider transport returned no exact status/raw body')
        if self._key.encode() in result['body']:
            self.failure='credential_leak'
            # A secret-bearing raw response cannot enter campaign/export files.
            # Quarantine is the human launcher's private, separately retained scope.
            if self.quarantine_dir is not None:
                import os,uuid
                folder=Path(self.quarantine_dir)/uuid.uuid4().hex;folder.mkdir(parents=True,mode=0o700,exist_ok=False)
                private=folder/'sensitive-response.bin';private.write_bytes(result['body']);os.chmod(private,0o600)
                _write(self.root/'leak-quarantine.json',{'credential_persisted_in_export_scope':False,
                    'sensitive_original_retained_outside_export':True,'raw_sha256':file_hash(private),'charging':'unknown_or_charged'})
            raise ValueError('Credential leakage detected; stop and quarantine outside exported evidence')
        (self.root/'response.bin').write_bytes(result['body'])
        facts=provider_event_facts(result['body'],result['status'],self.own_request,self.expected_actual_model)
        record={'data_class':'recorded_contract' if self.recorded_contract else 'empirical',
            'status':result['status'],'own_request_sha256':digest(self.own_request),
            'forwarded_requests':1,'received_requests':self.received_requests,
            'raw_response_sha256':file_hash(self.root/'response.bin'),'credential_persisted':False,**facts}
        _write(self.root/'exchange.json',record)
        return {**record,'body':result['body']}


def validate_qualification_launch_contract(contract):
    """Human bootstrap is authorized by the user's invoked real execution brief.

    Qualification has separate bounded calls/costs and cannot release a campaign.
    The actor boundary remains explicit; no developer tool invokes this launcher.
    """
    expected=EXECUTION_BRIEF_SHA256
    brief=ROOT.parent.parent/'instructions_between_agents/developer_m3b-execution-20261012.md'
    if type(contract) is not dict or contract.get('scope')!='human-provider-qualification' or contract.get('brief_sha256')!=expected or file_hash(brief)!=expected:
        raise ValueError('Actual invoked API qualification brief/review binding is missing or historical')
    if contract.get('data_class')!='empirical' or contract.get('model') not in MODEL_ALLOWLIST['api_key']:
        raise ValueError('Qualified eligible API route required; no model fallback')
    for key in ['max_calls','max_input_tokens','max_output_tokens','max_input_bytes','timeout_seconds']:
        if type(contract.get(key)) is not int or contract[key]<1:raise ValueError('Human qualification needs explicit bounded costs/calls')
    validate_qualification_code_review(contract)
    return deepcopy(contract)


def validate_qualification_code_review(contract):
    """Separate immutable main Overseer decision, never a launch boolean."""
    import subprocess
    filename='m3b-qualification-code-overseer-review.md'
    authority=ROOT.parent.parent/'instructions_between_agents'/filename
    try:
        from .experiment_isolation import _check_tree
        _check_tree(authority)
        blocks=re.findall(r'```intentlineage-qualification-code-review\r?\n(.*?)\r?\n```',authority.read_text(encoding='utf-8'),re.S)
        if len(blocks)!=1:raise ValueError('Missing exact code review record')
        decision=_strict_load(blocks[0])
        if decision.get('format_version')!='m3b-qualification-code-review.1' or decision.get('issued_by')!='overseer' or decision.get('status')!='approved' or decision.get('synthetic') is not False:
            raise ValueError('Qualification code review not approved')
        if decision.get('controller_source_sha256')!=controller_source_digest() or decision.get('qualification_launch_sha256')!=digest(contract):
            raise ValueError('Qualification code review source/configuration differs')
        if subprocess.run(['git','merge-base','--is-ancestor',decision['commit'],'HEAD'],cwd=ROOT,capture_output=True).returncode:
            raise ValueError('Qualification code review commit missing')
        return {'path':str(authority),'sha256':file_hash(authority),'decision':decision}
    except (OSError,KeyError,ValueError) as error:
        raise ValueError('Actual current Overseer qualification code review missing or inconsistent') from error


def prepare_qualification_plan(protocol,*,output):
    """Generate local inspection/hosted qualification argv; execute nothing."""
    if protocol.get('format_version') in {'m3b-chatgpt-protocol.1','m3b-chatgpt-single-protocol.1'}:
        from .experiment_chatgpt import prepare_chatgpt_qualification_plan
        return prepare_chatgpt_qualification_plan(protocol,output=output)
    import sys
    from .experiment_protocol import validate_execution_protocol
    validation=validate_execution_protocol(protocol);reviewer=protocol['reviewer'];blockers=[]
    if reviewer['model'] is None or reviewer['authentication']!='api_key':blockers.append('eligible_model_access')
    if reviewer['cli_path'] is None or reviewer['cli_sha256'] is None:blockers.append('supported_linux_cli')
    if any(v is None for v in protocol['limits'].values()):blockers.append('qualification_limits')
    try:
        qualification_launch_contract(model=reviewer['model'],reviewer=reviewer,max_calls=protocol['limits']['qualification_max_calls'],
            max_input_tokens=protocol['limits']['max_input_tokens'],max_output_tokens=protocol['limits']['max_output_tokens'],
            max_input_bytes=protocol['limits']['max_input_bytes'],timeout_seconds=protocol['limits']['max_seconds_per_invocation'])
    except (ValueError,TypeError):blockers.append('qualification_code_review')
    result={'format_version':'m3b-human-qualification-plan.1','model':reviewer['model'],
        'executed':False,'provider_qualified':False,'hosted_launch_actor':'experiment_developer_or_human','campaign_commands':[],
        'blockers':blockers,'validation':validation,'qualification_costs_separate':True,
        'local_inspection_command':[sys.executable,str(ROOT/'scripts/m3b.py'),'inspect-runtime','--output','<fresh-runtime-report>'],
        'qualification_command':None if blockers else [sys.executable,str(ROOT/'scripts/m3b.py'),'human-qualify',
            '--protocol','<reviewed-qualification-settings.json>','--output','<fresh-controller-private-qualification>'],
        'limits':['Code/commands/recorded fixtures do not qualify the actual provider or authorize the scientific campaign.']}
    from .review_runner import _write
    _write(output,result);return result


def validate_empirical_unit(unit,evidence_root,*,historical_source=None):
    """Actual rows require retained bound call provenance, not changed labels."""
    if unit.get('provenance',{}).get('kind')=='continued-qualified-actual-provider':
        from .experiment_resume import validate_composite_unit
        return validate_composite_unit(unit,evidence_root,historical_source=historical_source)
    if historical_source is not None:raise ValueError('Historical source cannot qualify new empirical units')
    if evidence_root is None or unit.get('data_class')!='empirical' or unit.get('synthetic') is not False:
        raise ValueError('Empirical unit requires bound actual invocation evidence')
    if unit.get('provenance',{}).get('kind')!='qualified-actual-provider':
        raise ValueError('Recorded fixture provenance cannot become empirical')
    root=Path(evidence_root)
    protocol=_strict_load((root/'protocol.json').read_bytes())
    provider_kind=protocol.get('provider_identity',{}).get('kind')
    scheduled=protocol.get('execution_contract',{}).get('protocol',{}).get('format_version')=='m3b-chatgpt-scheduled-protocol.1'
    if protocol.get('data_class')!='empirical' or provider_kind not in {'m3b-qualified-human','m3b-qualified-chatgpt','m3b-scheduled-chatgpt'}:
        raise ValueError('Empirical campaign provider/protocol provenance missing')
    for arm,session in unit['matrix']['sessions'].items():
        for call in session.get('calls',[]):
            folder=root/unit['directory']/arm/'calls'/f"{call['attempt']:04d}"/'invocation'
            launch=_strict_load((folder/'launch-receipt.json').read_bytes())
            isolation=_strict_load((folder/'isolation-receipt.json').read_bytes())
            if launch.get('data_class')!='empirical' or launch.get('request_sha256')!=call['request_sha256']:
                raise ValueError('Empirical call binding/provenance changed')
            expected_kind='actual-chatgpt-codex' if provider_kind in {'m3b-qualified-chatgpt','m3b-scheduled-chatgpt'} else 'actual-openai-api'
            if launch.get('provider_kind')!=expected_kind or launch.get('credential_persisted') is not False:
                raise ValueError('Local/recorded provider cannot supply actual calls')
            if isolation.get('data_class')!='empirical' or isolation.get('qualified') is not True:
                raise ValueError('Actual call isolation qualification missing')
            expected_qualification=None if scheduled else protocol['execution_contract']['qualification']['qualification_sha256']
            if launch.get('qualification_sha256')!=expected_qualification:
                raise ValueError('Actual call qualification version changed')
            request=_strict_load((folder/'evidence/request.json').read_bytes())
            if digest(request)!=call['request_sha256'] or request['model']!=protocol['model'] or digest(request['settings'])!=digest(protocol['settings']):
                raise ValueError('Actual model/settings/request mixed')
            validate_actual_call_files(folder,request,launch,limits=protocol['execution_contract']['protocol']['limits'])
            from .experiment_qualification import REQUIRED_PROBES,assert_runtime_matches
            if isolation.get('receipt_sha256')!=digest({k:v for k,v in isolation.items() if k!='receipt_sha256'}):
                raise ValueError('Actual isolation receipt integrity differs')
            if isolation.get('raw_events')!=launch.get('raw_events') or set(isolation.get('probes',{}))!=REQUIRED_PROBES or not all(isolation['probes'].values()):
                raise ValueError('Actual native probe/launch binding differs')
            if isolation['probes']!=launch['raw_events']['result']['probes']:raise ValueError('Actual native probes differ from raw launch')
            expected_runtime=protocol['execution_contract']['protocol']['execution_mode']['setup']['runtime'] if scheduled else protocol['execution_contract']['qualification']['runtime']
            assert_runtime_matches(expected_runtime,launch['runtime'])
            if scheduled and launch.get('frozen_protocol_sha256')!=digest(protocol['execution_contract']['protocol']):raise ValueError('Scheduled native launch freeze binding differs')
            response=folder/'output/real-transport-response.json'
            if response.exists():
                value=_strict_load(response.read_bytes())
                if value.get('synthetic') is not False or value.get('mocked') is not False or value.get('data_class')!='empirical':
                    raise ValueError('Synthetic/recorded response relabelled as actual')
                if value.get('launch_sha256')!=digest(launch):raise ValueError('Raw launch/response binding changed')
    return True


def model_permission_config():
    """Restricted native generated-command policy, separate from CLI transport."""
    return {'default_permissions':'intentlineage-review','approval_policy':'never',
        'permissions':{'intentlineage-review':{'filesystem':{':root':'deny',':minimal':'read',
            '/evidence':'read','/workspace':'read','/home':'deny','/proc':'deny','/runtime':'deny','/output':'deny'},
            'network':{'enabled':False}}},
        'features':{'shell_tool':False,'multi_agent':False,'js_repl':False},
        'web_search':'disabled','mcp_servers':{}}


def config_arguments(config):
    """TOML inline values; Codex splits override paths without unquoting keys.

    Keep filesystem paths inside the parsed TOML value, never in dotted override
    keys. This preserves path spelling and the exact native permission policy.
    """
    args=[]
    def encode(value):
        if type(value) is dict:
            return '{'+','.join(json.dumps(k,ensure_ascii=False)+'='+encode(v) for k,v in value.items())+'}'
        if type(value) is list:return '['+','.join(encode(v) for v in value)+']'
        if type(value) is bool:return 'true' if value else 'false'
        if value is None:raise ValueError('Native TOML configuration cannot contain null')
        return json.dumps(value,ensure_ascii=False,allow_nan=False)
    for key,value in config.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]+',key):raise ValueError('Native override top-level key must be an identifier')
        args.extend(['--config',key+'='+encode(value)])
    return args


def validate_native_cli(path):
    path=Path(path).resolve(strict=True)
    if path.is_symlink() or not path.is_file() or path.read_bytes()[:4]!=b'\x7fELF':
        raise ValueError('Qualified actual transport requires a native Linux ELF Codex binary; no Windows interop/script fallback')
    return {'path':str(path),'binary_sha256':file_hash(path),'native_elf':True}


def qualification_launch_contract(*,model,max_calls,max_input_tokens,max_output_tokens,max_input_bytes,timeout_seconds,reviewer=None):
    value={'scope':'human-provider-qualification','data_class':'empirical','model':model,
        'brief_sha256':EXECUTION_BRIEF_SHA256,
        'max_calls':max_calls,'max_input_tokens':max_input_tokens,'max_output_tokens':max_output_tokens,
        'max_input_bytes':max_input_bytes,'timeout_seconds':timeout_seconds,'reviewer':deepcopy(reviewer)}
    if type(max_input_tokens) is not int or max_input_tokens<1:raise ValueError('Explicit qualification input token bound required')
    validate_qualification_launch_contract(value)
    return value


def broker_source(approved_contract):
    """Reuse current M2 wire/writer and broker definitions in stdlib-only WSL.

    These are current source-bound definitions, not execution of an archived
    historical policy. Credentials are passed privately to the outer supervisor,
    never embedded in source or mounted into the reviewer.
    """
    import inspect
    from .review_runner import _write
    parts=['import hashlib,json,re\nfrom pathlib import Path\nfrom copy import deepcopy\n']
    parts.append('MODEL_ALLOWLIST='+repr(MODEL_ALLOWLIST)+'\n')
    from .review_usage import FIELDS,CORE,ALIASES
    parts.append('FIELDS='+repr(FIELDS)+'\nCORE='+repr(CORE)+'\nALIASES='+repr(ALIASES)+'\n')
    for definition in [canonical_bytes,_strict_load,digest,file_hash,_write,normalize_usage,_usage_candidates,extract_usage,
                       validate_provider_request,provider_event_facts,CredentialBroker]:
        source=inspect.getsource(definition)
        source=source.replace('        from .review_runner import _write\n','')
        parts.append(source+'\n')
    expected=digest(approved_contract)
    parts.append('''
def validate_execution_contract(**contract):
    if digest(contract) != APPROVED_CONTRACT_SHA256:raise ValueError('Controller release contract changed')
    return contract
def validate_qualification_launch_contract(contract):
    if digest(contract) != APPROVED_CONTRACT_SHA256:raise ValueError('Controller qualification launch changed')
    return contract
def make_broker(config,root):
    arguments={config['contract_kind']:config['approved_contract']}
    broker=CredentialBroker(config['request'],api_key=config['api_key'],output_dir=root/'.controller/broker',
        max_output_tokens=config['max_output_tokens'],max_input_bytes=config['max_input_bytes'],
        max_input_tokens=config['max_input_tokens'],**arguments)
    broker.expected_actual_model=config['expected_actual_model']
    broker.timeout_seconds=config['timeout_seconds']
    broker.quarantine_dir=config['quarantine_dir']
    return broker
''')
    parts.append('APPROVED_CONTRACT_SHA256='+repr(expected)+'\n')
    return ''.join(parts)


def validate_actual_call_files(invocation,request,launch,*,limits):
    """Pure raw API/CLI replay binding, also for failure/partial usage evidence."""
    if launch.get('authentication')=='chatgpt':
        from .experiment_chatgpt import validate_chatgpt_call_files
        return validate_chatgpt_call_files(invocation,request,launch,limits=limits)
    root=Path(invocation);broker=root/'.controller/broker';output=root/'output'
    if launch.get('data_class')!='empirical' or launch.get('request_sha256')!=digest(request):
        raise ValueError('Actual call provenance/request differs')
    transport=launch['raw_events']['result']['transport']
    import base64
    for name,key in [('stdout.bin','stdout_base64'),('stderr.bin','stderr_base64')]:
        if (output/name).read_bytes()!=base64.b64decode(transport[key],validate=True):
            raise ValueError('Raw CLI bytes differ from retained launch')
    if launch['forwarded_requests']==0:
        if (broker/'response.bin').exists() or launch.get('broker_exchange'):
            raise ValueError('Claimed uncharged failure contains a provider response')
        return {'charging':'confirmed_not_forwarded','complete':False}
    exchange=launch.get('broker_exchange')
    if exchange is None:
        if (broker/'response.bin').exists():raise ValueError('Raw API response without bound exchange')
        return {'charging':'unknown_or_charged','complete':False}
    if _strict_load((broker/'exchange.json').read_bytes())!=exchange:raise ValueError('API exchange differs from launch')
    record=_strict_load((broker/'request.json').read_bytes())
    if record['data_class']!='empirical' or record['own_request_sha256']!=digest(request):raise ValueError('API request provenance differs')
    bounded=validate_provider_request(record['cli_body'],request,max_output_tokens=limits['max_output_tokens'])
    if bounded!=record['provider_body'] or digest(bounded)!=record['provider_body_sha256']:raise ValueError('API budget/request body differs')
    raw=(broker/'response.bin').read_bytes()
    if file_hash(broker/'response.bin')!=exchange['raw_response_sha256']:raise ValueError('API response hash differs')
    facts=provider_event_facts(raw,exchange['status'],request,launch.get('actual_model'))
    if any(digest(exchange.get(k))!=digest(v) for k,v in facts.items()):raise ValueError('API summary inconsistent with raw streamed events')
    count=_strict_load((broker/'input-token-count.json').read_bytes())
    raw_count=_strict_load((broker/'input-token-count.bin').read_bytes())
    if raw_count.get('object')!='response.input_tokens' or raw_count['input_tokens']!=count['input_tokens'] or count['provider_body_sha256']!=digest(bounded):
        raise ValueError('Pre-reasoning input token observation differs')
    if count['input_tokens']>limits['max_input_tokens'] or len(canonical_bytes(bounded))>limits['max_input_bytes']:
        raise ValueError('Actual request exceeded frozen context budget')
    return {'charging':'unknown_or_charged','complete':not facts['errors'],'facts':facts}


def qualified_worker_source(request,argv,permission_arguments,timeout_seconds,*,probe_binary='/runtime/codex',namespace_private_canaries=False,probes_only=False):
    """Trusted CLI harness and direct native command probes; no credential."""
    # Native probe code adapts M3A's denial controls. Networking is checked by a
    # real connection attempt under Codex's native policy, not net-namespace
    # inequality: the trusted provider harness deliberately shares host networking.
    template = '''
import base64,json,os,socket,subprocess
from pathlib import Path
SEALED_STDIN=SEALED_BYTES
config=json.loads(Path('/runtime/probes.json').read_text())
if NAMESPACE_PRIVATE_CANARIES:
    for name in ['source','config']:
        path=Path('/runtime/'+name+'-canary');path.write_bytes(b'private-canary');config['paths'][name]=str(path)
namespaces={n:os.readlink('/proc/self/ns/'+n) for n in ['pid','mnt','net']}
fresh_state_before_canaries=not any(Path('/home/runner/.codex').iterdir())
if not fresh_state_before_canaries:raise ValueError('Inherited actual reviewer state; no qualification')
canaries=[Path('/home/runner/.codex/sessions/prior'),Path('/home/runner/.codex/auth.json'),
    Path('/home/runner/.codex/history.jsonl'),Path('/tmp/prior-session')]
for path in canaries:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'isolation-canary-not-credential')
state_canaries_established=True
os.symlink(config['paths']['source'],'/tmp/denial-link')
source="""import json,socket
from pathlib import Path
config=CONFIG
def denied(path):
    try: Path(path).read_bytes()
    except OSError:return True
    return False
probes={'own_package':bool(Path('/evidence/request.json').read_bytes()) and Path('/evidence/response-schema.json').is_file()}
for name,path in config['paths'].items():probes[name]=denied(path)
probes['session']=denied('/home/runner/.codex/sessions/prior')
probes['home']=denied('/home/runner/.codex/auth.json')
probes['temp']=denied('/tmp/prior-session')
probes['symlink']=denied('/tmp/denial-link')
probes['process']=denied('/proc/'+str(config['host_pid'])+'/environ')
probes['environment']=not any(name in __import__('os').environ for name in
    ['INTENTLINEAGE_PROVIDER_API_KEY','INTENTLINEAGE_CONTROLLER_CANARY','OPENAI_API_KEY'])
probes['private_state']=denied('/home/runner/.codex/history.jsonl')
try:Path('/evidence/request.json').write_text('tampered')
except OSError:probes['readonly']=True
else:probes['readonly']=False
s=None
try:
    s=socket.socket();s.settimeout(1)
    s.connect(('127.0.0.1',config['host_port']))
except OSError:probes['network']=True
else:probes['network']=False
finally:
    if s is not None:s.close()
print(json.dumps(probes))
""".replace('CONFIG',repr(config))
probe_argv=[PROBE_BINARY,'sandbox',*PERMISSION_ARGUMENTS,'--permission-profile','intentlineage-review','--cd','/workspace','--','/usr/bin/python3','-I','-c',source]
Path('/tmp/native-probe-cli').mkdir()
probe=subprocess.run(probe_argv,capture_output=True,timeout=30,env=dict(os.environ,CODEX_HOME='/tmp/native-probe-cli'))
if probe.returncode:
    print(json.dumps({'probes':{},'native_probe_exit_code':probe.returncode,'native_probe_stdout':probe.stdout.decode(errors='replace'),
        'native_probe_stderr':probe.stderr.decode(errors='replace'),'namespaces':namespaces}));raise SystemExit(0)
probes=json.loads(probe.stdout)
if not all(probes.values()):
    print(json.dumps({'probes':probes,'native_probe_exit_code':probe.returncode,'namespaces':namespaces}));raise SystemExit(0)
if PROBES_ONLY:
    print(json.dumps({'probes':probes,'namespaces':namespaces,'fresh_state_before_canaries':fresh_state_before_canaries,
        'state_canaries_established':True,'provider_review_calls':0,'scope':'native compatibility only; no provider qualification'}));raise SystemExit(0)
for path in canaries:path.unlink()
Path('/home/runner/.codex/sessions').rmdir()
try:
    child=subprocess.run(CLI_ARGUMENTS,input=SEALED_STDIN,capture_output=True,
        timeout=TIMEOUT,env=dict(os.environ))
    raw_stdout,raw_stderr,exit_code,timed_out=child.stdout,child.stderr,child.returncode,False
except subprocess.TimeoutExpired as error:
    raw_stdout,raw_stderr,exit_code,timed_out=error.stdout or b'',error.stderr or b'',None,True
Path('/output/events.jsonl').write_bytes(raw_stdout);Path('/output/stderr.txt').write_bytes(raw_stderr)
Path('/output/stdout.bin').write_bytes(raw_stdout);Path('/output/stderr.bin').write_bytes(raw_stderr)
print(json.dumps({'probes':probes,'namespaces':namespaces,'native_probe_exit_code':probe.returncode,
    'fresh_state_before_canaries':fresh_state_before_canaries,'state_canaries_established':True,
    'native_probe_stdout':probe.stdout.decode(errors='replace'),'native_probe_stderr':probe.stderr.decode(errors='replace'),
    'transport':{'exit_code':exit_code,'timed_out':timed_out,'stdout_base64':base64.b64encode(raw_stdout).decode(),
        'stderr_base64':base64.b64encode(raw_stderr).decode()}}))
'''
    replacements={'PERMISSION_ARGUMENTS':repr(permission_arguments),'CLI_ARGUMENTS':repr(argv),'TIMEOUT':repr(timeout_seconds),
        'SEALED_BYTES':repr(canonical_bytes(request)),'PROBE_BINARY':repr(probe_binary),
        'NAMESPACE_PRIVATE_CANARIES':repr(namespace_private_canaries),'PROBES_ONLY':repr(probes_only)}
    return re.sub(r'\b('+'|'.join(replacements)+r')\b',lambda match:replacements[match.group()],template)


def propose_protocol(bank,*,output):
    """Workload-derived review proposal, not a model selection or protocol freeze."""
    from .experiment_campaign import validate_bank_selection
    from .experiment_chatgpt import draft_chatgpt_protocol
    from .review_runner import _write
    original=validate_bank_selection(bank)
    root=Path(bank['root']);counts={};bytes_per_case={};sizes=set()
    for case in bank['cases']:
        if not case['qualified']:raise ValueError('Unqualified/invisible faults cannot enter protocol proposal')
        plan=_strict_load((root/case['directory']/'controller/review-plan.json').read_bytes())
        counts[case['case_id']]=plan['batch_count'];sizes.add(plan['batch_size'])
        bytes_per_case[case['case_id']]=len(canonical_bytes(plan))
    if len(sizes)!=1:raise ValueError('Mixed H batching in qualified bank')
    value=draft_chatgpt_protocol()
    value['population']={'case_ids':[c['case_id'] for c in bank['cases']],'bank_sha256':original['bank_sha256']}
    value['H']={'batch_size':next(iter(sizes)),'max_request_bytes':plan['max_request_bytes'],'batch_counts':counts}
    value['A']={'max_calls':max(counts.values())+2,'max_operations':2,'max_disclosure_bytes':100000}
    value['selection_policy']='question_driven';value['repeats']=1;value['scheduling']['seed']=20261012
    value['retry'].update(reasoning_retries=0,transport_retries=1)
    value['limits']={'max_input_tokens':65536,'max_input_bytes':300000,'max_output_tokens':8192,
        'max_output_bytes':1048576,'max_seconds_per_invocation':300,'qualification_max_calls':2}
    # Review may change every proposed scientific value. No account/CLI/model
    # or qualification binding is populated by inspecting a native workload.
    proposal={'format_version':'m3b-protocol-proposal.1','status':'unreviewed','protocol':value,
        'controller_source_sha256':controller_source_digest(),'source_manifest':controller_sources(),
        'measured_plan_bytes':bytes_per_case,'mechanically_qualified_cases':len(bank['cases']),
        'reasoning':'One dependent payment pair, six variants, one repeat; no independence-based intervals. A may request two native operations in two extra client turns. No reasoning retries; one confirmed no-turn transport retry. Input/output token limits are observed client stop limits, not an API precheck or provider output-token cap. Native bytes/time are bounded; mandatory evidence is never truncated.',
        'qualification_costs_separate':True,'model_selected':False,'experiment_authorized':False,
        'maximum_charged_calls':sum(1+2*n+2*value['A']['max_calls'] for n in counts.values()),
        'remaining':['Exact eligible model/access and CLI','Actual provider isolation qualification','Overseer code, protocol and campaign release'],
        'cost_semantics':'ChatGPT account usage and available native token receipts only; no assumed API dollar bill. Backend attempts/counters may remain unknown and require protocol review.'}
    _write(output,proposal);return proposal
