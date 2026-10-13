"""Offline WSL supervisor; adapted from use_case_icp n05_runner.

Runs outside the reviewer namespace. Only explicit own resources are mounted.
No provider transport or host repository/home mount is supported here.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys


def _runtime_binds():
    # Reused n05_runner._runtime_binds; OS runtime only, never /etc or host home.
    binds = []
    for path in ('/usr', '/lib', '/lib64'):
        if Path(path).exists():
            binds.extend(['--ro-bind', path, path])
    if Path('/bin').is_symlink():
        binds.extend(['--symlink', os.readlink('/bin'), '/bin'])
    elif Path('/bin').exists():
        binds.extend(['--ro-bind', '/bin', '/bin'])
    return binds


def offline_bubblewrap_command(invocation, worker, probe_config):
    """Adapt n05 python_bubblewrap_command; clear env/caps and ephemeral state."""
    root = Path(invocation).resolve(strict=True)
    return ['/usr/bin/bwrap', '--unshare-all', '--unshare-net', '--die-with-parent',
        '--new-session', '--clearenv', '--cap-drop', 'ALL', *_runtime_binds(),
        '--proc', '/proc', '--dev', '/dev',
        '--ro-bind', str(root/'evidence'), '/evidence',
        '--ro-bind', str(worker), '/runtime/worker.py',
        '--ro-bind', str(probe_config), '/runtime/probes.json',
        '--bind', str(root/'workspace'), '/workspace',
        '--bind', str(root/'output'), '/output',
        '--tmpfs', '/tmp', '--dir', '/home/runner/.codex',
        '--setenv', 'HOME', '/home/runner', '--setenv', 'TMPDIR', '/tmp',
        '--setenv', 'CODEX_HOME', '/home/runner/.codex',
        '--setenv', 'PATH', '/usr/bin:/bin', '--setenv', 'LANG', 'C.UTF-8',
        '--chdir', '/workspace', '--', '/usr/bin/python3', '-I', '/runtime/worker.py']


def main():
    config = json.load(sys.stdin)
    version = subprocess.run(['/usr/bin/bwrap', '--version'],capture_output=True,text=True,check=True).stdout.strip()
    interpreter=Path(sys.executable).resolve()
    runtime = {'bubblewrap_version':version,
        'python_version':sys.version,'kernel':os.uname().release,
        'os_release':Path('/etc/os-release').read_text(),
        'binary_sha256':__import__('hashlib').sha256(Path('/usr/bin/bwrap').read_bytes()).hexdigest(),
        'python_executable':str(interpreter),'python_binary_sha256':__import__('hashlib').sha256(interpreter.read_bytes()).hexdigest()}
    if config['action']=='inspect':
        print(json.dumps(runtime));return
    if config['action'] in {'chatgpt-probes','chatgpt-metadata','chatgpt-provider'}:
        import importlib.util
        spec=importlib.util.spec_from_file_location('chatgpt_provider_boundary',Path(__file__).with_name('chatgpt_boundary.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.main(config,runtime);return
    if config['action'] in {'provider','inspect-provider'}:
        import importlib.util
        spec=importlib.util.spec_from_file_location('qualified_provider_boundary',Path(__file__).with_name('provider_boundary.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.main(config,runtime);return
    # Host process/network canaries are real, outside the newly created namespaces.
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
    probes=dict(config['probes'])
    probes.update(host_pid=os.getpid(),host_port=listener.getsockname()[1],
        host_namespaces={name:os.readlink('/proc/self/ns/'+name) for name in ('pid','mnt','net')})
    controller=Path(config['invocation'])/'.controller'
    controller.mkdir(exist_ok=True)
    probe_path=controller/'probe-config.json'
    probe_path.write_text(json.dumps(probes),encoding='utf-8')
    argv=offline_bubblewrap_command(config['invocation'],config['worker'],probe_path)
    env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8',
         'INTENTLINEAGE_CONTROLLER_CANARY':'private-environment-must-not-be-inherited'}
    result=subprocess.run(argv,env=env,text=True,capture_output=True,timeout=45,close_fds=True)
    listener.close()
    if result.returncode:
        print(json.dumps({'error':'Bubblewrap invocation failed','returncode':result.returncode,
                         'stderr':result.stderr,'runtime':runtime,'argv':argv}));sys.exit(2)
    print(json.dumps({'result':json.loads(result.stdout),'runtime':runtime,
                     'argv':argv,'stderr':result.stderr,'exit_code':result.returncode}))


if __name__=='__main__':
    main()
