"""Read-only gates and human command artifacts. Preparation has no live executor."""
import json
from pathlib import Path
import sys

from .native_capture import ROOT, digest, file_hash
from .review_runner import SESSION_VERSION
from .review_provider import prepare_provider_command
from .experiment_protocol import validate_protocol, M1_COMMIT, M2_COMMIT, M3A_COMMIT, PREPARATION_COMMIT
from .experiment_qualification import validate_qualification
from .experiment_transport import PreparationOnly, _check_invocation


# These are observed Overseer decisions, not declarations issued by this code.
# Their exact archived Markdown bytes are required. Unknown future decisions
# (combined review and experiment authorization) are deliberately not registered.
AUTHORITY = {
    'm1_acceptance': ('accepted', M1_COMMIT, 'm1-overseer-acceptance-v4.md', 'b0cec136cc537b88ec90e3130cee8a7e085385b5aefa620184d2f6780c7de383'),
    'm2_acceptance': ('accepted', M2_COMMIT, 'm2-overseer-acceptance-v4.md', '769779ef95aea865a11cad094078f9ccf6b5bdb528f43627cbc9997a72689e3c'),
    'corrected_m3a_review': ('reviewed', M3A_COMMIT, 'm3a-overseer-clearance-20261012.md', 'f403a831789233e87bad0af37d76bd91c67f5ace6a6e30c9e8cc03bd2fa1f168'),
    'integrated_preparation_review': ('reviewed',PREPARATION_COMMIT,'m3b-integrated-overseer-review-20261012.md','8048533ec3017cccba55ad9a4c3587687ccaedd0c05a54cb96ec052689226529'),
}
AUTHORITY_DIRECTORY = 'instructions_between_agents/archive/m3b-integration-authority-20261012/instructions_between_agents'


def decision_records():
    return {key: {'status': status, 'commit': commit, 'synthetic': False, 'issued_by': 'overseer',
                  'path': ('instructions_between_agents/archive/m3b-execution-authority-20261012/instructions_between_agents'
                           if key=='integrated_preparation_review' else AUTHORITY_DIRECTORY)+'/'+filename,
                  'sha256': sha, 'kind': 'observed_overseer_decision'}
            for key, (status, commit, filename, sha) in AUTHORITY.items()}


def _authority(record, *, gate, status, commit=None, protocol_sha256=None, evidence_root):
    """Accept only the exact observed decision; self-issued JSON is not authority."""
    known = decision_records().get(gate)
    if known is None or record != known:
        return False
    if not isinstance(record, dict) or record.get('status') != status or record.get('synthetic') is not False:
        return False
    if record.get('issued_by') != 'overseer': return False
    if commit is not None and record.get('commit') != commit: return False
    if protocol_sha256 is not None:
        if record.get('protocol_sha256') != protocol_sha256 or record.get('scope') != 'human-run M3B': return False
    try:
        raw_path = evidence_root / record['path']
        from .experiment_isolation import _check_tree
        for item in [raw_path, *raw_path.parents]:
            if item == evidence_root: break
            if item.is_symlink(): return False
        _check_tree(raw_path)
        path = raw_path.resolve(strict=True)
        if not path.is_relative_to(evidence_root) or not path.is_file() or path.is_symlink(): return False
        if file_hash(path) != record['sha256']: return False
        return file_hash(path) == known['sha256']
    except (OSError, KeyError, TypeError, ValueError): return False


def preflight(protocol, gates, qualification, *, evidence_root=ROOT):
    blockers = []
    errors = []
    try:
        validation = validate_protocol(protocol)
        if not validation['ready']: blockers.append('protocol_unresolved')
    except (ValueError, TypeError) as error:
        validation = {'valid': False, 'ready': False, 'unresolved': [], 'protocol_sha256': None}
        blockers.append('protocol_invalid'); errors.append(str(error))
    gates = gates if isinstance(gates, dict) else {}
    root = Path(evidence_root).resolve()
    dependencies = protocol.get('dependencies', {}) if isinstance(protocol, dict) else {}
    for key, status, expected in [('m1_acceptance', 'accepted', dependencies.get('m1')),
                                  ('m2_acceptance', 'accepted', dependencies.get('m2')),
                                  ('corrected_m3a_review', 'reviewed', dependencies.get('m3a'))]:
        if not expected or not _authority(
                gates.get(key), gate=key, status=status, commit=expected, evidence_root=root):
            blockers.append(key)
    blockers.append('combined_m3b_review')
    # This is deliberately not an offline->real promotion path. Even an external
    # alleged real receipt cannot be qualified until the actual provider-boundary
    # implementation is integrated and reviewed. Current preparation accepts only
    # offline evidence and always leaves the real-provider gate closed.
    if qualification is not None:
        try: validate_qualification(qualification, scope='real-provider')
        except ValueError as error: errors.append(str(error))
    blockers.append('real_provider_isolation')
    identity = validation['protocol_sha256']
    if not identity or not _authority(gates.get('experiment_authorization'), gate='experiment_authorization', status='authorized',
                                      protocol_sha256=identity, evidence_root=root):
        blockers.append('experiment_authorization')
    # Reviewed M3A's 4.2 infrastructure is integrated, but remains synthetic-only.
    # Do not invent a second live campaign implementation or mislabel its output.
    blockers.append('campaign_integration')
    return {'format_version': 'm3b-preflight.1', 'ready': False, 'execution_available': False,
            'blockers': blockers, 'diagnostics': errors, 'protocol': validation,
            'coding_authorization_satisfies_experiment_gates': False,
            'provisional': False, 'review_session_version': SESSION_VERSION,
            'integrated_infrastructure': all(gate not in blockers for gate in AUTHORITY),
            'limits': ['Combined M3B code and a real-results campaign path still require Overseer review.',
                       'Real provider credential/control-plane access and generated-command networking need separate probes.',
                       'No live campaign entry point is implemented or enabled by preparation.']}


