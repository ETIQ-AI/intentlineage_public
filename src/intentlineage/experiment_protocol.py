"""Draft/freeze validation for M3B. No model or final population is selected."""
from copy import deepcopy
import re
from datetime import datetime, timezone

from .native_capture import digest
from .review_contract import build_request, canonical_bytes, PROMPT_CONTRACT, REPLY_SCHEMA

M1_COMMIT = '7178692b12c59a699c4fd7c1b0ed801759b3894d'
M2_COMMIT = '6dd91facc9f6b91a73faad40042a4baaae6d0fba'
M3A_COMMIT = 'fbedf3e98eb9e45f5aa140f20bd648a5dcc6e345'
PREPARATION_COMMIT = '37a3bca2d3393321717341f8fad1c64a2bfbddb7'
MODEL_CEILING = '5.5'
# Curated exact IDs from the fetched official model pages. Account access must
# separately be proved by the human-launched provider qualification/catalogue.
MODEL_ALLOWLIST = {
    'api_key': frozenset({'gpt-5.4-mini', 'gpt-5.4-mini-2026-03-17', 'gpt-5.5','gpt-5.5-2026-04-23'}),
    'chatgpt': frozenset({'gpt-5.5'}),
}
MODEL_REFERENCES = ['https://learn.chatgpt.com/docs/models',
                    'https://developers.openai.com/api/docs/models/gpt-5.4-mini',
                    'https://developers.openai.com/api/docs/models/gpt-5.5']
RETRY_POLICY = 'Only confirmed no-reasoning transport failures are uncharged; charged invalid replies consume logical calls.'
MATRIX = {
    'E': {'view': 'endpoints', 'opening': False, 'calls': 1},
    'H': {'view': 'fixed top-level batches', 'opening': False, 'calls': 'qualified H batches plus charged retries'},
    'A': {'view': 'H starting batches then eligible visible disclosure', 'opening': True, 'calls': 'bounded actual charged logical calls'},
    'R-H': {'view': 'unchanged endpoints', 'opening': False, 'calls': 'actual H charged logical calls'},
    'R-A': {'view': 'unchanged endpoints', 'opening': False, 'calls': 'actual A charged logical calls'},
}


def prompt_identity():
    request = build_request({}, model='identity-only', settings={})
    repeated = build_request({}, model='identity-only', settings={}, reconsider=True)
    return {'instruction': PROMPT_CONTRACT, 'guidance_sha256': digest(request['guidance']),
            'schema_sha256': digest(REPLY_SCHEMA), 'initial_pass': request['review_pass'],
            'reconsideration': repeated['review_pass']}


def draft_protocol():
    return {'format_version': 'm3b-preparation-protocol.2', 'status': 'draft',
            'reviewer': {'cli_name': 'codex', 'model': None, 'cli_version': None,
                         'cli_sha256': None, 'settings': None},
            'prompts': prompt_identity(), 'matrix': deepcopy(MATRIX),
            'common_evidence': ['original user prompt', 'identical three-category inventory',
                                'whole-job input statistics/descriptions', 'whole-job output statistics/descriptions'],
            'selection_policy': None,
            'H': {'batch_size': None, 'max_request_bytes': None, 'batch_counts': None},
            'A': {'max_calls': None, 'max_operations': None, 'max_disclosure_bytes': None},
            'repeats': None, 'scheduling': {'unit_order': 'seeded', 'seed': None, 'parallelism': 1},
            'retry': {'reasoning_retries': None, 'transport_retries': None,
                      'policy': RETRY_POLICY, 'internal_reasoning': 'reject_unaccounted'},
            'history_policy': 'none',
            'population': {'case_ids': None, 'bank_sha256': None},
            'dependencies': {'m1': M1_COMMIT, 'm2': M2_COMMIT, 'm3a': M3A_COMMIT}}


def _shape(value, template, path='protocol'):
    if type(value) is not dict or set(value) != set(template):
        raise ValueError(path + ' has missing or unknown settings')


