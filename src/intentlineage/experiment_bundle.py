"""Private export/replay preserving historical, recorded and actual provenance."""
import json
from pathlib import Path
import shutil

from .native_capture import digest,file_hash
from .experiment_faults import write
from .experiment_isolation import _check_tree
from .experiment_campaign import replay_campaign,inspect_incomplete_campaign


def export_bundle(campaign_dir,output_dir):
    source=Path(campaign_dir).resolve();output=Path(output_dir).resolve()
    if output.exists() or output.is_relative_to(source):
        raise ValueError('Bundle export needs a fresh directory outside campaign')
    _check_tree(source)
    complete=(source/'campaign.json').is_file()
    campaign=replay_campaign(source) if complete else inspect_incomplete_campaign(source)
    extended=campaign.get('data_class') in {'recorded_contract','empirical'}
    data_class=campaign.get('data_class') if extended else None
    if extended:
        if campaign.get('synthetic') is not (data_class!='empirical'):raise ValueError('Execution bundle provenance mismatch')
    elif campaign.get('synthetic') is not True:raise ValueError('M3A bundles require synthetic campaign labels')
    forbidden={'auth.json','credentials.json','.env','api-key.txt'}
    if any(p.is_file() and p.name.lower() in forbidden for p in source.rglob('*')):
        raise ValueError('Credentials/private environment files are excluded from bundles')
    output.mkdir(parents=True)
    shutil.copytree(source,output/'campaign')
    manifest={'format_version':'m3b-bundle.1' if extended else 'm3a-bundle.1','synthetic':data_class!='empirical','audience':'controller_private',
        'campaign_sha256':campaign.get('campaign_sha256'),
        'protocol_sha256':campaign['protocol_sha256'],
        'incomplete':not complete,'state':None if complete else campaign,
        'files':{p.relative_to(output).as_posix():file_hash(p) for p in output.rglob('*') if p.is_file()},
        'limits':['Contains private fault truth, catalogues and source snapshots; never mount as reviewer evidence.',
                  'Replay verifies software/integrity/accounting, not semantic model accuracy or empirical findings.',
                  'No hosted experiment was executed.']}
    if extended:
        manifest.update(data_class=data_class,empirical_admissible=data_class=='empirical' and complete)
        manifest['limits'][-1]='Actual-review costs and qualification costs are retained separately.' if data_class=='empirical' else 'Recorded contract fixtures are not empirical results.'
    manifest['bundle_sha256']=digest(manifest);write(output/'bundle.json',manifest)
    return manifest


def replay_bundle(directory):
    root=Path(directory).resolve();_check_tree(root)
    manifest=json.loads((root/'bundle.json').read_bytes())
    if manifest.get('bundle_sha256')!=digest({k:v for k,v in manifest.items() if k!='bundle_sha256'}):
        raise ValueError('Bundle manifest integrity mismatch')
    extended=manifest.get('format_version')=='m3b-bundle.1'
    data_class=manifest.get('data_class') if extended else None
    if extended:
        if data_class not in {'recorded_contract','empirical'} or manifest.get('synthetic') is not (data_class!='empirical') or manifest.get('empirical_admissible') is not (data_class=='empirical' and not manifest['incomplete']):
            raise ValueError('Bundle review provenance labels changed')
    elif manifest.get('synthetic') is not True:
        raise ValueError('Bundle must preserve private synthetic scope')
    if manifest.get('audience')!='controller_private':
        raise ValueError('Bundle must preserve private synthetic scope')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-{'bundle.json'}
    if actual!=set(manifest['files']):raise ValueError('Bundle exact file set mismatch')
    for relative,expected in manifest['files'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or file_hash(path)!=expected:
            raise ValueError('Bundle file hash/integrity mismatch: '+relative)
    if manifest['incomplete']:
        state=inspect_incomplete_campaign(root/'campaign')
        if state!=manifest['state']:raise ValueError('Incomplete bundle state mismatch')
        result={'synthetic':data_class!='empirical','incomplete':True,'bundle_sha256':manifest['bundle_sha256'],
                'files_verified':len(manifest['files']),'unknown_attempts':state['unknown_attempts']}
        if extended:
            if state.get('data_class')!=data_class:raise ValueError('Incomplete bundle/campaign provenance mixed')
            result.update(data_class=data_class,empirical_admissible=False)
        return result
    campaign=replay_campaign(root/'campaign')
    if campaign['campaign_sha256']!=manifest['campaign_sha256']:raise ValueError('Bundle campaign integrity mismatch')
    if extended and campaign.get('data_class')!=data_class:raise ValueError('Bundle/campaign review provenance mixed')
    result={'synthetic':data_class!='empirical','campaign_sha256':campaign['campaign_sha256'],
        'bundle_sha256':manifest['bundle_sha256'],'files_verified':len(manifest['files']),
        'units_replayed':len(campaign['units']),'score_sha256':campaign['score']['score_sha256'],
        'historical':campaign.get('historical',False),'current_42_qualified':not campaign.get('historical',False)}
    if extended:result.update(data_class=data_class,empirical_admissible=data_class=='empirical')
    return result
