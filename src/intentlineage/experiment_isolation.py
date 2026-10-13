"""Fail-closed offline Bubblewrap provider adapter on WSL Ubuntu.

Only the trusted synthetic M2 transport fixture can run. Qualification covers
filesystem, process, environment and command networking, not hosted transport.
"""
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

from .native_capture import ROOT, digest, file_hash
from .review_provider import MockProvider
from .review_runner import TransportFailure, prepare_invocation
from .review_contract import canonical_bytes
from .experiment_faults import write


class IsolationUnavailable(RuntimeError):
    pass


def _linux_path(path):
    value=Path(path).resolve().as_posix()
    if len(value)>2 and value[1]==':':
        return '/mnt/'+value[0].lower()+value[2:]
    if value.startswith('/'):
        return value
    raise ValueError('Unsupported WSL path')


def _check_tree(path):
    path=Path(path)
    for p in [path,*path.rglob('*')]:
        info=p.lstat()
        if p.is_symlink() or getattr(info,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',0x400):
            raise ValueError('Package contains a symlink/reparse boundary escape')
        if p.is_file() and info.st_nlink!=1:
            raise ValueError('Package contains a hardlinked resource')


PROBE_SOURCE = '''
import json, os, socket
from pathlib import Path
config=json.loads(Path('/runtime/probes.json').read_text())
probes={}
request=json.loads(Path('/evidence/request.json').read_text())
probes['own_package']=bool(request) and Path('/evidence/response-schema.json').is_file()
def denied(path):
    try: Path(path).read_bytes()
    except OSError: return True
    return False
for key,path in config['paths'].items(): probes[key]=denied(path)
os.symlink(config['paths']['source'],'/tmp/escape')
probes['symlink']=denied('/tmp/escape')
probes['process']=denied('/proc/'+str(config['host_pid'])+'/environ')
probes['environment']='INTENTLINEAGE_CONTROLLER_CANARY' not in os.environ
probes['private_state']=not list(Path('/home/runner/.codex').iterdir()) and not list(Path('/workspace').iterdir()) and not Path('/tmp/prior-session').exists()
Path('/home/runner/.codex/new-session').write_text('fresh offline invocation')
try: Path('/evidence/request.json').write_text('changed')
except OSError: probes['readonly']=True
else: probes['readonly']=False
namespaces={name:os.readlink('/proc/self/ns/'+name) for name in ('pid','mnt','net')}
probes['process']=probes['process'] and namespaces['pid']!=config['host_namespaces']['pid'] and namespaces['mnt']!=config['host_namespaces']['mnt']
connection=socket.socket();connection.settimeout(1)
try: connection.connect(('127.0.0.1',config['host_port']))
except OSError: probes['network']=namespaces['net']!=config['host_namespaces']['net']
else: probes['network']=False
connection.close()
if not all(probes.values()):
    print(json.dumps({'probes':probes,'response':None}));raise SystemExit(0)
'''


class OfflineSandbox:
    def __init__(self, *, wsl_bin='wsl', distro='Ubuntu'):
        self.wsl_bin=wsl_bin;self.distro=distro

    def _call(self,config):
        executable=shutil.which(self.wsl_bin)
        if not executable:
            raise IsolationUnavailable('WSL/Bubblewrap unavailable; unrestricted fallback forbidden')
        supervisor=ROOT/'src/intentlineage/_reference/offline_boundary.py'
        argv=[executable,'-d',self.distro,'--exec','/usr/bin/python3',_linux_path(supervisor)]
        try:
            client_actions={'provider','chatgpt-provider','chatgpt-metadata','chatgpt-probes'}
            wait_limit=config['timeout_seconds']+75 if config.get('action') in client_actions else 60
            completed=subprocess.run(argv,input=canonical_bytes(config),capture_output=True,timeout=wait_limit,close_fds=True)
        except (OSError,subprocess.TimeoutExpired) as error:
            raise IsolationUnavailable('Offline sandbox runtime unavailable: '+str(error)) from error
        if completed.returncode:
            detail=completed.stdout.decode('utf-8',errors='replace')+completed.stderr.decode('utf-8',errors='replace')
            raise IsolationUnavailable('Offline sandbox failed closed: '+detail[:3000])
        try:
            return json.loads(completed.stdout)
        except ValueError as error:
            raise IsolationUnavailable('Offline sandbox returned no valid receipt') from error

    def inspect_runtime(self):
        return self._call({'action':'inspect'})

    def run(self,invocation,*,adaptive=False,fixture='normal',probes_only=False):
        invocation=Path(invocation).resolve()
        _check_tree(invocation)
        evidence=invocation/'evidence'
        if {p.name for p in evidence.iterdir()} != {'request.json','response-schema.json'}:
            raise ValueError('Only sealed own request/schema may enter reviewer access')
        for name in ['workspace','home','temp','output']:
            if any((invocation/name).iterdir()):
                raise ValueError('Reviewer mutable contexts must be fresh and private')
        if fixture not in {'normal','invalid','transport','failure'}:
            raise ValueError('Unknown explicit synthetic transport fixture')
        controller=invocation/'.controller';controller.mkdir()
        paths={}
        for name in ['sibling','oracle','source','config']:
            path=controller/(name+'-canary.txt');path.write_text('controller-only-'+name,encoding='utf-8')
            paths[name]=_linux_path(path)
        # Reuse the exact committed M2 MockProvider definition instead of reimplementing an assessor.
        worker=PROBE_SOURCE+'\nfrom copy import deepcopy\ndef canonical_bytes(value):\n    return json.dumps(value,sort_keys=True,separators=(\",\",\":\"),ensure_ascii=False,allow_nan=False).encode()\n'
        worker+=inspect.getsource(MockProvider)
        worker+='\nresponse=MockProvider(adaptive='+repr(bool(adaptive))+')(request,None)\n'
        if fixture=='invalid':worker+="response['raw_reply']='{}'\n"
        elif fixture=='failure':worker+="response['failure']='synthetic provider failure with unknown charging'\n"
        elif fixture=='transport':worker+="response['synthetic_transport_failure']=True\n"
        worker+="print(json.dumps({'probes':probes,'response':response,'namespaces':namespaces}))\n"
        worker_path=controller/'worker.py';worker_path.write_text(worker,encoding='utf-8',newline='\n')
        config={'action':'run','invocation':_linux_path(invocation),'worker':_linux_path(worker_path),'probes':{'paths':paths}}
        request_before=file_hash(evidence/'request.json')
        result=self._call(config)
        probes=result['result']['probes']
        if request_before!=file_hash(evidence/'request.json') or not probes or not all(probes.values()):
            write(controller/'failed-isolation.json',result)
            raise IsolationUnavailable('Positive/denial isolation probes failed; no review admissible')
        receipt={'format_version':'m3a-isolation.1','qualified':True,'synthetic':True,
            'scope':'offline synthetic reviewer command boundary','provider_transport':'disabled',
            'command_network':'denied','fresh_session':True,'history_policy':'none',
            'request_file_sha256':request_before,'worker_sha256':file_hash(worker_path),
            'supervisor_sha256':file_hash(ROOT/'src/intentlineage/_reference/offline_boundary.py'),
            'runtime':result['runtime'],'probes':probes,'argv':result['argv'],
            'namespaces':result['result']['namespaces'],'raw_events':result,
            'limits':['Hosted provider transport and model CLI remain unqualified for M3B.']}
        receipt['receipt_sha256']=digest(receipt)
        write(invocation/'isolation-receipt.json',receipt)
        return receipt if probes_only else (result['result']['response'],receipt)

    def qualify(self,directory):
        directory=Path(directory)
        prepare_invocation(directory,{'evidence':{'evidence_sha256':'offline-probe','elements':[]},
                                      'allow_opening':False,'probe':'own sealed package'})
        return self.run(directory,probes_only=True)


class IsolatedMockProvider:
    """M2 provider adapter. No caller-supplied command or live provider route."""
    def __init__(self, *, adaptive=False, fixtures=(), sandbox=None):
        self.adaptive=adaptive;self.fixtures=list(fixtures);self.calls=0
        self.sandbox=sandbox or OfflineSandbox();self.receipts=[]

    def __call__(self,request,invocation):
        staged=json.loads((Path(invocation)/'evidence/request.json').read_bytes())
        if staged!=request:
            raise ValueError('Sealed provider request differs from controller request')
        index=self.calls;self.calls+=1
        fixture=self.fixtures[index] if index<len(self.fixtures) else 'normal'
        response,receipt=self.sandbox.run(invocation,adaptive=self.adaptive,fixture=fixture)
        self.receipts.append(receipt)
        if response.pop('synthetic_transport_failure',False):
            raise TransportFailure('Explicit synthetic transport-only failure; no reasoning started')
        response.update(synthetic=True,mocked=True,provider_call_id=f'offline-{self.calls}',
                        isolation_receipt_sha256=receipt['receipt_sha256'])
        return response