def _hash(value, length):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{' + str(length) + '}', value) is not None


def validate_protocol(protocol, *, require_frozen=False):
    """Validate supported contracts; draft nulls are reported, never filled in."""
    template = draft_protocol()
    _shape(protocol, template)
    for key in ['reviewer', 'prompts', 'H', 'A', 'scheduling', 'retry', 'population', 'dependencies']:
        _shape(protocol[key], template[key], key)
    try: canonical_bytes(protocol)
    except (TypeError, ValueError) as error: raise ValueError('Protocol must be finite JSON data') from error
    if protocol['format_version'] != template['format_version'] or not isinstance(protocol['status'], str) or protocol['status'] not in {'draft', 'frozen'}:
        raise ValueError('Unknown protocol version/status')
    for key in ['prompts', 'matrix', 'common_evidence', 'history_policy']:
        if digest(protocol[key]) != digest(template[key]):
            raise ValueError(key + ' differs from the implemented M2 five-arm contract')
    reviewer = protocol['reviewer']
    if reviewer['cli_name'] != 'codex': raise ValueError('This transport prepares the existing Codex CLI contract')
    unresolved = []

    def check(path, valid):
        value = protocol
        for part in path.split('.'): value = value[part]
        if value is None: unresolved.append(path)
        elif not valid(value): raise ValueError('Invalid or inconsistent setting: ' + path)
        return value

    for path in ['reviewer.model', 'reviewer.cli_version']:
        check(path, lambda v: isinstance(v, str) and bool(v.strip()))
    check('reviewer.cli_sha256', lambda v: _hash(v, 64))
    check('reviewer.settings', lambda v: type(v) is dict and set(v) == {'reasoning_effort'}
          and isinstance(v['reasoning_effort'], str) and bool(v['reasoning_effort'].strip()))
    check('selection_policy', lambda v: isinstance(v, str) and v in {'question_driven', 'breadth_first', 'requirement_prioritized'})
    for path, minimum in [('H.batch_size', 1), ('H.max_request_bytes', 1), ('A.max_calls', 1),
                          ('A.max_operations', 0), ('A.max_disclosure_bytes', 0), ('repeats', 1),
                          ('scheduling.seed', 0), ('retry.reasoning_retries', 0), ('retry.transport_retries', 0)]:
        check(path, lambda v, n=minimum: type(v) is int and v >= n)
    if protocol['scheduling']['parallelism'] != 1 or type(protocol['scheduling']['parallelism']) is not int:
        raise ValueError('Campaign preparation is serial')
    if protocol['scheduling']['unit_order'] != 'seeded': raise ValueError('Unsupported scheduling policy')
    if protocol['retry']['policy'] != RETRY_POLICY or protocol['retry']['internal_reasoning'] != 'reject_unaccounted':
        raise ValueError('Unsupported retry accounting policy')
    cases = check('population.case_ids', lambda v: type(v) is list and bool(v)
                  and all(isinstance(i, str) and bool(i.strip()) for i in v) and len(v) == len(set(v)))
    check('population.bank_sha256', lambda v: _hash(v, 64))
    counts = check('H.batch_counts', lambda v: type(v) is dict and bool(v)
                   and all(isinstance(k, str) and bool(k) and type(n) is int and n >= 1 for k, n in v.items()))
    if cases is not None and counts is not None and set(counts) != set(cases):
        raise ValueError('Qualified H batch counts must cover the exact population')
    calls = protocol['A']['max_calls']
    if counts is not None and calls is not None and calls < max(counts.values()):
        raise ValueError('A call budget cannot review its H starting batches')
    if protocol['A']['max_operations'] and protocol['A']['max_disclosure_bytes'] == 0:
        raise ValueError('Selected openings require a disclosure byte budget')
    deps = protocol['dependencies']
    for key in ['m1', 'm2', 'm3a']:
        if deps[key] != template['dependencies'][key]:
            raise ValueError('Reviewed dependency pin changed; reconcile source before using another delivery')
    ready = protocol['status'] == 'frozen' and not unresolved
    if require_frozen and not ready: raise ValueError('Protocol freeze incomplete: ' + ', '.join(unresolved))
    return {'valid': True, 'ready': ready, 'unresolved': unresolved,
            'protocol_sha256': digest(protocol),
            'limits': ['Configuration validation does not establish dependency acceptance or provider qualification.',
                       'H=1 makes R-H equivalent to E; no H calls are manufactured.']}


