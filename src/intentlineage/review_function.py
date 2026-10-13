"""Versioned compact/function views around the existing M2 controller/checks.

Only already supplied public evidence is projected. Full signed projections and
original inventories remain controller-owned; this module never reads fault truth
or private catalogue source and never calls a model.
"""
from copy import deepcopy
import json
import re
from .native_capture import digest
from .review_batches import validate_evidence,validate_plan,seal_evidence
from .review_contract import (build_request as original_request,validate_reply as original_reply,
    canonical_bytes,evidence_index,_strict_load)

CONTRACT_VERSION='m3-function-review.1'
SESSION_VERSION='m3-function-session.1'
MATRIX_VERSION='m3-function-matrix.1'
COVERAGE_VERSION='m3-function-coverage.1'
RESPONSE_LIMITS={'max_sentence_chars':80,'max_citations_per_assessment':2,'max_observed_bytes':64,
                 'max_questions':2,'max_question_chars':160,'max_openings':2,'max_reason_chars':120,
                 'max_reply_bytes':20000}
GUIDANCE=[
 'Compact view v1: all original requirements remain available; bookkeeping/provenance is in the bound private registry.',
 'For a function request, jointly select and assess requirements applicable to this function or its stated local scope. Unmatched/ambiguous focus remains eligible; uncovered means unassessed.',
 'Use one short relevance and one short uncertainty sentence, at most 80 characters each. No narrative outside the original M2 JSON.',
 'Use at most two necessary citations per assessment, only listed permitted_citations IDs/pointers and their exact supplied small JSON values (at most 64 encoded bytes). Prefer scalar observations. Never copy tables, descriptions or documents.',
 'omissions, applicability and source_binding are context/missingness metadata, not artifact citation IDs. Do not cite them.',
 'At most two necessary unresolved questions (160 characters each) and two eligible requested openings (reason 120 characters). Complete M2 reply at most 20000 UTF-8 bytes; output token stop remains 8192.',
 'For preservation/receipt checks use necessary supplied input/output/prior facts; missing or unopened information remains unknown. A json_encoded_string wrapper explicitly decodes an observed string and is not a native typed ontology object.',
]


def contract():
 return {'format_version':CONTRACT_VERSION,'inventory_policy':'all-substantive-fields-v1',
  'artifact_policy':'already-public-summary-sample-v1','graph_policy':'local-subset-of-signed-projection-v1',
  'applicability_policy':'conservative-fields-and-public-function-terms-v1',
  'response_limits':deepcopy(RESPONSE_LIMITS),'guidance':GUIDANCE[:],
  'coverage_policy':COVERAGE_VERSION,'adaptive_policy':'one-selected-local-scope-no-answer-history-v1'}


def enabled(plan):return plan.get('function_review')==contract()


def attach_contract(plan):
 validate_plan(plan)
 if plan['batch_size']!=1 or any(len(b.get('functions',[]))!=1 for b in plan['batches']):
  raise ValueError('Function review requires exactly one visible function per initial batch')
 value=deepcopy(plan);value['format_version']='m3-function-plan.1';value['function_review']=contract()
 value['original_plan_sha256']=plan['plan_sha256'];value.pop('plan_sha256');value['plan_sha256']=digest(value)
 return value


def compact_inventory(elements):
 result=[]
 for e in elements:
  # Unknown substantive fields in operationalization are retained, never guessed away.
  item={k:deepcopy(e.get(k)) for k in ['element_id','category','kind','role','operator','meaning','parameters','grounding','supporting_elements']}
  item['scope']={k:deepcopy(v) for k,v in (e.get('scope') or {}).items() if k!='source_id'}
  item['criteria']={k:deepcopy(v) for k,v in (e.get('operationalization') or {}).items() if k!='version'}
  result.append(item)
 return result


def _decode_cells(value):
 if isinstance(value,dict):return {k:_decode_cells(v) for k,v in value.items()}
 if isinstance(value,list):return [_decode_cells(v) for v in value]
 if isinstance(value,str) and len(canonical_bytes(value))>RESPONSE_LIMITS['max_observed_bytes'] and value.lstrip().startswith(('{','[')):
  try:decoded=_strict_load(value);canonical_bytes(decoded)
  except (ValueError,TypeError):return value
  return {'representation':'json_encoded_string','decoded':decoded}
 return value


