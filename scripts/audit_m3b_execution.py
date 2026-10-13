"""Local source, reuse and preservation audit; never runs qualification/inference."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

from intentlineage.native_capture import ROOT,digest,file_hash
from intentlineage.experiment_execution import controller_sources,controller_source_digest
from intentlineage.review_runner import _write


def correction_reconciliations(root,baseline):
    root=Path(root).resolve();path=root/'resources/evidence/m3b-chatgpt-integration.json'
    if not path.exists():return {}
    record=json.loads(path.read_bytes())
    if record['reviewed_base']!='4896fce39e6beb0666b268dd68859cb0d2c9e94e':
        raise ValueError('Correction predecessor commit changed')
    rows=record['baseline_reconciliations']
    for name,row in rows.items():
        current=(root/name).resolve();archive=(root/row['archive']).resolve()
        if not current.is_relative_to(root) or not archive.is_relative_to(root):
            raise ValueError('Correction reconciliation path escapes checkout')
        if row['baseline_sha256']!=baseline['own_files'][name] or file_hash(archive)!=row['baseline_sha256']:
            raise ValueError('Correction exact predecessor bytes differ: '+name)
        if file_hash(current)!=row['current_sha256']:
            raise ValueError('Correction current bytes differ: '+name)
    return rows


def audit():
    spec=importlib.util.spec_from_file_location('m3b_integrated_audit',ROOT/'scripts/audit_m3b.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);combined=m.audit_sources()
    spec=importlib.util.spec_from_file_location('m3a_reviewed_audit',ROOT/'scripts/audit_m3a.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);infrastructure=m.audit()
    baseline=json.loads((ROOT/'resources/evidence/m3b-execution-baseline.json').read_bytes())
    reconciled=correction_reconciliations(ROOT,baseline)
    changed=[];preserved=0
    allowed=set(baseline['archive'])|{'.gitattributes','resources/reference-use-case-icp/reuse-m3a.json'}
    for name,expected in baseline['own_files'].items():
        if file_hash(ROOT/name)==expected:preserved+=1;continue
        if name in reconciled:
            changed.append(name);continue
        if name not in allowed:raise ValueError('Undeclared historical change: '+name)
        if name in baseline['archive']:
            archived=ROOT/'resources/evidence/archive/m3b-execution-37a3bca'/name
        elif name=='resources/reference-use-case-icp/reuse-m3a.json':
            archived=ROOT/'resources/evidence/archive/m3b-execution-37a3bca-extra/reuse-m3a.json'
        else:archived=None
        if archived and file_hash(archived)!=expected:raise ValueError('Predecessor archive differs: '+name)
        changed.append(name)
    others={}
    for name,original in baseline['other_worktrees'].items():
        root=Path(name);changes=[]
        for relative,expected in original['files'].items():
            if file_hash(root/relative)!=expected:changes.append(relative)
        # Shared workspace may receive later Overseer documentation. Report it,
        # never revert it or claim those observed external edits were preserved.
        if any(p.startswith('src/') for p in changes):raise ValueError('Accepted external source changed: '+name)
        others[name]={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'observed_changes_since_baseline':changes,'written_by_this_session':False}
    reuse=json.loads((ROOT/'resources/reference-use-case-icp/reuse-m3b-execution.json').read_bytes())
    if reuse['upstream_commit']!='5bd37b1ca3e49e940fc885839fa56411203afee0':raise ValueError('Upstream pin changed')
    return {'scope':'local implementation; no actual-provider qualification','source_manifest':controller_sources(),
        'controller_source_sha256':controller_source_digest(),'pins':baseline['commits'],
        'unchanged_predecessor_files':preserved,'explicit_current_adaptations':changed,
        'correction_reconciliations':reconciled,
        'other_worktree_observations':others,'combined_source_audit':combined,'reviewed_infrastructure_audit':infrastructure,
        'hosted_calls':0,'provider_qualified':False,'current_code_reviewed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise ValueError('Use a globally unique audit output')
    result=audit();result['report_sha256']=digest(result);_write(args.output,result)
    print(json.dumps({'passed':True,'report_sha256':result['report_sha256'],'unchanged_predecessor_files':result['unchanged_predecessor_files']}))
