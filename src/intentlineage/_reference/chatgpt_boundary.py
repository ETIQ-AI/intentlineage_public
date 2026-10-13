"""Trusted ChatGPT extension of the existing M3A/provider namespace launcher.

Only one explicit cached auth file is supplied to the supported client; neither
the existing Codex home nor existing sessions/config/history are mounted.
"""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import re
import shutil
import stat


CODEX_ELF_SHA256 = '12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad'


def _unlinked_path(path):
    path = Path(path).absolute()
    for candidate in [path, *path.parents]:
        info = candidate.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Public runtime path/link escape refused')
    return path


def _verified_elf(path):
    path = _unlinked_path(path); info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('Public Codex ELF must be one regular unlinked file')
    raw = path.read_bytes()
    if raw[:4] != b'\x7fELF' or hashlib.sha256(raw).hexdigest() != CODEX_ELF_SHA256:
        raise ValueError('Public Codex ELF identity differs')
    return path


def verify_public_runtime(directory):
    directory = _unlinked_path(directory)
    if not directory.is_dir() or {p.name for p in directory.iterdir()} != {'intentlineage-codex'}:
        raise ValueError('Public runtime must contain exactly the verified Codex ELF')
    _verified_elf(directory/'intentlineage-codex')
    return directory


def prepare_public_runtime(cli_binary, directory):
    source = _verified_elf(cli_binary)
    directory = Path(directory).absolute()
    _unlinked_path(directory.parent)
    directory.mkdir(exist_ok=False)
    target = directory/'intentlineage-codex'
    with source.open('rb') as original, target.open('xb') as copied:
        shutil.copyfileobj(original, copied)
    target.chmod(0o755)
    return verify_public_runtime(directory)


def prepare_network_runtime(directory, *, resolver=Path('/etc/resolv.conf'),
                            ca=Path('/etc/ssl/certs/ca-certificates.crt')):
    """Copy only public OS resolver and CA inputs; no broad configuration mount."""
    directory=Path(directory).absolute(); _unlinked_path(directory.parent)
    directory.mkdir(exist_ok=False)
    argv=[]; record={}
    for source,name,destination in [(resolver,'resolv.conf','/etc/resolv.conf'),
            (ca,'ca-certificates.crt','/etc/ssl/certs/ca-certificates.crt')]:
        # /etc/resolv.conf is a normal WSL-managed symlink. Resolve only these
        # explicit public OS inputs and copy their regular target, never its tree.
        source=_unlinked_path(Path(source).resolve(strict=True))
        if not source.is_file():raise ValueError('Public network runtime file missing')
        raw=source.read_bytes(); target=directory/name
        with target.open('xb') as stream:stream.write(raw)
        target.chmod(0o644)
        record[destination]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        argv += ['--ro-bind',str(target),destination]
    if {p.name for p in directory.iterdir()} != {'resolv.conf','ca-certificates.crt'}:
        raise ValueError('Unexpected public network runtime membership')
    return argv,record


