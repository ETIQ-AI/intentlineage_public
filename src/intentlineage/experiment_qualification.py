"""Offline probes and gated actual qualification; no provider is qualified here."""
from copy import deepcopy

from .native_capture import digest
from .experiment_protocol import _hash

REQUIRED_PROBES = frozenset({'own_package', 'readonly', 'sibling', 'oracle', 'source', 'config',
                            'session', 'home', 'temp', 'symlink', 'process', 'environment',
                            'private_state', 'network'})

RUNTIME_FIELDS=frozenset({'bubblewrap_version','binary_sha256','python_version',
    'python_binary_sha256','python_executable','kernel','os_release'})


def runtime_identity(runtime):
    """Persistent runtime identity, including build and interpreter bytes.

    Launch PID/namespace/nonce fields belong in raw launch records, never here.
    No existing runtime field is dropped or normalized to forgive drift.
    """
    if type(runtime) is not dict or set(runtime)!=RUNTIME_FIELDS:
        raise ValueError('Runtime identity needs the exact qualified field set')
    if any(type(v) is not str or not v for v in runtime.values()):
        raise ValueError('Runtime identity fields must be explicit nonempty strings')
    for key in ['binary_sha256','python_binary_sha256']:
        if not _hash(runtime[key],64):raise ValueError('Runtime binary binding missing')
    if not runtime['python_executable'].startswith('/'):
        raise ValueError('Runtime interpreter path is not an absolute Linux path')
    return deepcopy(runtime)


def assert_runtime_matches(expected,actual):
    if runtime_identity(expected)!=runtime_identity(actual):
        raise ValueError('Qualified runtime changed; preserve raw receipts and requalify')
    return True