def prepare_schedule(protocol):
    """Pure schedule data from the existing M3A scheduler; never stages a unit."""
    validate_protocol(protocol, require_frozen=True)
    from .experiment_campaign import schedule
    return schedule(protocol['population']['case_ids'], repeats=protocol['repeats'],
                    seed=protocol['scheduling']['seed'])


def validate_reviewer_model(model, *, authentication, available_models, verified_at):
    """Eligibility/configuration check; a caller's list is not qualification."""
    if type(model) is not str or type(authentication) is not str or authentication not in MODEL_ALLOWLIST or model not in MODEL_ALLOWLIST[authentication]:
        raise ValueError('Model is outside the explicit eligible <=5.5 allowlist/authentication route')
    if type(available_models) is not list or any(type(x) is not str for x in available_models) or model not in available_models:
        raise ValueError('Exact eligible model is not in the observed available catalogue')
    if type(verified_at) is not str or re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z',verified_at) is None:
        raise ValueError('Model availability requires an exact UTC observation time')
    try: observed=datetime.fromisoformat(verified_at[:-1]+'+00:00')
    except ValueError as error: raise ValueError('Invalid model availability observation') from error
    if authentication=='chatgpt' and observed>=datetime(2026,10,14,tzinfo=timezone.utc):
        raise ValueError('GPT-5.5 retired from ChatGPT-authenticated Codex; no higher-version fallback')
    return {'eligible':True,'model':model,'ceiling':MODEL_CEILING,'authentication':authentication,
            'eligibility_only':True,'account_qualification_granted':False,'references':MODEL_REFERENCES[:]}


def draft_execution_protocol():
    """Separate real-path draft; never silently populate scientific choices."""
    value=draft_protocol()
    value['format_version']='m3b-execution-protocol.1'
    value['reviewer'].update(authentication=None,actual_model=None,model_catalog_sha256=None,
                             cli_platform='linux',cli_path=None)
    value['dependencies']['preparation']=PREPARATION_COMMIT
    value.update(data_class='empirical',model_policy={'ceiling':MODEL_CEILING,
        'allowlist':{key:sorted(ids) for key,ids in MODEL_ALLOWLIST.items()}},
        limits={'max_input_tokens':None,'max_input_bytes':None,'max_output_tokens':None,
                'max_seconds_per_invocation':None,'qualification_max_calls':None},
        bindings={'controller_source_sha256':None,'qualification_sha256':None,'model_catalog':None},
        replacement_policy='Fresh campaign only; retain interrupted originals and their costs',
        treatment_failure_policy='Match actual charged treatment counts; failures never imply correctness')
    return value


