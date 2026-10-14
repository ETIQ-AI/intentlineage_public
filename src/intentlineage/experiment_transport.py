"""M2 transport adapter using M3A's existing fail-closed isolation launcher.

Legacy preparation executes only explicit offline fakes. The separately gated
operator adapter supports actual qualification/campaign calls after review.
M2 owns assessment, retry policy, transcript replay and token normalization.
"""
import base64
import json
from pathlib import Path

from .native_capture import ROOT, digest, file_hash
from .review_contract import REPLY_SCHEMA
from .review_provider import prepare_provider_command, collect_provider_response, extract_usage
from .review_runner import TransportFailure, _write, ARMS
from .experiment_isolation import OfflineSandbox, IsolationUnavailable, PROBE_SOURCE, _check_tree, _linux_path
from .experiment_qualification import seal, validate_qualification


def prepare_qualified_command(invocation,request,*,gateway_url):
    """Adapt the existing M2 argv for a native, credential-free CLI namespace."""
    from urllib.parse import urlparse
    from .experiment_execution import model_permission_config,config_arguments
    endpoint=urlparse(gateway_url)
    if endpoint.scheme!='http' or endpoint.hostname!='127.0.0.1' or endpoint.path!='/v1' or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or not endpoint.port:
        raise ValueError('Only the bound local provider-control-plane broker is allowed')
    invocation=_check_invocation(invocation,request)
    base=prepare_provider_command(invocation,request,codex_bin='/runtime/codex')
    argv=base['argv'][:]
    index=argv.index('--sandbox');del argv[index:index+2]
    substitutions={str(invocation/'workspace'):'/workspace',str(invocation/'evidence/response-schema.json'):'/evidence/response-schema.json',
                   str(invocation/'output/reply.json'):'/output/reply.json'}
    argv=[substitutions.get(item,item) for item in argv]
    config=model_permission_config()
    config.update(model_provider='intentlineage-broker',model_providers={'intentlineage-broker':{
        'name':'IntentLineage bound transport','base_url':gateway_url,'wire_api':'responses',
        'request_max_retries':0,'stream_max_retries':0,'requires_openai_auth':False}})
    argv=argv[:-1]+['--strict-config']+config_arguments(config)+argv[-1:]
    result={'format_version':'m3b-qualified-command.1','argv':argv,'config':config,'request_sha256':digest(request),
        'executed':False,'hosted_launch_actor':'experiment_developer_or_human','provider_command_sha256':file_hash(invocation/'provider-command.json'),
        'credentials':'held by broker outside reviewer namespace','model_command_network':'denied',
        'qualification_required':True,'source':'Existing M2 template with explicit native profile and no hidden retries/tools'}
    _write(invocation/'qualified-command.json',result);return result


class PreparationOnly(RuntimeError):
    pass


