"""Trusted provider supervisor extending the existing offline namespace launcher.

Provider transport is mediated outside the reviewer namespace. Model-generated
commands additionally use the selected Codex native restricted profile. The
offline namespace alone does not prove that separate native command policy.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer


def _base():
    spec=importlib.util.spec_from_file_location('reviewed_offline_boundary',Path(__file__).with_name('offline_boundary.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def qualified_bubblewrap_command(invocation,worker,probe_config,cli_binary):
    """Reuse the existing mounts/caps/PID boundary, with trusted CLI networking."""
    argv=_base().offline_bubblewrap_command(invocation,worker,probe_config)
    argv.remove('--unshare-net');argv.insert(argv.index('--unshare-all')+1,'--share-net')
    at=argv.index('--chdir')
    argv[at:at]=['--ro-bind',str(Path(cli_binary).resolve()),'/runtime/codex']
    return argv


def cli_identity(path):
    path=Path(path).resolve(strict=True)
    if path.read_bytes()[:4]!=b'\x7fELF':raise ValueError('Actual namespace requires native Linux ELF CLI; no interop fallback')
    result=subprocess.run([str(path),'--version'],capture_output=True,timeout=20,
        env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','CODEX_HOME':'/nonexistent','LANG':'C.UTF-8'})
    if result.returncode:raise ValueError('Actual CLI version inspection failed closed')
    return {'path':str(path),'binary_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'version':result.stdout.decode('utf-8').strip(),'native_elf':True,
            'version_stderr':result.stderr.decode('utf-8',errors='replace')}


def main(config,runtime):
    identity=cli_identity(config['cli_binary'])
    if config['action']=='inspect-provider':
        print(json.dumps({'runtime':runtime,'cli':identity}));return
    if config.get('expected_cli_sha256')!=identity['binary_sha256'] or config.get('expected_runtime')!=runtime:
        raise ValueError('Actual provider runtime/CLI drift; stop and requalify')
    root=Path(config['invocation']).resolve(strict=True)
    if set(p.name for p in (root/'evidence').iterdir())!={'request.json','response-schema.json'}:
        raise ValueError('Only sealed own request/schema may enter reviewer mounts')
    # The code is generated from exact current M2 collection/canonical definitions
    # and the bound broker. It runs here, outside the model namespace, with no
    # provider credential in the mounted worker, argv or retained public records.
    broker_namespace={'__name__':'trusted_broker','__file__':__file__}
    exec(compile(config['broker_source'],'current-source-bound-broker','exec'),broker_namespace)
    broker=broker_namespace['make_broker'](config,root)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            if self.path not in {'/v1/responses','/responses'}:
                self.send_error(403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if length<1 or length>config['max_input_bytes']:raise ValueError('Input byte budget exceeded')
                raw=self.rfile.read(length)
                body=broker_namespace['_strict_load'](raw)
                result=broker.forward(body)
                self.send_response(result['status']);self.send_header('Content-Type','text/event-stream')
                self.send_header('Content-Length',str(len(result['body'])));self.end_headers();self.wfile.write(result['body'])
            except Exception as error:
                # Keep the failure class, never private exception/credential text.
                broker.failure=broker.failure or type(error).__name__
                data=b'{"error":{"message":"Bound provider transport refused; controller retained evidence"}}'
                self.send_response(502);self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    server=HTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    port=server.server_port
    # Gateway URL is fixed only after binding an own per-invocation listener.
    worker_source=config['worker_source'].replace('__INTENTLINEAGE_BROKER_PORT__',str(port))
    controller=root/'.controller';controller.mkdir(exist_ok=True)
    worker=controller/'qualified-worker.py';worker.write_text(worker_source,encoding='utf-8')
    canary=socket.socket();canary.bind(('127.0.0.1',0));canary.listen(1)
    probes=dict(config['probes']);probes.update(host_pid=os.getpid(),host_port=canary.getsockname()[1],
        host_namespaces={n:os.readlink('/proc/self/ns/'+n) for n in ['pid','mnt','net']})
    path=controller/'probe-config.json';path.write_text(json.dumps(probes),encoding='utf-8')
    argv=qualified_bubblewrap_command(root,worker,path,identity['path'])
    before=hashlib.sha256((root/'evidence/request.json').read_bytes()).hexdigest()
    try:
        try:
            result=subprocess.run(argv,capture_output=True,timeout=config['timeout_seconds']+35,close_fds=True,
                env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','INTENTLINEAGE_CONTROLLER_CANARY':'private-must-not-inherit'})
        except subprocess.TimeoutExpired as error:
            (controller/'boundary-timeout-stdout.bin').write_bytes(error.stdout or b'')
            (controller/'boundary-timeout-stderr.bin').write_bytes(error.stderr or b'')
            raise ValueError('Actual boundary timed out; charging unknown; raw partial evidence retained')
    finally:
        server.shutdown();server.server_close();canary.close()
    after=hashlib.sha256((root/'evidence/request.json').read_bytes()).hexdigest()
    if before!=after:raise ValueError('Own sealed evidence changed during actual provider launch')
    if result.returncode:
        print(json.dumps({'error':'Qualified boundary worker failed closed','exit_code':result.returncode,
            'stdout_base64':__import__('base64').b64encode(result.stdout).decode(),
            'stderr_base64':__import__('base64').b64encode(result.stderr).decode(),'runtime':runtime,'cli':identity,
            'forwarded_requests':broker.forwarded_requests,'received_requests':broker.received_requests,'argv':argv}));sys.exit(2)
    public=json.loads(result.stdout)
    exchange_path=broker.root/'exchange.json'
    exchange=json.loads(exchange_path.read_bytes()) if exchange_path.exists() else None
    print(json.dumps({'result':public,'runtime':runtime,'cli':identity,'argv':argv,'exit_code':result.returncode,
        'stderr':result.stderr.decode('utf-8',errors='replace'),
        'forwarded_requests':broker.forwarded_requests,'received_requests':broker.received_requests,
        'broker_failure':broker.failure,'broker_exchange':exchange,'credential_persisted':False}))
