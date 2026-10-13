"""Regressions from real native failures and the single active completion brief."""
import ast
import json
from types import SimpleNamespace
import pytest
from intentlineage import experiment_chatgpt as chat
from intentlineage import experiment_execution as execution
from intentlineage import experiment_isolation as isolation
from intentlineage.review_contract import build_request
from pathlib import Path
import importlib.util


@pytest.mark.parametrize('failure', ['create', 'connect'])
def test_actual_native_network_probe_accepts_kernel_denial_at_socket_creation(monkeypatch, failure):
    import socket
    request = build_request({}, model='gpt-5.5',settings={'reasoning_effort':'none'})
    worker = execution.qualified_worker_source(request,[],[],30)
    assignment = next(n for n in ast.parse(worker).body if isinstance(n,ast.Assign)
                      and any(isinstance(t,ast.Name) and t.id=='source' for t in n.targets))
    probe = assignment.value.func.value.value
    # Execute the exact generated networking probe, with the same EPERM the
    # native receipt observed. Other probe behavior is established on real Linux.
    start = 's=None' if 's=None' in probe else 's=socket.socket()'
    network = probe[probe.index(start):probe.index('print(json.dumps(probes))')]
    class DeniedSocket:
        def settimeout(self,*args): pass
        def connect(self,*args): raise PermissionError('kernel denied connection')
        def close(self): pass
    def create():
        if failure=='create': raise PermissionError('kernel denied socket')
        return DeniedSocket()
    monkeypatch.setattr(socket,'socket',create)
    values={'socket':socket,'probes':{},'config':{'host_port':1}}
    exec(compile(network,'exact-native-network-probe','exec'),values)
    assert values['probes']['network'] is True


def test_auth_contract_binds_single_active_completion_brief():
    assert chat.CORRECTION_NAME == 'developer_m3-completion-20261012.md'


def test_provider_outer_wait_preserves_explicit_client_timeout(monkeypatch):
    monkeypatch.setattr(isolation.shutil,'which',lambda _: 'wsl')
    observed=[]
    def launch(*args,**kwargs):
        observed.append(kwargs['timeout'])
        return SimpleNamespace(returncode=0,stdout=b'{}',stderr=b'')
    monkeypatch.setattr(isolation.subprocess,'run',launch)
    isolation.OfflineSandbox()._call({'action':'chatgpt-provider','timeout_seconds':300})
    assert observed == [375]


def test_trusted_client_runtime_supplies_only_public_dns_and_ca_files(tmp_path):
    spec=importlib.util.spec_from_file_location('client_runtime_boundary',
        isolation.ROOT/'src/intentlineage/_reference/chatgpt_boundary.py')
    boundary=importlib.util.module_from_spec(spec);spec.loader.exec_module(boundary)
    resolver=tmp_path/'resolv.conf';resolver.write_bytes(b'nameserver 192.0.2.1\n')
    ca=tmp_path/'ca.pem';ca.write_bytes(b'synthetic-public-ca-fixture')
    args,record=boundary.prepare_network_runtime(tmp_path/'network-runtime',resolver=resolver,ca=ca)
    assert {p.name for p in (tmp_path/'network-runtime').iterdir()} == {'resolv.conf','ca-certificates.crt'}
    assert args == ['--ro-bind',str(tmp_path/'network-runtime/resolv.conf'),'/etc/resolv.conf',
                    '--ro-bind',str(tmp_path/'network-runtime/ca-certificates.crt'),'/etc/ssl/certs/ca-certificates.crt']
    assert set(record)=={'/etc/resolv.conf','/etc/ssl/certs/ca-certificates.crt'}
    assert '/etc' not in args and '/home' not in args