def check_public_network_runtime(config,actual):
    expected=config.get('expected_public_network_runtime')
    if config['action']=='chatgpt-provider' and not expected:
        raise ValueError('Reviewed public DNS/TLS runtime binding required')
    if expected is not None and expected != actual:
        raise ValueError('Reviewed public DNS/TLS runtime drift; stop and requalify')


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _admission(config):
    """Recheck real main decisions/source before the trusted client may reason."""
    source=Path(config['source_root']).resolve(strict=True)
    files=list((source/'src/intentlineage').rglob('*.py'))
    files += [source/name for name in ['scripts/m3b.py','scripts/audit_m3b.py','scripts/audit_m3b_execution.py','scripts/capture_m1_v4.py','requirements.txt']]
    actual={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    if actual!=config['controller_source_manifest']:raise ValueError('Trusted native controller source changed')
    current=_digest(actual);admission=config.get('admission') or {};authority=source.parent.parent/'instructions_between_agents'
    contract=admission.get('contract')
    user_authority=None
    def user_module():
        spec=importlib.util.spec_from_file_location('user_continuation_gate',source/'src/intentlineage/experiment_user_authorization.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    if admission.get('kind')=='qualification':
        path=authority/'m3b-qualification-code-overseer-review.md'
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=admission['review_sha256']:raise ValueError('Actual main qualification review changed')
        blocks=re.findall(r'```intentlineage-qualification-code-review\r?\n(.*?)\r?\n```',raw.decode(),re.S)
        if len(blocks)!=1:raise ValueError('Actual qualification review missing')
        decision=json.loads(blocks[0])
        technical_binding=user_module().capture_authorized_launch(source,contract,decision)
        if technical_binding['authorized_launch_sha256']!=_digest(contract):raise ValueError('Qualification capture amendment binding differs')
        if decision.get('controller_source_sha256')!=current:
            user_authority=user_module().validate_source_authorization(source)
            if decision.get('controller_source_sha256')!=user_authority['reviewed_source_sha256'] or technical_binding['controller_source_sha256']!=current:
                raise ValueError('User qualification adaptation source/launch differs')
        decisions=[decision]
    elif admission.get('kind')=='campaign':
        protocol=contract['protocol'];qualification=contract['qualification'];decisions=[]
        for gate,name in [('real_path_review','m3b-real-path-overseer-review.md'),('protocol_review','m3b-protocol-overseer-review.md'),('experiment_authorization','m3b-campaign-overseer-release.md')]:
            record=contract['gates'][gate]
            if record.get('kind')=='observed_user_authorization':
                if not user_module().validate_user_campaign_record(source,record,gate,protocol,qualification,evidence_root=source):
                    raise ValueError('Actual user campaign binding missing or changed')
                continue
            raw=(authority/name).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=contract['gates'][gate]['sha256']:raise ValueError('Actual main campaign decision changed')
            blocks=re.findall(r'```intentlineage-overseer-decision\r?\n(.*?)\r?\n```',raw.decode(),re.S)
            if len(blocks)!=1:raise ValueError('Actual campaign release missing')
            decision=json.loads(blocks[0])
            if decision.get('gate')!=gate or decision.get('protocol_sha256')!=_digest(protocol) or decision.get('qualification_sha256')!=qualification['qualification_sha256']:
                raise ValueError('Actual campaign source/configuration/qualification differs')
            decisions.append(decision)
    else:raise ValueError('Native reviewer admission requires actual source-bound Overseer decisions')
    for decision in decisions:
        if decision.get('issued_by')!='overseer' or decision.get('status')!='approved' or decision.get('synthetic') is not False:
            raise ValueError('Native reviewer source-bound decision not approved')
        if decision.get('controller_source_sha256')!=current and (user_authority is None or decision.get('controller_source_sha256')!=user_authority['reviewed_source_sha256']):
            raise ValueError('Native source changed outside explicit user adaptation')


def _provider():
    spec = importlib.util.spec_from_file_location('existing_provider_boundary', Path(__file__).with_name('provider_boundary.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def chatgpt_bubblewrap_command(invocation, worker, probes, cli_binary, auth_file=None, quarantine=None,
                              network_runtime_binds=()):
    argv = _provider().qualified_bubblewrap_command(invocation, worker, probes, cli_binary)
    # Codex launches its own Linux sandbox helper before executing the command.
    # Its public ELF belongs in the already-readable minimal OS runtime. Private
    # worker/auth/config files remain under denied /runtime; no policy is relaxed.
    root = Path(invocation).absolute()
    controller = root/'.controller'; controller.mkdir(exist_ok=True)
    public_runtime = prepare_public_runtime(cli_binary, controller/'public-runtime')
    index = argv.index('/runtime/codex')
    del argv[index-2:index+1]
    at = argv.index('--chdir')
    additions = ['--ro-bind', str(public_runtime), '/usr/local/bin', *network_runtime_binds]
    if auth_file is not None:
        additions += ['--ro-bind', str(Path(auth_file).resolve()), '/runtime/cached-auth.json']
    if quarantine is not None:
        additions += ['--bind', str(Path(quarantine).resolve()), '/private/quarantine']
    argv[at:at] = additions
    return argv


def main(config, runtime):
    if config['action']=='chatgpt-provider':_admission(config)
    cli = _provider().cli_identity(config['cli_binary'])
    if config['expected_cli_sha256'] != cli['binary_sha256'] or config['expected_runtime'] != runtime:
        raise ValueError('ChatGPT native CLI/runtime drift')
    root = Path(config['invocation']).resolve(strict=True)
    if {p.name for p in (root/'evidence').iterdir()} != {'request.json', 'response-schema.json'}:
        raise ValueError('Only own sealed evidence/schema may be mounted')
    controller = root/'.controller'; controller.mkdir(exist_ok=True)
    worker = controller/'chatgpt-worker.py'; worker.write_text(config['worker_source'], encoding='utf-8')
    listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(1)
    probes = dict(config['probes']); probes.update(host_pid=os.getpid(), host_port=listener.getsockname()[1],
        host_namespaces={n: os.readlink('/proc/self/ns/'+n) for n in ['pid','mnt','net']})
    probe_file = controller/'probe-config.json'; probe_file.write_text(json.dumps(probes), encoding='utf-8')
    before = hashlib.sha256((root/'evidence/request.json').read_bytes()).hexdigest()
    network_binds,network_record=prepare_network_runtime(controller/'network-runtime')
    (controller/'network-runtime-record.json').write_text(json.dumps(network_record),encoding='utf-8')
    check_public_network_runtime(config,network_record)
    source = None; cached = None
    private = tempfile.TemporaryDirectory(prefix='intentlineage-chatgpt-auth-')
    quarantine = Path(tempfile.mkdtemp(prefix='intentlineage-chatgpt-quarantine-'))
    os.chmod(quarantine, 0o700)
    original_auth = None
    try:
        if config['action'] != 'chatgpt-probes':
            source = Path(config['auth_source']['path']).resolve(strict=True)
            if source.is_symlink() or source.stat().st_nlink != 1: raise ValueError('Auth source link refused')
            original_auth = source.read_bytes()
            value = json.loads(original_auth)
            tokens = value.get('tokens') or {}
            account_hash = hashlib.sha256(json.dumps(tokens.get('account_id'), sort_keys=True, separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            if value.get('auth_mode') != 'chatgpt' or value.get('OPENAI_API_KEY') or account_hash != config['auth_source']['account_sha256']:
                raise ValueError('Existing ChatGPT auth account/source changed')
            cached = Path(private.name)/'auth.json'; cached.write_bytes(original_auth); os.chmod(cached, 0o600)
        argv = chatgpt_bubblewrap_command(root, worker, probe_file, cli['path'], cached, quarantine,network_binds)
        try:
            result = subprocess.run(argv, capture_output=True, timeout=config['timeout_seconds']+40,
                env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','INTENTLINEAGE_CONTROLLER_CANARY':'not-inherited'}, close_fds=True)
        except subprocess.TimeoutExpired as error:
            (controller/'boundary-timeout-stdout.bin').write_bytes(error.stdout or b'')
            (controller/'boundary-timeout-stderr.bin').write_bytes(error.stderr or b'')
            raise ValueError('ChatGPT boundary interrupted; unknown charging; original partial files retained')
        if hashlib.sha256((root/'evidence/request.json').read_bytes()).hexdigest() != before:
            raise ValueError('Own evidence was modified')
        verify_public_runtime(controller/'public-runtime')
        if result.returncode:
            print(json.dumps({'error':'ChatGPT boundary failed closed','exit_code':result.returncode,
                'stdout_base64':base64.b64encode(result.stdout).decode(),'stderr_base64':base64.b64encode(result.stderr).decode(),
                'runtime':runtime,'cli':cli,'argv':argv,'public_network_runtime':network_record}));return
        public = json.loads(result.stdout)
        # Supported client's refreshed cache is never exported. Preserve it privately;
        # do not overwrite a login changed concurrently by the user's live client.
        refresh = quarantine/'refreshed-auth.json'
        if source is not None and refresh.exists():
            refreshed = refresh.read_bytes(); replacement = json.loads(refreshed)
            if replacement.get('auth_mode') != 'chatgpt' or replacement.get('OPENAI_API_KEY') or replacement.get('tokens',{}).get('account_id') != json.loads(original_auth)['tokens']['account_id']:
                raise ValueError('Supported client changed authentication route/account')
            if source.read_bytes() != original_auth:
                public['auth_refresh'] = 'retained_privately; source changed concurrently, not overwritten'
            else:
                source.write_bytes(refreshed)
                public['auth_refresh'] = 'supported_client_cache_updated_without_history'
            refresh.unlink()
        print(json.dumps({'result':public,'runtime':runtime,'cli':cli,'argv':argv,
            'public_network_runtime':network_record,
            'exit_code':result.returncode,'stderr':result.stderr.decode(errors='replace'),
            'credential_persisted_in_export':False,'quarantine_present':any(quarantine.iterdir())}))
    finally:
        listener.close(); private.cleanup()
