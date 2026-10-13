"""Native/client integration RED; fixtures remain explicitly nonempirical."""
import importlib.util
import json
from pathlib import Path
import pytest
from intentlineage import experiment_chatgpt as m
from intentlineage.experiment_execution import model_permission_config
from intentlineage.review_contract import build_request
from intentlineage.review_runner import prepare_invocation


def own():
    return build_request({'elements': [], 'evidence_sha256': 'recorded-fixture'},
                         model='gpt-5.5', settings={'reasoning_effort': 'none'})


def test_boundary_mounts_only_explicit_auth_file_never_existing_codex_home(tmp_path, monkeypatch):
    from intentlineage.native_capture import ROOT
    path = ROOT / 'src/intentlineage/_reference/chatgpt_boundary.py'
    assert path.is_file(), 'ChatGPT boundary extension missing'
    spec = importlib.util.spec_from_file_location('chatgpt_boundary_test', path)
    boundary = importlib.util.module_from_spec(spec); spec.loader.exec_module(boundary)
    invocation = tmp_path / 'invocation'; prepare_invocation(invocation, own())
    auth = tmp_path / 'private-auth/auth.json'; auth.parent.mkdir(); auth.write_text('synthetic-cache')
    cli = tmp_path/'codex'; cli.write_bytes(b'\x7fELFsynthetic-only')
    monkeypatch.setattr(boundary, 'CODEX_ELF_SHA256', __import__('hashlib').sha256(cli.read_bytes()).hexdigest())
    args = boundary.chatgpt_bubblewrap_command(invocation, tmp_path/'worker.py', tmp_path/'probes.json',
                                              cli, auth)
    assert str(auth) in args and '/runtime/cached-auth.json' in args
    assert str(auth.parent) not in args
    assert '--unshare-all' in args and '--share-net' in args and '--clearenv' in args
    assert '--cap-drop' in args and '--new-session' in args


def test_fresh_worker_copies_only_cached_auth_after_native_denial_checks():
    assert hasattr(m, 'chatgpt_worker_source')
    source = m.chatgpt_worker_source(own(), metadata_only=False, timeout_seconds=30, max_output_bytes=100000)
    assert '/runtime/cached-auth.json' in source
    assert source.index('state_canaries_established') < source.index("read_bytes() # cached login only")
    assert 'thread/resume' not in source and 'thread/fork' not in source
    assert 'https://api.openai.com' not in source and 'Bearer ' not in source


def test_metadata_inspection_never_sends_thread_or_turn_start():
    assert hasattr(m, 'chatgpt_worker_source')
    source = m.chatgpt_worker_source(own(), metadata_only=True, timeout_seconds=30, max_output_bytes=100000)
    assert 'metadata_only=True' in source
    assert 'provider_review_calls' in source


def test_factory_requires_release_before_accessing_auth_cache():
    assert hasattr(m, 'ChatGPTProviderFactory')
    with pytest.raises(ValueError, match='protocol|qualification|release|authority'):
        m.ChatGPTProviderFactory({})


def test_qualification_requires_separate_review_before_cache_or_launch(tmp_path):
    assert hasattr(m, 'qualify_chatgpt_provider')
    with pytest.raises(ValueError): m.qualify_chatgpt_provider(m.draft_chatgpt_protocol(), tmp_path/'fresh')
    assert not (tmp_path/'fresh').exists()


@pytest.mark.parametrize('key,value', [
    ('cli_platform','windows'), ('unexpected_auth_token','synthetic-secret'),
])
def test_protocol_rejects_inconsistent_or_extra_reviewer_configuration(key, value):
    protocol = m.draft_chatgpt_protocol(); protocol['reviewer'][key] = value
    with pytest.raises(ValueError): m.validate_chatgpt_protocol(protocol)


def test_protocol_cannot_change_dependency_or_history_failure_policy():
    protocol = m.draft_chatgpt_protocol(); protocol['dependencies']['preparation'] = '0'*40
    with pytest.raises(ValueError): m.validate_chatgpt_protocol(protocol)