def prepare_commands(protocol, gates, qualification, *, output, protocol_path='protocol.json',
                     gates_path='gates.json', qualification_path='qualification.json', evidence_root=ROOT):
    """Write argv/data only. No subprocess, inference, campaign or hosted command."""
    check = preflight(protocol, gates, qualification, evidence_root=evidence_root)
    script = str(ROOT/'scripts/m3b.py')
    artifact = {'format_version': 'm3b-human-commands.1', 'executable': False,
                'preflight': check, 'campaign_commands': [],
                'validation_commands': [
                    [sys.executable, script, 'validate', '--protocol', str(protocol_path)],
                    [sys.executable, script, 'preflight', '--protocol', str(protocol_path),
                     '--gates', str(gates_path), '--qualification', str(qualification_path)]],
                'offline_probe_command': [sys.executable, script, 'probe-offline', '--output', '<fresh-local-probe-directory>'],
                'remaining_work': check['limits']}
    artifact['commands_sha256'] = digest(artifact)
    from .review_runner import _write
    _write(output, artifact)
    return artifact


def prepare_reviewer_command(protocol, gates, qualification, invocation, request, *, evidence_root=ROOT):
    check = preflight(protocol, gates, qualification, evidence_root=evidence_root)
    if not check['ready']: raise ValueError('Reviewer command blocked: ' + ', '.join(check['blockers']))
    _check_invocation(invocation, request)
    if request['model'] != protocol['reviewer']['model'] or request['settings'] != protocol['reviewer']['settings']:
        raise ValueError('Reviewer request differs from the frozen protocol')
    return prepare_provider_command(invocation, request)


def execute_campaign(*args, **kwargs):
    raise PreparationOnly('Preparation coding does not authorize or provide real campaign execution')


def execution_preflight(protocol,gates,qualification,*,evidence_root=ROOT):
    """Real-path gates are based on concrete decisions and bound actual evidence."""
    if type(protocol) is dict and protocol.get('format_version')=='m3b-chatgpt-scheduled-protocol.1':
        from .experiment_scheduled import validate_execution_contract as scheduled
        try:
            check=scheduled(protocol,gates,qualification,evidence_root=evidence_root)
            return {'ready':True,'execution_available':True,'blockers':[],'execution_mode':'m3-scheduled-readiness.1','runtime_ready':False,'protocol_sha256':check['protocol_sha256']}
        except (ValueError,OSError,KeyError,TypeError) as error:
            return {'ready':False,'execution_available':False,'blockers':['scheduled_admission'],'diagnostics':[str(error)]}
    from .experiment_protocol import validate_execution_protocol,draft_protocol
    from .experiment_execution import validate_execution_decision,controller_source_digest
    from copy import deepcopy
    blockers=[];diagnostics=[]
    try:
        validation=validate_execution_protocol(protocol)
        if not validation['ready']:blockers.append('protocol_unresolved')
    except (ValueError,TypeError,KeyError) as error:
        validation={'valid':False,'ready':False,'unresolved':[]};blockers.append('protocol_invalid');diagnostics.append(str(error))
    gates=gates if type(gates) is dict else {}
    deps=protocol.get('dependencies',{}) if type(protocol) is dict else {}
    for key,status,commit in [('m1_acceptance','accepted',deps.get('m1')),('m2_acceptance','accepted',deps.get('m2')),
                            ('corrected_m3a_review','reviewed',deps.get('m3a')),
                            ('integrated_preparation_review','reviewed',deps.get('preparation'))]:
        if not _authority(gates.get(key),gate=key,status=status,commit=commit,evidence_root=Path(evidence_root).resolve()):
            blockers.append(key)
    # Concrete actual-provider qualification validation is shared with intake.
    try:
        from .experiment_qualification import validate_provider_qualification
        validate_provider_qualification(qualification,protocol=protocol,evidence_root=evidence_root)
    except (ImportError,ValueError,KeyError,TypeError,OSError) as error:
        blockers.append('real_provider_isolation');diagnostics.append(str(error))
    for gate in ['real_path_review','protocol_review','experiment_authorization']:
        if not validate_execution_decision(gates.get(gate),gate,protocol,qualification,evidence_root=evidence_root):blockers.append(gate)
    if type(protocol) is dict and protocol.get('bindings',{}).get('controller_source_sha256') not in {None,controller_source_digest()}:
        blockers.append('controller_source_changed')
    ready=not blockers
    return {'format_version':'m3b-execution-preflight.1','ready':ready,'execution_available':ready,
            'blockers':blockers,'diagnostics':diagnostics,'protocol':validation,
            'coding_authorization_satisfies_experiment_gates':False,'hosted_launch_actor':'experiment_developer_or_human'}
