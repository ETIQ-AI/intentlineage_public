"""Source-bound historical structural checks; never corrected-current replay.

Adapted from the reviewed 1f1c7c1 structural replay_session. Archived Python is
read as provenance data only, never imported/executed. No controller/assessor here.
"""
import ast
import json
from pathlib import Path
from .native_capture import ROOT,digest,file_hash
from .review_batches import validate_plan,validate_evidence
from .review_contract import validate_reply


def validate_historical_binding(root,protocol):
    known=[ROOT/'resources/evidence/archive/m3a-4d80a29/resources/evidence/m3a-m2-interface.json',
           ROOT/'resources/evidence/archive/m3a-6edec09/resources/evidence/m3a-m2-interface.json']
    interface=protocol.get('m2_interface',{})
    trusted=next((json.loads(p.read_bytes()) for p in known if json.loads(p.read_bytes())['commit']==interface.get('commit')),None)
    if trusted is None or interface.get('files')!=trusted['files']:
        raise ValueError('Unregistered historical M2 source binding')
    sources=protocol['controller_sources']
    for relative,expected in trusted['files'].items():
        if relative.startswith('src/'):
            path=root/'controller-source'/relative
            if sources.get(relative)!=expected or file_hash(path)!=expected:
                raise ValueError('Historical producer source mismatch')
    # Reply/plan schemas are compatible; source policies/statistics are not rerun.
    for name in ('review_contract','review_batches'):
        relative='src/intentlineage/'+name+'.py'
        old=ast.dump(ast.parse((root/'controller-source'/relative).read_text(encoding='utf-8')))
        if old!=ast.dump(ast.parse((ROOT/relative).read_text(encoding='utf-8'))):
            raise ValueError('Historical structural schema requires separate reviewed adaptation')


def replay_historical_session(directory):
    """Adapt prior request/reply/receipt validation, without deriving summaries."""
    root=Path(directory).resolve();result=json.loads((root/'session.json').read_bytes())
    if result.get('format_version') not in {'m2-session.4.0','m2-session.4.1'}:
        raise ValueError('Historical checks cannot accept current session versions')
    if result.get('session_sha256')!=digest({k:v for k,v in result.items() if k!='session_sha256'}):
        raise ValueError('Historical session integrity mismatch')
    for relative,expected in result['files'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or path.is_symlink() or not path.is_file() or file_hash(path)!=expected:
            raise ValueError('Historical transcript hash mismatch')
    validate_plan(json.loads((root/'plan.json').read_bytes()))
    logical=0;transport=0
    for call in result['calls']:
        folder=root/'calls'/f"{call['attempt']:04d}"
        request=json.loads((folder/'request.json').read_bytes());validate_evidence(request['evidence'])
        if digest(request)!=call['request_sha256'] or request['evidence']['evidence_sha256']!=call['evidence_sha256']:
            raise ValueError('Historical request replay mismatch')
        raw=(folder/'raw-reply.txt').read_text(encoding='utf-8')
        if call['failure_kind'] is None:
            parsed=validate_reply(raw,request['evidence'],allow_opening=call['approved_openings'])
            if parsed!=json.loads((folder/'parsed-reply.json').read_bytes()):raise ValueError('Historical parsed reply mismatch')
        elif call['failure_kind']=='invalid_reply':
            try:validate_reply(raw,request['evidence'],allow_opening=call['approved_openings'])
            except ValueError:pass
            else:raise ValueError('Historical invalid reply now validates')
        logical+=call['charged_reasoning'];transport+=call['failure_kind']=='transport_failure'
    if logical!=result['logical_calls'] or transport!=result['transport_failures']:
        raise ValueError('Historical call accounting mismatch')
    for receipt in result['reconsiderations']:
        if receipt['before_sha256']!=receipt['after_sha256'] or receipt['evidence_bytes_added']:
            raise ValueError('Historical control evidence mismatch')
    receipts=[]
    for path in sorted((root/'disclosures').glob('*.json')):
        event=json.loads(path.read_bytes());validate_evidence(event['before_evidence']);validate_evidence(event['evidence'])
        receipts.extend(event['receipts'])
    if receipts!=result['operation_receipts'] or len(receipts)!=result['controller_operations']:
        raise ValueError('Historical controller receipts mismatch')
    if sum(r['evidence_bytes_added'] for r in receipts)!=result['evidence_bytes_added']:
        raise ValueError('Historical disclosure bytes mismatch')
    return result