def validate_execution_protocol(protocol, *, require_frozen=False):
    if type(protocol) is dict and protocol.get('format_version') in {'m3b-chatgpt-protocol.1','m3b-chatgpt-function-protocol.1','m3b-chatgpt-function-protocol.2'}:
        from .experiment_chatgpt import validate_chatgpt_protocol
        return validate_chatgpt_protocol(protocol,require_frozen=require_frozen)
    template=draft_execution_protocol();_shape(protocol,template)
    for key in ['reviewer','dependencies','limits','bindings','model_policy']:
        _shape(protocol[key],template[key],key)
    if protocol['format_version']!=template['format_version'] or protocol['data_class']!='empirical':
        raise ValueError('Execution requires explicit empirical protocol scope')
    for key in ['model_policy','replacement_policy','treatment_failure_policy']:
        if digest(protocol[key])!=digest(template[key]):raise ValueError('Execution policy changed: '+key)
    if protocol['dependencies']['preparation']!=PREPARATION_COMMIT:raise ValueError('Reviewed preparation dependency changed')
    # Reuse all existing five-arm/protocol validation rather than copy its rules.
    base={key:deepcopy(protocol[key]) for key in draft_protocol()}
    base['format_version']=draft_protocol()['format_version']
    base['reviewer']={key:base['reviewer'][key] for key in draft_protocol()['reviewer']}
    base['dependencies']={key:base['dependencies'][key] for key in draft_protocol()['dependencies']}
    result=validate_protocol(base);unresolved=result['unresolved'][:]
    reviewer=protocol['reviewer']
    for key in ['authentication','actual_model','model_catalog_sha256','cli_path']:
        if reviewer[key] is None:unresolved.append('reviewer.'+key)
        elif type(reviewer[key]) is not str or not reviewer[key]:raise ValueError('Invalid execution reviewer identity: '+key)
    if reviewer['model_catalog_sha256'] is not None and not _hash(reviewer['model_catalog_sha256'],64):
        raise ValueError('Invalid frozen model catalogue hash')
    if reviewer['model'] is not None:
        if reviewer['model'] not in set().union(*MODEL_ALLOWLIST.values()):raise ValueError('Model exceeds ceiling or is not explicitly eligible')
        if reviewer['settings'] is not None and reviewer['settings']['reasoning_effort'] not in {'none','low','medium','high','xhigh'}:
            raise ValueError('Unsupported reasoning effort for eligible model')
    if reviewer['actual_model'] is not None and reviewer['actual_model'] not in set().union(*MODEL_ALLOWLIST.values()):
        raise ValueError('Actual server model exceeds ceiling or is not explicitly eligible')
    if reviewer['authentication'] is not None and reviewer['authentication'] not in MODEL_ALLOWLIST:
        raise ValueError('Unknown provider authentication route')
    if reviewer['cli_platform']!='linux':raise ValueError('Windows interop cannot enter the qualified Linux boundary')
    if reviewer['cli_path'] is not None and (type(reviewer['cli_path']) is not str or not reviewer['cli_path'].startswith('/') or '..' in reviewer['cli_path'].split('/')):
        raise ValueError('Explicit absolute Linux CLI binary required')
    for key in template['limits']:
        v=protocol['limits'][key]
        if v is None:unresolved.append('limits.'+key)
        elif type(v) is not int or v<1:raise ValueError('Invalid bounded execution limit: '+key)
    for key in ['controller_source_sha256','qualification_sha256']:
        v=protocol['bindings'][key]
        if v is None:unresolved.append('bindings.'+key)
        elif not _hash(v,64):raise ValueError('Missing execution source/qualification hash')
    catalog=protocol['bindings']['model_catalog']
    if catalog is None:unresolved.append('bindings.model_catalog')
    elif reviewer['model'] is not None and reviewer['authentication'] is not None:
        if type(catalog) is not dict or catalog.get('data_class')!='empirical' or catalog.get('source_kind')!='qualified-provider-catalog':
            raise ValueError('Cached/synthetic model catalogue cannot qualify actual availability')
        if digest(catalog)!=reviewer['model_catalog_sha256']:raise ValueError('Frozen model catalogue differs')
        validate_reviewer_model(reviewer['model'],authentication=reviewer['authentication'],
            available_models=catalog['models'],verified_at=catalog['verified_at'])
    ready=protocol['status']=='frozen' and not unresolved
    if require_frozen and not ready:raise ValueError('Execution protocol incomplete: '+', '.join(unresolved))
    return {**result,'ready':ready,'unresolved':unresolved,'protocol_sha256':digest(protocol),
            'model_ceiling':MODEL_CEILING,'model_selected_by_validation':False}