class HumanProviderFactory:
    """Actual adapter for the same M2 controller; only human launches its CLI.

    Construction verifies actual release and evidence before any staging. No
    synthetic factory or declaration can supply an actual context.
    """
    def __init__(self,execution_contract,*,api_key=None,sandbox=None):
        raise ValueError('API-key protocol/qualification is historical; use the ChatGPT provider factory')
        from .experiment_execution import validate_execution_contract
        if type(execution_contract) is not dict:raise ValueError('Actual protocol/qualification/release contract required')
        self.context=validate_execution_contract(**execution_contract)
        self.api_key=api_key;self.sandbox=sandbox or OfflineSandbox();self.providers={};self.stop_reason=None
        self.qualification_root=ROOT/self.context['qualification']['artifact_directory']

    @property
    def identity(self):
        p=self.context['protocol'];return {'kind':'m3b-qualified-human','data_class':'empirical',
            'model':p['reviewer']['model'],'actual_model':p['reviewer']['actual_model'],
            'cli_sha256':p['reviewer']['cli_sha256'],'settings':p['reviewer']['settings'],
            'qualification_sha256':self.context['qualification']['qualification_sha256'],
            'retry_owner':'existing M2 controller','hosted_launch_actor':'experiment_developer_or_human'}

    def verify(self):
        if self.stop_reason:raise ValueError('Actual campaign stopped after qualification/leak drift: '+self.stop_reason)
        from .experiment_execution import validate_execution_contract
        validate_execution_contract(**{k:self.context[k] for k in ['protocol','gates','qualification']})

    def inspect_runtime(self):
        from .experiment_qualification import assert_runtime_matches
        p=self.context['protocol'];result=self.sandbox._call({'action':'inspect-provider','cli_binary':p['reviewer']['cli_path']})
        assert_runtime_matches(self.context['qualification']['runtime'],result['runtime'])
        if result['cli']['binary_sha256']!=p['reviewer']['cli_sha256'] or result['cli']['version']!=p['reviewer']['cli_version']:
            raise ValueError('Actual model CLI drift; stop and requalify')
        return result['runtime']

    def stage_qualification(self,campaign_root):
        import shutil
        target=Path(campaign_root)/self.context['qualification']['artifact_directory']
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(self.qualification_root,target)

    def __call__(self,arm):
        self.verify()
        if arm not in ARMS:raise ValueError('Unknown actual arm')
        provider=HumanReviewerTransport(self);self.providers[arm]=provider;return provider


class HumanReviewerTransport:
    """Provider adapter only; assessment/accounting/retries remain exact M2."""
    def __init__(self,owner):self.owner=owner;self.receipts=[];self.calls=0

    def __call__(self,request,invocation):
        self.owner.verify();context=self.owner.context;p=context['protocol']
        if request['model']!=p['reviewer']['model'] or digest(request['settings'])!=digest(p['reviewer']['settings']):
            raise ValueError('Actual call differs from frozen model/settings')
        runtime=self.owner.inspect_runtime()
        raw,receipt,launch=run_qualified_invocation(invocation,request,sandbox=self.owner.sandbox,
            protocol=p,qualification=context['qualification'],approved_contract={k:context[k] for k in ['protocol','gates','qualification']},
            contract_kind='execution_contract',api_key=self.owner.api_key,runtime=runtime)
        self.receipts.append(receipt);self.calls+=1
        if raw.get('broker_failure') or raw.get('received_requests',0)>1 or (raw.get('broker_exchange') or {}).get('errors'):
            self.owner.stop_reason='Provider tool/retry/transport qualification drift'
        if launch.get('forwarded_requests')==0 and not launch['timed_out']:
            raise TransportFailure('Bound broker proves no provider reasoning request was forwarded; retained actual launch')
        return collect_real_response(invocation,request,launch=launch,execution_contract={k:context[k] for k in ['protocol','gates','qualification']})


