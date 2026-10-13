"""Frozen joint-review batches from M1 public views; no model retrieval call."""
from copy import deepcopy

from .evidence_packages import validate_package
from .native_capture import digest
from .review_contract import build_request, canonical_bytes

COMMON_KEYS = ('prompt', 'elements', 'conditions', 'inventory_sha256', 'capture_sha256',
               'job_inputs', 'job_outputs', 'limits')
POLICIES = {'question_driven', 'breadth_first', 'requirement_prioritized'}


def common_evidence(evidence):
    return {k: deepcopy(evidence[k]) for k in COMMON_KEYS}


def seal_evidence(evidence):
    evidence.pop('evidence_sha256', None)
    evidence['evidence_sha256'] = digest(evidence)
    return evidence


def validate_evidence(evidence):
    if (evidence.get('format_version') != 'm2.4.0' or
        evidence.get('evidence_sha256') != digest({k:v for k,v in evidence.items() if k != 'evidence_sha256'})):
        raise ValueError('M2 evidence integrity mismatch')
    return evidence


def ordered_functions(functions, elements, policy):
    if policy not in POLICIES: raise ValueError('Unknown selection policy')
    if policy == 'requirement_prioritized':
        # Ranking affects order only. No unmatched requirement or function is excluded.
        terms = {str(x).lower() for e in elements for x in
                 list((e.get('parameters') or {}).values()) + (e.get('operationalization') or {}).get('fields', [])
                 if isinstance(x, (str, int))}
        def rank(g):
            name = str(g.get('name', '')).lower()
            return (-sum(t in name for t in terms if t), g['native_id'])
        return sorted(functions, key=rank)
    return sorted(functions, key=lambda g: g['native_id'])


def _size(evidence):
    # Conservative request bound includes the complete contract and schema.
    return len(canonical_bytes(build_request(evidence, model='qualification-placeholder', settings={}, allow_opening=True)))


def build_review_plan(endpoint, top_level, *, batch_size=8, max_request_bytes=200000, policy='breadth_first'):
    validate_package(endpoint); validate_package(top_level)
    if endpoint['mode'] != 'endpoints' or top_level['mode'] != 'top_level':
        raise ValueError('M2 requires endpoint and unopened top-level M1 packages')
    if common_evidence(endpoint) != common_evidence(top_level):
        raise ValueError('Every arm requires identical common evidence')
    if type(batch_size) is not int or batch_size < 1 or type(max_request_bytes) is not int or max_request_bytes < 1:
        raise ValueError('Batch size and request byte budget must be positive integers')
    ids = [e['element_id'] for e in endpoint['elements']]
    if len(ids) != len(set(ids)) or {e['category'] for e in endpoint['elements']} - {'intent','ontology','business_rules'}:
        raise ValueError('Inventory requires unique IDs in three categories')
    base = {**common_evidence(endpoint), 'format_version':'m2.4.0', 'inspections':[],
            'omissions': {'function_ids':[], 'artifact_refs':[], 'reason':'Endpoint-only evidence.'}}
    endpoint_view = seal_evidence(base)
    if _size(endpoint_view) > max_request_bytes:
        raise ValueError('Mandatory prompt/inventory/whole-job evidence exceeds request budget')
    graph = deepcopy(top_level['graph'])
    functions = ordered_functions(graph['eligible_groups'], endpoint['elements'], policy)
    views = {a['artifact_ref']: a for a in top_level['intermediate_artifacts']}
    job_refs = {a['artifact_ref'] for key in ('job_inputs','job_outputs') for a in endpoint[key]}

    def batch(groups):
        refs = {r for g in groups for key in ('input_artifacts','output_artifacts') for r in g[key]} - job_refs
        if refs - views.keys(): raise ValueError('Function boundary has no supplied artifact view')
        value = {**common_evidence(endpoint), 'format_version':'m2.4.0', 'graph':deepcopy(graph),
                 'functions':deepcopy(groups), 'intermediate_artifacts':[deepcopy(views[r]) for r in sorted(refs)],
                 'inspections':[], 'omissions':{
                     'function_ids':[g['group_id'] for g in functions if g not in groups],
                     'artifact_refs':sorted(set(views) - refs),
                     'reason':'Predeclared boundary batch; other visible values withheld, no hidden descendants listed.'}}
        return seal_evidence(value)

    batches, current = [], []
    for group in functions:
        candidate = batch(current + [group])
        if current and (len(current) == batch_size or _size(candidate) > max_request_bytes):
            batches.append(batch(current)); current=[]
        current.append(group)
        if _size(batch(current)) > max_request_bytes:
            raise ValueError('Mandatory single-function boundary/graph evidence exceeds request budget')
    if current or not batches: batches.append(batch(current))
    if any(_size(e)>max_request_bytes for e in batches):
        raise ValueError('Mandatory visible graph evidence exceeds request budget')
    result = {'format_version':'m2-plan.4.0','endpoint':endpoint_view,'batches':batches,
              'batch_count':len(batches),'batch_size':batch_size,'max_request_bytes':max_request_bytes,
              'policy':policy,'common_sha256':digest(common_evidence(endpoint_view)),
              'top_level_package_sha256':top_level['package_sha256'],
              'limits':['Request byte limits are qualified locally; tokenizer/model context qualification belongs to M3.',
                        'H call count is exactly the predeclared batch count, subject to charged retries.']}
    result['plan_sha256']=digest(result)
    return result


def validate_plan(plan):
    if plan.get('plan_sha256') != digest({k:v for k,v in plan.items() if k != 'plan_sha256'}):
        raise ValueError('Review plan integrity mismatch')
    for e in [plan['endpoint'], *plan['batches']]:
        validate_evidence(e)
        if digest(common_evidence(e)) != plan['common_sha256']:
            raise ValueError('Review plan common evidence mismatch')
    return plan
