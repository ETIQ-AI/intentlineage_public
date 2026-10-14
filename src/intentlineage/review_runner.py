"""Serial review/reconsider orchestration adapted from use_case_icp n27pb.

Fresh requests, exact replies, operation receipts and unchanged control hashes are
retained. Provider is injected; this module does not establish OS arm isolation.
"""
from copy import deepcopy
import json
from pathlib import Path
import time

from .artifact_views import _validate_catalogue, _validate_view
from .native_capture import digest, file_hash
from .review_batches import validate_plan, validate_evidence, ordered_functions
from .review_contract import build_request, validate_reply, canonical_bytes, REPLY_SCHEMA
from .review_disclosure import disclose
from .review_usage import normalize_usage, aggregate_usage

ARMS={'E','H','A','R-H','R-A'}
SESSION_VERSION='m2-session.4.2'
MATRIX_VERSION='m2-matrix.4.2'


class _RecordedProviderFailure(Exception):
    """Replay an exact retained exception receipt without invoking a provider."""


class _ReplayMismatch(ValueError):
    """Integrity failures must escape the ordinary rejected-operation policy."""


class TransportFailure(RuntimeError):
    """Provider positively confirms no reasoning request was charged/started."""


def _write(path, value, *, raw=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    data=value.encode('utf-8') if raw else canonical_bytes(value)+b'\n'
    with path.open('xb') as stream: stream.write(data)


def _invocation_manifest(request):
    return {'fresh_session':True,'history_policy':'none','request_sha256':digest(request),
            'evidence_sha256':request['evidence']['evidence_sha256'],
            'readable_resources':['evidence/request.json','evidence/response-schema.json'],
            'isolation_qualified':False,'required_before_hosted_campaign':'M3 enforced boundary qualification',
            'private_contexts':['workspace','home','temp','output']}


def prepare_invocation(directory, request):
    """Adapt CodexRunner fresh private resource staging; never mount public siblings."""
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    for name in ('evidence','workspace','home','temp','output'): (directory/name).mkdir()
    _write(directory/'evidence/request.json',request)
    _write(directory/'evidence/response-schema.json',request['response_schema'])
    manifest=_invocation_manifest(request)
    _write(directory/'invocation.json',manifest)
    return manifest


def _positive(name,value,minimum=0):
    if type(value) is not int or value<minimum: raise ValueError(name+' must be a bounded integer')


class _Session:
    def __init__(self,plan,*,arm,provider,output_dir,model,settings,max_calls,
                 reasoning_retries,transport_retries,max_request_bytes=None,policy='question_driven',
                 max_operations=0,max_disclosure_bytes=0,_persist=True,response_policy=None):
        validate_plan(plan)
        if arm not in ARMS: raise ValueError('Unknown review arm')
        if not isinstance(model,str) or not model.strip(): raise ValueError('Freeze an explicit model')
        canonical_bytes(settings)
        if policy not in {'question_driven','breadth_first','requirement_prioritized','review_driven'}:raise ValueError('Unknown selection policy')
        _positive('max_operations',max_operations);_positive('max_disclosure_bytes',max_disclosure_bytes)
        for name,value,minimum in [('max_calls',max_calls,1),('reasoning_retries',reasoning_retries,0),('transport_retries',transport_retries,0)]:
            _positive(name,value,minimum)
        from . import review_single
        self.single_mode=review_single.enabled(plan)
        from .review_failures import POLICY
        if self.single_mode:
            if max_calls>9 or max_operations>2 or max_disclosure_bytes>100000:
                raise ValueError('Single-review fixed call/operation/byte caps exceeded')
            response_policy=POLICY
        if response_policy not in {None,POLICY}:raise ValueError("Unknown response policy")
        if response_policy and reasoning_retries:raise ValueError("Response policy forbids reasoning retries")
        self.response_policy=response_policy
        self.root=Path(output_dir)
        self.persist=_persist
        if _persist:
            if self.root.exists(): raise ValueError('Review output must be a fresh nonexistent directory')
            self.root.mkdir(parents=True)
        self.plan=deepcopy(plan);self.arm=arm;self.provider=provider
        from . import review_function
        self.function_mode=self.single_mode or review_function.enabled(plan)
        self.scope_module=review_single if self.single_mode else review_function if self.function_mode else None
        self.request_builder=self.scope_module.build_request if self.function_mode else build_request
        self.reply_validator=self.scope_module.validate_reply if self.function_mode else validate_reply
        self.model=model;self.settings=deepcopy(settings);self.max_calls=max_calls
        self.reasoning_retries=reasoning_retries;self.transport_retries=transport_retries
        self.max_request_bytes=max_request_bytes or plan['max_request_bytes']
        self.policy='review_driven' if self.single_mode else policy;policy=self.policy
        self.max_operations=max_operations;self.max_disclosure_bytes=max_disclosure_bytes
        self.action_outcomes=[]
        self.disclosure_attempts=0
        self.calls=[];self.failures=[];self.replies=[];self.operations=[];self.reconsiderations=[]
        self.omitted_openings=[];self.terminal_reply=None
        self.logical_calls=0;self.transport_failures=0;self.stop_reason=None
        self.latest_evidence=deepcopy(plan['endpoint']);self.reviewed_functions=set()
        self.write(self.root/'plan.json',self.plan)
        self.write(self.root/'protocol.json',{'arm':arm,'model':model,'settings':settings,'max_calls':max_calls,
               'selection_policy':policy,'max_operations':max_operations,'max_disclosure_bytes':max_disclosure_bytes,
               'H_batch_count':plan['batch_count'],'A_max_logical_calls':max_calls if arm=='A' else None,
               'reasoning_retries':reasoning_retries,'transport_retries':transport_retries,
               'max_request_bytes':self.max_request_bytes,'history_policy':'none',
               'transport_policy':'Retry only explicitly confirmed no-reasoning transport failures.',
               'isolation_qualified':False,**({'response_policy':response_policy} if response_policy else {})})

    def write(self,path,value,*,raw=False):
        _write(path,value,raw=raw)

    def stage_invocation(self,path,request):
        prepare_invocation(path,request)

    def record_call(self,folder,record):
        self.write(folder/'call.json',record)
        callback=getattr(self.provider,'after_call',None)
        if callback is not None:callback(folder,deepcopy(record))
        return record

    def disclosure(self,catalogue,evidence,actions,*,cache_dir=None):
        # Retain even rejected or budget-denied candidates: replay must be able
        # to derive their stop without consulting a saved summary claim.
        self.disclosure_attempts+=1
        event={'before_evidence':deepcopy(evidence),'actions':deepcopy(actions)}
        try:
            if self.single_mode:
                from .review_disclosure import disclose_single
                expanded,receipts=disclose_single(catalogue,evidence,actions,cache_dir=cache_dir)
            else:expanded,receipts=disclose(catalogue,evidence,actions,cache_dir=cache_dir)
        except (KeyError,TypeError,ValueError) as error:
            event['failure']={'reason':str(error)}
            self.write(self.root/'disclosure-attempts'/f'{self.disclosure_attempts:04d}.json',event)
            raise
        event.update(evidence=expanded,receipts=receipts,failure=None)
        self.write(self.root/'disclosure-attempts'/f'{self.disclosure_attempts:04d}.json',event)
        return expanded,receipts

    def review(self,evidence,*,allow_opening=False,reconsider=False):
        validate_evidence(evidence);self.latest_evidence=deepcopy(evidence)
        self.terminal_reply=None
        request=self.request_builder(evidence,model=self.model,settings=self.settings,
                              allow_opening=allow_opening,reconsider=reconsider)
        if len(canonical_bytes(request))>self.max_request_bytes:
            self.failures.append({'kind':'context_budget','reason':'Exact request exceeds frozen byte budget.'})
            self.stop_reason='context_budget';return None
        reasoning_retry=0;transport_retry=0
        while self.logical_calls<self.max_calls:
            number=len(self.calls)+1;folder=self.root/'calls'/f'{number:04d}'
            if self.persist:folder.mkdir(parents=True)
            self.write(folder/'request.json',request)
            invocation=folder/'invocation';self.stage_invocation(invocation,request)
            started=time.monotonic();raw='';parsed=None;failure=None;charged=True;provider_id=None
            usage_observation=normalize_usage({})
            try:
                response=self.provider(deepcopy(request),invocation)
                if not isinstance(response,dict) or not isinstance(response.get('raw_reply'),str):
                    raise ValueError('Provider must return exact raw_reply text and usage metadata')
                raw=response['raw_reply'];provider_id=response.get('provider_call_id')
                self.write(folder/'provider-response.json',response)
                supplied_usage=response.get('usage',{})
                usage_observation=normalize_usage(response.get('usage_raw',supplied_usage))
                if response.get('failure'):
                    failure={'kind':'provider_error','reason':str(response['failure'])}
                    if self.response_policy:
                        from .review_failures import stable_failure
                        fields=stable_failure(response['failure'])
                        classification=response['failure'].get('classification')
                        failure.update(reason=fields['text'],structured=fields)
                        if classification and classification.get('kind')=='invalid_response':
                            failure.update(kind='invalid_response',specific_reason=classification['specific_reason'],classification=deepcopy(classification))
                elif usage_observation['errors']:
                    failure={'kind':'provider_metadata','reason':'Malformed provider usage metadata; valid partial counters retained, other counters unknown.'}
                else:
                    try: parsed=self.reply_validator(raw,request['evidence'],allow_opening=allow_opening)
                    except ValueError as error:
                        failure={'kind':'invalid_response' if self.response_policy else 'invalid_reply','reason':str(error)}
                        if self.response_policy:failure['specific_reason']=str(error)
            except TransportFailure as error:
                charged=False;self.transport_failures+=1
                failure={'kind':'transport_failure','reason':str(error)}
            except _RecordedProviderFailure as error:
                failure={'kind':'provider_error','reason':str(error)}
            except Exception as error:
                # Unknown completion/charging is conservative: count the invocation.
                failure={'kind':'provider_error','reason':f'{type(error).__name__}: {error}'}
            elapsed=time.monotonic()-started
            if charged:self.logical_calls+=1
            self.write(folder/'raw-reply.txt',raw,raw=True)
            if parsed is not None:self.write(folder/'parsed-reply.json',parsed)
            if failure:failure.update(attempt=number,charged_reasoning=charged)
            record={'attempt':number,'logical_call':self.logical_calls if charged else None,
                    'charged_reasoning':charged,'evidence_sha256':evidence['evidence_sha256'],
                    'request_sha256':digest(request),'raw_reply_sha256':file_hash(folder/'raw-reply.txt'),
                    'provider_call_id':provider_id,'usage':usage_observation['values'],
                    'usage_raw':usage_observation['raw'],'usage_observation':usage_observation,
                    'usage_available':usage_observation['available'],'usage_complete':usage_observation['complete'],
                    'elapsed_seconds':elapsed,
                    'failure_kind':failure['kind'] if failure else None,'failure':deepcopy(failure),
                    'approved_openings':allow_opening,'history_policy':'none',
                    'files':{p.relative_to(self.root).as_posix():file_hash(p) for p in folder.rglob('*') if p.is_file() and p!=folder/'call.json'}}
            if self.function_mode:
                record.update(function_scope=(request['evidence'].get('functions') or [{'group_id':'endpoint'}])[0]['group_id'],applicability=request['evidence'].get('applicability',[]))
            record=self.record_call(folder,record);self.calls.append(record)
            if failure:
                failure=deepcopy(record["failure"])
            if failure:
                self.failures.append(failure)
                if not charged and transport_retry<self.transport_retries:
                    transport_retry+=1;continue
                if charged and failure['kind']=='invalid_reply' and reasoning_retry<self.reasoning_retries:
                    reasoning_retry+=1;continue
                self.stop_reason='model_call_budget' if self.logical_calls>=self.max_calls else failure['kind']
                return None
            self.replies.append(parsed)
            self.terminal_reply=deepcopy(parsed)
            self.reviewed_functions.update(g['group_id'] for g in evidence.get('functions',[]))
            return parsed
        self.stop_reason='model_call_budget';return None

    def finish(self,*,unchecked_functions=(),unresolved=None,coverage_replies=None,extra=None):
        ids=[e['element_id'] for e in self.plan['endpoint']['elements']]
        observations={i:[] for i in ids}
        for reply in self.replies:
            for a in reply['assessments']:observations[a['element_id']].append(a)
        coverage={i:[] for i in ids}
        for reply in self.replies if coverage_replies is None else coverage_replies:
            for assessment in reply['assessments']:coverage[assessment['element_id']].append(assessment)
        uncovered=[i for i in ids if not coverage[i]]
        insufficient=[i for i in ids if coverage[i] and
                      not any(a['assessment'] in {'supported','contradicted'} for a in coverage[i])]
        conflicts=[i for i in ids if {a['assessment'] for a in coverage[i]} >= {'supported','contradicted'}]
        questions=[] if self.single_mode else deepcopy(unresolved if unresolved is not None else
                           [q for r in self.replies for q in r['unresolved_questions']])
        # No global semantic verdict is manufactured from disparate observations.
        complete=not (uncovered or insufficient or conflicts or questions or self.stop_reason in
                      {'context_budget','invalid_response','invalid_reply','provider_error','provider_metadata','transport_failure','model_call_budget','operation_budget','disclosure_byte_budget','rejected_operation'})
        result={'format_version':SESSION_VERSION,'arm':self.arm,'model':self.model,'settings':self.settings,
                'plan_sha256':self.plan['plan_sha256'],'history_policy':'none','isolation_qualified':False,
                'status':'complete' if complete else 'incomplete','stop_reason':self.stop_reason or 'evidence_reviewed',
                'logical_calls':self.logical_calls,'transport_failures':self.transport_failures,
                'controller_operations':len(self.operations),'evidence_bytes_added':sum(r['evidence_bytes_added'] for r in self.operations),
                'calls':self.calls,'failures':self.failures,'replies':self.replies,
                'terminal_assessment':self.terminal_reply,'omitted_openings':self.omitted_openings,
                'operation_receipts':self.operations,'reconsiderations':self.reconsiderations,
                'element_observations':observations,'uncovered_elements':uncovered,
                'insufficient_elements':insufficient,'conflicting_elements':conflicts,
                'unresolved_questions':questions,'unchecked_functions':list(unchecked_functions),
                **aggregate_usage(self.calls),
                'final_evidence_sha256':self.latest_evidence['evidence_sha256'],
                'limits':['Local contract validation does not establish semantic model accuracy.',
                          'Accepted M1 is integrated; M2 acceptance and M3 qualification are required before campaign.'],
                **(extra or {})}
        if self.single_mode:
            result=self.scope_module.augment_result(result,self.plan,self)
        elif self.function_mode:
            from .review_function import augment_result
            result=augment_result(result,self.plan)
        if self.response_policy:
            from .review_failures import terminal_metadata,SESSION_VERSION as RESPONSE_SESSION
            result.update(terminal_metadata(self),format_version=self.scope_module.SESSION_VERSION if self.single_mode else RESPONSE_SESSION)
            result['status']='incomplete' if result['terminal_outcome'] else result['status']
        self.write(self.root/'final-evidence.json',self.latest_evidence)
        result['files']={p.relative_to(self.root).as_posix():file_hash(p) for p in self.root.rglob('*') if p.is_file() and p!=self.root/'session.json'}
        result['session_sha256']=digest(result)
        if self.persist:self.write(self.root/'session.json',result)
        return result


def _select_actions(evidence,reply,policy):
    if policy=='question_driven':return deepcopy(reply['requested_openings'])
    questions=reply['unresolved_questions']
    if not questions:return []
    ids={i for q in questions for i in q['element_ids']}
    elements=[e for e in evidence['elements'] if e['element_id'] in ids]
    groups=ordered_functions(evidence['graph']['eligible_groups'],elements,policy)
    if not groups:return deepcopy(reply['requested_openings'])
    q=questions[0]
    return [{'kind':'function','target_id':groups[0]['group_id'],'question_id':q['question_id'],
             'reason':f"Frozen {policy} policy: disclose the next eligible function to investigate {q['question']}"}]


def run_review_session(plan,catalogue,*,arm,provider,output_dir,model,settings,max_calls=None,
                       max_operations=4,max_disclosure_bytes=100000,policy='question_driven',
                       reasoning_retries=0,transport_retries=0,cache_dir=None,response_policy=None):
    if arm not in {'E','H','A'}:raise ValueError('Use reconsider_same_evidence for repeated endpoint controls')
    if policy not in {'question_driven','breadth_first','requirement_prioritized','review_driven'}:raise ValueError('Unknown selection policy')
    _positive('max_operations',max_operations);_positive('max_disclosure_bytes',max_disclosure_bytes)
    _validate_catalogue(catalogue);validate_plan(plan)
    for batch in plan['batches']:_validate_view(catalogue,batch['graph'])
    if catalogue['capture_sha256']!=plan['endpoint']['capture_sha256']:raise ValueError('Review catalogue is from another capture')
    if arm=='E':
        # E remains exactly one charged logical review: no reasoning retry arm.
        if reasoning_retries or max_calls not in (None,1):raise ValueError('Endpoint arm requires one logical call')
        max_calls=1
    elif max_calls is None:max_calls=plan['batch_count']+reasoning_retries*(plan['batch_count'])+(4 if arm=='A' else 0)
    session=_Session(plan,arm=arm,provider=provider,output_dir=output_dir,model=model,settings=settings,
                     max_calls=max_calls,reasoning_retries=reasoning_retries,transport_retries=transport_retries,
                     policy=policy,max_operations=max_operations if arm=='A' else 0,
                     max_disclosure_bytes=max_disclosure_bytes if arm=='A' else 0,response_policy=response_policy)
    return _run_treatment(session,catalogue,cache_dir=cache_dir)


def _run_treatment(session,catalogue,*,cache_dir=None):
    plan=session.plan;arm=session.arm;model=session.model;settings=session.settings
    policy=session.policy;max_operations=session.max_operations;max_disclosure_bytes=session.max_disclosure_bytes
    if arm=='E':
        session.review(plan['endpoint']);return session.finish()
    current=None;initial_replies=[];pending_actions=[];local_pending=[]
    for batch in plan['batches']:
        checked=session.review(batch,allow_opening=arm=='A')
        if checked is None:break
        initial_replies.append(checked);pending_actions.extend(checked['requested_openings'])
        if session.function_mode:
            local_pending.append((deepcopy(batch),checked));current=deepcopy(batch);continue
        if current is None:current=deepcopy(batch)
        else:
            from .review_batches import seal_evidence
            by={v['artifact_ref']:v for v in current['intermediate_artifacts']}
            by.update({v['artifact_ref']:v for v in batch['intermediate_artifacts']})
            current['intermediate_artifacts']=[by[r] for r in sorted(by)]
            current['functions'].extend(deepcopy(batch['functions']))
            current['omissions']['function_ids']=[g['group_id'] for g in current['graph']['eligible_groups'] if g['group_id'] not in session.reviewed_functions]
            current['omissions']['artifact_refs']=[r for r in current['omissions']['artifact_refs'] if r not in by]
            seal_evidence(current)
    unchecked=[g['group_id'] for batch in plan['batches'] for g in batch['functions'] if g['group_id'] not in session.reviewed_functions]
    if arm=='H' or current is None or session.stop_reason:
        return session.finish(unchecked_functions=unchecked)
    if session.function_mode:
        adaptive_followups=session.scope_module.adaptive_followups
        return adaptive_followups(session,catalogue,local_pending,unchecked,cache_dir=cache_dir)
    # Adaptive follow-up sees the union of permitted starting batches, no answers.
    synthetic={'assessments':[a for r in initial_replies for a in r['assessments']],
               'unresolved_questions':[q for r in initial_replies for q in r['unresolved_questions']],
               'requested_openings':pending_actions}
    latest=synthetic
    while True:
        actions=_select_actions(current,latest,policy)
        if not actions:
            session.stop_reason='no_requested_disclosure';break
        if session.logical_calls>=session.max_calls:
            session.stop_reason='model_call_budget';break
        # Deduplicate shared selections across initial batches in the controller.
        unique={}
        for action in actions:unique.setdefault((action['kind'],action['target_id']),action)
        actions=list(unique.values())
        remaining=max_operations-len(session.operations)
        if remaining<=0:session.stop_reason='operation_budget';break
        if len(actions)>remaining:
            session.omitted_openings.extend({**deepcopy(a),'omission_reason':'operation_budget'} for a in actions[remaining:])
        actions=actions[:remaining]
        try:expanded,receipts=session.disclosure(catalogue,current,actions,cache_dir=cache_dir)
        except (KeyError,TypeError,ValueError) as error:
            if isinstance(error,_ReplayMismatch):raise
            session.failures.append({'kind':'rejected_operation','reason':str(error),'requests':actions})
            session.stop_reason='rejected_operation';break
        added=len(canonical_bytes(expanded))-len(canonical_bytes(current))
        if sum(r['evidence_bytes_added'] for r in session.operations)+max(0,added)>max_disclosure_bytes:
            session.stop_reason='disclosure_byte_budget';break
        candidate_request=build_request(expanded,model=model,settings=settings,allow_opening=True)
        if len(canonical_bytes(candidate_request))>session.max_request_bytes:
            session.stop_reason='context_budget';break
        # Receipts measure each operation independently; batch bytes are not double counted.
        previous=deepcopy(current);session.operations.extend(receipts);current=expanded
        session.write(session.root/'disclosures'/f'{len(session.operations):04d}.json',
               {'before_evidence':previous,'actions':deepcopy(actions),'receipts':receipts,'evidence':current})
        latest=session.review(current,allow_opening=True)
        if latest is None:break
    session.latest_evidence=deepcopy(current)
    unopened=[g['group_id'] for g in current['graph']['eligible_groups']]
    adaptive_reviewed=bool(session.operations)
    return session.finish(unchecked_functions=sorted(set(unchecked+unopened)),unresolved=latest['unresolved_questions'] if latest else None,
                          coverage_replies=([session.terminal_reply] if session.terminal_reply else []) if adaptive_reviewed else None,
                          extra={'selection_policy':policy,'max_operations':max_operations,'max_disclosure_bytes':max_disclosure_bytes})


def reconsider_same_evidence(plan,*,arm,logical_calls,provider,output_dir,model,settings,
                             transport_retries=0,response_policy=None):
    """Adapt n27pb P12: neutral fresh passes, before/after evidence hashes, zero bytes."""
    if arm not in {'R-H','R-A'}:raise ValueError('Unknown repeated endpoint control')
    _positive('logical_calls',logical_calls,1)
    session=_Session(plan,arm=arm,provider=provider,output_dir=output_dir,model=model,settings=settings,
                     max_calls=logical_calls,reasoning_retries=0,transport_retries=transport_retries,response_policy=response_policy)
    return _run_control(session)


def _run_control(session):
    plan=session.plan;logical_calls=session.max_calls
    endpoint=deepcopy(plan['endpoint'])
    # An invalid charged reply consumes a matched pass; next neutral pass still runs.
    while session.logical_calls<logical_calls:
        before=digest(endpoint);prior=session.logical_calls
        checked=session.review(endpoint,reconsider=session.logical_calls>0)
        after=digest(endpoint)
        if before!=after:raise RuntimeError('Zero-evidence reconsideration changed endpoint evidence')
        session.reconsiderations.append({'operation':'reconsider_same_evidence','pass':session.logical_calls,
                                        'before_sha256':before,'after_sha256':after,'evidence_bytes_added':0})
        if session.logical_calls==prior or (session.response_policy and session.failures):break  # no extra failed-control calls
        session.stop_reason=None
    # Matching calls is not completing coverage. Preserve invalid passes as failures.
    if any(f['kind']!='transport_failure' for f in session.failures):session.stop_reason='invalid_response' if session.response_policy else 'invalid_reply'
    return session.finish(coverage_replies=[session.terminal_reply] if session.terminal_reply else [],
                          unresolved=session.terminal_reply.get('unresolved_questions',[]) if session.terminal_reply else [],
                          extra={'matched_logical_calls':logical_calls,
                                 'count_match':session.logical_calls==logical_calls})


class _ReplaySession(_Session):
    """Run the same controller policy with retained receipts; never call a model."""
    def __init__(self,root,plan,protocol,catalogue):
        self.catalogue=catalogue
        super().__init__(plan,arm=protocol['arm'],provider=self.retained_response,
            output_dir=root,model=protocol['model'],settings=protocol['settings'],
            max_calls=protocol['max_calls'],reasoning_retries=protocol['reasoning_retries'],
            transport_retries=protocol['transport_retries'],max_request_bytes=protocol['max_request_bytes'],
            policy=protocol['selection_policy'],max_operations=protocol['max_operations'],
            max_disclosure_bytes=protocol['max_disclosure_bytes'],_persist=False,response_policy=protocol.get('response_policy'))

    def write(self,path,value,*,raw=False):
        expected=value.encode('utf-8') if raw else canonical_bytes(value)+b'\n'
        if not path.is_file() or path.read_bytes()!=expected:
            raise ValueError('Transcript replay mismatch: '+path.relative_to(self.root).as_posix())

    def stage_invocation(self,path,request):
        self.write(path/'evidence/request.json',request)
        self.write(path/'evidence/response-schema.json',request['response_schema'])
        self.write(path/'invocation.json',_invocation_manifest(request))

    def retained_response(self,request,invocation):
        folder=invocation.parent
        call=json.loads((folder/'call.json').read_bytes())
        path=folder/'provider-response.json'
        if path.is_file():return json.loads(path.read_bytes())
        failure=call.get('failure')
        if not isinstance(failure,dict):raise ValueError('Missing provider/failure replay receipt')
        if failure['kind']=='transport_failure':raise TransportFailure(failure['reason'])
        if failure['kind']=='provider_error':raise _RecordedProviderFailure(failure['reason'])
        raise ValueError('Invalid provider/failure replay receipt')

    def record_call(self,folder,record):
        saved=json.loads((folder/'call.json').read_bytes())
        if record['failure_kind'] is not None and (folder/'parsed-reply.json').exists():
            raise ValueError('Failed call has an unbound parsed reply replay record')
        # Latency is an observation; reproduce every other field mechanically.
        elapsed=saved.get('elapsed_seconds')
        if type(elapsed) not in (int,float) or elapsed<0:
            raise ValueError('Invalid call latency replay receipt')
        record['elapsed_seconds']=elapsed
        if not self.response_policy:
            from .review_failures import legacy_record_reason
            response_path=folder/'provider-response.json'
            if response_path.exists():record=legacy_record_reason(record,saved,json.loads(response_path.read_bytes()))
        if canonical_bytes(record)!=canonical_bytes(saved):
            fields=[key for key in set(record)|set(saved) if canonical_bytes(record.get(key))!=canonical_bytes(saved.get(key))]
            label='Token coverage/aggregation' if any(key.startswith('usage') for key in fields) else 'Call record'
            raise ValueError(label+' replay mismatch: '+','.join(sorted(fields)))
        return record

    def disclosure(self,catalogue,evidence,actions,*,cache_dir=None):
        self.disclosure_attempts+=1
        path=self.root/'disclosure-attempts'/f'{self.disclosure_attempts:04d}.json'
        event=json.loads(path.read_bytes())
        if canonical_bytes(event['before_evidence'])!=canonical_bytes(evidence) or canonical_bytes(event['actions'])!=canonical_bytes(actions):
            raise _ReplayMismatch('Disclosure policy replay mismatch')
        validate_evidence(event['before_evidence'])
        failure=event['failure']
        if self.catalogue is not None:
            expected={'before_evidence':deepcopy(evidence),'actions':deepcopy(actions)}
            try:
                if self.single_mode:
                    from .review_disclosure import disclose_single
                    expanded,receipts=disclose_single(self.catalogue,evidence,actions)
                else:expanded,receipts=disclose(self.catalogue,evidence,actions)
            except (KeyError,TypeError,ValueError) as error:
                expected['failure']={'reason':str(error)}
            else:expected.update(evidence=expanded,receipts=receipts,failure=None)
            if canonical_bytes(expected)!=canonical_bytes(event):
                raise _ReplayMismatch('Native disclosure/receipt replay mismatch')
        if failure:raise ValueError(failure['reason'])
        validate_evidence(event['evidence'])
        return deepcopy(event['evidence']),deepcopy(event['receipts'])


def replay_session(directory,*,catalogue=None):
    """Read-only policy replay; summaries must follow validated transcript records.

    4.0/4.1 evidence remains historical and requires its archived implementation;
    it is never accepted here as a corrected-current outcome.
    """
    root=Path(directory).resolve();result=json.loads((root/'session.json').read_bytes())
    from . import review_function,review_single
    from .review_failures import SESSION_VERSION as RESPONSE_SESSION
    if result.get('format_version') not in {SESSION_VERSION,review_function.SESSION_VERSION,RESPONSE_SESSION,review_single.SESSION_VERSION}:
        raise ValueError('Historical session contract/version: use its archived audit, regenerate current evidence')
    if result.get('session_sha256')!=digest({k:v for k,v in result.items() if k!='session_sha256'}):
        raise ValueError('Session integrity mismatch')
    for relative,expected in result['files'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or path.is_symlink() or not path.is_file() or file_hash(path)!=expected:
            raise ValueError('Transcript file hash/integrity mismatch: '+relative)
    folders=sorted((root/'calls').glob('*'))
    if len(folders)!=len(result['calls']):raise ValueError('Call collection replay mismatch')
    for number,(folder,call) in enumerate(zip(folders,result['calls']),1):
        if folder.name!=f'{number:04d}' or canonical_bytes(call)!=canonical_bytes(json.loads((folder/'call.json').read_bytes())):
            raise ValueError('Saved call collection differs from call.json replay record')
    plan=json.loads((root/'plan.json').read_bytes());validate_plan(plan)
    protocol=json.loads((root/'protocol.json').read_bytes())
    expected_version=review_single.SESSION_VERSION if review_single.enabled(plan) else RESPONSE_SESSION if protocol.get('response_policy') else review_function.SESSION_VERSION if review_function.enabled(plan) else SESSION_VERSION
    if result['format_version']!=expected_version:raise ValueError('Session/view version mismatch')
    protocol=json.loads((root/'protocol.json').read_bytes())
    if protocol['arm']=='E' and (protocol['max_calls']!=1 or protocol['reasoning_retries']):
        raise ValueError('Endpoint policy replay mismatch')
    if protocol['arm']!='A' and (protocol['max_operations'] or protocol['max_disclosure_bytes']):
        raise ValueError('Nonadaptive disclosure policy replay mismatch')
    if protocol['arm'].startswith('R-') and protocol['reasoning_retries']:
        raise ValueError('Control retry policy replay mismatch')
    session=_ReplaySession(root,plan,protocol,catalogue)
    derived=_run_control(session) if session.arm.startswith('R-') else _run_treatment(session,catalogue)
    attempts=list((root/'disclosure-attempts').glob('*.json'))
    if len(attempts)!=session.disclosure_attempts or len(session.calls)!=len(folders):
        raise ValueError('Unconsumed call/disclosure policy replay records')
    if canonical_bytes(derived)!=canonical_bytes(result):
        fields=[key for key in set(derived)|set(result) if canonical_bytes(derived.get(key))!=canonical_bytes(result.get(key))]
        label='Token coverage/aggregation' if any(key.startswith('usage') for key in fields) else 'Terminal/assessment summary'
        raise ValueError(label+' replay mismatch: '+','.join(sorted(fields)))
    return result


def run_review_matrix(plan,catalogue,*,provider_factory,output_dir,model,settings,
                      max_calls=None,max_operations=4,max_disclosure_bytes=100000,
                      policy='question_driven',reasoning_retries=0,transport_retries=0,provider_mode=None,response_policy=None):
    """Serial E/H/A then neutral R-H/R-A. Only numeric counts cross into controls."""
    validate_plan(plan)
    root=Path(output_dir)
    if root.exists():raise ValueError('Matrix output requires a fresh directory')
    root.mkdir(parents=True)
    from . import review_single
    sessions={}
    for arm in ('E','H','A'):
        sessions[arm]=run_review_session(plan,catalogue,arm=arm,provider=provider_factory(arm),
                  output_dir=root/arm,model=model,settings=settings,
                  max_calls=1 if arm=='E' else plan['batch_count'] if review_single.enabled(plan) and arm=='H' else max_calls,max_operations=max_operations,
                  max_disclosure_bytes=max_disclosure_bytes,policy=policy,
                  reasoning_retries=0 if arm=='E' else reasoning_retries,transport_retries=transport_retries,response_policy=response_policy)
        from .review_failures import assert_not_hard_failure
        assert_not_hard_failure(sessions[arm])
    for control,paired in [('R-H','H'),('R-A','A')]:
        count=sessions[paired]['logical_calls']
        if count:
            sessions[control]=reconsider_same_evidence(plan,arm=control,logical_calls=count,
                      provider=provider_factory(control),output_dir=root/control,model=model,
                      settings=settings,transport_retries=transport_retries,response_policy=response_policy)
            assert_not_hard_failure(sessions[control])
        else:
            sessions[control]={'status':'not_run','logical_calls':0,'count_match':True,
                               'reason':'Paired arm made no charged reasoning calls.'}
    from . import review_function
    from .review_failures import MATRIX_VERSION as RESPONSE_MATRIX
    result={'format_version':review_single.MATRIX_VERSION if review_single.enabled(plan) else RESPONSE_MATRIX if response_policy else review_function.MATRIX_VERSION if review_function.enabled(plan) else MATRIX_VERSION,'plan_sha256':plan['plan_sha256'],'model':model,
            'settings':deepcopy(settings),'sessions':sessions,'isolation_qualified':False,
            'provider_mode':provider_mode,'hosted_calls':0 if provider_mode=='mock' else None,
            'paired_counts':{c:{'control':sessions[c]['logical_calls'],'paired':sessions[p]['logical_calls'],
                              'matched':sessions[c]['logical_calls']==sessions[p]['logical_calls']}
                            for c,p in [('R-H','H'),('R-A','A')]},
            'limits':['Local mocked matrix is a plumbing demonstration; no campaign/scoring/semantic accuracy claim.']}
    result['matrix_sha256']=digest(result)
    _write(root/'matrix.json',result)
    return result


def replay_matrix(directory,*,catalogue=None):
    """Validate every session and neutral pairing through the corrected replay."""
    root=Path(directory);matrix=json.loads((root/'matrix.json').read_bytes())
    from . import review_function,review_single
    from .review_failures import MATRIX_VERSION as RESPONSE_MATRIX,SESSION_VERSION as RESPONSE_SESSION
    if matrix.get('format_version') not in {MATRIX_VERSION,review_function.MATRIX_VERSION,RESPONSE_MATRIX,review_single.MATRIX_VERSION}:
        raise ValueError('Historical matrix contract/version: regenerate current evidence')
    if matrix.get('matrix_sha256')!=digest({k:v for k,v in matrix.items() if k!='matrix_sha256'}):
        raise ValueError('Matrix replay integrity mismatch')
    if set(matrix['sessions'])!=ARMS:raise ValueError('Matrix arm collection replay mismatch')
    function_mode=matrix['sessions']['E'].get('format_version')==review_function.SESSION_VERSION
    response_mode=matrix['sessions']['E'].get('response_policy')
    single_mode=matrix['sessions']['E'].get('format_version')==review_single.SESSION_VERSION
    if matrix['format_version']!=(review_single.MATRIX_VERSION if single_mode else RESPONSE_MATRIX if response_mode else review_function.MATRIX_VERSION if function_mode else MATRIX_VERSION):
        raise ValueError('Matrix/session view version mismatch')
    for arm in ('E','H','A'):
        replayed=replay_session(root/arm,catalogue=catalogue)
        row=matrix['sessions'][arm]
        if canonical_bytes(replayed)!=canonical_bytes(row):raise ValueError('Matrix session replay mismatch')
        if row['arm']!=arm or row['model']!=matrix['model'] or canonical_bytes(row['settings'])!=canonical_bytes(matrix['settings']) or row['plan_sha256']!=matrix['plan_sha256']:
            raise ValueError('Matrix protocol replay mismatch')
    counts={}
    for control,paired in [('R-H','H'),('R-A','A')]:
        count=matrix['sessions'][paired]['logical_calls'];row=matrix['sessions'][control]
        if count==0:
            expected={'status':'not_run','logical_calls':0,'count_match':True,
                      'reason':'Paired arm made no charged reasoning calls.'}
            if canonical_bytes(row)!=canonical_bytes(expected) or (root/control).exists():
                raise ValueError('Zero-call control not_run replay mismatch')
        else:
            replayed=replay_session(root/control,catalogue=catalogue)
            if canonical_bytes(replayed)!=canonical_bytes(row):raise ValueError('Matrix control session replay mismatch')
            if row['arm']!=control or row['model']!=matrix['model'] or canonical_bytes(row['settings'])!=canonical_bytes(matrix['settings']) or row['plan_sha256']!=matrix['plan_sha256'] or row['matched_logical_calls']!=count or (not row['count_match'] and not (response_mode and row.get('terminal_outcome')=='invalid_response')):
                raise ValueError('Neutral control protocol/count replay mismatch')
        if row['logical_calls']!=count and not (response_mode and row.get('terminal_outcome')=='invalid_response'):raise ValueError('Actual control count replay mismatch')
        counts[control]={'control':row['logical_calls'],'paired':count,'matched':row['logical_calls']==count}
    if canonical_bytes(matrix['paired_counts'])!=canonical_bytes(counts):
        raise ValueError('Matrix pairing summary replay mismatch')
    if matrix['isolation_qualified'] is not False or (matrix['provider_mode']=='mock' and matrix['hosted_calls']!=0):
        raise ValueError('Matrix qualification summary replay mismatch')
    return matrix