def run_qualified_invocation(invocation,request,*,sandbox,protocol,qualification,approved_contract,contract_kind,api_key,runtime):
    """Human-invoked real transport through the existing M3A isolation launcher."""
    raise ValueError('API-key launcher is historical; current authorization requires ChatGPT')
    from .experiment_execution import broker_source,qualified_worker_source,model_permission_config,config_arguments
    from .experiment_qualification import REQUIRED_PROBES,runtime_identity
    if not api_key:raise ValueError('Human provider credential must be supplied outside reviewer mounts')
    invocation=_check_invocation(invocation,request)
    command=prepare_qualified_command(invocation,request,gateway_url='http://127.0.0.1:__PORT__/v1'.replace('__PORT__','12345'))
    argv=[x.replace('127.0.0.1:12345','127.0.0.1:__INTENTLINEAGE_BROKER_PORT__') for x in command['argv']]
    controller=invocation/'.controller';controller.mkdir()
    paths={}
    for name in ['sibling','oracle','source','config']:
        path=controller/(name+'-canary.txt');path.write_bytes(('controller-private-'+name).encode());paths[name]=_linux_path(path)
    paths['source']=_linux_path(ROOT/'examples/native_payment_workflow.py');paths['config']=_linux_path(ROOT/'Agents.md')
    config={'action':'provider','invocation':_linux_path(invocation),'cli_binary':protocol['reviewer']['cli_path'],
        'expected_cli_sha256':protocol['reviewer']['cli_sha256'],'expected_runtime':runtime_identity(runtime),
        'api_key':api_key,'request':request,'approved_contract':approved_contract,'contract_kind':contract_kind,
        'expected_actual_model':protocol['reviewer']['actual_model'],
        'max_input_bytes':protocol['limits']['max_input_bytes'],'max_input_tokens':protocol['limits']['max_input_tokens'],
        'max_output_tokens':protocol['limits']['max_output_tokens'],'timeout_seconds':protocol['limits']['max_seconds_per_invocation'],
        'broker_source':broker_source(approved_contract),
        'quarantine_dir':_linux_path(ROOT/'.tmp/m3b-provider-private-quarantine'),
        'worker_source':qualified_worker_source(request,argv,config_arguments(model_permission_config()),protocol['limits']['max_seconds_per_invocation']),
        'probes':{'paths':paths}}
    raw=sandbox._call(config)
    probes=raw.get('result',{}).get('probes',{})
    if (set(probes)!=REQUIRED_PROBES or any(v is not True for v in probes.values()) or 'transport' not in raw['result']
            or raw['result'].get('fresh_state_before_canaries') is not True or raw['result'].get('state_canaries_established') is not True):
        _write(controller/'failed-provider-boundary.json',{'data_class':'empirical','request_sha256':digest(request),'raw_events':raw})
        raise IsolationUnavailable('Actual native command probes failed; no provider call admitted')
    transport=raw['result']['transport']
    launch={'format_version':'m3b-launch.1','data_class':'empirical','request_sha256':digest(request),
        'model':request['model'],'actual_model':raw.get('broker_exchange',{}).get('observed_actual_model'),'settings':request['settings'],
        'provider_kind':'actual-openai-api','credential_persisted':False,'exit_code':transport['exit_code'],
        'timed_out':transport['timed_out'],'forwarded_requests':raw['forwarded_requests'],
        'runtime':runtime,'qualification_sha256':qualification.get('qualification_sha256'),
        'broker_exchange':raw.get('broker_exchange'),
        'raw_events':raw,'provider_call_id':digest({'request':digest(request),'argv':raw['argv']})}
    receipt=seal({'format_version':'m3b-provider-call-isolation.1','data_class':'empirical','synthetic':False,
        'qualified':True,'scope':'actual-provider','request_sha256':digest(request),'runtime':runtime,'probes':probes,
        'provider_transport':'bound credential broker outside namespace','model_command_network':'denied',
        'fresh_session':True,'history_policy':'none','credential_model_access':'denied','raw_events':raw,'argv':raw['argv']})
    _write(invocation/'launch-receipt.json',launch);_write(invocation/'isolation-receipt.json',receipt)
    return raw,receipt,launch


class OfflineProviderFactory:
    """Explicit source-bound fake CLI factory for the existing M3A controller."""
    def __init__(self, executables_by_arm):
        if type(executables_by_arm) is not dict or set(executables_by_arm) != ARMS:
            raise ValueError('Offline provider factory requires exactly the existing five arms')
        self._sources = {}
        for arm, paths in executables_by_arm.items():
            if not isinstance(paths, (list, tuple)) or not paths:
                raise ValueError('Each offline arm needs explicit fake executables')
            self._sources[arm] = [(Path(p).resolve(strict=True), file_hash(p)) for p in paths]
        self.providers = {}
        self.verify()

    def verify(self):
        for sources in self._sources.values():
            for path, expected in sources:
                _check_tree(path)
                if file_hash(path) != expected: raise ValueError('Frozen offline fake program changed')

    @property
    def identity(self):
        return {'kind': 'm3b-offline-fake', 'synthetic': True, 'provider_transport': 'disabled',
                'programs': {arm: [sha for _, sha in sources] for arm, sources in self._sources.items()},
                'retry_owner': 'existing M2 controller'}

    def __call__(self, arm):
        self.verify()
        if arm not in ARMS: raise ValueError('Unknown offline review arm')
        provider = ReviewerTransport(fake_executables=[path for path, _ in self._sources[arm]])
        self.providers[arm] = provider
        return provider


