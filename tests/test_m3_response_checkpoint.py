"""Controller journal fixture only; never a hosted reviewer outcome."""
from pathlib import Path
import importlib
import json
import pytest

def test_each_completed_unit_keeps_an_exclusively_created_cost_checkpoint(tmp_path):
    m=importlib.import_module('intentlineage.experiment_resume')
    one={'unit_id':'u1'};two={'unit_id':'u2'}
    a={'retained_charges':79,'new_charged_calls':0,'cumulative_charges':79,'remaining_allowance':119}
    b={**a,'new_charged_calls':12,'cumulative_charges':91,'remaining_allowance':107}
    m.write_cost_checkpoint(tmp_path,one,a)
    m.write_cost_checkpoint(tmp_path,two,b)
    assert json.loads((tmp_path/'cost-checkpoints/u1.json').read_bytes())==a
    assert json.loads((tmp_path/'cost-checkpoints/u2.json').read_bytes())==b
    with pytest.raises(FileExistsError):m.write_cost_checkpoint(tmp_path,one,b)
    assert json.loads((tmp_path/'cost-checkpoints/u1.json').read_bytes())==a