def validate_provider_qualification(receipt,*,protocol,evidence_root=None):
    """Validate actual provider/control-plane and native command probe evidence.

    Qualification costs belong to this report, never outcome rows. Positive
    declarations without exact raw files and matching scope cannot qualify.
    """
    if type(protocol) is dict and protocol.get('format_version') in {'m3b-chatgpt-protocol.1','m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2','m3b-chatgpt-single-protocol.1'}:
        from .experiment_chatgpt import validate_chatgpt_qualification
        return validate_chatgpt_qualification(receipt,protocol=protocol,evidence_root=evidence_root)
    from pathlib import Path
    from .native_capture import ROOT,file_hash
    from .experiment_isolation import _check_tree
    from .experiment_protocol import validate_reviewer_model
    from .review_contract import _strict_load
    from .experiment_execution import controller_source_digest,validate_actual_call_files
    if type(receipt) is not dict or receipt.get('format_version')!='m3b-provider-qualification.1':
        raise ValueError('Actual provider qualification is missing')
    if receipt.get('data_class')!='empirical' or receipt.get('synthetic') is not False or receipt.get('qualified') is not True:
        raise ValueError('Offline/recorded/synthetic receipts cannot qualify an actual provider')
    if receipt.get('qualification_sha256')!=digest({k:v for k,v in receipt.items() if k!='qualification_sha256'}):
        raise ValueError('Provider qualification integrity mismatch')
    reviewer=protocol['reviewer']
    for key in ['model','actual_model','settings','cli_sha256','cli_version','authentication']:
        if digest(receipt.get('reviewer',{}).get(key))!=digest(reviewer.get(key)):
            raise ValueError('Qualified reviewer/model/CLI/settings changed')
    runtime_identity(receipt['runtime'])
    probes=receipt.get('probes',{})
    if set(probes)!=REQUIRED_PROBES or any(value is not True for value in probes.values()):
        raise ValueError('Actual native model-command probes missing or failed')
    if receipt.get('credential_model_access')!='denied' or receipt.get('model_command_network')!='denied':
        raise ValueError('Provider credentials/command networking are not separated')
    if receipt.get('history_policy')!='none' or receipt.get('fresh_sessions') is not True:
        raise ValueError('Qualified provider sessions must be fresh')
    base=Path(evidence_root or ROOT).resolve();root=(base/receipt['artifact_directory']).resolve()
    if not root.is_relative_to(base) or root==base:raise ValueError('Qualification evidence directory escapes its bound root')
    _check_tree(root)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-{'qualification.json'}
    if actual!=set(receipt['files']):raise ValueError('Qualification exact file membership mismatch')
    for name,expected in receipt['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or file_hash(path)!=expected:raise ValueError('Qualification raw file binding mismatch')
    raw=_strict_load((root/'raw-provider-proof.json').read_bytes())
    if raw.get('data_class')!='empirical' or raw.get('provider_kind')!='actual-openai-api' or raw.get('credential_persisted') is not False:
        raise ValueError('Recorded/local provider source cannot be relabelled as actual qualification')
    if raw.get('runtime')!=receipt['runtime'] or digest(raw.get('command_probes'))!=digest(probes):
        raise ValueError('Qualification summary disagrees with raw runtime/probes')
    if raw.get('native_cli_binary_sha256')!=reviewer['cli_sha256'] or raw.get('forwarded_requests',0)<1:
        raise ValueError('No actual qualified CLI/provider invocation')
    catalog=raw.get('model_catalog',{})
    if catalog.get('source_kind')!='qualified-provider-catalog' or catalog.get('data_class')!='empirical':
        raise ValueError('Actual authenticated model catalogue required')
    validate_reviewer_model(reviewer['model'],authentication=reviewer['authentication'],available_models=catalog['models'],verified_at=catalog['verified_at'])
    if any(model!=reviewer['actual_model'] for model in raw.get('actual_models',[])) or not raw.get('actual_models'):
        raise ValueError('Actual model identity is not qualified consistently')
    if raw.get('tool_or_internal_retry_detected') is not False or raw.get('completion_and_usage_verified') is not True:
        raise ValueError('Genuine completion/usage/internal retry policy remains unqualified')
    if raw.get('controller_source_sha256')!=controller_source_digest() or receipt.get('controller_source_sha256')!=controller_source_digest():
        raise ValueError('Actual qualification source differs from current reviewed implementation')
    if protocol['bindings']['qualification_sha256']!=receipt['qualification_sha256']:
        raise ValueError('Frozen protocol does not bind this actual qualification')
    if protocol['bindings']['model_catalog']!=catalog or reviewer['model_catalog_sha256']!=digest(catalog):
        raise ValueError('Qualified/frozen model catalogue differs')
    catalog_raw=_strict_load((root/'model-catalog.bin').read_bytes())
    if sorted({m['id'] for m in catalog_raw['data']})!=catalog['models'] or file_hash(root/'model-catalog.bin')!=catalog['raw_sha256']:
        raise ValueError('Actual catalogue summary differs from raw authenticated response')
    if raw.get('calls')!=receipt.get('calls') or len(raw['calls'])!=2:
        raise ValueError('Two fresh bound qualification calls required')
    settings=_strict_load((root/'launch-settings.json').read_bytes())
    limits={'max_input_tokens':settings['contract']['max_input_tokens'],'max_input_bytes':settings['contract']['max_input_bytes'],
        'max_output_tokens':settings['contract']['max_output_tokens']}
    for call in raw['calls']:
        folder=(root/call['directory']).resolve()
        if not folder.is_relative_to(root):raise ValueError('Qualification invocation escapes root')
        request=_strict_load((folder/'evidence/request.json').read_bytes())
        launch=_strict_load((folder/'launch-receipt.json').read_bytes())
        response=_strict_load((folder/'output/real-transport-response.json').read_bytes())
        if digest(request)!=call['request_sha256'] or digest(launch)!=call['launch_sha256'] or digest(response)!=call['response_sha256']:
            raise ValueError('Qualification summary inconsistent with actual call files')
        facts=validate_actual_call_files(folder,request,launch,limits=limits)
        if not facts['complete'] or not facts['facts']['usage_observation']['complete']:
            raise ValueError('Actual qualification completion/usage unavailable')
        if launch['raw_events']['received_requests']!=1 or call['probes']!=probes or launch['raw_events']['result']['probes']!=probes:
            raise ValueError('Actual qualification retry/probe summary differs')
        assert_runtime_matches(receipt['runtime'],launch['runtime'])
    return {'qualified':True,'qualification_sha256':receipt['qualification_sha256'],'scope':'actual-provider',
            'qualification_costs_separate':True}


def seal(receipt):
    value = deepcopy(receipt)
    value.pop('receipt_sha256', None)
    value['receipt_sha256'] = digest(value)
    return value


def validate_qualification(receipt, *, request_sha256=None, scope='offline'):
    """Checks complete receipts, never promotes offline probes to a provider proof."""
    if not isinstance(receipt, dict) or receipt.get('receipt_sha256') != digest({k: v for k, v in receipt.items() if k != 'receipt_sha256'}):
        raise ValueError('Isolation receipt hash mismatch')
    if scope != 'offline' or receipt.get('scope') != 'offline':
        raise ValueError('Actual provider transport and model-command isolation are not qualified by preparation')
    if receipt.get('format_version') != 'm3b-isolation.1' or receipt.get('qualified') is not True:
        raise ValueError('Unqualified preparation boundary')
    if receipt.get('synthetic') is not True or receipt.get('real_provider_qualified') is not False:
        raise ValueError('Offline synthetic scope is required')
    if receipt.get('provider_transport') != 'disabled' or receipt.get('model_command_network') != 'denied':
        raise ValueError('Offline provider transport must be disabled and command network denied')
    if receipt.get('fresh_session') is not True or receipt.get('history_policy') != 'none':
        raise ValueError('Fresh session with no inherited history required')
    probes = receipt.get('probes', {})
    if set(probes) != REQUIRED_PROBES or any(v is not True for v in probes.values()):
        raise ValueError('Missing or failed positive/denial probe')
    if not isinstance(receipt.get('request_sha256'), str) or not receipt['request_sha256']:
        raise ValueError('Missing request binding')
    if request_sha256 is not None and receipt['request_sha256'] != request_sha256:
        raise ValueError('Qualification request binding mismatch')
    if not receipt.get('argv') or not receipt.get('raw_events'):
        raise ValueError('Missing raw launch evidence')
    for key in ['worker_sha256', 'supervisor_sha256', 'launcher_sha256']:
        if not _hash(receipt.get('bindings', {}).get(key), 64): raise ValueError('Missing isolation source binding')
    if not _hash(receipt.get('runtime', {}).get('binary_sha256'), 64):
        raise ValueError('Missing sandbox runtime identity')
    raw = receipt['raw_events']
    if not isinstance(raw, dict) or raw.get('exit_code') != 0 or type(raw.get('exit_code')) is not int:
        raise ValueError('Missing successful raw boundary exit status')
    result = raw.get('result', {})
    if not isinstance(result, dict) or digest(result.get('probes')) != digest(probes):
        raise ValueError('Probe summary disagrees with retained raw launch')
    if raw.get('runtime') != receipt['runtime'] or raw.get('argv') != receipt['argv']:
        raise ValueError('Runtime/argv summary disagrees with retained raw launch')
    request_file = receipt.get('request_file_sha256')
    if not _hash(request_file, 64) or result.get('request_file_sha256') != request_file:
        raise ValueError('Own evidence read disagrees with retained request file binding')
    return {'qualified': True, 'scope': 'offline', 'real_provider_qualified': False,
            'receipt_sha256': receipt['receipt_sha256']}


def qualify_offline(directory, *, sandbox=None):
    # Same reviewer transport and same M3A launcher; no separate qualification runner.
    from pathlib import Path
    from .review_runner import prepare_invocation
    from .review_contract import build_request
    from .experiment_transport import ReviewerTransport
    request = build_request({'evidence_sha256': 'offline-probe', 'elements': []},
                            model='offline-probe-no-model-call', settings={})
    directory = Path(directory)
    prepare_invocation(directory, request)
    provider = ReviewerTransport(sandbox=sandbox, probes_only=True)
    return provider(request, directory)


def qualify_provider(protocol,directory,*,api_key,sandbox=None):
    """Explicit authorized-operator entry point; never called by preparation.

    Runs two fresh qualification invocations, using the existing M2 staging and
    M3A launcher. These calls and costs cannot enter scientific denominators.
    Failure preserves the fresh directory and emits no qualified packet.
    """
    raise ValueError('API-key qualification is historical; current authorization requires ChatGPT cached Codex login')
    import json
    from datetime import datetime,timezone
    from pathlib import Path
    import urllib.request
    from .native_capture import ROOT,file_hash
    from .review_contract import build_request,_strict_load
    from .review_runner import prepare_invocation,_write
    from .experiment_protocol import validate_execution_protocol,validate_reviewer_model
    from .experiment_execution import qualification_launch_contract,controller_source_digest
    from .experiment_isolation import OfflineSandbox,_check_tree
    from .experiment_transport import run_qualified_invocation,collect_real_response
    validate_execution_protocol(protocol)
    reviewer=protocol['reviewer'];limits=protocol['limits']
    if reviewer['authentication']!='api_key' or reviewer['model'] is None:
        raise ValueError('Explicit eligible API model route required; no automatic selection')
    contract=qualification_launch_contract(model=reviewer['model'],max_calls=limits['qualification_max_calls'],
        max_input_tokens=limits['max_input_tokens'],max_output_tokens=limits['max_output_tokens'],
        max_input_bytes=limits['max_input_bytes'],timeout_seconds=limits['max_seconds_per_invocation'],reviewer=reviewer)
    if contract['max_calls']!=2:raise ValueError('Qualification requires exactly two bounded fresh invocations')
    root=Path(directory).resolve()
    if not root.is_relative_to(ROOT) or root==ROOT:raise ValueError('Qualification must have a fresh controller-private checkout directory')
    _check_tree(root.parent)
    if root.exists():raise ValueError('Never overwrite prior qualification evidence')
    if not api_key:raise ValueError('Provider credential is missing; never supply it in argv/evidence')
    sandbox=sandbox or OfflineSandbox()
    inspection=sandbox._call({'action':'inspect-provider','cli_binary':reviewer['cli_path']})
    if inspection['cli']['binary_sha256']!=reviewer['cli_sha256'] or inspection['cli']['version']!=reviewer['cli_version']:
        raise ValueError('CLI differs from reviewed qualification settings')
    runtime=runtime_identity(inspection['runtime']);root.mkdir(parents=True)
    _write(root/'launch-settings.json',{'scope':'provider qualification only','controller_source_sha256':controller_source_digest(),
        'contract':contract,'reviewer':reviewer,'runtime':runtime,'campaign_authorized':False})
    from .experiment_execution import validate_qualification_code_review
    review=validate_qualification_code_review(contract)
    (root/'qualification-code-overseer-review.md').write_bytes(Path(review['path']).read_bytes())
    try:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        request=urllib.request.Request('https://api.openai.com/v1/models',headers={'Authorization':'Bearer '+api_key})
        with opener.open(request,timeout=30) as response:
            raw=response.read(1048577)
            if response.status!=200 or len(raw)>1048576:raise ValueError('Authenticated model catalogue unavailable/beyond bound')
        if api_key.encode() in raw:raise ValueError('Credential appears in catalogue; stop before model reasoning')
        (root/'model-catalog.bin').write_bytes(raw)
        observed=_strict_load(raw)
        models=sorted({item['id'] for item in observed['data']})
        catalog={'data_class':'empirical','source_kind':'qualified-provider-catalog','models':models,
            'verified_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
            'raw_sha256':file_hash(root/'model-catalog.bin'),'endpoint':'https://api.openai.com/v1/models',
            'authentication':'api_key','model_review_calls':0}
        validate_reviewer_model(reviewer['model'],authentication='api_key',available_models=models,verified_at=catalog['verified_at'])
        _write(root/'model-catalog.json',catalog)
        calls=[];actual_models=[]
        for index in range(2):
            evidence={'evidence_sha256':digest({'scope':'qualification','invocation':index,'source':controller_source_digest()}),
                'elements':[],'qualification_notice':'Transport/isolation check only. Return the supplied assessment schema; no scientific case or tools.',
                'fresh_nonce':__import__('uuid').uuid4().hex}
            own=build_request(evidence,model=reviewer['model'],settings=reviewer['settings'])
            invocation=root/f'invocation-{index+1:02d}';prepare_invocation(invocation,own)
            events,isolation,launch=run_qualified_invocation(invocation,own,sandbox=sandbox,protocol=protocol,
                qualification={},approved_contract=contract,contract_kind='qualification_contract',api_key=api_key,runtime=runtime)
            response=collect_real_response(invocation,own,launch=launch,qualification_contract=contract)
            if response.get('failure') or not response.get('usage_observation',{}).get('complete'):
                raise ValueError('Actual qualification completion/usage/tool/retry proof failed; retained invocation')
            if events.get('broker_failure') or events['received_requests']!=1 or events['forwarded_requests']!=1:
                raise ValueError('Actual native CLI transport retried or failed; no qualification')
            actual_models.append(launch['actual_model'])
            calls.append({'directory':invocation.relative_to(root).as_posix(),'request_sha256':digest(own),
                'launch_sha256':digest(launch),'response_sha256':digest(response),'usage':response['usage'],
                'probes':isolation['probes'],'charged_calls':1})
        if len(set(actual_models))!=1:raise ValueError('Qualification served mixed models')
        final=sandbox._call({'action':'inspect-provider','cli_binary':reviewer['cli_path']})
        assert_runtime_matches(runtime,final['runtime'])
        if final['cli']!=inspection['cli']:raise ValueError('CLI drift during qualification')
        bound=deepcopy(reviewer);bound.update(actual_model=actual_models[0],model_catalog_sha256=digest(catalog))
        proof={'data_class':'empirical','provider_kind':'actual-openai-api','credential_persisted':False,
            'controller_source_sha256':controller_source_digest(),'runtime':runtime,'command_probes':calls[0]['probes'],
            'native_cli_binary_sha256':reviewer['cli_sha256'],'forwarded_requests':2,'model_catalog':catalog,
            'actual_models':actual_models,'tool_or_internal_retry_detected':False,'completion_and_usage_verified':True,
            'calls':calls,'qualification_costs_separate':True,'scope':'qualification only; no campaign release'}
        _write(root/'raw-provider-proof.json',proof)
        receipt={'format_version':'m3b-provider-qualification.1','data_class':'empirical','synthetic':False,'qualified':True,
            'artifact_directory':root.relative_to(ROOT).as_posix(),'reviewer':bound,'runtime':runtime,'probes':proof['command_probes'],
            'credential_model_access':'denied','model_command_network':'denied','history_policy':'none','fresh_sessions':True,
            'controller_source_sha256':controller_source_digest(),'model_catalog':catalog,'calls':calls,
            'qualification_costs_separate':True,'files':{p.relative_to(root).as_posix():file_hash(p) for p in root.rglob('*') if p.is_file()}}
        receipt['qualification_sha256']=digest(receipt);_write(root/'qualification.json',receipt)
        return receipt
    except Exception as error:
        _write(root/'qualification-failure.json',{'qualified':False,'data_class':'empirical','scope':'qualification only',
            'error_class':type(error).__name__,'campaign_authorized':False,'retained_originals':True})
        raise