def _artifact(view):
 summary=view['summary'];description=summary['description'];marker=' Observed captured sample: '
 result={'artifact_ref':view['artifact_ref'],'native_ids':deepcopy(view['native_ids']),
  'description':(f"Captured table: {summary['statistics']['row_count']} rows; {summary['statistics']['column_count']} columns." if 'row_count' in summary['statistics'] else description.split(marker,1)[0]),'statistics':deepcopy(summary['statistics']),
  'coverage':deepcopy(summary['coverage']),'sample_available':False}
 # A truncated public description cannot be repaired from private raw data.
 if marker in description and not summary.get('description_truncated'):
  try:sample=_strict_load(description.split(marker,1)[1]);canonical_bytes(sample)
  except (ValueError,TypeError):pass
  else:result.update(sample=_decode_cells(sample),sample_available=True)
 if not result['sample_available']:
  result.update(captured_description_fragment=description,missingness='Original public sample incomplete or unavailable; no additional values fetched.')
 return result


def _local_graph(evidence,group):
 graph=evidence['graph'];nodes={n['native_id']:n for n in graph['nodes']}
 refs=set(group['input_artifacts']+group['output_artifacts'])
 ids={group['native_id']}|{n['native_id'] for n in graph['nodes'] if any(a['artifact_ref'] in refs for a in n['artifacts'])}
 # Only already visible parent/child descriptors, never hidden catalogue nodes.
 for n in graph['nodes']:
  parent=(n.get('scope') or {}).get('native_parent_group') if isinstance(n.get('scope'),dict) else None
  if parent==group['group_id']:ids.add(n['native_id'])
 parent=(nodes.get(group['native_id'],{}).get('scope') or {}).get('native_parent_group')
 if parent:
  ids.update(n['native_id'] for n in graph['nodes'] if n['native_id']==next((g['native_id'] for g in graph['eligible_groups'] if g['group_id']==parent),None))
 local_nodes=[]
 for i in sorted(ids):
  if i not in nodes:continue
  n=nodes[i];local_nodes.append({k:deepcopy(n[k]) for k in ['native_id','name','type','scope']})
 edges=[deepcopy(e) for e in graph['relationships'] if e['tail'] in ids and e['head'] in ids]
 eligible=[deepcopy(g) for g in graph['eligible_groups'] if g['group_id']==group['group_id'] or
  (nodes.get(g['native_id'],{}).get('scope') or {}).get('native_parent_group')==group['group_id']]
 supplied={v['artifact_ref'] for k in ['job_inputs','job_outputs','intermediate_artifacts'] for v in evidence.get(k,[])}
 return {'format_version':'m3-local-graph.1','nodes':local_nodes,'relationships':edges,'eligible_groups':eligible,
  'opened_groups':[g for g in graph['opened_groups'] if g==group['group_id']],
  'visible_artifacts':sorted(supplied & set(graph['visible_artifacts'])),
  'description':f"Visible local scope {group['name']}; other function scopes and unopened descendants withheld."}


def project_evidence(evidence):
 validate_evidence(evidence)
 value={k:deepcopy(evidence[k]) for k in ['prompt','conditions','inventory_sha256','capture_sha256']}
 value.update(format_version='m3-function-evidence.1',elements=compact_inventory(evidence['elements']),
  job_inputs=[_artifact(a) for a in evidence['job_inputs']],job_outputs=[_artifact(a) for a in evidence['job_outputs']],
  intermediate_artifacts=[],inspections=deepcopy(evidence.get('inspections',[])),
  source_binding={'original_evidence_sha256':evidence['evidence_sha256'],
   'registry_sha256':digest({'prompt':evidence['prompt'],'conditions':evidence['conditions'],'elements':evidence['elements']}),
   'original_inventory_sha256':evidence['inventory_sha256'],'view_contract_sha256':digest(contract())})
 groups=evidence.get('functions',[])
 if groups:
  if len(groups)!=1:raise ValueError('Public function request may contain exactly one function')
  group=groups[0];value['functions']=deepcopy(groups)
  value['graph']=_local_graph(evidence,group)
  refs=set(group['input_artifacts']+group['output_artifacts'])
  # Approved local opening artifacts are within this selected scope; no H union.
  local_ids={n['native_id'] for n in value['graph']['nodes']}
  local_ids.update(evidence.get('local_disclosed_native_ids',[]))
  local_views=[a for a in evidence.get('intermediate_artifacts',[]) if a['artifact_ref'] in refs or set(a['native_ids'])&local_ids]
  value['intermediate_artifacts']=[_artifact(a) for a in local_views]
  value['source_binding']['signed_projection_sha256']=evidence['graph']['projection_sha256']
  fields={column for a in value['intermediate_artifacts']+value['job_inputs']+value['job_outputs']
   if a['artifact_ref'] in refs for column in a['statistics'].get('columns',[])}
  terms=set(re.findall(r'[a-z]+',group['name'].lower()))
  focus=[]
  for e in value['elements']:
   required=set(e['criteria'].get('fields',[]))|{e['parameters'].get('field')} if isinstance(e['parameters'],dict) else set(e['criteria'].get('fields',[]))
   meaning=set(re.findall(r'[a-z]+',canonical_bytes(e['meaning']).decode().lower()))
   matches=sorted((required-{None})&fields)
   semantic=sorted(terms&meaning-{'the','and','of','is'})
   focus.append({'element_id':e['element_id'],'eligible':True,'status':'potentially_applicable' if matches or semantic else 'unknown',
                 'matched_fields':matches,'matched_terms':semantic})
  value['applicability']=focus
  available={a['artifact_ref'] for k in ['job_inputs','job_outputs','intermediate_artifacts'] for a in value.get(k,[])}
  value['missingness']={'boundary_values_not_supplied':sorted(refs-available),'other_scopes_unreviewed':True}
 if 'question_context' in evidence:value['question_context']=deepcopy(evidence['question_context'])
 if 'required_prior_artifact_refs' in evidence:
  value['required_prior_facts']=[_artifact(a) for a in evidence.get('intermediate_artifacts',[]) if a['artifact_ref'] in evidence['required_prior_artifact_refs'] and a['artifact_ref'] not in {v['artifact_ref'] for v in value['intermediate_artifacts']}]
  # Prior facts must be actual supplied artifact views and therefore citeable.
  value['intermediate_artifacts'].extend(deepcopy(value['required_prior_facts']))
 value['evidence_sha256']=digest(value)
 return value