def _bind_request(invocation, request):
    invocation = Path(invocation).resolve(strict=True)
    _check_tree(invocation)
    if digest(json.loads((invocation/'evidence/request.json').read_bytes())) != digest(request):
        raise ValueError('Sealed request differs from the controller request')
    if json.loads((invocation/'invocation.json').read_bytes()).get('request_sha256') != digest(request):
        raise ValueError('Request differs from the original M2 invocation binding')
    schema=REPLY_SCHEMA
    if request.get('contract_version')=='m3-single-review.1':
        from .review_single import REPLY_SCHEMA as schema
    if (request.get('contract_version')=='m3-single-review.1' and request.get('response_schema')!=schema) or digest(json.loads((invocation/'evidence/response-schema.json').read_bytes())) != digest(schema):
        raise ValueError('Sealed response schema differs from the M2 reviewer contract')
    if {p.name for p in (invocation/'evidence').iterdir()} != {'request.json', 'response-schema.json'}:
        raise ValueError('Only own sealed request/schema may enter the reviewer boundary')
    return invocation


def _check_invocation(invocation, request):
    invocation = _bind_request(invocation, request)
    for name in ['workspace', 'home', 'temp', 'output']:
        if any((invocation/name).iterdir()): raise ValueError('Reviewer mutable contexts must be fresh')
    return invocation


