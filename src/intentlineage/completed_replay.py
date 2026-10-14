"""Read-only replay of the exact completed campaign; no launch authority.

Archived Python is verified as provenance data, never imported or executed.
Current compatible historical validators/controller paths recompute observations.
"""
from pathlib import Path
from .native_capture import ROOT,digest,file_hash
from .review_contract import _strict_load

ARCHIVE='resources/evidence/archive/m3-completed-005383b'
SOURCE='8c3369b80d6c36f5757dcb7cafe0447480270a76df194f9db22137b7d1b9e5a9'
CAMPAIGN='5988fca873f1d1af1fe1bbbfba51fee58155ae4f9ee0b52779d2d987709cc924'
PROTOCOL='b50ba93045dfdab4740aa5e3f4e728c585ca731c8250636e451336c812e88e3b'
QUALIFICATION='3f1ef1311d3ce01021de7b1650f8ad3d4f155522af6120f7ba3544234573fc02'


def verify_archive(root):
    from .experiment_isolation import _check_tree
    archive=Path(root)/ARCHIVE;_check_tree(archive)
    manifest=_strict_load((archive/'source-manifest.json').read_bytes())
    if digest(manifest)!=SOURCE or len(manifest)!=58:raise ValueError('Completed source archive seal differs')
    actual={p.relative_to(archive/'source').as_posix() for p in (archive/'source').rglob('*') if p.is_file()}
    if actual!=set(manifest):raise ValueError('Completed source archive membership differs')
    for name,sha in manifest.items():
        path=(archive/'source'/name).resolve()
        if not path.is_relative_to((archive/'source').resolve()) or file_hash(path)!=sha:raise ValueError('Completed source archive bytes differ: '+name)
    return SOURCE


def check_campaign(root):
    result=_strict_load((Path(root)/'campaign.json').read_bytes())
    if result.get('campaign_sha256')!=CAMPAIGN or digest({k:v for k,v in result.items() if k!='campaign_sha256'})!=CAMPAIGN:
        raise ValueError('Only the exact registered completed campaign can use historical replay')
    return result


def assert_unit_bound(unit,root,source):
    if source!=verify_archive(ROOT) or unit not in check_campaign(root)['units']:
        raise ValueError('Historical unit is outside the pinned completed campaign')


def replay(root):
    from .experiment_isolation import _check_tree
    from .experiment_chatgpt import validate_chatgpt_call_files
    from .experiment_qualification import REQUIRED_PROBES,assert_runtime_matches
    from .experiment_resume import (validate_retained_manifest,replay_composite_unit,admit_calls)
    from .experiment_scoring import rows_from_units,score_rows
    root=Path(root).resolve();_check_tree(root);verify_archive(ROOT);result=check_campaign(root)
    files={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-{'campaign.json'}
    if files!=set(result['files']):raise ValueError('Completed campaign membership differs')
    for name,sha in result['files'].items():
        if file_hash(root/name)!=sha:raise ValueError('Completed evidence bytes differ: '+name)
    p=_strict_load((root/'protocol.json').read_bytes());execution=p['execution_contract'];q=execution['qualification']
    if p['protocol_sha256']!=PROTOCOL or digest({k:v for k,v in p.items() if k!='protocol_sha256'})!=PROTOCOL:
        raise ValueError('Completed protocol binding differs')
    if q['qualification_sha256']!=QUALIFICATION or digest({k:v for k,v in q.items() if k!='qualification_sha256'})!=QUALIFICATION or q['controller_source_sha256']!=SOURCE:
        raise ValueError('Completed qualification/source differs')
    if q['qualified'] is not True or q['synthetic'] is not False or len(q['calls'])!=2 or len({c['thread_id'] for c in q['calls']})!=2:
        raise ValueError('Completed genuine fresh qualification missing')
    if set(q['probes'])!=REQUIRED_PROBES or any(v is not True for v in q['probes'].values()):raise ValueError('Completed native controls differ')
    for call in q['calls']:
        folder=root/q['artifact_directory']/call['directory']
        request=_strict_load((folder/'evidence/request.json').read_bytes());launch=_strict_load((folder/'launch-receipt.json').read_bytes())
        response=_strict_load((folder/'output/real-transport-response.json').read_bytes())
        facts=validate_chatgpt_call_files(folder,request,launch,limits=execution['protocol']['limits'],historical_source=SOURCE)
        if not facts['complete'] or facts['facts']!=response['native_client_facts'] or digest(launch)!=call['launch_sha256'] or digest(response)!=call['response_sha256']:
            raise ValueError('Completed qualification raw replay differs')
        assert_runtime_matches(q['runtime'],launch['runtime'])
    manifest=_strict_load((root/'continuation-manifest.json').read_bytes())
    validate_retained_manifest(ROOT,manifest,evidence_root=root/'retained/campaign')
    calls=[]
    for unit in result['units']:
        replay_composite_unit(root,unit,historical_source=SOURCE)
        for arm,session in unit['matrix']['sessions'].items():
            calls.extend({**c,'case_id':unit['case_id'],'arm':arm} for c in session['calls'])
    accounting=admit_calls(calls,ceiling=198)
    if accounting['charged_calls']!=178 or result['hosted_calls']!=178 or result['retained_charged_calls']!=79 or result['new_charged_calls']!=99:
        raise ValueError('Completed accounting differs')
    truth=_strict_load((root/'truth.json').read_bytes())
    if truth!=result['truth'] or digest(truth)!=p['truth_sha256']:raise ValueError('Completed hidden truth differs')
    rows=rows_from_units(result['units'],data_class='empirical',evidence_root=root,historical_source=SOURCE)
    score=score_rows(truth,rows,format_version='m3b-score.1',data_class='empirical')
    if score!=result['score']:raise ValueError('Completed actual score does not recompute')
    return {'historical':True,'read_only':True,'new_campaign_authority':False,'source_sha256':SOURCE,
        'campaign_sha256':CAMPAIGN,'calls':178,'retained_calls':79,'new_calls':99,
        'units':len(result['units']),'score_sha256':digest(score),'files_verified':len(files),
        'scope':'Exact completed source-bound evidence and policy/accounting replay; no new inputs or semantic acceptance.'}
