"""Versioned single-review candidate over the existing capture/execution harness.

Preparation is offline. New hosted qualification and release require their own
exact Overseer decisions; completed continuation authority is never inherited.
"""
from copy import deepcopy
from pathlib import Path
from .native_capture import ROOT,digest,file_hash
from .review_contract import _strict_load,canonical_bytes
from . import review_single

FORMAT='m3b-chatgpt-single-protocol.1'
PROFILE='resources/protocol/m3-single-profile.json'
BRIEF='developer_m3-single-review-correction-20261013.md'
BRIEF_SHA='09508f5e053cb6c66e49d41cd21dbbb9fd4090f084c94f3753bf408f4db6e118'
QUALIFICATION_REVIEW='m3-single-qualification-code-overseer-review.md'


def fixed_policy():
    return {'A':{'max_calls':9,'max_operations':2,'max_disclosure_bytes':100000},
        'limits':{'max_input_bytes':300000,'max_input_tokens':196608,'max_output_tokens':8192,
            'max_output_bytes':33554432,'max_seconds_per_invocation':300,'qualification_max_calls':2},
        'repeats':1,'scheduling':{'unit_order':'seeded','seed':20261012,'parallelism':1},
        'reviewer_model':'gpt-5.5','settings':{'reasoning_effort':'low'},
        'inference_authorized':False,'historical_calls_reusable':False}


def profile():
    try:
        value=_strict_load((ROOT/PROFILE).read_bytes())
        if value['format_version']!='m3-single-profile.1' or value['brief_sha256']!=BRIEF_SHA:
            raise ValueError('Single-review candidate identity differs')
        return value
    except (OSError,KeyError,TypeError) as error:raise ValueError('Single-review candidate has not been prepared') from error


def verify_m2_extension(root):
    """Accepted original bytes and current optional extensions have separate seals."""
    root=Path(root);interface=_strict_load((root/'resources/evidence/m3a-m2-interface.json').read_bytes())
    archive=root/'resources/evidence/archive/m3-completed-005383b'
    records=interface.get('single_review_extension',{})
    changed=[]
    for name,sha in interface['files'].items():
        if file_hash(root/name)==sha:continue
        changed.append(name)
        record=records.get('files',{}).get(name)
        if not record or record['accepted_sha256']!=sha or file_hash(root/record['accepted_archive'])!=sha or record['current_sha256']!=file_hash(root/name):
            raise ValueError('Explicit accepted/current single-review source binding differs: '+name)
    if (set(changed)!=set(records.get('files',{})) or records.get('accepted') is not False
        or records.get('instruction_sha256')!=BRIEF_SHA or records.get('contract')!=review_single.contract()):
        raise ValueError('Single-review extension provenance is missing/inconsistent')
    return {'accepted_files':len(interface['files']),'current_files_byte_exact':len(interface['files'])-len(changed),
            'changed_files':changed,'new_extension_accepted':False,'response_contract':review_single.CONTRACT_VERSION}


def qualification_request(protocol,index):
    from .review_batches import validate_evidence
    value=profile();record=value['qualification_requests'][index]
    for key,sha in [('request_path','request_file_sha256'),('controller_evidence_path','controller_evidence_file_sha256')]:
        if file_hash(ROOT/record[key])!=record[sha]:raise ValueError('Single-review qualification input binding differs')
    evidence=_strict_load((ROOT/record['controller_evidence_path']).read_bytes());validate_evidence(evidence)
    request=review_single.build_request(evidence,model=protocol['reviewer']['model'],settings=protocol['reviewer']['settings'])
    if request!=_strict_load((ROOT/record['request_path']).read_bytes()) or digest(request)!=record['request_sha256']:
        raise ValueError('Single-review native request replay differs')
    return request


