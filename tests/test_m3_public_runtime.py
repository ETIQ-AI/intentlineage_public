"""Public runtime placement contracts; synthetic bytes do not qualify the CLI."""
import hashlib
import importlib.util
from pathlib import Path
import pytest
from intentlineage.native_capture import ROOT
from intentlineage.review_runner import prepare_invocation
from intentlineage.review_contract import build_request
from intentlineage.experiment_chatgpt import chatgpt_worker_source


@pytest.fixture
def boundary():
    path = ROOT / 'src/intentlineage/_reference/chatgpt_boundary.py'
    spec = importlib.util.spec_from_file_location('public_runtime_contract', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@pytest.fixture
def elf(tmp_path, monkeypatch, boundary):
    path = tmp_path / 'codex'; path.write_bytes(b'\x7fELFsynthetic-only')
    monkeypatch.setattr(boundary, 'CODEX_ELF_SHA256', hashlib.sha256(path.read_bytes()).hexdigest(), raising=False)
    return path


def test_runtime_has_only_verified_regular_elf_and_refuses_existing_root(tmp_path, boundary, elf):
    root = tmp_path / 'public-runtime'
    boundary.prepare_public_runtime(elf, root)
    assert [p.name for p in root.iterdir()] == ['intentlineage-codex']
    assert (root/'intentlineage-codex').read_bytes() == elf.read_bytes()
    boundary.verify_public_runtime(root)
    with pytest.raises((ValueError, FileExistsError)):
        boundary.prepare_public_runtime(elf, root)


@pytest.mark.parametrize('change', ['extra', 'changed', 'directory'])
def test_runtime_rejects_extra_members_and_hash_or_type_drift(tmp_path, boundary, elf, change):
    root = tmp_path/'public-runtime'; boundary.prepare_public_runtime(elf, root)
    if change == 'extra': (root/'extra').write_bytes(b'private')
    elif change == 'changed': (root/'intentlineage-codex').write_bytes(b'drift')
    else:
        (root/'intentlineage-codex').unlink(); (root/'intentlineage-codex').mkdir()
    with pytest.raises(ValueError): boundary.verify_public_runtime(root)


def test_runtime_refuses_wrong_binary_before_mount(tmp_path, boundary, elf):
    elf.write_bytes(b'\x7fELFwrong')
    with pytest.raises(ValueError): boundary.prepare_public_runtime(elf, tmp_path/'public-runtime')


def test_namespace_overlays_directory_never_new_child_under_read_only_usr(tmp_path, boundary, elf):
    invocation = tmp_path/'invocation'
    request = build_request({'elements': [], 'evidence_sha256':'synthetic-only'}, model='gpt-5.5', settings={'reasoning_effort':'none'})
    prepare_invocation(invocation, request)
    args = boundary.chatgpt_bubblewrap_command(invocation,tmp_path/'worker',tmp_path/'probes',elf)
    at = args.index('/usr/local/bin')
    assert args[at-2:at] == ['--ro-bind', str(invocation/'.controller/public-runtime')]
    assert '/runtime/codex' not in args and '/usr/bin/intentlineage-codex' not in args
    assert '--clearenv' in args and '--cap-drop' in args and '--new-session' in args
    source = chatgpt_worker_source(request,metadata_only=True,timeout_seconds=30,max_output_bytes=100000)
    assert '/usr/local/bin/intentlineage-codex' in source
    assert '/usr/bin/intentlineage-codex' not in source


def test_runtime_refuses_hardlinked_source(tmp_path, boundary, elf):
    import os
    try: os.link(elf, tmp_path/'other')
    except OSError: pytest.skip('host hardlinks unavailable')
    with pytest.raises(ValueError): boundary.prepare_public_runtime(elf,tmp_path/'public-runtime')


def test_credential_free_generated_worker_compiles_before_native_launch():
    request = build_request({'elements': []}, model='gpt-5.5', settings={'reasoning_effort':'none'})
    source = chatgpt_worker_source(request,metadata_only=False,probes_only=True,
                                  timeout_seconds=30,max_output_bytes=100000)
    compile(source,'native-probes-worker','exec')
