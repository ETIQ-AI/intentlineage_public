"""Read-only M3A dependency/provenance and optional complete delivery audit."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

from intentlineage.native_capture import ROOT,file_hash,digest,load_native
from intentlineage.experiment_campaign import environment,validate_bank_selection,replay_campaign
from intentlineage.experiment_bundle import replay_bundle
from intentlineage.experiment_faults import write


def read(path):return json.loads(Path(path).read_bytes())


def definition(path,name,*,line_style=False):
    text=Path(path).read_bytes().decode('utf-8')
    if line_style != 'raw':text=text.replace('\r\n','\n')
    nodes=ast.parse(text).body
    if '.' in name:
        cls,name=name.split('.')
        nodes=next(n for n in nodes if isinstance(n,ast.ClassDef) and n.name==cls).body
    node=next(n for n in nodes if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
    if line_style=='raw':segment=''.join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
    else:segment='\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])+'\n' if line_style else ast.get_source_segment(text,node)
    return hashlib.sha256(segment.encode()).hexdigest()


def audit():
    # Reuse M2's corrected source/dependency audit, including archived M1
    # interfaces, current 7178692 sources, installed pins and historical data.
    spec=importlib.util.spec_from_file_location('m3a_corrected_m2_audit',ROOT/'scripts/audit_m2_v4.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    extension=None
    interface=read(ROOT/'resources/evidence/m3a-m2-interface.json')
    if 'function_review_extension' in interface:
        from intentlineage.experiment_function import verify_m2_extension
        extension=verify_m2_extension(ROOT)
        # Run the unchanged historical M2 auditor against its exact accepted
        # runner bytes. Current extension identity was checked separately above.
        original_file_hash=module.file_hash
        module.file_hash=lambda path: original_file_hash(ROOT/extension['archive'] if Path(path)==ROOT/extension['path'] else path)
        original_definition=module._definition
        module._definition=lambda path,name,**kwargs: original_definition(ROOT/extension['archive'] if Path(path)==ROOT/extension['path'] else path,name,**kwargs)
    dependencies=module.audit_sources(ROOT)
    m1=read(ROOT/'resources/reference-use-case-icp/reuse-v4.json')
    for item in m1['functions']:
        source=ROOT/'resources/reference-use-case-icp/upstream'/Path(item['upstream_path']).name
        assert file_hash(source)==item['upstream_file_sha256']
        assert definition(source,item['upstream_function'])==item['upstream_function_sha256']
        assert definition(ROOT/item['local_file'],item['local_function'])==item['local_function_sha256']
    counts={}
    for name,line_style in [('reuse-m2-v4.json','raw'),('reuse-m3a.json',True)]:
        manifest=read(ROOT/'resources/reference-use-case-icp'/name)
        for item in manifest['adaptations']:
            source=ROOT/item['snapshot'];local=ROOT/item['local_path']
            if extension and item['local_path']==extension['path']:local=ROOT/extension['archive']
            assert file_hash(source)==item['upstream']['file_sha256']
            assert definition(source,item['upstream_definition'],line_style=line_style)==item['upstream']['definition_sha256']
            assert file_hash(local)==item['local']['file_sha256']
            assert definition(local,item['local_definition'],line_style=line_style)==item['local']['definition_sha256']
        counts[name]=len(manifest['adaptations'])
    m2=read(ROOT/'resources/evidence/m3a-m2-interface.json')
    for name,expected in m2['files'].items():
        path=ROOT/extension['archive'] if extension and name==extension['path'] else ROOT/name
        assert file_hash(path)==expected
    # Preserved historical evidence is checked against its own frozen sources.
    historical=0
    index=read(ROOT/'.etiq/artifacts/m1-v4-delivery/index.json')
    for case in index['results']:
        folder=ROOT/case['output']
        sources=read(folder/'controller/source-manifest.json')
        for name,expected in sources.items():assert file_hash(folder/'controller/source-snapshot'/name)==expected
        if case['wrapper_scans']:
            load_native(folder/'capture/scan-result.json')
            assert file_hash(ROOT/case['native_capture'])==case['native_capture_sha256']
            for name,expected in case['public_files'].items():assert file_hash(folder/'public'/name)==expected
            historical+=1
    protected=0
    predecessors=read(ROOT/'resources/evidence/m1-v4-fixes-preservation.json')['archives']
    for filename in ['m1-v4-preservation.json','m1-v4-persistence-preservation.json',
                     'm1-v4-disclosure-order-preservation.json','m1-v4-o01-preservation.json']:
        for relative,expected in read(ROOT/'resources/evidence'/filename)['protected_files'].items():
            archived=predecessors.get(relative)
            path=ROOT/archived['archive'] if archived and archived['sha256']==expected else ROOT/relative
            assert file_hash(path)==expected, relative
            protected+=1
    preservation=read(ROOT/'resources/evidence/m3a-o01-preservation.json')
    for relative,expected in preservation['protected_files'].items():
        assert file_hash(ROOT/relative)==expected, relative
    for relative,expected in preservation['archived_sources'].items():
        assert file_hash(ROOT/'resources/evidence/archive/m3a-4d80a29'/relative)==expected, relative
    integration=read(ROOT/'resources/evidence/m3a-42-preservation.json')
    for relative,row in integration['protected_files'].items():
        assert file_hash(ROOT/relative)==row['sha256'] and (ROOT/relative).stat().st_size==row['bytes'], relative
    for relative,expected in integration['archived_sources'].items():
        assert file_hash(ROOT/integration['archive']/relative)==expected, relative
    return {'synthetic':True,'environment':environment(),'m1_commit':dependencies['current']['dependency_commit'],
        'm1_status':'accepted within tested scope','m1_pending':[],
        'm1_versions':read(ROOT/'resources/evidence/m3a-dependency-reconciliation.json')['m1_delivery_versions'],
        'm2_commit':m2['commit'],'m2_contract':m2['contract_version'],'m2_session_version':m2['session_version'],
        'm2_status':m2['status'],'m1_reused_definitions':len(m1['functions']),
        'function_review_extension':extension,'m2_source_audit_scope':'accepted original bytes; current runner separately verified' if extension else 'current accepted sources',
        'additional_reuse':counts,'historical_native_captures':historical,
        'protected_checks_including_overlap':protected,'corrected_dependency_audit':dependencies,
        'historical_m3a_files_preserved':len(preservation['protected_files']),
        'historical_m3a_sources_archived':len(preservation['archived_sources']),
        'integration_history_preserved':len(integration['protected_files']),
        'integration_source_archives':len(integration['archived_sources']),
        'acceptance':'M3A correction resubmission; M3B not qualified',
        'source_versions':{name:file_hash(ROOT/name) for name in
            ['src/intentlineage/experiment_faults.py','src/intentlineage/experiment_isolation.py',
             'src/intentlineage/experiment_campaign.py','src/intentlineage/experiment_scoring.py',
             'src/intentlineage/experiment_bundle.py','src/intentlineage/experiment_history.py','src/intentlineage/review_runner.py',
             'src/intentlineage/review_usage.py','scripts/capture_m1_v4.py','scripts/audit_m3a.py']}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank',type=Path);parser.add_argument('--campaign',type=Path)
    parser.add_argument('--bundle',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=audit()
    if args.bank:
        bank=read(args.bank);validate_bank_selection(bank)
        report['bank']={'bank_sha256':bank['bank_sha256'],'scans':bank['wrapper_scans'],
                        'qualified':sum(c['qualified'] for c in bank['cases'])}
    if args.campaign:
        campaign=replay_campaign(args.campaign)
        report['campaign']={'campaign_sha256':campaign['campaign_sha256'],'units':campaign['completed_units'],
                            'score_sha256':campaign['score']['score_sha256'],'usage':campaign['score']['usage']}
    if args.bundle:report['bundle']=replay_bundle(args.bundle)
    report['report_sha256']=digest(report)
    if args.output.exists():
        if read(args.output)!=report:raise ValueError('Existing audit differs; select a fresh output')
    else:write(args.output,report)
    print(json.dumps({'passed':True,'report_sha256':report['report_sha256']}))
    return 0


if __name__=='__main__':raise SystemExit(main())