class CommandSandbox(OfflineSandbox):
    """Reuse OfflineSandbox._call and offline_bubblewrap_command without fallback."""

    def run_command(self, invocation, request, *, fake_source=None, timeout_seconds=5):
        invocation = _check_invocation(invocation, request)
        template = prepare_provider_command(invocation, request)
        controller = invocation/'.controller'
        controller.mkdir()
        paths = {}
        for name in ['sibling', 'oracle', 'source', 'config', 'session', 'home', 'temp']:
            path = controller/(name+'-canary.txt')
            path.write_bytes(('controller-private-'+name).encode())
            paths[name] = _linux_path(path)
        # Probe actual repository/configuration files as well as private canaries.
        paths['source'] = _linux_path(ROOT/'examples/native_payment_workflow.py')
        paths['config'] = _linux_path(ROOT/'Agents.md')
        # The existing launcher mounts just the worker and probe config, not this
        # private directory. The fake executable is embedded in that worker;
        # the actual child is a separate Python process inside the same boundary.
        replacements = {str(invocation/'workspace'): '/workspace',
                        str(invocation/'evidence/response-schema.json'): '/evidence/response-schema.json',
                        str(invocation/'output/reply.json'): '/output/reply.json'}
        cli_arguments = [replacements.get(v, v) for v in template['argv'][1:]]
        worker = PROBE_SOURCE + '\n'
        worker += '''
import base64, subprocess
transport = None
'''
        if fake_source is not None:
            argv = ['/usr/bin/python3', '-I', '-c', fake_source, *cli_arguments]
            worker += 'argv = ' + repr(argv) + '\n'
            worker += 'timeout_seconds = ' + repr(timeout_seconds) + '\n'
            worker += '''
try:
    child = subprocess.run(argv, input=Path('/evidence/request.json').read_bytes(),
                           capture_output=True, close_fds=True, timeout=timeout_seconds)
    stdout, stderr, exit_code, timed_out = child.stdout, child.stderr, child.returncode, False
except subprocess.TimeoutExpired as error:
    stdout, stderr, exit_code, timed_out = error.stdout or b'', error.stderr or b'', None, True
Path('/output/stdout.bin').write_bytes(stdout)
Path('/output/stderr.bin').write_bytes(stderr)
transport = {'stdout_base64': base64.b64encode(stdout).decode(),
             'stderr_base64': base64.b64encode(stderr).decode(),
             'exit_code': exit_code, 'timed_out': timed_out,
             'argv': argv}
'''
        worker += "import hashlib\nprint(json.dumps({'probes': probes, 'namespaces': namespaces, 'transport': transport, 'request_file_sha256': hashlib.sha256(Path('/evidence/request.json').read_bytes()).hexdigest()}))\n"
        worker_path = controller/'worker.py'
        worker_path.write_text(worker, encoding='utf-8', newline='\n')
        config = {'action': 'run', 'invocation': _linux_path(invocation),
                  'worker': _linux_path(worker_path), 'probes': {'paths': paths}}
        before = file_hash(invocation/'evidence/request.json')
        try:
            raw = self._call(config)
            if before != file_hash(invocation/'evidence/request.json'):
                raise IsolationUnavailable('Reviewer changed sealed evidence')
            _check_tree(invocation)
            result = raw['result']
            receipt = seal({'format_version': 'm3b-isolation.1', 'qualified': True,
                'synthetic': True, 'scope': 'offline', 'real_provider_qualified': False,
                'provider_transport': 'disabled', 'model_command_network': 'denied',
                'fresh_session': True, 'history_policy': 'none', 'request_sha256': digest(request),
                'request_file_sha256': before, 'probes': result['probes'],
                'bindings': {'worker_sha256': file_hash(worker_path),
                             'supervisor_sha256': file_hash(ROOT/'src/intentlineage/_reference/offline_boundary.py'),
                             'launcher_sha256': file_hash(ROOT/'src/intentlineage/experiment_isolation.py')},
                'runtime': raw['runtime'], 'argv': raw['argv'], 'namespaces': result['namespaces'],
                'raw_events': raw,
                'limits': ['Offline probes do not qualify the actual model/CLI provider transport or its generated-command policy.']})
            validate_qualification(receipt, request_sha256=digest(request))
        except Exception as error:
            _write(controller/'failed-isolation.json', {'qualified': False, 'synthetic': True,
                   'failure': str(error), 'request_sha256': digest(request)})
            raise
        _write(invocation/'isolation-receipt.json', receipt)
        return result['transport'], receipt


def _events(raw):
    events = []
    for line in raw.splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        if isinstance(event, dict): events.append(event)
    return events


def _collect_exact(invocation, request, *, provider_call_id, exit_code):
    """Preserve binary transport while delegating usage to the existing M2 parser."""
    output = invocation/'output'
    def read(name):
        path = output/name
        return path.read_bytes() if path.exists() else b''
    reply_bytes = read('reply.json'); event_bytes = read('events.jsonl'); stderr_bytes = read('stderr.txt')
    raw_reply = reply_bytes.decode('utf-8', errors='replace')
    raw_events = event_bytes.decode('utf-8', errors='replace')
    raw_stderr = stderr_bytes.decode('utf-8', errors='replace')
    encoding_errors = any(text.encode('utf-8') != raw for text, raw in
                          [(raw_reply, reply_bytes), (raw_events, event_bytes), (raw_stderr, stderr_bytes)])
    try:
        response = collect_provider_response(invocation, provider_call_id=provider_call_id, exit_code=exit_code)
    except UnicodeError:
        # The reused text collector cannot consume invalid UTF-8, but its usage
        # parser can still preserve valid event observations. No assessor is added.
        extracted = extract_usage(_events(raw_events))
        response = {'request_sha256': digest(request), 'provider_call_id': provider_call_id, **extracted,
                    'event_diagnostics': [{'reason': 'Invalid UTF-8 transport; original bytes retained.'}]}
        if exit_code or not raw_reply: response['failure'] = {'exit_code': exit_code, 'reason': 'Recorded provider failure or missing reply'}
    response.update(raw_reply=raw_reply, raw_events=raw_events, raw_stdout=raw_events,
                    raw_stderr=raw_stderr, exit_code=exit_code, encoding_errors=encoding_errors)
    if encoding_errors: response['failure'] = {'exit_code': exit_code, 'reason': 'Invalid UTF-8 transport; charging unknown'}
    return response


