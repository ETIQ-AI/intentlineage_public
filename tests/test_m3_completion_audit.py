"""Declared correction reconciliation must verify exact current/predecessor bytes."""
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('drift', [None,'current','archive','escape'])
def test_correction_audit_rejects_unbound_reconciliation(tmp_path,drift):
    spec=importlib.util.spec_from_file_location('correction_audit',ROOT/'scripts/audit_m3b_execution.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sha=lambda raw:hashlib.sha256(raw).hexdigest()
    current=tmp_path/'README.md';current.write_bytes(b'new')
    archive=tmp_path/'resources/evidence/archive/old.md';archive.parent.mkdir(parents=True);archive.write_bytes(b'old')
    record={'baseline_sha256':sha(b'old'),'current_sha256':sha(b'new'),
            'archive':'resources/evidence/archive/old.md','kind':'declared_edit'}
    if drift=='current':current.write_bytes(b'drift')
    if drift=='archive':archive.write_bytes(b'drift')
    if drift=='escape':record['archive']='../outside.md'
    (tmp_path/'resources/evidence/m3b-chatgpt-integration.json').write_text(json.dumps({
        'reviewed_base':'4896fce39e6beb0666b268dd68859cb0d2c9e94e',
        'baseline_reconciliations':{'README.md':record}}))
    baseline={'own_files':{'README.md':sha(b'old')}}
    if drift:
        with pytest.raises(ValueError):module.correction_reconciliations(tmp_path,baseline)
    else:assert module.correction_reconciliations(tmp_path,baseline)=={'README.md':record}