def validate_protocol(protocol,*,require_frozen=False):
    from .experiment_execution import controller_source_digest
    from .experiment_chatgpt import validate_chatgpt_protocol,CHATGPT_FORMAT,draft_chatgpt_protocol
    value=profile();expected=deepcopy(value['candidate'])
    try:
        fixed=fixed_policy()
        if (any(protocol[k]!=fixed[k] for k in ['A','limits','repeats','scheduling'])
            or protocol['reviewer']['model']!=fixed['reviewer_model'] or protocol['reviewer']['settings']!=fixed['settings']
            or protocol['single_review']['contract']!=review_single.contract()
            or protocol['selection_policy']!='review_driven' or protocol['H']['batch_size']!=1
            or protocol['H']['max_request_bytes']!=200000):raise ValueError('Single-review fixed scientific bounds changed')
        expected.update(status=protocol['status'],reviewer=deepcopy(protocol['reviewer']),bindings=deepcopy(protocol['bindings']))
        if protocol!=expected:raise ValueError('Single-review fixed protocol/input/budget changed')
        reviewer=deepcopy(protocol['reviewer']);reviewer['client_effective_model']=None;reviewer['model_metadata_sha256']=None
        if reviewer!=value['candidate']['reviewer'] or protocol['reviewer']['client_effective_model'] not in {None,'gpt-5.5'}:
            raise ValueError('Single-review model/CLI/auth/settings drift')
        if protocol['bindings']['controller_source_sha256']!=controller_source_digest():raise ValueError('Single-review source drift')
        for index in range(2):qualification_request(protocol,index)
        base=deepcopy(protocol);base.pop('single_review');base.pop('response_policy');base['format_version']=CHATGPT_FORMAT
        original=draft_chatgpt_protocol()
        for key in ['prompts','matrix','common_evidence']:base[key]=deepcopy(original[key])
        # The new policy is validated above; reuse historical infrastructure checks.
        base['selection_policy']='question_driven'
        result=validate_chatgpt_protocol(base,require_frozen=require_frozen)
        return {**result,'protocol_sha256':digest(protocol),'new_release_required':True}
    except (KeyError,TypeError) as error:raise ValueError('Single-review candidate contract is incomplete') from error


def qualification_contract(protocol):
    validate_protocol(protocol)
    value=profile()
    return {'scope':'chatgpt-single-provider-qualification','data_class':'empirical',
        'controller_source_sha256':protocol['bindings']['controller_source_sha256'],
        'user_brief_sha256':BRIEF_SHA,'reviewer':deepcopy(protocol['reviewer']),
        'limits':deepcopy(protocol['limits']),'observability':deepcopy(protocol['observability']),
        'single_review':deepcopy(protocol['single_review']),'response_policy':protocol['response_policy'],
        'qualification_inputs':deepcopy(value['qualification_requests']),
        'profile_sha256':file_hash(ROOT/PROFILE),
        'transport_framing':'one strict reply_json string; exactly one decode; declared single-review validation'}


def audit_candidate(protocol,bank):
    from .experiment_execution import controller_sources
    from .experiment_campaign import validate_bank_selection
    verified=validate_bank_selection(bank)
    if profile()['source_manifest']!=controller_sources():raise ValueError('Single-review launch/controller source drift')
    if protocol['population']['bank_sha256']!=verified['bank_sha256']:raise ValueError('Single-review candidate population differs')
    return {'source_provenance':verify_m2_extension(ROOT),'protocol':validate_protocol(protocol),
        'bank_sha256':verified['bank_sha256'],'mechanically_qualified_cases':sum(c['qualified'] for c in bank['cases']),
        'capture_source_manifest_sha256':verified['source_manifest_sha256'],
        'launch_source_sha256':digest(controller_sources()),
        'hosted_calls':0,'qualified_provider':False,'campaign_authorized':False}