def _small_pointers(value,path=''):
 if len(canonical_bytes(value))<=RESPONSE_LIMITS['max_observed_bytes']:
  yield path
 if isinstance(value,dict):
  for k,v in sorted(value.items()):yield from _small_pointers(v,path+'/'+str(k).replace('~','~0').replace('/','~1'))
 elif isinstance(value,list):
  for i,v in enumerate(value):yield from _small_pointers(v,path+'/'+str(i))


def permitted_citations(evidence):
 return [{'evidence_id':ref,'pointers':list(_small_pointers(v))} for ref,v in sorted(evidence_index(evidence).items()) if list(_small_pointers(v))]


def build_request(evidence,*,model,settings,allow_opening=False,reconsider=False,max_request_bytes=300000):
 view=project_evidence(evidence)
 request=original_request(view,model=model,settings=settings,allow_opening=allow_opening,reconsider=reconsider)
 request['contract_version']=CONTRACT_VERSION;request['guidance'].extend(GUIDANCE)
 request['function_review']={'format_version':CONTRACT_VERSION,'contract_sha256':digest(contract()),'response_limits':deepcopy(RESPONSE_LIMITS)}
 request['permitted_citations']=permitted_citations(view)
 if len(canonical_bytes(request))>max_request_bytes:raise ValueError('Mandatory compact single-function/common evidence exceeds byte budget; never clip')
 return request


def validate_reply(raw,evidence,*,allow_opening=False):
 reply=original_reply(raw,evidence,allow_opening=allow_opening)
 if len(raw.encode())>RESPONSE_LIMITS['max_reply_bytes']:raise ValueError('Concise reply byte bound exceeded')
 allowed={r['evidence_id']:set(r['pointers']) for r in permitted_citations(evidence)}
 for a in reply['assessments']:
  for key in ['relevance','uncertainty']:
   if len(a[key])>RESPONSE_LIMITS['max_sentence_chars'] or '\n' in a[key]:raise ValueError('Concise assessment sentence bound exceeded')
  if len(a['citations'])>RESPONSE_LIMITS['max_citations_per_assessment']:raise ValueError('Too many assessment citations')
  for c in a['citations']:
   if c['pointer'] not in allowed.get(c['evidence_id'],set()) or len(canonical_bytes(c['observed']))>RESPONSE_LIMITS['max_observed_bytes']:
    raise ValueError('Citation is outside declared small supplied references')
 if len(reply['unresolved_questions'])>RESPONSE_LIMITS['max_questions'] or any(len(q['question'])>RESPONSE_LIMITS['max_question_chars'] for q in reply['unresolved_questions']):raise ValueError('Concise question bound exceeded')
 if len(reply['requested_openings'])>RESPONSE_LIMITS['max_openings'] or any(len(a['reason'])>RESPONSE_LIMITS['max_reason_chars'] for a in reply['requested_openings']):raise ValueError('Concise opening bound exceeded')
 return reply


def followup_evidence(expanded,action,question,group,*,newly_disclosed_ids=()):
 value=deepcopy(expanded);prior={r for g in value.get('functions',[]) for k in ['input_artifacts','output_artifacts'] for r in g[k]}
 value['functions']=[deepcopy(group)];value['question_context']=deepcopy(question)
 value['required_prior_artifact_refs']=sorted(prior);value['local_disclosed_native_ids']=sorted(set(newly_disclosed_ids))
 return seal_evidence(value)


