"""Versioned controller failure policy; never changes or repairs model answers."""
import ast
from copy import deepcopy
import json

POLICY = 'm3-response-policy.1'
SESSION_VERSION = 'm3-function-session.2'
MATRIX_VERSION = 'm3-function-matrix.2'


class CampaignStop(RuntimeError):
    """A bounded execution/provenance failure, never an ordinary content error."""


def stable_failure(fields):
    if type(fields) is not dict:
        raise ValueError('Structured failure fields required')
    text = json.dumps(fields, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    return {'format_version': 'm3-failure-fields.1', 'fields': deepcopy(fields), 'text': text}


def decode_legacy_failure(text):
    """Only the recorded reason/exit-code dictionary family; no general coercion."""
    try:
        tree = ast.parse(text, mode='eval')
        if not isinstance(tree.body, ast.Dict):
            raise ValueError('Unsupported historical failure representation')
        keys = [ast.literal_eval(k) for k in tree.body.keys]
        if len(keys)!=len(set(keys)) or set(keys) not in ({'reason'},{'reason','exit_code'}):
            raise ValueError('Unknown/duplicate historical failure fields')
        value = ast.literal_eval(tree)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as error:
        raise ValueError('Unsupported historical failure representation') from error
    if type(value['reason']) is not str or ('exit_code' in value and type(value['exit_code']) is not int):
        raise ValueError('Malformed historical failure fields')
    return value


def legacy_record_reason(record, saved, response):
    """Compare supported bound values, retaining the original literal and hashes."""
    if record.get('failure') and saved.get('failure') and response.get('failure'):
        actual = record['failure']; original = saved['failure']; fields = response['failure']
        if actual['kind'] == original['kind'] == 'provider_error' and type(fields) is dict:
            if decode_legacy_failure(actual['reason']) != fields or decode_legacy_failure(original['reason']) != fields:
                raise ValueError('Historical failure reason/exit-code differs from provider receipt')
            actual['reason'] = original['reason']
    return record


def assessment_failure(wire, request, observed, *, charging, probes):
    """Content-only classification after native completion/identity/usage checks."""
    from .experiment_qualification import REQUIRED_PROBES
    if (set(observed.get('errors', [])) != {'Malformed/unbound native reply'}
        or observed.get('logical_turns') != 1 or charging != 'unknown_or_charged'
        or observed.get('client_effective_model') != request['model']
        or observed.get('effective_reasoning_effort') != request['settings'].get('reasoning_effort')
        or observed.get('usage_observation', {}).get('complete') is not True
        or observed['usage_observation'].get('errors')
        or set(probes) != REQUIRED_PROBES or any(v is not True for v in probes.values())):
        return None
    from .experiment_chatgpt import decode_chatgpt_wire_reply
    from .review_function import validate_reply
    if request.get('contract_version') == 'm3-single-review.1':
        from .review_single import validate_reply
    stage = 'native_envelope'
    try:
        decoded = decode_chatgpt_wire_reply(wire)
        stage = 'assessment_contract'
        validate_reply(decoded, request['evidence'], allow_opening=request['allow_opening'])
    except (ValueError, TypeError) as error:
        return {'format_version': POLICY, 'kind': 'invalid_response', 'stage': stage,
                'specific_reason': str(error), 'generic_reason': 'Malformed/unbound native reply'}
    return None


def terminal_metadata(session):
    invalid = [c['attempt'] for c in session.calls if c['failure_kind'] == 'invalid_response']
    return {'response_policy': POLICY, 'terminal_outcome': 'invalid_response' if invalid else None,
            'invalid_response_calls': invalid,
            'validation_failures': [deepcopy(c['failure']) for c in session.calls if c['failure']]}


def assert_not_hard_failure(session):
    if session.get('response_policy') != POLICY:
        return
    allowed = {'invalid_response', 'transport_failure'}
    if (any(f['kind'] not in allowed for f in session['failures'])
        or session['stop_reason'] in {'context_budget', 'disclosure_byte_budget', 'rejected_operation'}):
        raise CampaignStop('Non-content review failure; preserve receipts and stop: ' + session['stop_reason'])
    # A transport retry is allowed only while the controller can confirm no turn.
    if session['stop_reason'] == 'transport_failure':
        raise CampaignStop('Exhausted confirmed-no-turn transport policy')