def measure_nested_requests(plan,catalogue):
    """Enumerate eligible one/two-function paths; inspect maximal captured reads.

    No provider, selector, hidden truth or model history participates. Runtime
    request/byte checks still apply to every later reviewer-selected action.
    """
    from .review_disclosure import disclose_single
    from .review_batches import seal_evidence
    count=0;maximum=0;by_depth={1:0,2:0}
    for batch in plan['batches']:
        frontier=[(batch,0,0)]
        while frontier:
            current,depth,added=frontier.pop(0)
            if depth==2:continue
            view=review_single.project_evidence(current)
            actions=[{'kind':'function','target_id':g['group_id']} for g in view['graph']['eligible_groups']]
            actions.extend({'kind':'artifact','target_id':r,'inspection':'read','start':0,'count':1000,
                'columns':catalogue['artifacts'][r]['artifact_content'].get('columns',[])} for r in view['graph']['visible_artifacts']
                if catalogue['artifacts'][r]['artifact_kind']=='table')
            for action in actions:
                action.update(reason='Measure maximal permitted captured disclosure.',element_ids=[view['elements'][0]['element_id']])
                expanded,receipts=disclose_single(catalogue,current,[action])
                total=added+receipts[0]['evidence_bytes_added']
                if total>100000:continue
                group=next((g for g in current['graph']['eligible_groups'] if g['group_id']==action['target_id']),current['functions'][0])
                focused=review_single.followup_evidence(expanded,action,group,newly_disclosed_ids=receipts[0].get('nodes_added',[]))
                q=review_single.build_request(focused,model='gpt-5.5',settings={'reasoning_effort':'low'},allow_opening=True,max_request_bytes=200000)
                size=len(canonical_bytes(q));maximum=max(maximum,size);by_depth[depth+1]=max(by_depth[depth+1],size);count+=1
                if action['kind']=='function':frontier.append((focused,depth+1,total))
    return {'measured_disclosure_requests':count,'maximum_measured_bytes':maximum,'maximum_bytes_by_operation_depth':by_depth,
        'scope':'All eligible one/two-function paths and maximal full-column captured table reads at those scopes; later exact selected requests remain guarded.'}


def freeze_candidate(qualification):
    from .experiment_chatgpt import validate_chatgpt_qualification
    p=deepcopy(profile()['candidate']);p.update(status='frozen',reviewer=deepcopy(qualification['reviewer']))
    p['bindings'].update(model_metadata=deepcopy(qualification['model_metadata']),qualification_sha256=qualification['qualification_sha256'])
    validate_protocol(p,require_frozen=True);validate_chatgpt_qualification(qualification,protocol=p)
    return p