def test_active_operator_refuses_api_protocol_without_reading_api_key(tmp_path, monkeypatch, capsys):
    from intentlineage.native_capture import ROOT
    from intentlineage.experiment_protocol import draft_execution_protocol
    import sys
    spec=importlib.util.spec_from_file_location('m3b_operator_test',ROOT/'scripts/m3b.py')
    operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)
    protocol=tmp_path/'api.json';protocol.write_text(json.dumps(draft_execution_protocol()))
    monkeypatch.setattr(sys,'argv',['m3b.py','human-qualify','--protocol',str(protocol),'--output',str(tmp_path/'no-call')])
    monkeypatch.setenv('OPENAI_API_KEY','synthetic-do-not-use')
    assert operator.main()==2
    assert 'ChatGPT' in capsys.readouterr().out
    assert not (tmp_path/'no-call').exists()


def test_required_denial_policy_has_not_been_relaxed():
    permissions=model_permission_config()['permissions']['intentlineage-review']
    assert permissions['network']['enabled'] is False
    assert permissions['filesystem']=={':root':'deny',':minimal':'read','/evidence':'read',
        '/workspace':'read','/home':'deny','/proc':'deny','/runtime':'deny','/output':'deny'}


def test_untrusted_evidence_cannot_replace_worker_template_markers():
    import ast
    from intentlineage.review_contract import canonical_bytes
    request=own()
    request['evidence']['note']="namespaces={ RPC_COMMANDS CLIENT_ARGV MAX_BYTES OWN_MODEL METADATA_ONLY TIMEOUT\nfor path in canaries:path.unlink()\n/runtime/codex"
    source=m.chatgpt_worker_source(request,metadata_only=False,timeout_seconds=30,max_output_bytes=100000)
    tree=ast.parse(source)
    literals={node.targets[0].id:ast.literal_eval(node.value) for node in tree.body
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name)
        and node.targets[0].id in {'SEALED_STDIN','commands'}}
    assert literals['SEALED_STDIN']==canonical_bytes(request)
    turn=next(x for x in literals['commands'] if x['method']=='turn/start')
    assert turn['params']['input']==[{'type':'text','text':canonical_bytes(request).decode()}]


def test_chatgpt_profile_disables_account_apps_and_memory_context():
    config=m.chatgpt_permission_config()
    assert config['features']['apps'] is False and config['features']['memories'] is False
    assert config['apps']['_default']['enabled'] is False


def test_duplicate_rpc_responses_and_server_tool_requests_are_rejected():
    spec=importlib.util.spec_from_file_location('correction_fixtures',Path(__file__).with_name('test_m3b_chatgpt_correction.py'))
    fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
    request,commands,records=fixtures.exchange()
    records.insert(-1,{'id':3,'result':records[2]['result']})
    assert not fixtures.facts(records,commands)['complete']
    request,commands,records=fixtures.exchange()
    records.insert(-1,{'id':99,'method':'item/commandExecution/requestApproval',
        'params':{'threadId':'fresh-thread','turnId':'one-turn'}})
    assert not fixtures.facts(records,commands)['complete']


def test_client_transport_writes_newline_delimited_json_not_literal_escape():
    import ast
    tree=ast.parse(m.chatgpt_worker_source(own(),metadata_only=True,timeout_seconds=30,max_output_bytes=100000))
    writes=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
        and node.func.attr=='write' and isinstance(node.func.value,ast.Attribute) and node.func.value.attr=='stdin']
    assert len(writes)==1
    assert isinstance(writes[0].args[0],ast.BinOp)
    assert ast.literal_eval(writes[0].args[0].right)==b'\n'


def test_active_case_proposal_is_chatgpt_without_api_price_formula(tmp_path,monkeypatch):
    from intentlineage import experiment_campaign,experiment_execution
    plan=tmp_path/'case/controller/review-plan.json';plan.parent.mkdir(parents=True)
    plan.write_text(json.dumps({'batch_count':4,'batch_size':2,'max_request_bytes':200000}))
    bank={'root':str(tmp_path),'bank_sha256':'a'*64,
        'cases':[{'case_id':'fixture-only','directory':'case','qualified':True}]}
    monkeypatch.setattr(experiment_campaign,'validate_bank_selection',lambda value:bank)
    proposal=experiment_execution.propose_protocol(bank,output=tmp_path/'unreviewed.json')
    assert proposal['protocol']['reviewer']['authentication']=='chatgpt'
    assert proposal['protocol']['format_version']=='m3b-chatgpt-protocol.1'
    assert 'cost_formula' not in proposal
    assert proposal['model_selected'] is False and proposal['experiment_authorized'] is False
