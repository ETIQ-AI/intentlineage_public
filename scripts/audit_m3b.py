"""Combined code/decision/source audit; delegates reviewed infrastructure checks."""
import argparse
import importlib.util
import json
from pathlib import Path

from intentlineage.native_capture import ROOT,file_hash,digest
from intentlineage.experiment_protocol import M3A_COMMIT,M2_COMMIT,M1_COMMIT
from intentlineage.experiment_preflight import decision_records,preflight,_authority
from intentlineage.experiment_bundle import replay_bundle
from intentlineage.experiment_campaign import replay_campaign,environment


def read(path):return json.loads(Path(path).read_bytes())


def audit_sources(root=ROOT):
    root=Path(root);metadata=read(root/'resources/evidence/m3b-preparation-dependencies.json')
    if metadata['provisional'] is not False or (metadata['m1'],metadata['m2'],metadata['m3a'])!=(M1_COMMIT,M2_COMMIT,M3A_COMMIT):
        raise ValueError('Not the reviewed integrated dependency pins')
    interface=read(root/'resources/evidence/m3a-m2-interface.json')
    if interface['commit']!=M2_COMMIT or interface['status']!='accepted_within_tested_local_scope':raise ValueError('Accepted M2 binding missing')
    extension=None
    if 'function_review_extension' in interface:
        from intentlineage.experiment_function import verify_m2_extension
        extension=verify_m2_extension(root)
    for name,expected in interface['files'].items():
        path=root/extension['archive'] if extension and name==extension['path'] else root/name
        if file_hash(path)!=expected:raise ValueError('Exact accepted M2 file changed: '+name)
    for name,item in metadata['reviewed_m3a_files'].items():
        if file_hash(root/name)!=item['current_sha256']:raise ValueError('Integrated source binding changed: '+name)
        archive=root/'resources/evidence/archive/m3b-reviewed-fbedf3e'/name
        if file_hash(archive)!=item['reviewed_sha256']:raise ValueError('Reviewed predecessor changed')
        if not item['adapted'] and item['current_sha256']!=item['reviewed_sha256']:raise ValueError('Unregistered source adaptation')
    for name,expected in metadata['preparation_sources'].items():
        if file_hash(root/name)!=expected:raise ValueError('Preparation source hash mismatch: '+name)
    original=read(root/'resources/evidence/m3b-integration-baseline.json')
    for name,expected in original['archive'].items():
        if file_hash(root/'resources/evidence/archive/m3b-330fd4e'/name)!=expected:raise ValueError('Preparation predecessor changed')
    gates=read(root/'resources/protocol/m3b-preparation-gates.json')
    check=preflight(read(root/'resources/protocol/m3b-preparation-draft.json'),gates,None,evidence_root=root)
    for key,record in decision_records().items():
        if key in check['blockers'] or record!=metadata['overseer_decisions'][key]:raise ValueError('Actual dependency authority not bound')
        if not _authority(record,gate=key,status=record['status'],commit=record['commit'],evidence_root=root):
            raise ValueError('Observed Overseer Markdown bytes changed: '+key)
    return {'m1_commit':M1_COMMIT,'m2_commit':M2_COMMIT,'m3a_commit':M3A_COMMIT,
            'm2_interfaces_verified':len(interface['files']),'preparation_preserved':True,
            'm2_current_files_byte_exact':len(interface['files'])-(1 if extension else 0),
            'function_review_extension':extension,
            'reviewed_m3a_mechanisms_verified':len(metadata['reviewed_m3a_files']),
            'real_execution_available':False,'preflight':check,'environment':environment()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--campaign',type=Path);parser.add_argument('--bundle',type=Path)
    parser.add_argument('--infrastructure',action='store_true');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=audit_sources()
    if args.infrastructure:
        spec=importlib.util.spec_from_file_location('reviewed_m3a_audit',ROOT/'scripts/audit_m3a.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);report['reviewed_infrastructure_audit']=m.audit()
    if args.campaign:report['campaign_sha256']=replay_campaign(args.campaign)['campaign_sha256']
    if args.bundle:report['bundle']=replay_bundle(args.bundle)
    report['report_sha256']=digest(report)
    if args.output.exists():
        if read(args.output)!=report:raise ValueError('Saved audit differs; choose a fresh path')
    else:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({'passed':True,'report_sha256':report['report_sha256']}))


if __name__=='__main__':main()
