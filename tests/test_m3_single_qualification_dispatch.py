"""Pure routing guards; patched functions do not qualify any provider."""
from intentlineage import experiment_chatgpt as native


def test_new_qualification_packet_uses_chatgpt_validator(monkeypatch):
    from intentlineage.experiment_qualification import validate_provider_qualification
    monkeypatch.setattr(native,'validate_chatgpt_qualification',lambda *a,**k: {'route_only':'chatgpt'})
    assert validate_provider_qualification({},protocol={'format_version':'m3b-chatgpt-single-protocol.1'})=={'route_only':'chatgpt'}


def test_new_qualification_command_builder_uses_chatgpt_route(monkeypatch,tmp_path):
    from intentlineage.experiment_execution import prepare_qualification_plan
    monkeypatch.setattr(native,'prepare_chatgpt_qualification_plan',lambda *a,**k: {'route_only':'chatgpt'})
    assert prepare_qualification_plan({'format_version':'m3b-chatgpt-single-protocol.1'},output=tmp_path/'plan.json')=={'route_only':'chatgpt'}
