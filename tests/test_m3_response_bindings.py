"""Additional REDs for exact retained reference/provenance admission."""
import importlib
from copy import deepcopy
import pytest

def test_known_reason_only_legacy_failure_is_preserved():
    f=importlib.import_module('intentlineage.review_failures')
    assert f.decode_legacy_failure("{'reason': 'fixture failure'}")=={'reason':'fixture failure'}

@pytest.mark.parametrize('charge',[1,'true',None])
def test_invalid_charge_provenance_is_not_boolean_coerced(charge):
    f=importlib.import_module('intentlineage.experiment_resume')
    r={'case_id':'case-006','arm':'A','attempt':5,'provider_call_id':'id','request_sha256':'a'*64,'charged_reasoning':charge}
    with pytest.raises(ValueError):f.admit_calls([r],ceiling=198)

@pytest.mark.parametrize('change',['case','arm','phase','directory','session'])
def test_retained_reference_cannot_relabel_valid_observations(change):
    f=importlib.import_module('intentlineage.experiment_resume')
    item={'case_id':'case-006','unit_id':'u'}
    s={'arm':'A','plan_sha256':'p','session_sha256':'s'}
    manifest={'sessions':[{'case_id':'case-006','unit_id':'u','arm':'A','directory':'units/u/A','session_sha256':'s'}]}
    ref={'phase':'retained','directory':'retained/campaign/units/u/A','session_sha256':'s'}
    if change=='case':item['case_id']='case-001'
    elif change=='arm':s['arm']='E'
    elif change=='phase':ref['phase']='unknown'
    elif change=='directory':ref['directory']='retained/campaign/units/other/A'
    else:ref['session_sha256']='changed'
    with pytest.raises(ValueError):f.validate_session_reference(item,'A',s,ref,manifest,plan_sha256='p')

def test_mismatched_retained_tree_is_refused_before_any_inference(tmp_path, monkeypatch):
    from intentlineage.native_capture import ROOT
    f=importlib.import_module('intentlineage.experiment_resume')
    # Supply a minimal manifest fixture; the real membership rejection is unchanged.
    monkeypatch.setattr(f, 'parent_bundle', lambda _: {'files': {'campaign/expected.json': 'a'*64}})
    with pytest.raises(ValueError,match='membership'):
        f.validate_retained_manifest(ROOT,{},evidence_root=tmp_path)
