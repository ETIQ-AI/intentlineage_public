"""Trusted public OS networking inputs must match the reviewed metadata binding."""
import importlib.util
from pathlib import Path
import pytest

@pytest.mark.parametrize('expected', [None,{}, {'/etc/resolv.conf':{'sha256':'drift','bytes':1}}])
def test_provider_refuses_missing_or_drifted_public_runtime(expected):
    path=Path(__file__).resolve().parents[1]/'src/intentlineage/_reference/chatgpt_boundary.py'
    spec=importlib.util.spec_from_file_location('runtime_drift',path)
    boundary=importlib.util.module_from_spec(spec);spec.loader.exec_module(boundary)
    actual={'/etc/resolv.conf':{'sha256':'a'*64,'bytes':20},
            '/etc/ssl/certs/ca-certificates.crt':{'sha256':'b'*64,'bytes':100}}
    with pytest.raises(ValueError):boundary.check_public_network_runtime(
        {'action':'chatgpt-provider','expected_public_network_runtime':expected},actual)


def test_provider_accepts_exact_bound_runtime_but_setup_is_unqualified():
    path=Path(__file__).resolve().parents[1]/'src/intentlineage/_reference/chatgpt_boundary.py'
    spec=importlib.util.spec_from_file_location('runtime_match',path)
    boundary=importlib.util.module_from_spec(spec);spec.loader.exec_module(boundary)
    actual={'/etc/resolv.conf':{'sha256':'a'*64,'bytes':20},
            '/etc/ssl/certs/ca-certificates.crt':{'sha256':'b'*64,'bytes':100}}
    boundary.check_public_network_runtime({'action':'chatgpt-provider','expected_public_network_runtime':actual},actual)
    boundary.check_public_network_runtime({'action':'chatgpt-metadata','expected_public_network_runtime':None},actual)