def prepare_candidate(extraction,output):
    """Six genuine native captures, zero reviewer calls, no release/decision files."""
    from .ordinary_review_inputs import PROFILE as inventory_profile
    from .experiment_faults import capture_bank
    from .experiment_campaign import validate_bank_selection,schedule
    from .experiment_execution import controller_sources,controller_source_digest
    from .review_runner import _write
    from .experiment_chatgpt import draft_chatgpt_protocol
    root=Path(output).resolve()
    if root.exists() or not root.is_relative_to(ROOT):raise ValueError('Single-review preparation needs a fresh own directory')
    if (ROOT/PROFILE).exists():raise ValueError('Preserve existing candidate; explicitly version a later correction')
    root.mkdir(parents=True)
    bank=capture_bank(root/'bank',seed=17,extraction_file=extraction,batch_size=1,profile=inventory_profile)
    validate_bank_selection(bank)
    if len(bank['cases'])!=6 or not all(c['qualified'] for c in bank['cases']):raise ValueError('Six mechanically qualified native cases required')
    policy=fixed_policy();old=_strict_load((ROOT/'resources/protocol/m3-function-profile.json').read_bytes())['candidate']
    p=draft_chatgpt_protocol();p.update(format_version=FORMAT,response_policy='m3-response-policy.1',
        selection_policy='review_driven',A=policy['A'],limits=policy['limits'],repeats=1,scheduling=policy['scheduling'])
    p['reviewer']=deepcopy(old['reviewer']);p['reviewer'].update(client_effective_model=None,model_metadata_sha256=None)
    p['bindings'].update(controller_source_sha256=controller_source_digest(),model_metadata=None,qualification_sha256=None)
    p['correction_brief_sha256']=BRIEF_SHA
    p['retry'].update(reasoning_retries=0,transport_retries=1)
    p['population']={'case_ids':[c['case_id'] for c in bank['cases']],'bank_sha256':bank['bank_sha256']}
    p['single_review']={'contract':review_single.contract(),'inventory_profile':inventory_profile,
        'profile_path':PROFILE,'bank_path':(root/'bank/bank.json').relative_to(ROOT).as_posix(),
        'instruction_sha256':BRIEF_SHA,'prior_campaign_authority':'not_applicable; new qualification and release required'}
    p['prompts']={'function_instruction':review_single.FUNCTION_INSTRUCTION,'endpoint_instruction':review_single.ENDPOINT_INSTRUCTION,
        'guidance_sha256':digest(review_single.GUIDANCE),'schema_sha256':digest(review_single.REPLY_SCHEMA)}
    p['matrix']=deepcopy(old['matrix']);p['matrix']['H']['calls']='exactly the frozen one-function batch count'
    p['matrix']['A']['view']='same initial functions then one eligible action per response'
    p['common_evidence']=deepcopy(old['common_evidence'])
    counts={};measured={};records=[]
    for case in bank['cases']:
        plan=_strict_load((root/'bank'/case['directory']/'controller/review-plan.json').read_bytes())
        if not review_single.enabled(plan):raise ValueError('New bank requires declared single-review contract')
        counts[case['case_id']]=plan['batch_count']
        requests=[review_single.build_request(e,model='gpt-5.5',settings=policy['settings'],allow_opening=i>0)
                  for i,e in enumerate([plan['endpoint'],*plan['batches']])]
        sizes=[len(canonical_bytes(q)) for q in requests]
        if max(sizes)>plan['max_request_bytes']:raise ValueError('Mandatory new evidence exceeds frozen request bytes')
        measured[case['case_id']]={'endpoint_bytes':sizes[0],'function_bytes':sizes[1:],
            'maximum_initial_request_bytes':max(sizes),'conservative_token_estimate_ceiling_bytes':max(sizes),
            'token_limit_semantics':'Observed native usage stop; byte count is a conservative workload estimate, not a provider tokenizer.'}
        catalogue=_strict_load((root/'bank'/case['directory']/'controller/catalogue.json').read_bytes())
        measured[case['case_id']]['nested_disclosure']=measure_nested_requests(plan,catalogue)
        if not records:
            for kind,e in [('endpoint',plan['endpoint']),('function',plan['batches'][0])]:
                base='resources/protocol/m3-single-qualification-'+kind
                evidence_path=base+'-controller-evidence.json';request_path=base+'-request.json'
                q=review_single.build_request(e,model='gpt-5.5',settings=policy['settings'])
                _write(ROOT/evidence_path,e);_write(ROOT/request_path,q)
                records.append({'kind':kind,'controller_evidence_path':evidence_path,'request_path':request_path,
                    'controller_evidence_file_sha256':file_hash(ROOT/evidence_path),'request_file_sha256':file_hash(ROOT/request_path),
                    'request_sha256':digest(q),'inventory_sha256':e['inventory_sha256']})
    p['H']={'batch_size':1,'max_request_bytes':200000,'batch_counts':counts}
    proposal={'format_version':'m3-single-profile.1','brief_sha256':BRIEF_SHA,'candidate':p,'bank_sha256':bank['bank_sha256'],
        'qualification_requests':records,'source_manifest':controller_sources(),'measured_requests':measured,
        'schedule':schedule(p['population']['case_ids'],repeats=1,seed=20261012),
        'base_calls_without_disclosure':sum(1+4*n for n in counts.values()),
        'maximum_campaign_logical_calls':sum(1+2*n+2*9 for n in counts.values()),
        'qualification_calls_separate':2,'hosted_calls':0,'historical_calls_reused':0,'experiment_authorized':False,
        'limitations':['Six dependent variants of one payment pair; one repeat; descriptive comparisons only.',
            'Missing/unopened evidence is insufficient; valid citations do not prove semantic correctness.',
            'A follow-ups remain bounded by two operations, nine charged calls and 100000 added bytes; requests are never truncated.',
            'Fresh native provider qualification and exact new Overseer campaign release remain required.']}
    _write(ROOT/PROFILE,proposal)
    _write(root/'candidate.json',p);_write(root/'proposal.json',proposal)
    validate_protocol(p)
    _write(root/'qualification-launch-contract.json',qualification_contract(p))
    return proposal