def collect_recorded_response(invocation, request, *, provider_call_id, exit_code):
    """Consume human/fixture outputs locally. It grants no campaign admissibility."""
    invocation = _bind_request(invocation, request)
    if exit_code is not None and type(exit_code) is not int: raise ValueError('Exact exit status must be an integer or unknown')
    if not isinstance(provider_call_id, str) or not provider_call_id.strip(): raise ValueError('Provider call identity required')
    output = invocation/'output'
    for source, destination in [('events.jsonl', 'stdout.bin'), ('stderr.txt', 'stderr.bin')]:
        data = (output/source).read_bytes() if (output/source).exists() else b''
        path = output/destination
        if path.exists():
            if path.read_bytes() != data: raise ValueError('Recorded binary/text transport differs')
        else: path.write_bytes(data)
    response = _collect_exact(invocation, request, provider_call_id=provider_call_id, exit_code=exit_code)
    response.update(recorded_only=True, admissible_for_campaign=False, isolation_qualified=False,
                    raw_byte_files={name: file_hash(output/name) for name in ['stdout.bin', 'stderr.bin']})
    _write(output/'transport-response.json', response)
    return response


def collect_real_response(invocation,request,*,launch,recorded_contract=False,execution_contract=None,qualification_contract=None):
    """Reuse exact M2 collection for a bound actual-shaped launch receipt.

    Recorded fixtures exercise this path with a permanent recorded-contract
    classification. Actual admission needs the separately qualified/released
    execution contract; changing a fixture's label cannot supply that authority.
    """
    invocation=_bind_request(invocation,request)
    if type(launch) is not dict or launch.get('format_version')!='m3b-launch.1':
        raise ValueError('Missing exact provider launch contract')
    for field,expected in [('request_sha256',digest(request)),('model',request['model']),('settings',request['settings'])]:
        if digest(launch.get(field))!=digest(expected):raise ValueError('Provider launch request/model/settings binding changed')
    if recorded_contract:
        if launch.get('data_class')!='recorded_contract':raise ValueError('Recorded contract fixture scope changed')
        expected_actual=request['model']
    elif qualification_contract is not None:
        from .experiment_execution import validate_qualification_launch_contract,MODEL_ALLOWLIST
        validate_qualification_launch_contract(qualification_contract)
        if launch.get('data_class')!='empirical' or request['model']!=qualification_contract['model']:
            raise ValueError('Qualification source/model differs')
        expected_actual=launch.get('actual_model')
        if expected_actual is not None and expected_actual not in MODEL_ALLOWLIST['api_key']:
            raise ValueError('Observed actual qualification model exceeds ceiling')
    else:
        from .experiment_execution import validate_execution_contract
        if type(execution_contract) is not dict:raise ValueError('Actual qualification/authority execution contract required')
        validated=validate_execution_contract(execution_contract.get('protocol'),execution_contract.get('gates'),execution_contract.get('qualification'))
        if launch.get('data_class')!='empirical':raise ValueError('Synthetic/recorded launches are not empirical')
        expected_actual=validated['protocol']['reviewer']['actual_model']
    if launch.get('actual_model') is not None and launch.get('actual_model')!=expected_actual:raise ValueError('Actual provider model changed')
    exit_code=launch.get('exit_code')
    if exit_code is not None and type(exit_code) is not int:raise ValueError('Exact/unknown exit status required')
    if type(launch.get('timed_out')) is not bool or type(launch.get('forwarded_requests')) is not int or launch['forwarded_requests']<0:
        raise ValueError('Invalid timeout/provider-attempt facts')
    from .experiment_qualification import runtime_identity
    runtime_identity(launch['runtime'])
    response=collect_recorded_response(invocation,request,provider_call_id=launch.get('provider_call_id','bound-provider-launch'),exit_code=exit_code)
    errors=[]
    from .review_contract import _strict_load
    events=[]
    for line in response['raw_events'].splitlines():
        if not line.strip():continue
        try:
            event=_strict_load(line)
            if type(event) is not dict:raise ValueError('Event is not an object')
            events.append(event)
        except ValueError:errors.append('Malformed/duplicate-key provider event')
    starts=sum(e.get('type')=='turn.started' for e in events)
    completed=[e for e in events if e.get('type')=='turn.completed']
    messages=[e['item'].get('text') for e in events if e.get('type')=='item.completed' and type(e.get('item')) is dict and e['item'].get('type')=='agent_message']
    if starts!=1 or len(completed)!=1:errors.append('Completion or internal reasoning-turn count is unknown/unaccounted')
    if any(e.get('type') in {'error','turn.failed'} for e in events):errors.append('Provider failure event')
    if any(type(e.get('item')) is dict and e['item'].get('type') not in {'reasoning','agent_message'} for e in events):
        errors.append('Unexpected model tool/command/leak surface')
    try:
        if not messages or digest(_strict_load(messages[-1]))!=digest(_strict_load(response['raw_reply'])):
            errors.append('Final reply is not bound to retained agent-message event')
    except (ValueError,TypeError):errors.append('Unbound/malformed final reply')
    if launch['timed_out'] or exit_code is None or exit_code!=0 or launch['forwarded_requests']!=1:
        errors.append('Timeout/failure or unknown/internal provider charging')
    if not recorded_contract:
        exchange=launch.get('broker_exchange') or {}
        if exchange.get('data_class')!='empirical' or exchange.get('own_request_sha256')!=digest(request):
            errors.append('Actual API request/completion binding unavailable')
        errors.extend(exchange.get('errors',[]))
        if exchange.get('completion_events')!=1 or not exchange.get('observed_actual_model'):
            errors.append('Actual API completion/model unavailable')
        # Use accepted M2 usage extraction; partial/zero usage stays explicit.
        api_usage=extract_usage([{'usage':exchange.get('usage_raw',[])[-1]}])['usage'] if exchange.get('usage_raw') else {}
        cli_usage=response.get('usage',{})
        for key in ['input_tokens','output_tokens','total_tokens']:
            if key in api_usage and key in cli_usage and api_usage[key]!=cli_usage[key]:errors.append('API/CLI usage disagrees: '+key)
        from .experiment_execution import validate_actual_call_files
        limits=qualification_contract if qualification_contract is not None else validated['protocol']['limits']
        facts=validate_actual_call_files(invocation,request,launch,limits=limits)
        if not facts['complete']:errors.append('Actual API raw proof incomplete')
    response.update(data_class='recorded_contract' if recorded_contract else 'empirical',
        synthetic=bool(recorded_contract),mocked=bool(recorded_contract),recorded_only=bool(recorded_contract),
        charging='unknown_or_charged',reasoning_attempts_observed=starts,
        provider_requests_observed=launch['forwarded_requests'],launch_sha256=digest(launch),
        qualification_only=qualification_contract is not None,
        admissible_for_campaign=not recorded_contract and qualification_contract is None and not errors)
    if errors:response['failure']={'reason':'; '.join(errors),'exit_code':exit_code}
    _write(invocation/'output/real-transport-response.json',response)
    return response


