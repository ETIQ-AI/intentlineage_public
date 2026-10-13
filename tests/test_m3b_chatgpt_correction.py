"""Correction contracts; synthetic records never qualify a provider."""
import importlib.util
import json
from pathlib import Path
import tomllib
import pytest

from intentlineage.native_capture import ROOT
from intentlineage.review_contract import build_request, canonical_bytes
from intentlineage.experiment_execution import config_arguments, model_permission_config, qualified_worker_source


def corrected():
    spec = importlib.util.find_spec('intentlineage.experiment_chatgpt')
    assert spec is not None, 'Supported ChatGPT adapter has not been implemented'
    from intentlineage import experiment_chatgpt
    return experiment_chatgpt


def own():
    return build_request({'elements': [], 'evidence_sha256': 'fixture'},
                         model='gpt-5.5', settings={'reasoning_effort': 'none'})


def reply():
    return {'assessments': [], 'no_relevant_element': True, 'uncovered_elements': [],
            'unresolved_questions': [], 'requested_openings': []}


def exchange():
    request = own()
    commands = corrected().chatgpt_rpc_requests(request, thread_id='fresh-thread')
    records = [
        {'id': 1, 'result': {'userAgent': 'fixture'}},
        {'id': 2, 'result': {'account': {'type': 'chatgpt'}, 'requiresOpenaiAuth': True}},
        {'id': 3, 'result': {'data': [{'id': 'gpt-5.5', 'model': 'gpt-5.5'}], 'nextCursor': None}},
        {'id': 4, 'result': {'thread': {'id': 'fresh-thread', 'turns': [], 'ephemeral': True}, 'model': 'gpt-5.5', 'modelProvider': 'openai'}},
        {'id': 5, 'result': {'turn': {'id': 'one-turn', 'status': 'inProgress'}}},
        {'method': 'turn/started', 'params': {'threadId': 'fresh-thread', 'turn': {'id': 'one-turn'}}},
        {'method': 'item/completed', 'params': {'threadId': 'fresh-thread', 'turnId': 'one-turn',
         'item': {'type': 'agentMessage', 'id': 'answer', 'text': json.dumps({'reply_json':json.dumps(reply())}), 'phase': 'final_answer'}}},
        {'method': 'turn/completed', 'params': {'threadId': 'fresh-thread',
         'turn': {'id': 'one-turn', 'status': 'completed', 'error': None}}},
    ]
    return request, commands, records


def facts(records, commands=None):
    request = own()
    return corrected().chatgpt_event_facts(
        b'\n'.join(canonical_bytes(e) for e in records) + b'\n',
        commands or corrected().chatgpt_rpc_requests(request, thread_id='fresh-thread'),
        request, json.dumps({'reply_json':json.dumps(reply())}), exit_code=0)


def test_permission_overrides_survive_actual_client_dotted_key_semantics():
    expected = model_permission_config()
    args = config_arguments(expected)
    observed = {}
    for i in range(0, len(args), 2):
        assert args[i] == '--config'
        key, value = args[i+1].split('=', 1)
        destination = observed
        parts = key.split('.')  # Codex override key parser, not TOML key parsing.
        for part in parts[:-1]:
            destination = destination.setdefault(part, {})
        destination[parts[-1]] = tomllib.loads('value=' + value)['value']
    assert observed == expected


def test_worker_uses_platform_native_sandbox_and_explicit_profile():
    source = qualified_worker_source(own(), [], config_arguments(model_permission_config()), 30)
    assert "'sandbox','linux'" not in source
    assert '--permission-profile' in source
    assert 'intentlineage-review' in source


def test_active_draft_is_chatgpt_only_without_api_catalogue_or_dollar_requirements():
    protocol = corrected().draft_chatgpt_protocol()
    assert protocol['reviewer']['authentication'] == 'chatgpt'
    assert protocol['format_version'] != 'm3b-execution-protocol.1'
    assert protocol['observability']['backend_served_model'] == 'unavailable_unless_client_reports'
    assert protocol['observability']['provider_attempts'] == 'unknown_unless_client_reports'
    assert protocol['observability']['monetary_cost'] == 'not_an_api_dollar_bill'


def test_auth_descriptor_never_exports_cached_tokens(tmp_path):
    source = tmp_path / 'auth.json'
    source.write_text(json.dumps({'auth_mode': 'chatgpt', 'OPENAI_API_KEY': None,
        'tokens': {'access_token': 'synthetic-secret-access', 'refresh_token': 'synthetic-secret-refresh',
                   'id_token': 'synthetic-secret-id', 'account_id': 'synthetic-account'}}))
    descriptor = corrected().chatgpt_auth_source(source)
    assert descriptor['authentication'] == 'chatgpt'
    assert descriptor['kind'] == 'cached_codex_auth'
    assert 'synthetic-secret' not in json.dumps(descriptor)
    assert 'synthetic-account' not in json.dumps(descriptor)


