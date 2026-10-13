"""Adapt upstream advertised-target inspection through M1 signed native views."""
from copy import deepcopy

from .artifact_views import open_group, inspect_artifact, _validate_view
from .evidence_packages import _summary
from .native_capture import digest
from .review_batches import seal_evidence, validate_evidence
from .review_contract import canonical_bytes


def disclose(catalogue, evidence, actions, *, cache_dir=None):
    """Transactional, zero-model-call batch; hidden targets remain controller-private."""
    validate_evidence(evidence)
    if 'graph' not in evidence: raise ValueError('Endpoint evidence cannot open native functions/artifacts')
    _validate_view(catalogue, evidence['graph'])
    if evidence['capture_sha256'] != catalogue['capture_sha256']:
        raise ValueError('Disclosure belongs to another capture')
    value=deepcopy(evidence); receipts=[]
    # Eligibility is frozen at the request boundary: siblings do not grant a child
    # permission within the same model-selected batch.
    eligible={g['group_id'] for g in evidence['graph']['eligible_groups']}
    visible=set(evidence['graph']['visible_artifacts']); seen=set()
    for action in actions:
        target=action['target_id'];kind=action['kind']
        if not action.get('reason','').strip() or not action.get('question_id','').strip():
            raise ValueError('Disclosure requires a specific question and reason')
        if (kind,target) in seen: raise ValueError('Duplicate disclosure target')
        seen.add((kind,target))
        before=value['evidence_sha256'];before_bytes=len(canonical_bytes(value))
        if kind=='function':
            if target not in eligible: raise ValueError('Function is not currently visible/eligible')
            graph,receipt=open_group(catalogue,value['graph'],target)
            value['graph']=graph
            refs={v['artifact_ref'] for v in value['intermediate_artifacts']}
            job_refs=set(catalogue['job_inputs']+catalogue['job_outputs'])
            additions=set(receipt['newly_disclosed_artifacts'])-refs-job_refs
            value['intermediate_artifacts'].extend(_summary(catalogue,r,cache_dir) for r in sorted(additions))
            value['omissions']['artifact_refs']=[r for r in value['omissions']['artifact_refs'] if r not in additions]
        elif kind=='artifact':
            if target not in visible: raise ValueError('Artifact is not currently visible/eligible')
            result=inspect_artifact(catalogue,value['graph'],target,operation=action['inspection'],
                                    start=action['start'],count=action['count'],columns=action['columns'])
            receipt=result.pop('receipt')
            value['inspections'].append({'evidence_id':f"inspection:{len(value['inspections'])+1}:{target}",
                                        'artifact_ref':target,'result':result})
        else: raise ValueError('Only function opening and bounded artifact inspection are allowed')
        seal_evidence(value)
        receipt.update(question_id=action['question_id'],reason=action['reason'],request=deepcopy(action),
                       before_evidence_sha256=before,after_evidence_sha256=value['evidence_sha256'],
                       evidence_bytes_added=max(0,len(canonical_bytes(value))-before_bytes))
        receipts.append(receipt)
    return value,receipts