def augment_result(result,plan):
 if not enabled(plan):return result
 result['format_version']=SESSION_VERSION;result['coverage_contract']=COVERAGE_VERSION
 successes=[c for c in result['calls'] if not c['failure']];coverage=[];effective={}
 for call,reply in zip(successes,result['replies']):
  scope=call['function_scope'];coverage.append({'attempt':call['attempt'],'scope_id':scope,
   'assessed_elements':[a['element_id'] for a in reply['assessments']],
   'uncovered_elements':reply['uncovered_elements'][:],'applicability':deepcopy(call['applicability']),
   'evidence_sha256':call['evidence_sha256']})
  for a in reply['assessments']:effective[(scope,a['element_id'])]={**deepcopy(a),'scope_id':scope}
 if result['arm'].startswith('R-'):
  effective={( 'endpoint',a['element_id']):{**deepcopy(a),'scope_id':'endpoint'} for a in (result.get('terminal_assessment') or {}).get('assessments',[])}
 required={g['group_id'] for b in plan['batches'] for g in b['functions']} if result['arm'] in {'H','A'} else {'endpoint'}
 required.update(c['function_scope'] for c in result['calls'])
 result['required_scopes']=sorted(required)
 result['scope_coverage']=coverage;result['effective_scoped_assessments']=[effective[k] for k in sorted(effective)]
 result['scope_policy']='Latest explicit reassessment per function/element; uncovered text never erases earlier observations. Different function scopes remain separate.'
 return result


def scoped_outcome(record,row):
 """Versioned interpretation of independently reviewed function scopes."""
 scopes={}
 allowed=set(record.get('inventory_element_ids',record['target_element_ids']))
 for a in row['assessments']:
  if a['element_id'] not in allowed:raise ValueError('Assessment element is outside inventory')
  if a['assessment'] not in {'supported','contradicted','insufficient_evidence'}:raise ValueError('Unknown assessment status')
  scopes.setdefault((a['scope_id'],a['element_id']),set()).add(a['assessment'])
 if record['kind'] in {'clean','benign'}:
  if any('contradicted' in status for status in scopes.values()):return 'false_alarm'
 else:
  if any(status=={'contradicted'} and element in record['target_element_ids'] for (scope,element),status in scopes.items()):return 'detected'
 required=row['required_scopes'];targets=record['target_element_ids']
 if not required or not targets or any(scopes.get((s,e))!={'supported'} for s in required for e in targets):return 'insufficient_evidence'
 return 'no_alarm' if record['kind'] in {'clean','benign'} else 'missed'


def adaptive_followups(session,catalogue,pending,unchecked,*,cache_dir=None):
 """Only the existing Session performs calls, disclosure, accounting and replay."""
 queue=list(pending);seen=set();questions=[]
 while queue and session.logical_calls<session.max_calls:
  current,reply=queue.pop(0)
  for action in reply['requested_openings']:
   key=(action['kind'],action['target_id'])
   if key in seen:continue
   if len(session.operations)>=session.max_operations:
    session.omitted_openings.append({**deepcopy(action),'omission_reason':'operation_budget'});continue
   seen.add(key);question=next(q for q in reply['unresolved_questions'] if q['question_id']==action['question_id'])
   group=next((g for g in current['graph']['eligible_groups'] if g['group_id']==action['target_id']),current['functions'][0])
   try:expanded,receipts=session.disclosure(catalogue,current,[action],cache_dir=cache_dir)
   except (KeyError,TypeError,ValueError) as error:
    if error.__class__.__name__=='_ReplayMismatch':raise
    session.failures.append({'kind':'rejected_operation','reason':str(error),'requests':[action]});session.stop_reason='rejected_operation';break
   if sum(r['evidence_bytes_added'] for r in session.operations+receipts)>session.max_disclosure_bytes:
    session.stop_reason='disclosure_byte_budget';break
   focused=followup_evidence(expanded,action,question,group,newly_disclosed_ids=receipts[0].get('nodes_added',[]))
   try:build_request(focused,model=session.model,settings=session.settings,allow_opening=True,max_request_bytes=session.max_request_bytes)
   except ValueError:session.stop_reason='context_budget';break
   session.operations.extend(receipts)
   session.write(session.root/'disclosures'/f'{len(session.operations):04d}.json',{'before_evidence':deepcopy(current),'actions':[deepcopy(action)],'receipts':receipts,'evidence':focused})
   latest=session.review(focused,allow_opening=True)
   if latest is None:break
   questions=latest['unresolved_questions'];queue.append((focused,latest))
   if session.logical_calls>=session.max_calls:break
  if session.stop_reason:break
 if not session.stop_reason:session.stop_reason='local_scopes_reviewed'
 return session.finish(unchecked_functions=unchecked,extra={'selection_policy':session.policy,
  'max_operations':session.max_operations,'max_disclosure_bytes':session.max_disclosure_bytes})