@pytest.mark.parametrize('value', [
    {'auth_mode': 'api', 'OPENAI_API_KEY': 'synthetic-key'},
    {'auth_mode': 'chatgpt', 'OPENAI_API_KEY': 'synthetic-key', 'tokens': {'access_token': 'x'}},
    {'auth_mode': 'chatgpt', 'tokens': {}},
])
def test_auth_descriptor_rejects_api_and_missing_login(tmp_path, value):
    source = tmp_path / 'auth.json'; source.write_text(json.dumps(value))
    with pytest.raises(ValueError): corrected().chatgpt_auth_source(source)


def test_auth_inside_export_tree_is_refused():
    with pytest.raises(ValueError): corrected().chatgpt_auth_source(ROOT / 'auth.json')


def test_rpc_uses_one_fresh_ephemeral_thread_and_exact_own_prompt_schema():
    commands = corrected().chatgpt_rpc_requests(own(), thread_id='fresh-thread')
    methods = [x['method'] for x in commands]
    assert methods.count('thread/start') == methods.count('turn/start') == 1
    assert not any(x in methods for x in ['thread/resume', 'thread/fork', 'thread/inject_items', 'turn/steer'])
    start = next(x['params'] for x in commands if x['method'] == 'thread/start')
    turn = next(x['params'] for x in commands if x['method'] == 'turn/start')
    assert start['ephemeral'] is True and start['model'] == 'gpt-5.5'
    assert turn['threadId'] == 'fresh-thread' and turn['effort'] == 'none'
    assert turn['input'] == [{'type': 'text', 'text': canonical_bytes(own()).decode()}]
    assert turn['outputSchema'] == corrected().chatgpt_wire_schema()
    assert own()['response_schema'] == __import__('intentlineage.review_contract',fromlist=['REPLY_SCHEMA']).REPLY_SCHEMA


def test_rpc_refuses_model_above_ceiling():
    request = own(); request['model'] = 'gpt-6.1-sol'
    with pytest.raises(ValueError): corrected().chatgpt_rpc_requests(request, thread_id='fresh-thread')


def test_completed_client_turn_preserves_unknown_provider_counters():
    request, commands, records = exchange()
    observed = facts(records, commands)
    assert observed['complete'] and observed['client_effective_model'] == 'gpt-5.5'
    assert observed['backend_served_model'] is None and observed['provider_attempts'] is None
    assert observed['logical_turns'] == 1 and not observed['usage_observation']['complete']
    assert observed['monetary_cost'] is None


def test_partial_and_zero_usage_remain_m2_observations():
    request, commands, records = exchange()
    records.insert(-1, {'method': 'thread/tokenUsage/updated', 'params': {'threadId': 'fresh-thread',
        'turnId': 'one-turn', 'tokenUsage': {'last': {'inputTokens': 0}}}})
    observed = facts(records, commands)
    assert observed['usage_observation']['values'] == {'input_tokens': 0}
    assert observed['usage_observation']['status'] == 'partial'


@pytest.mark.parametrize('addition', [
    {'method': 'model/rerouted', 'params': {'threadId': 'fresh-thread', 'turnId': 'one-turn', 'fromModel': 'gpt-5.5', 'toModel': 'gpt-6.1-sol'}},
    {'method': 'item/started', 'params': {'threadId': 'fresh-thread', 'turnId': 'one-turn', 'item': {'type': 'commandExecution'}}},
    {'method': 'error', 'params': {'threadId': 'fresh-thread', 'turnId': 'one-turn', 'willRetry': True}},
    {'method': 'turn/started', 'params': {'threadId': 'fresh-thread', 'turn': {'id': 'second-turn'}}},
])
def test_raw_retry_tool_model_and_turn_drift_stop_admission(addition):
    request, commands, records = exchange(); records.insert(-1, addition)
    assert not facts(records, commands)['complete']


def test_reply_must_match_raw_final_message():
    request, commands, records = exchange()
    records[-2]['params']['item']['text'] = '{}'
    assert not facts(records, commands)['complete']


def test_client_thread_cannot_include_inherited_turns():
    request, commands, records = exchange()
    records[3]['result']['thread']['turns'] = [{'id': 'developer-conversation'}]
    assert not facts(records, commands)['complete']


def test_missing_separate_review_never_releases_qualification():
    protocol = corrected().draft_chatgpt_protocol()
    with pytest.raises(ValueError): corrected().validate_chatgpt_qualification_review(protocol)
