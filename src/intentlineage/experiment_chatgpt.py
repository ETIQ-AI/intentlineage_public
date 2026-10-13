"""ChatGPT client transport contracts around the accepted M2/M3A harness.

Cached login is used only by the supported Codex client. No OAuth/API proxy,
assessment loop, alternate normalizer or scoring implementation lives here.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

from .native_capture import ROOT, digest, file_hash
from .review_contract import canonical_bytes, _strict_load, PROMPT_CONTRACT, REPLY_SCHEMA, validate_reply
from .review_usage import normalize_usage
from .experiment_protocol import draft_execution_protocol, draft_protocol, validate_protocol, validate_reviewer_model

CHATGPT_FORMAT = 'm3b-chatgpt-protocol.1'
ALLOWED_MODELS = frozenset({'gpt-5.5'})
CORRECTION_NAME = 'developer_m3-completion-20261012.md'
QUALIFICATION_INPUT = 'resources/protocol/m3b-qualification-endpoint.json'
WIRE_PACKAGING_INSTRUCTIONS = (
    'Transport packaging only: return a closed JSON object containing exactly the required '
    'string field reply_json. Put the complete original M2 reply JSON, following the supplied '
    'response_schema, inside that string. Keep the assessment task and supplied evidence '
    'unchanged, including original typed object/array citation values. No prose, code fences, '
    'answer repair or additional model calls. Decode only this one envelope.'
)
OBSERVABILITY = {
    'backend_served_model': 'unavailable_unless_client_reports',
    'provider_attempts': 'unknown_unless_client_reports',
    'monetary_cost': 'not_an_api_dollar_bill',
    'input_tokens': 'local workload estimates and observed client stop limits; CLI overhead not pre-counted; no API input-token endpoint',
    'output_tokens': 'observed_stop_limit; client does not expose a per-turn provider output-token cap',
    'call_matching': 'fresh client logical turns; backend attempts may remain unknown',
}


def draft_chatgpt_protocol():
    value = draft_execution_protocol()
    value['format_version'] = CHATGPT_FORMAT
    reviewer = value['reviewer']
    reviewer['authentication'] = 'chatgpt'
    reviewer.pop('actual_model'); reviewer.pop('model_catalog_sha256')
    reviewer.update(client_effective_model=None, model_metadata_sha256=None, auth_source=None)
    value['bindings'].pop('model_catalog')
    value['bindings']['model_metadata'] = None
    value['limits']['max_output_bytes'] = None
    value['model_policy']['allowlist'] = {'chatgpt': sorted(ALLOWED_MODELS)}
    value['observability'] = deepcopy(OBSERVABILITY)
    value['correction_brief_sha256'] = None
    return value


def chatgpt_auth_source(path):
    """Describe the external cached login without exporting any credential."""
    source = Path(path).absolute()
    if source.is_relative_to(ROOT.parent.parent) or source.is_symlink():
        raise ValueError('Cached auth must stay outside checkout/evidence, with no symlink')
    from .experiment_isolation import _check_tree
    _check_tree(source)
    value = _strict_load(source.read_bytes())
    tokens = value.get('tokens') or {}
    if value.get('auth_mode') != 'chatgpt' or value.get('OPENAI_API_KEY'):
        raise ValueError('Existing ChatGPT cached login required; no API-key fallback')
    if any(type(tokens.get(name)) is not str or not tokens[name] for name in
           ['access_token', 'refresh_token', 'id_token', 'account_id']):
        raise ValueError('Existing supported Codex cached login is incomplete')
    return {'kind': 'cached_codex_auth', 'authentication': 'chatgpt', 'path': str(source),
            'account_sha256': digest(tokens['account_id'])}


def _model(model):
    if model not in ALLOWED_MODELS:
        raise ValueError('ChatGPT experimental model must be explicitly eligible <=5.5; no fallback')


def chatgpt_wire_schema():
    """Native strict-output framing, independent of the unchanged M2 schema."""
    return {'type':'object','properties':{'reply_json':{'type':'string',
            'description':'The complete original M2 JSON reply encoded as one string.'}},
            'required':['reply_json'],'additionalProperties':False}


def decode_chatgpt_wire_reply(raw):
    """Remove exactly one envelope without repairing or rewriting its string."""
    value=_strict_load(raw)
    if type(value) is not dict or set(value)!={'reply_json'} or type(value['reply_json']) is not str:
        raise ValueError('Native wire reply requires exactly one JSON string')
    return value['reply_json']


def chatgpt_rpc_requests(request, *, thread_id):
    """One process, one new ephemeral thread, one new own-evidence turn."""
    _model(request['model'])
    effort = request['settings'].get('reasoning_effort')
    if effort not in {'none', 'low', 'medium', 'high', 'xhigh'}:
        raise ValueError('Explicit supported reasoning effort required')
    return [
        {'id': 1, 'method': 'initialize', 'params': {'clientInfo': {
            'name': 'intentlineage-reviewer', 'title': 'IntentLineage', 'version': 'm3b-chatgpt.1'},
            'capabilities': {'experimentalApi': True}}},
        {'method': 'initialized', 'params': {}},
        {'id': 2, 'method': 'account/read', 'params': {'refreshToken': False}},
        {'id': 3, 'method': 'model/list', 'params': {'includeHidden': True, 'limit': 100}},
        {'id': 4, 'method': 'thread/start', 'params': {
            'model': request['model'], 'modelProvider': 'openai', 'cwd': '/workspace',
            'approvalPolicy': 'never', 'ephemeral': True, 'baseInstructions': PROMPT_CONTRACT,
            'developerInstructions': WIRE_PACKAGING_INSTRUCTIONS, 'config': {'model_reasoning_effort': effort}}},
        {'id': 5, 'method': 'turn/start', 'params': {
            'threadId': thread_id, 'model': request['model'], 'effort': effort,
            'cwd': '/workspace', 'approvalPolicy': 'never',
            'input': [{'type': 'text', 'text': canonical_bytes(request).decode('utf-8')}],
            'outputSchema': chatgpt_wire_schema()}},
    ]


def chatgpt_event_facts(raw, commands, request, raw_reply, *, exit_code):
    """Replay raw client messages; do not equate a client turn with API attempts."""
    errors = []; events = []
    try:
        for line in raw.splitlines():
            if line.strip(): events.append(_strict_load(line))
    except (ValueError, UnicodeError): errors.append('Malformed/duplicate-key native client event')
    if any(type(x) is not dict for x in events):
        errors.append('Client event must be an object'); events = [x for x in events if type(x) is dict]
    response_ids=[x.get('id') for x in events if 'id' in x and 'result' in x]
    if len(response_ids)!=len(set(response_ids)):errors.append('Duplicate native RPC response')
    if any('id' in x and 'method' in x for x in events):errors.append('Unexpected native server tool/approval request')
    results = {x.get('id'): x.get('result') for x in events if 'id' in x and 'result' in x}
    if any('error' in x and 'id' in x for x in events): errors.append('Client RPC error')
    methods = [x.get('method') for x in commands]
    if methods != ['initialize', 'initialized', 'account/read', 'model/list', 'thread/start', 'turn/start']:
        errors.append('Unexpected request/history surface')
    turn_request = next((x.get('params', {}) for x in commands if x.get('method') == 'turn/start'), {})
    thread_request = next((x.get('params', {}) for x in commands if x.get('method') == 'thread/start'), {})
    thread_id = turn_request.get('threadId')
    if thread_request.get('ephemeral') is not True or thread_request.get('model') != request['model']:
        errors.append('Fresh thread/model policy changed')
    if thread_request.get('baseInstructions') != PROMPT_CONTRACT or thread_request.get('developerInstructions') != WIRE_PACKAGING_INSTRUCTIONS:
        errors.append('Assessment/packaging instruction binding differs')
    if turn_request.get('input') != [{'type': 'text', 'text': canonical_bytes(request).decode()}] or turn_request.get('outputSchema') != chatgpt_wire_schema():
        errors.append('Own prompt/schema binding differs')
    if turn_request.get('model') != request['model'] or turn_request.get('effort') != request['settings'].get('reasoning_effort'):
        errors.append('Own model/settings binding differs')
    account = (results.get(2) or {}).get('account') or {}
    if account.get('type') != 'chatgpt': errors.append('Actual client is not ChatGPT authenticated')
    catalog = (results.get(3) or {}).get('data') or []
    if request['model'] not in {m.get('model') for m in catalog if type(m) is dict}:
        errors.append('Requested model absent from supported client metadata')
    resolved = results.get(4) or {}; thread = resolved.get('thread') or {}
    if thread.get('id') != thread_id or thread.get('turns') or thread.get('ephemeral') is not True:
        errors.append('Inherited or mismatched client thread')
    effective = resolved.get('model')
    if effective != request['model'] or resolved.get('modelProvider') != 'openai': errors.append('Effective client model/provider drift')
    if resolved.get('reasoningEffort') is not None and resolved['reasoningEffort']!=request['settings']['reasoning_effort']:
        errors.append('Effective client reasoning setting drift')
    starts = []; completions = []; messages = []; usage_raw = {}
    for event in events:
        method = event.get('method', ''); params = event.get('params') or {}
        if not method: continue
        if params.get('threadId') is not None and params['threadId'] != thread_id:
            errors.append('Foreign thread event')
        if method == 'turn/started': starts.append(params.get('turn') or {})
        if method == 'turn/completed': completions.append(params.get('turn') or {})
        if method in {'model/rerouted', 'error', 'turn/failed', 'thread/compacted'}:
            errors.append('Client model/retry/failure/history drift: ' + method)
        if method.startswith('item/'):
            item = params.get('item') or {}
            if item.get('type') not in {None, 'agentMessage', 'reasoning', 'userMessage'}:
                errors.append('Unexpected native tool/command/compaction item')
            if method == 'item/completed' and item.get('type') == 'agentMessage' and item.get('phase') in {None, 'final_answer'}:
                messages.append(item.get('text'))
        if method == 'thread/tokenUsage/updated':
            usage_raw = deepcopy((params.get('tokenUsage') or {}).get('last') or {})
    if len(starts) != 1 or len(completions) != 1:
        errors.append('Unknown/multiple logical native turns')
    elif starts[0].get('id') != completions[0].get('id') or completions[0].get('status') != 'completed' or completions[0].get('error'):
        errors.append('Native turn did not complete consistently')
    decoded_sha=None
    try:
        if len(messages) != 1 or messages[0] != raw_reply:
            errors.append('Final reply not bound to native final message')
        else:
            decoded=decode_chatgpt_wire_reply(raw_reply)
            validator=validate_reply
            if request.get('contract_version')=='m3-function-review.1':
                from .review_function import validate_reply as validator
            parsed=validator(decoded, request['evidence'], allow_opening=request['allow_opening'])
            canonical_bytes(parsed) # Reject nonfinite numeric overflow anywhere in the M2 reply.
            decoded_sha=digest(parsed)
    except (ValueError, TypeError): errors.append('Malformed/unbound native reply')
    if exit_code != 0: errors.append('Native client failure or unknown exit')
    return {'complete': not errors, 'errors': sorted(set(errors)), 'logical_turns': len(starts),
            'client_effective_model': effective, 'backend_served_model': None,
            'effective_reasoning_effort':resolved.get('reasoningEffort'),
            'native_wire_schema_sha256':digest(chatgpt_wire_schema()),
            'decoded_m2_reply_sha256':decoded_sha,
            'provider_attempts': None, 'usage_observation': normalize_usage(usage_raw),
            'monetary_cost': None, 'request_sha256': digest(request), 'native_events_sha256': __import__('hashlib').sha256(raw).hexdigest(),
            'identity_basis': 'explicit client thread-start result and completed turn; backend identity unavailable'}


def validate_chatgpt_protocol(protocol, *, require_frozen=False):
    if type(protocol) is dict and protocol.get('format_version') in {'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}:
        from .experiment_function import validate_protocol as validate_function_protocol
        return validate_function_protocol(protocol,require_frozen=require_frozen)
    template = draft_chatgpt_protocol()
    if type(protocol) is not dict or set(protocol) != set(template) or protocol.get('format_version') != CHATGPT_FORMAT:
        raise ValueError('Explicit ChatGPT protocol required')
    for key in ['reviewer', 'dependencies', 'limits', 'bindings']:
        if type(protocol[key]) is not dict or set(protocol[key]) != set(template[key]):
            raise ValueError('Unknown or missing ChatGPT configuration: ' + key)
    if protocol['reviewer'].get('authentication') != 'chatgpt' or protocol['observability'] != OBSERVABILITY or protocol['model_policy'] != template['model_policy']:
        raise ValueError('ChatGPT authentication/observability/model policy changed')
    if protocol['reviewer']['cli_platform'] != 'linux': raise ValueError('Native Linux CLI required')
    for key in ['data_class', 'replacement_policy', 'treatment_failure_policy']:
        if protocol[key] != template[key]: raise ValueError('ChatGPT execution policy changed: ' + key)
    if protocol['dependencies'] != template['dependencies']: raise ValueError('Reviewed source dependency changed')
    base = {k: deepcopy(protocol[k]) for k in draft_protocol()}
    base['format_version'] = draft_protocol()['format_version']
    base['reviewer'] = {k: base['reviewer'][k] for k in draft_protocol()['reviewer']}
    base['dependencies'] = {k: base['dependencies'][k] for k in draft_protocol()['dependencies']}
    validation = validate_protocol(base)
    unresolved = validation['unresolved'][:]
    reviewer = protocol['reviewer']
    if reviewer['model'] is not None: _model(reviewer['model'])
    for name in ['auth_source', 'model_metadata_sha256', 'client_effective_model', 'cli_path']:
        if reviewer.get(name) is None: unresolved.append('reviewer.' + name)
    if reviewer.get('auth_source') is not None:
        if set(reviewer['auth_source']) != {'kind', 'authentication', 'path', 'account_sha256'} or reviewer['auth_source']['authentication'] != 'chatgpt':
            raise ValueError('Narrow cached ChatGPT auth binding required')
    for name, value in protocol['limits'].items():
        if value is None: unresolved.append('limits.' + name)
        elif type(value) is not int or value < 1: raise ValueError('Explicit integer limit required')
    for name, value in protocol['bindings'].items():
        if value is None: unresolved.append('bindings.' + name)
    if protocol['correction_brief_sha256'] is None: unresolved.append('correction_brief_sha256')
    metadata = protocol['bindings']['model_metadata']
    if metadata is not None:
        if metadata.get('source_kind') != 'codex-app-server-model-list' or metadata.get('authentication') != 'chatgpt':
            raise ValueError('Supported Codex metadata required; no API catalogue')
        if reviewer['model_metadata_sha256'] != digest(metadata): raise ValueError('Client metadata binding differs')
        validate_reviewer_model(reviewer['model'], authentication='chatgpt',
                               available_models=metadata['models'], verified_at=metadata['verified_at'])
    ready = protocol['status'] == 'frozen' and not unresolved
    if require_frozen and not ready: raise ValueError('ChatGPT protocol unresolved: ' + ', '.join(unresolved))
    return {**validation, 'unresolved': unresolved, 'ready': ready, 'protocol_sha256': digest(protocol)}


def chatgpt_qualification_request(protocol):
    """Unchanged M2 endpoint request from the reviewed real native evidence."""
    if protocol.get('format_version') in {'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}:
        from .experiment_function import qualification_request
        return qualification_request(ROOT,0)
    from .experiment_isolation import _check_tree
    from .review_batches import validate_evidence
    from .review_contract import build_request
    path=ROOT/QUALIFICATION_INPUT;_check_tree(path)
    evidence=_strict_load(path.read_bytes())
    if type(evidence) is not dict:raise ValueError('Qualification input must be real endpoint evidence')
    validate_evidence(evidence)
    if ({e.get('category') for e in evidence.get('elements',[])}!={'intent','ontology','business_rules'}
        or not (evidence.get('prompt') or {}).get('text')
        or not evidence.get('job_inputs') or not evidence.get('job_outputs')):
        raise ValueError('Qualification input requires full prompt/inventory/whole-job I/O')
    return build_request(evidence,model=protocol['reviewer']['model'],settings=protocol['reviewer']['settings'])


def chatgpt_qualification_contract(protocol):
    if protocol.get('format_version') in {'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}:
        from .experiment_function import qualification_contract
        return qualification_contract(ROOT,protocol)
    from .experiment_user_authorization import qualification_brief_sha256
    validate_chatgpt_protocol(protocol)
    reviewer = protocol['reviewer']; _model(reviewer['model'])
    if any(v is None for v in protocol['limits'].values()) or reviewer['auth_source'] is None:
        raise ValueError('Explicit cached auth and bounded qualification limits required')
    brief = ROOT.parent.parent / 'instructions_between_agents' / CORRECTION_NAME
    if protocol['correction_brief_sha256'] != qualification_brief_sha256(brief, ROOT):
        raise ValueError('Actual user ChatGPT correction brief binding changed')
    own=chatgpt_qualification_request(protocol);evidence=own['evidence']
    return {'scope': 'chatgpt-provider-qualification', 'data_class': 'empirical',
            'brief_sha256': qualification_brief_sha256(brief, ROOT), 'reviewer': deepcopy(reviewer),
            'limits': deepcopy(protocol['limits']), 'observability': deepcopy(OBSERVABILITY),
            'qualification_input':{'path':QUALIFICATION_INPUT,'file_sha256':file_hash(ROOT/QUALIFICATION_INPUT),
                'evidence_sha256':evidence['evidence_sha256'],'inventory_sha256':evidence['inventory_sha256'],
                'capture_sha256':evidence['capture_sha256'],'request_sha256':digest(own)},
            'transport_framing':{'format_version':'m3-codex-wire.1','schema':chatgpt_wire_schema(),
                'native_wire_schema_sha256':digest(chatgpt_wire_schema()),'m2_schema_sha256':digest(REPLY_SCHEMA),
                'packaging_instructions':WIRE_PACKAGING_INSTRUCTIONS,
                'decoding':'exactly one envelope; unchanged M2 validation required'}}


def validate_chatgpt_qualification_review(protocol):
    """The developer cannot issue its own source/configuration approval."""
    from .experiment_execution import controller_source_digest
    contract = chatgpt_qualification_contract(protocol)
    authority = ROOT.parent.parent / 'instructions_between_agents/m3b-qualification-code-overseer-review.md'
    try:
        blocks = re.findall(r'```intentlineage-qualification-code-review\r?\n(.*?)\r?\n```', authority.read_text(encoding='utf-8'), re.S)
        if len(blocks) != 1: raise ValueError('Missing exact review record')
        decision = _strict_load(blocks[0])
        if decision.get('format_version') != 'm3b-qualification-code-review.1' or decision.get('issued_by') != 'overseer' or decision.get('status') != 'approved' or decision.get('synthetic') is not False:
            raise ValueError('Separate qualification review is not approved')
        from .experiment_user_authorization import capture_authorized_launch
        technical_binding=capture_authorized_launch(ROOT,contract,decision)
        if technical_binding['authorized_launch_sha256']!=digest(contract):
            raise ValueError('Qualification capture configuration differs')
        if decision.get('controller_source_sha256') != controller_source_digest():
            from .experiment_user_authorization import validate_source_authorization
            authority_binding=validate_source_authorization(ROOT)
            if decision.get('controller_source_sha256')!=authority_binding['reviewed_source_sha256'] or technical_binding['controller_source_sha256']!=controller_source_digest():
                raise ValueError('User authorization does not cover this source/launch')
        if subprocess.run(['git', 'merge-base', '--is-ancestor', decision['commit'], 'HEAD'], cwd=ROOT, capture_output=True).returncode:
            raise ValueError('Qualification reviewed ancestor missing')
        return {'path': str(authority), 'sha256': file_hash(authority), 'decision': decision, 'contract': contract, 'configuration_disposition':technical_binding}
    except (OSError, KeyError, ValueError) as error:
        raise ValueError('Actual current Overseer ChatGPT qualification code review missing or inconsistent') from error


def chatgpt_permission_config():
    from .experiment_execution import model_permission_config
    value = model_permission_config()
    value['features'].update(apps=False,memories=False,remote_plugin=False,hooks=False,
                              code_mode={'enabled':False})
    value['apps']={'_default':{'enabled':False}}
    # Native 0.160.0 reserves built-in provider IDs. Keep its supported ChatGPT
    # login route; backend retry counters/defaults are not a fabricated zero.
    value.update(forced_login_method='chatgpt', cli_auth_credentials_store='file', model_provider='openai')
    return value


def chatgpt_worker_source(request, *, metadata_only, timeout_seconds, max_output_bytes, probes_only=False):
    """Reuse exact native probe program, then supported credential-free RPC wiring."""
    from .experiment_execution import qualified_worker_source, config_arguments
    permissions = config_arguments(chatgpt_permission_config())
    prefix = qualified_worker_source(request, [], permissions, timeout_seconds,
        probe_binary='/usr/local/bin/intentlineage-codex',namespace_private_canaries=True,
        probes_only=probes_only).split('\nfor path in canaries:path.unlink()\n', 1)[0]
    if probes_only:
        return prefix + '\n'
    commands = chatgpt_rpc_requests(request, thread_id='__FRESH_THREAD__')
    if metadata_only: commands = commands[:4]
    argv = ['/usr/local/bin/intentlineage-codex','app-server','--listen','stdio://', *permissions]
    tail = r'''
for path in canaries:path.unlink()
Path('/home/runner/.codex/sessions').rmdir()
auth_bytes=Path('/runtime/cached-auth.json').read_bytes() # cached login only
auth_value=json.loads(auth_bytes)
if auth_value.get('auth_mode')!='chatgpt' or auth_value.get('OPENAI_API_KEY'):raise ValueError('ChatGPT cached login required')
Path('/home/runner/.codex/auth.json').write_bytes(auth_bytes)
secrets=[auth_value['tokens'][name].encode() for name in ['access_token','refresh_token','id_token'] if auth_value.get('tokens',{}).get(name)]
import time,threading
metadata_only=METADATA_ONLY
commands=RPC_COMMANDS
actual_commands=[];raw_lines=[];stderr_parts=[];started_turn=False;timed_out=False;failure=None
child=subprocess.Popen(CLIENT_ARGV,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=dict(os.environ))
def read_stderr():
    while True:
        part=child.stderr.read(4096)
        if not part:break
        stderr_parts.append(part)
thread=threading.Thread(target=read_stderr,daemon=True);thread.start()
def deadline():
    global timed_out
    if child.poll() is None:timed_out=True;child.kill()
timer=threading.Timer(TIMEOUT,deadline);timer.start()
results={};seen_turns=set();completed=False
try:
    def read_until(expected=None,final=False):
        global completed,failure
        while True:
            line=child.stdout.readline(MAX_BYTES+1)
            if not line:raise ValueError('Native app-server ended before expected completion')
            raw_lines.append(line)
            if sum(map(len,raw_lines))+sum(map(len,stderr_parts))>MAX_BYTES:
                raise ValueError('Native client output-byte stop limit reached; retain partial original')
            event=json.loads(line)
            if event.get('method') in {'error','model/rerouted','turn/failed','thread/compacted'}:
                raise ValueError('Native model/retry/history drift')
            item=event.get('params',{}).get('item') or {}
            if item.get('type') not in {None,'agentMessage','reasoning','userMessage'}:
                raise ValueError('Native model tool request/compaction refused')
            if 'id' in event and 'method' in event:raise ValueError('Unexpected server tool/approval request')
            if event.get('method')=='turn/started':
                turn=event['params']['turn']['id'];seen_turns.add(turn)
                if len(seen_turns)>1:raise ValueError('Multiple native logical turns')
            if expected is not None and event.get('id')==expected:
                if 'error' in event:raise ValueError('Native RPC failed')
                results[expected]=event['result'];return event['result']
            if final and event.get('method')=='turn/completed':
                turn=event['params']['turn']
                if turn.get('status')!='completed' or turn.get('error'):raise ValueError('Native turn incomplete')
                completed=True;return
    for message in commands:
        if message['method']=='turn/start':
            resolved=results[4]
            if resolved.get('model')!=OWN_MODEL or resolved.get('modelProvider')!='openai' or resolved['thread'].get('turns'):
                raise ValueError('Native effective model/history differs before reasoning')
            message['params']['threadId']=resolved['thread']['id'];started_turn=True
        actual_commands.append(message)
        child.stdin.write(json.dumps(message,separators=(',',':'),ensure_ascii=False).encode()+b'\n');child.stdin.flush()
        if 'id' in message:
            result=read_until(message['id'])
            if message['id']==2 and (result.get('account') or {}).get('type')!='chatgpt':raise ValueError('Actual native account is not ChatGPT authenticated')
            if message['id']==3 and not metadata_only:
                if OWN_MODEL not in [x.get('model') for x in result.get('data',[])]:raise ValueError('Eligible <=5.5 model unavailable through existing login')
                entry=next(x for x in result['data'] if x.get('model')==OWN_MODEL)
                if OWN_EFFORT not in [x.get('reasoningEffort') for x in entry.get('supportedReasoningEfforts',[])]:raise ValueError('Requested reasoning setting unavailable for eligible model')
    if not metadata_only:read_until(final=True)
except Exception as error:
    failure=type(error).__name__+': '+str(error)
finally:
    timer.cancel()
    try:child.stdin.close()
    except OSError:pass
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.terminate()
        try:child.wait(timeout=5)
        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
    raw_lines.append(child.stdout.read())
    thread.join(timeout=5)
stdout=b''.join(raw_lines);stderr=b''.join(stderr_parts)
refreshed=Path('/home/runner/.codex/auth.json').read_bytes()
if refreshed!=auth_bytes:Path('/private/quarantine/refreshed-auth.json').write_bytes(refreshed)
if any(value in stdout or value in stderr for value in secrets):
    Path('/private/quarantine/sensitive-stdout.bin').write_bytes(stdout)
    Path('/private/quarantine/sensitive-stderr.bin').write_bytes(stderr)
    print(json.dumps({'probes':probes,'namespaces':namespaces,'fresh_state_before_canaries':True,
        'state_canaries_established':True,'credential_leak':True,'sensitive_original_retained_outside_export':True,
        'provider_review_calls':1 if started_turn else 0,'charging':'unknown_or_charged' if started_turn else 'confirmed_no_turn'}))
    raise SystemExit(0)
for name,raw in [('events.jsonl',stdout),('stdout.bin',stdout),('stderr.txt',stderr),('stderr.bin',stderr)]:Path('/output/'+name).write_bytes(raw)
Path('/output/client-requests.json').write_text(json.dumps(actual_commands),encoding='utf-8')
messages=[]
for line in stdout.splitlines():
    try:event=json.loads(line)
    except ValueError:continue
    item=event.get('params',{}).get('item') or {}
    if event.get('method')=='item/completed' and item.get('type')=='agentMessage' and item.get('phase') in {None,'final_answer'}:messages.append(item.get('text',''))
if len(messages)==1:Path('/output/reply.json').write_text(messages[0],encoding='utf-8')
print(json.dumps({'probes':probes,'namespaces':namespaces,'fresh_state_before_canaries':True,
    'state_canaries_established':True,'metadata_only':metadata_only,'provider_review_calls':1 if started_turn else 0,
    'logical_turns':len(seen_turns),'provider_attempts':None,'credential_leak':False,
    'transport':{'exit_code':child.returncode if (completed or metadata_only) and failure is None else child.returncode or 1,
        'native_process_exit_code':child.returncode,'timed_out':timed_out,'failure':failure,
        'stdout_base64':base64.b64encode(stdout).decode(),'stderr_base64':base64.b64encode(stderr).decode()}}))
'''
    replacements={'METADATA_ONLY':repr(metadata_only),'RPC_COMMANDS':repr(commands),'CLIENT_ARGV':repr(argv),
        'TIMEOUT':repr(timeout_seconds),'MAX_BYTES':repr(max_output_bytes),'OWN_MODEL':repr(request['model']),
        'OWN_EFFORT':repr(request['settings']['reasoning_effort'])}
    return prefix + re.sub(r'\b('+'|'.join(replacements)+r')\b',lambda match:replacements[match.group()],tail)


def _boundary_setup(invocation, request, protocol, runtime, *, action):
    from .experiment_isolation import _linux_path
    from .review_runner import _write
    controller = Path(invocation)/'.controller'; controller.mkdir(exist_ok=True)
    paths = {}
    for name in ['sibling','oracle','source','config']:
        path = controller/(name+'-canary.txt'); path.write_bytes(('private-'+name).encode())
        paths[name] = _linux_path(path)
    source = protocol['reviewer'].get('auth_source')
    return {'action':action,'invocation':_linux_path(invocation),'cli_binary':protocol['reviewer']['cli_path'],
        'expected_cli_sha256':protocol['reviewer']['cli_sha256'],'expected_runtime':runtime,
        'expected_public_network_runtime':(protocol['bindings'].get('model_metadata') or {}).get('public_network_runtime'),
        'auth_source':{**source,'path':_linux_path(source['path'])} if source is not None else None,
        'timeout_seconds':protocol['limits']['max_seconds_per_invocation'],
        'worker_source':chatgpt_worker_source(request,metadata_only=action=='chatgpt-metadata',
            probes_only=action=='chatgpt-probes',timeout_seconds=protocol['limits']['max_seconds_per_invocation'],
            max_output_bytes=protocol['limits']['max_output_bytes']), 'probes':{'paths':paths}}


def inspect_chatgpt_boundary(protocol, directory, *, metadata=False, sandbox=None):
    """Local probes or supported no-turn metadata; never provider qualification."""
    from .experiment_isolation import OfflineSandbox
    from .review_runner import prepare_invocation, _write
    from .review_contract import build_request
    from .experiment_qualification import runtime_identity
    sandbox = sandbox or OfflineSandbox()
    root = Path(directory).resolve()
    if not root.is_relative_to(ROOT) or root.exists(): raise ValueError('Fresh own inspection directory required')
    request = build_request({'elements':[],'evidence_sha256':digest({'inspection':'no model review'})},
                            model=protocol['reviewer'].get('model') or 'gpt-5.5',
                            settings=protocol['reviewer'].get('settings') or {'reasoning_effort':'none'})
    prepare_invocation(root,request)
    runtime = runtime_identity(sandbox.inspect_runtime())
    config = _boundary_setup(root,request,protocol,runtime,action='chatgpt-metadata' if metadata else 'chatgpt-probes')
    raw = sandbox._call(config)
    _write(root/'inspection.json',{'scope':'supported client setup only; no provider qualification',
        'provider_review_calls':0,'provider_qualified':False,'raw':raw})
    return raw


def run_chatgpt_invocation(invocation, request, *, sandbox, protocol, qualification, runtime,
                           qualification_only=False, execution_contract=None):
    from .experiment_transport import _check_invocation
    from .experiment_isolation import IsolationUnavailable
    from .experiment_qualification import REQUIRED_PROBES, seal
    from .experiment_execution import controller_source_digest
    from .review_runner import _write
    invocation = _check_invocation(invocation, request)
    if len(canonical_bytes(request)) > protocol['limits']['max_input_bytes']:
        raise ValueError('Mandatory own request exceeds bounded input bytes; never truncate')
    if qualification_only:
        review=validate_chatgpt_qualification_review(protocol)
        expected_requests=([r['request_sha256'] for r in review['contract']['qualification_inputs']] if 'qualification_inputs' in review['contract'] else [review['contract']['qualification_input']['request_sha256']])
        if digest(request) not in expected_requests:
            raise ValueError('Qualification request differs from reviewed endpoint input')
        admission={'kind':'qualification','contract':review['contract'],'review_sha256':review['sha256']}
    else:
        from .experiment_execution import validate_execution_contract
        if type(execution_contract) is not dict:raise ValueError('Actual ChatGPT campaign authority/release contract required')
        approved=validate_execution_contract(**execution_contract)
        if approved['protocol']!=protocol or approved['qualification']!=qualification:
            raise ValueError('Actual approved ChatGPT execution contract differs')
        admission={'kind':'campaign','contract':execution_contract}
    source = chatgpt_auth_source(protocol['reviewer']['auth_source']['path'])
    if source != protocol['reviewer']['auth_source']: raise ValueError('Cached ChatGPT account/source changed')
    config = _boundary_setup(invocation, request, protocol, runtime, action='chatgpt-provider')
    from .experiment_execution import controller_sources
    from .experiment_isolation import _linux_path
    config.update(admission=admission,source_root=_linux_path(ROOT),controller_source_manifest=controller_sources())
    raw = sandbox._call(config)
    _write(invocation/'.controller/raw-client-launch.json', raw)
    result = raw.get('result') or {}; probes = result.get('probes') or {}
    if set(probes) != REQUIRED_PROBES or any(x is not True for x in probes.values()) or result.get('credential_leak'):
        _write(invocation/'.controller/failed-chatgpt-boundary.json', {
            'qualified':False,'credential_leak':bool(result.get('credential_leak')),
            'request_sha256':digest(request),'raw_sha256':digest(raw)})
        raise IsolationUnavailable('Actual native ChatGPT boundary failed; retained; no permissive fallback')
    if result.get('fresh_state_before_canaries') is not True or result.get('state_canaries_established') is not True:
        raise IsolationUnavailable('Actual client state/canary proof unavailable')
    transport = result.get('transport') or {}
    launch = {'format_version':'m3b-launch.1','data_class':'empirical','authentication':'chatgpt',
        'provider_kind':'actual-chatgpt-codex','credential_persisted':False,
        'request_sha256':digest(request),'model':request['model'],'settings':request['settings'],
        'actual_model':None,'backend_served_model':None,'provider_attempts':None,
        'logical_turns_submitted':result.get('provider_review_calls'),
        'exit_code':transport.get('exit_code'),'timed_out':transport.get('timed_out',False),
        'worker_source_sha256':file_hash(invocation/'.controller/chatgpt-worker.py'),
        'controller_source_sha256':controller_source_digest(), 'auth_binding_sha256':digest(source),
        'native_cli_sha256':protocol['reviewer']['cli_sha256'],'runtime':runtime,
        'limits':deepcopy(protocol['limits']), 'raw_events':raw,
        'qualification_sha256':qualification.get('qualification_sha256'),
        'provider_call_id':digest({'request':digest(request),'argv':raw['argv']})}
    _write(invocation/'launch-receipt.json',launch)
    receipt = seal({'format_version':'m3b-provider-call-isolation.1','data_class':'empirical','synthetic':False,
        'qualified':True,'scope':'actual native client command boundary','request_sha256':digest(request),
        'runtime':runtime,'probes':probes,'provider_transport':'supported ChatGPT cached login; no API proxy',
        'model_command_network':'denied','fresh_session':True,'history_policy':'none',
        'credential_model_access':'denied','raw_events':raw,'argv':raw['argv']})
    _write(invocation/'isolation-receipt.json',receipt)
    return raw,receipt,launch


def validate_chatgpt_call_files(invocation, request, launch, *, limits, historical_source=None):
    import base64
    from .experiment_execution import controller_source_digest
    root = Path(invocation); output = root/'output'
    if launch.get('authentication') != 'chatgpt' or launch.get('provider_kind') != 'actual-chatgpt-codex' or launch.get('data_class') != 'empirical':
        raise ValueError('Actual ChatGPT client call provenance required')
    if launch['request_sha256'] != digest(request) or launch['model'] != request['model'] or launch['settings'] != request['settings']:
        raise ValueError('Actual ChatGPT own request/model/settings differs')
    expected_source=controller_source_digest()
    if historical_source is not None:
        from .experiment_resume import verify_baseline
        if historical_source!=verify_baseline(ROOT):raise ValueError('Unknown historical call source')
        expected_source=historical_source
    if launch['limits'] != limits or launch['controller_source_sha256'] != expected_source:
        raise ValueError('Actual client source/limit binding differs')
    raw = launch['raw_events']; transport = raw['result'].get('transport') or {}
    if _strict_load((root/'.controller/raw-client-launch.json').read_bytes()) != raw:
        raise ValueError('Native client launch differs from retained raw receipt')
    if file_hash(root/'.controller/chatgpt-worker.py') != launch['worker_source_sha256']:
        raise ValueError('Native worker source binding changed')
    expected_worker = chatgpt_worker_source(request, metadata_only=False,
        timeout_seconds=limits['max_seconds_per_invocation'], max_output_bytes=limits['max_output_bytes'])
    if (root/'.controller/chatgpt-worker.py').read_bytes() != expected_worker.encode('utf-8'):
        raise ValueError('Actual worker is not current qualified client/probe source')
    if raw['cli']['native_elf'] is not True or raw['cli']['binary_sha256'] != launch['native_cli_sha256'] or raw['runtime'] != launch['runtime']:
        raise ValueError('Native CLI/runtime raw binding differs')
    if len(canonical_bytes(request)) > limits['max_input_bytes']:
        raise ValueError('Actual own input byte limit exceeded')
    for name,key in [('stdout.bin','stdout_base64'),('stderr.bin','stderr_base64')]:
        if (output/name).read_bytes() != base64.b64decode(transport.get(key,''),validate=True):
            raise ValueError('Raw native client bytes differ from bound launch')
    commands = _strict_load((output/'client-requests.json').read_bytes()) if (output/'client-requests.json').exists() else []
    raw_reply = (output/'reply.json').read_bytes().decode('utf-8') if (output/'reply.json').exists() else ''
    facts = chatgpt_event_facts((output/'stdout.bin').read_bytes(),commands,request,raw_reply,exit_code=launch['exit_code'])
    if launch['timed_out']: facts['errors'].append('Native client timed out'); facts['complete']=False
    if len((output/'stdout.bin').read_bytes()) + len((output/'stderr.bin').read_bytes()) > limits['max_output_bytes']:
        facts['errors'].append('Native output-byte stop limit exceeded');facts['complete']=False
    usage = facts['usage_observation']
    for key,cap in [('input_tokens','max_input_tokens'),('output_tokens','max_output_tokens')]:
        if usage['values'].get(key,0) > limits[cap]:facts['errors'].append('Observed client token stop limit exceeded: '+key);facts['complete']=False
    if usage['errors']: facts['errors'].append('Malformed client usage observation');facts['complete']=False
    no_turn = not any(x.get('method')=='turn/start' for x in commands)
    if launch['logical_turns_submitted']==0 and not no_turn:raise ValueError('Uncharged claim includes a submitted turn')
    if raw_reply and 'Final reply not bound to native final message' in facts['errors']:
        raise ValueError('Native raw reply differs from exact native final message')
    try:decoded=decode_chatgpt_wire_reply(raw_reply)
    except (ValueError,TypeError):decoded=None
    decoded_path=output/'decoded-m2-reply.json'
    saved=output/'real-transport-response.json'
    if decoded_path.exists() and (decoded is None or decoded_path.read_bytes()!=decoded.encode('utf-8')):
        raise ValueError('Decoded M2 reply differs from exact native wire')
    if saved.exists():
        retained=_strict_load(saved.read_bytes())
        if (decoded is not None and not decoded_path.is_file()) or retained.get('raw_reply')!=(decoded if decoded is not None else '') or retained.get('native_wire_reply')!=raw_reply:
            raise ValueError('Retained M2 response differs from exact native wire')
    return {'complete':facts['complete'],'facts':facts,
        'charging':'confirmed_no_turn' if launch['logical_turns_submitted']==0 and no_turn else 'unknown_or_charged'}


def collect_chatgpt_response(invocation,request,*,launch,protocol,qualification_only=False):
    from .review_provider import collect_provider_response
    from .review_runner import _write
    facts = validate_chatgpt_call_files(invocation,request,launch,limits=protocol['limits'])
    observed = facts['facts']
    response = collect_provider_response(invocation, provider_call_id=launch['provider_call_id'],
        usage=observed['usage_observation']['raw'],exit_code=launch['exit_code'])
    output = Path(invocation)/'output'
    wire_reply=(output/'reply.json').read_bytes().decode('utf-8') if (output/'reply.json').exists() else ''
    try:decoded_reply=decode_chatgpt_wire_reply(wire_reply)
    except (ValueError,TypeError):decoded_reply=None
    if decoded_reply is not None:_write(output/'decoded-m2-reply.json',decoded_reply,raw=True)
    response.update(raw_reply=decoded_reply if decoded_reply is not None else '',native_wire_reply=wire_reply,
        native_wire_schema_sha256=digest(chatgpt_wire_schema()),
        raw_events=(output/'stdout.bin').read_bytes().decode('utf-8',errors='replace'),
        raw_stdout=(output/'stdout.bin').read_bytes().decode('utf-8',errors='replace'),
        raw_stderr=(output/'stderr.bin').read_bytes().decode('utf-8',errors='replace'),
        exit_code=launch['exit_code'],data_class='empirical',synthetic=False,mocked=False,recorded_only=False,
        authentication='chatgpt',usage_status=observed['usage_observation']['status'],
        usage_source='thread/tokenUsage/updated.tokenUsage.last; normalized by accepted M2',
        launch_sha256=digest(launch),qualification_only=qualification_only,
        admissible_for_campaign=not qualification_only and facts['complete'],
        charging=facts['charging'],logical_turns_observed=observed['logical_turns'],
        provider_requests_observed=None,backend_served_model=None,client_effective_model=observed['client_effective_model'],
        monetary_cost=None,monetary_cost_semantics='ChatGPT account usage; no API price formula',
        native_client_facts=observed)
    if not facts['complete']:
        response['failure']={'reason':'; '.join(observed['errors']),'exit_code':launch['exit_code']}
        if protocol.get('response_policy') and not qualification_only:
            from .review_failures import assessment_failure
            classification=assessment_failure(wire_reply,request,observed,charging=facts['charging'],probes=launch['raw_events']['result']['probes'])
            if classification:response['failure']['classification']=classification
    _write(output/'real-transport-response.json',response)
    return response


class ChatGPTProviderFactory:
    """M2 provider factory only; same controller, calls, disclosure and replay."""
    def __init__(self,execution_contract,*,sandbox=None):
        from .experiment_execution import validate_execution_contract
        from .experiment_isolation import OfflineSandbox
        if type(execution_contract) is not dict:raise ValueError('Actual ChatGPT protocol/qualification/release required')
        self.context=validate_execution_contract(**execution_contract)
        if self.context['protocol']['reviewer']['authentication']!='chatgpt':raise ValueError('ChatGPT protocol required')
        self.sandbox=sandbox or OfflineSandbox();self.providers={};self.stop_reason=None
        p=self.context['protocol']
        self.qualification_root=ROOT/self.context['qualification']['artifact_directory']
        self.identity={'kind':'m3b-qualified-chatgpt','authentication':'chatgpt','model':p['reviewer']['model'],
            'cli_sha256':p['reviewer']['cli_sha256'],'settings':p['reviewer']['settings'],
            'qualification_sha256':self.context['qualification']['qualification_sha256'],
            'retry_owner':'existing M2 controller; backend attempts unknown unless client reports'}

    def verify(self):
        from .experiment_execution import validate_execution_contract
        if self.stop_reason:raise ValueError('Actual campaign stopped on native client drift: '+self.stop_reason)
        validate_execution_contract(**{k:self.context[k] for k in ['protocol','gates','qualification']})

    def inspect_runtime(self):
        from .experiment_qualification import assert_runtime_matches
        p=self.context['protocol'];raw=self.sandbox._call({'action':'inspect-provider','cli_binary':p['reviewer']['cli_path']})
        assert_runtime_matches(self.context['qualification']['runtime'],raw['runtime'])
        if raw['cli']['binary_sha256']!=p['reviewer']['cli_sha256'] or raw['cli']['version']!=p['reviewer']['cli_version']:
            raise ValueError('Actual native CLI drift')
        return raw['runtime']

    def stage_qualification(self,campaign_root):
        import shutil
        target=Path(campaign_root)/self.context['qualification']['artifact_directory']
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(self.qualification_root,target)

    def __call__(self,arm):
        from .review_runner import ARMS
        self.verify()
        if arm not in ARMS:raise ValueError('Unknown review arm')
        provider=ChatGPTReviewerTransport(self);self.providers[arm]=provider;return provider


class ChatGPTReviewerTransport:
    def __init__(self,owner):self.owner=owner;self.receipts=[];self.calls=0

    def __call__(self,request,invocation):
        from .review_runner import TransportFailure
        self.owner.verify();p=self.owner.context['protocol']
        if request['model']!=p['reviewer']['model'] or request['settings']!=p['reviewer']['settings']:
            raise ValueError('Frozen native client model/settings differs')
        try:
            raw,receipt,launch=run_chatgpt_invocation(invocation,request,sandbox=self.owner.sandbox,
                protocol=p,qualification=self.owner.context['qualification'],runtime=self.owner.inspect_runtime(),
                execution_contract={k:self.owner.context[k] for k in ['protocol','gates','qualification']})
            self.receipts.append(receipt);self.calls+=1
            response=collect_chatgpt_response(invocation,request,launch=launch,protocol=p)
        except Exception:
            self.owner.stop_reason='boundary/source/auth/runtime failure; retain current invocation';raise
        if response['charging']=='confirmed_no_turn':
            self.owner.stop_reason='client/auth/model failure before any turn'
            raise TransportFailure('Supported client proves no review turn was submitted')
        content=response.get('failure',{}).get('classification',{}).get('kind')=='invalid_response' if response.get('failure') else False
        if not response['native_client_facts']['complete'] and not content:
            self.owner.stop_reason='client completion/model/tool/retry/schema drift'
        return response


def qualify_chatgpt_provider(protocol,directory,*,sandbox=None):
    from .experiment_isolation import OfflineSandbox, _check_tree
    from .experiment_qualification import runtime_identity,assert_runtime_matches
    from .experiment_execution import controller_source_digest
    from .review_runner import prepare_invocation,_write
    review=validate_chatgpt_qualification_review(protocol)
    if protocol['limits']['qualification_max_calls']!=2:raise ValueError('Exactly two separate qualification turns required')
    root=Path(directory).resolve()
    if not root.is_relative_to(ROOT) or root==ROOT or root.exists():raise ValueError('Fresh own qualification directory required')
    _check_tree(root.parent)
    if chatgpt_auth_source(protocol['reviewer']['auth_source']['path'])!=protocol['reviewer']['auth_source']:
        raise ValueError('Cached account/auth source changed')
    sandbox=sandbox or OfflineSandbox()
    inspection=sandbox._call({'action':'inspect-provider','cli_binary':protocol['reviewer']['cli_path']})
    if inspection['cli']['binary_sha256']!=protocol['reviewer']['cli_sha256'] or inspection['cli']['version']!=protocol['reviewer']['cli_version']:
        raise ValueError('Reviewed native CLI differs')
    runtime=runtime_identity(inspection['runtime']);root.mkdir(parents=True)
    _write(root/'launch-settings.json',{'contract':review['contract'],'protocol':deepcopy(protocol),'runtime':runtime,
        'controller_source_sha256':controller_source_digest(),'campaign_authorized':False})
    (root/'qualification-code-overseer-review.md').write_bytes(Path(review['path']).read_bytes())
    function_mode=protocol.get('format_version') in {'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}
    if function_mode:
        for record in review['contract']['qualification_inputs']:
            for field,suffix in [('request_path','request'),('controller_evidence_path','controller')]:
                with (root/(record['kind']+'-'+suffix+'.json')).open('xb') as stream:stream.write((ROOT/record[field]).read_bytes())
    else:
        with (root/'qualification-endpoint.json').open('xb') as stream:stream.write((ROOT/QUALIFICATION_INPUT).read_bytes())
    calls=[];threads=[]
    try:
        for index in range(2):
            if function_mode:
                from .experiment_function import qualification_request
                request=qualification_request(ROOT,index)
            else:request=chatgpt_qualification_request(protocol)
            invocation=root/f'invocation-{index+1:02d}';prepare_invocation(invocation,request)
            raw,receipt,launch=run_chatgpt_invocation(invocation,request,sandbox=sandbox,protocol=protocol,
                qualification={},runtime=runtime,qualification_only=True)
            response=collect_chatgpt_response(invocation,request,launch=launch,protocol=protocol,qualification_only=True)
            if response.get('failure'):raise ValueError('Actual native client qualification failed; originals retained')
            commands=_strict_load((invocation/'output/client-requests.json').read_bytes())
            thread=next(x['params']['threadId'] for x in commands if x['method']=='turn/start')
            if thread in threads:raise ValueError('Native qualification reused a thread')
            threads.append(thread)
            calls.append({'directory':invocation.relative_to(root).as_posix(),'request_sha256':digest(request),
                'launch_sha256':digest(launch),'response_sha256':digest(response),'usage':response['usage'],
                'usage_observation':response['usage_observation'],'thread_id':thread,'logical_calls':1,
                'provider_attempts':None,'monetary_cost':None,'probes':receipt['probes']})
        final=sandbox._call({'action':'inspect-provider','cli_binary':protocol['reviewer']['cli_path']})
        assert_runtime_matches(runtime,final['runtime'])
        if final['cli']!=inspection['cli']:raise ValueError('Native CLI changed during qualification')
        metadata=deepcopy(protocol['bindings']['model_metadata'])
        if metadata is None:
            first=root/calls[0]['directory']/'output/stdout.bin'
            client_events=[_strict_load(line) for line in first.read_bytes().splitlines() if line.strip()]
            models=next(e['result']['data'] for e in client_events if e.get('id')==3)
            metadata={'source_kind':'codex-app-server-model-list','authentication':'chatgpt','data_class':'empirical',
                'models':sorted({item['model'] for item in models}),
                'verified_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
                'raw_client_stdout_sha256':file_hash(first),'account_access_basis':'two actual completed native qualification turns; catalog alone may be cached'}
        bound=deepcopy(protocol['reviewer']);bound['client_effective_model']=bound['model'];bound['model_metadata_sha256']=digest(metadata)
        packet={'format_version':'m3b-chatgpt-qualification.1','data_class':'empirical','synthetic':False,'qualified':True,
            'artifact_directory':root.relative_to(ROOT).as_posix(),'reviewer':bound,'runtime':runtime,
            'probes':calls[0]['probes'],'history_policy':'none','fresh_sessions':True,
            'credential_model_access':'denied','model_command_network':'denied',
            'controller_source_sha256':controller_source_digest(),'model_metadata':metadata,
            'calls':calls,'observability':deepcopy(OBSERVABILITY),'qualification_costs_separate':True,
            'files':{p.relative_to(root).as_posix():file_hash(p) for p in root.rglob('*') if p.is_file()}}
        packet['qualification_sha256']=digest(packet);_write(root/'qualification.json',packet)
        return packet
    except Exception as error:
        _write(root/'qualification-failure.json',{'qualified':False,'scope':'ChatGPT qualification only',
            'error_class':type(error).__name__,'retained_originals':True,'campaign_authorized':False})
        raise


def validate_chatgpt_qualification(packet,*,protocol,evidence_root=None):
    """Recompute genuine client receipts; a cached catalog or fixture is insufficient."""
    from .experiment_isolation import _check_tree
    from .experiment_execution import controller_source_digest
    from .experiment_qualification import REQUIRED_PROBES,assert_runtime_matches
    if type(packet) is not dict or packet.get('format_version')!='m3b-chatgpt-qualification.1' or packet.get('data_class')!='empirical' or packet.get('synthetic') is not False or packet.get('qualified') is not True:
        raise ValueError('Actual ChatGPT qualification missing; recorded fixtures cannot qualify')
    if packet.get('qualification_sha256')!=digest({k:v for k,v in packet.items() if k!='qualification_sha256'}):
        raise ValueError('Actual ChatGPT qualification seal differs')
    if packet['controller_source_sha256']!=controller_source_digest() or packet['reviewer']!=protocol['reviewer']:
        raise ValueError('Qualified ChatGPT source/model/auth/CLI/settings differs')
    if packet['observability']!=OBSERVABILITY or packet['history_policy']!='none' or packet['fresh_sessions'] is not True:
        raise ValueError('Qualified ChatGPT observability/history policy differs')
    if packet['credential_model_access']!='denied' or packet['model_command_network']!='denied':
        raise ValueError('Qualified credential/native command separation missing')
    if set(packet['probes'])!=REQUIRED_PROBES or any(v is not True for v in packet['probes'].values()):
        raise ValueError('Actual native denial/positive controls unavailable')
    if protocol['bindings']['qualification_sha256']!=packet['qualification_sha256'] or protocol['bindings']['model_metadata']!=packet['model_metadata']:
        raise ValueError('Frozen qualification/client metadata differs')
    base=Path(evidence_root or ROOT).resolve();root=(base/packet['artifact_directory']).resolve()
    if not root.is_relative_to(base) or root==base:raise ValueError('Qualification evidence escapes bound root')
    _check_tree(root)
    files={p.relative_to(root).as_posix():file_hash(p) for p in root.rglob('*') if p.is_file() and p.name!='qualification.json'}
    if files!=packet['files']:raise ValueError('Actual qualification exact membership/hashes differ')
    settings=_strict_load((root/'launch-settings.json').read_bytes());contract=settings['contract']
    authority=ROOT.parent.parent/'instructions_between_agents/m3b-qualification-code-overseer-review.md'
    if authority.read_bytes()!=(root/'qualification-code-overseer-review.md').read_bytes():raise ValueError('Qualification authority anchor differs')
    blocks=re.findall(r'```intentlineage-qualification-code-review\r?\n(.*?)\r?\n```',authority.read_text(encoding='utf-8'),re.S)
    if len(blocks)!=1:raise ValueError('Qualification approval record missing')
    decision=_strict_load(blocks[0])
    if decision.get('issued_by')!='overseer' or decision.get('status')!='approved' or decision.get('synthetic') is not False:
        raise ValueError('Actual ChatGPT code/configuration review changed')
    from .experiment_user_authorization import capture_authorized_launch
    technical_binding=capture_authorized_launch(ROOT,contract,decision)
    if decision.get('controller_source_sha256')!=controller_source_digest():
        from .experiment_user_authorization import validate_source_authorization
        authority_binding=validate_source_authorization(ROOT)
        if decision.get('controller_source_sha256')!=authority_binding['reviewed_source_sha256'] or technical_binding['controller_source_sha256']!=controller_source_digest():
            raise ValueError('User qualification source authorization changed')
    if subprocess.run(['git','merge-base','--is-ancestor',decision['commit'],'HEAD'],cwd=ROOT,capture_output=True).returncode:
        raise ValueError('Qualification reviewed source ancestor unavailable')
    original=settings['protocol']
    if chatgpt_qualification_contract(original)!=contract or contract['limits']!=protocol['limits']:
        raise ValueError('Qualification launch/auth/limit contract differs')
    function_mode=protocol.get('format_version') in {'m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}
    if function_mode:
        from .experiment_function import qualification_request
        own_requests=[qualification_request(ROOT,i) for i in range(2)]
        for record in contract['qualification_inputs']:
            for field,suffix,hashfield in [('request_path','request','request_file_sha256'),('controller_evidence_path','controller','controller_evidence_file_sha256')]:
                if file_hash(root/(record['kind']+'-'+suffix+'.json'))!=record[hashfield]:raise ValueError('Exact function qualification snapshot changed')
    else:
        input_path=root/'qualification-endpoint.json'
        if file_hash(input_path)!=contract['qualification_input']['file_sha256']:
            raise ValueError('Qualification endpoint snapshot differs from reviewed input')
        from .review_contract import build_request
        own=build_request(_strict_load(input_path.read_bytes()),model=original['reviewer']['model'],settings=original['reviewer']['settings'])
        if digest(own)!=contract['qualification_input']['request_sha256']:
            raise ValueError('Qualification endpoint/request binding differs')
        own_requests=[own,own]
    if len(packet['calls'])!=2 or len({c['thread_id'] for c in packet['calls']})!=2:
        raise ValueError('Two separate fresh genuine qualification threads required')
    for index,call in enumerate(packet['calls']):
        folder=(root/call['directory']).resolve()
        if not folder.is_relative_to(root):raise ValueError('Qualification call escapes root')
        request=_strict_load((folder/'evidence/request.json').read_bytes())
        if request!=own_requests[index]:raise ValueError('Qualification request differs from bound endpoint/function input')
        launch=_strict_load((folder/'launch-receipt.json').read_bytes())
        response=_strict_load((folder/'output/real-transport-response.json').read_bytes())
        if digest(request)!=call['request_sha256'] or digest(launch)!=call['launch_sha256'] or digest(response)!=call['response_sha256']:
            raise ValueError('Actual qualification summary differs from raw files')
        facts=validate_chatgpt_call_files(folder,request,launch,limits=protocol['limits'])
        if not facts['complete'] or facts['facts']['logical_turns']!=1 or facts['facts']['client_effective_model']!=protocol['reviewer']['model']:
            raise ValueError('Genuine client qualification completion/model unavailable')
        if facts['facts']!=response['native_client_facts'] or facts['facts']['usage_observation']!=response['usage_observation']:
            raise ValueError('Client receipt/partial usage replay differs')
        if response.get('failure') or response.get('synthetic') is not False or response.get('mocked') is not False:
            raise ValueError('Failed or recorded reply cannot qualify')
        if call['usage']!=response['usage'] or call['usage_observation']!=response['usage_observation'] or call['logical_calls']!=1 or call['provider_attempts'] is not None or call['monetary_cost'] is not None:
            raise ValueError('Qualification counters are not native observations')
        if call['probes']!=packet['probes'] or launch['raw_events']['result']['probes']!=packet['probes']:
            raise ValueError('Native qualification probe summary differs')
        assert_runtime_matches(packet['runtime'],launch['runtime'])
    return {'qualified':True,'qualification_sha256':packet['qualification_sha256'],
            'scope':'actual ChatGPT client; backend attempts/identity/cost may remain unavailable',
            'qualification_costs_separate':True}


def prepare_chatgpt_qualification_plan(protocol,*,output):
    from .review_runner import _write
    import sys
    validation=validate_chatgpt_protocol(protocol);blockers=[]
    for field in ['model','settings','auth_source','cli_path','cli_sha256','cli_version','model_metadata_sha256']:
        if protocol['reviewer'][field] is None:blockers.append('reviewer.'+field)
    if any(v is None for v in protocol['limits'].values()):blockers.append('qualification_limits')
    try:review=validate_chatgpt_qualification_review(protocol)
    except (OSError,ValueError,KeyError,TypeError):blockers.append('qualification_code_review')
    result={'format_version':'m3b-chatgpt-qualification-plan.1','executed':False,'provider_qualified':False,
        'authentication':'chatgpt','hosted_launch_actor':'experiment_developer_or_human',
        'blockers':blockers,'validation':validation,'campaign_commands':[],
        'qualification_command':None if blockers else [sys.executable,str(ROOT/'scripts/m3b.py'),'human-qualify',
            '--protocol','<reviewed-chatgpt-qualification-settings.json>','--output','<fresh-qualified-directory>'],
        'qualification_costs_separate':True,'observability':deepcopy(OBSERVABILITY)}
    _write(output,result);return result