class ReviewerTransport:
    """Injected M2 provider: no internal retries and no hosted execution route.

    Fake source hashes are frozen on construction; fresh calls reuse the last
    explicit fixture if fewer fixture programs than M2 logical calls are given.
    This selection exists only for offline contract tests.
    """
    def __init__(self, *, mode='offline_fake', fake_executables=(), sandbox=None,
                 timeout_seconds=5, probes_only=False):
        if mode not in {'offline_fake', 'real'}: raise ValueError('Unknown transport mode')
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 20:
            raise ValueError('Offline fake timeout must be positive and at most 20 seconds')
        self.mode = mode
        self.sources = [(Path(p).resolve(strict=True), file_hash(p)) for p in fake_executables]
        for path, _ in self.sources: _check_tree(path)
        self.sandbox = sandbox or CommandSandbox()
        self.timeout_seconds = timeout_seconds
        self.probes_only = probes_only
        self.calls = 0
        self.receipts = []

    def __call__(self, request, invocation):
        if self.mode == 'real':
            raise PreparationOnly('Real execution is blocked in preparation pending corrected integration and provider qualification')
        invocation = _check_invocation(invocation, request)
        source = None
        source_hash = None
        if not self.probes_only:
            if not self.sources: raise ValueError('An explicit local fake executable is required')
            path, source_hash = self.sources[min(self.calls, len(self.sources)-1)]
            _check_tree(path)
            if file_hash(path) != source_hash: raise ValueError('Fake executable hash changed')
            source = path.read_text(encoding='utf-8')
        self.calls += 1
        transport, receipt = self.sandbox.run_command(invocation, request, fake_source=source,
                                                     timeout_seconds=self.timeout_seconds)
        self.receipts.append(receipt)
        if self.probes_only: return receipt
        output = invocation/'output'
        stdout = base64.b64decode(transport['stdout_base64'], validate=True)
        stderr = base64.b64decode(transport['stderr_base64'], validate=True)
        encoding_errors = False
        try: stdout_text, stderr_text = stdout.decode('utf-8'), stderr.decode('utf-8')
        except UnicodeError:
            encoding_errors = True
            stdout_text, stderr_text = stdout.decode('utf-8', errors='replace'), stderr.decode('utf-8', errors='replace')
        # Exact bytes are already retained; M2 consumes decoded diagnostic text.
        (output/'events.jsonl').write_bytes(stdout_text.encode('utf-8'))
        (output/'stderr.txt').write_bytes(stderr_text.encode('utf-8'))
        response = _collect_exact(invocation, request, provider_call_id=f'offline-fake-{self.calls}',
                                  exit_code=transport['exit_code'])
        events = _events(stdout_text)
        starts = sum(event.get('type') == 'turn.started' for event in events)
        response.update(synthetic=True, mocked=True, request_sha256=digest(request),
                        exit_code=transport['exit_code'], timed_out=transport['timed_out'],
                        raw_stdout=stdout_text, raw_stderr=stderr_text,
                        raw_byte_files={'stdout.bin': file_hash(output/'stdout.bin'),
                                        'stderr.bin': file_hash(output/'stderr.bin')},
                        fake_executable_sha256=source_hash,
                        isolation_receipt_sha256=receipt['receipt_sha256'],
                        reasoning_attempts_observed=starts, internal_retries=0,
                        encoding_errors=encoding_errors or response['encoding_errors'])
        if transport['timed_out'] or encoding_errors or starts > 1:
            response['failure'] = {'reason': 'Timeout, invalid encoding or unaccounted internal reasoning attempts; charging unknown.',
                                   'exit_code': transport['exit_code']}
        # Only a complete explicit offline no-start receipt can use M2's
        # transport-only retry path. Hosted receipt semantics remain unqualified.
        confirmed_transport = (transport['exit_code'] == 75 and not transport['timed_out']
                               and not encoding_errors and not response['raw_reply'] and starts == 0
                               and events == [{'type': 'transport.not_started', 'reasoning_started': False, 'charged': False}])
        _write(output/'transport-response.json', response)
        if confirmed_transport:
            raise TransportFailure('Offline fake explicitly confirms no reasoning started/charged; exact receipt retained')
        return response
