"""Local mock/saved/manual transports. No automatic hosted command execution."""
from copy import deepcopy
import json
from pathlib import Path
import time

from .native_capture import digest
from .review_contract import canonical_bytes
from .review_runner import _write
from .review_usage import normalize_usage, ALIASES


class SavedProvider:
    """Replay human/provider records only when bound to the exact current request."""
    def __init__(self,directory):
        self.directory=Path(directory);self.calls=0

    def __call__(self,request,invocation):
        self.calls+=1
        path=self.directory/f'{self.calls:04d}.json'
        value=json.loads(path.read_bytes())
        if value.get('request_sha256')!=digest(request):
            raise ValueError('Saved provider reply request binding mismatch')
        return value


class MockProvider:
    """Explicit no-match fixture; optional question-driven native opening exercise."""
    def __init__(self,adaptive=False):self.adaptive=adaptive;self.calls=0

    def __call__(self,request,invocation):
        self.calls+=1;evidence=request['evidence']
        ids=[e['element_id'] for e in evidence['elements']]
        groups=evidence.get('graph',{}).get('eligible_groups',[])
        openings=[]
        questions=[{'question_id':'q-observation','element_ids':ids,
                    'question':'Do further captured values resolve the unassessed requirements?'}] if ids else []
        if self.adaptive and request['allow_opening'] and groups and not evidence['graph']['opened_groups'] and questions:
            openings=[{'kind':'function','target_id':groups[0]['group_id'],'question_id':'q-observation',
                       'reason':'Exercise native disclosure for this unresolved fixture question.'}]
        reply={'assessments':[],'no_relevant_element':True,'uncovered_elements':ids,
               'unresolved_questions':questions,'requested_openings':openings}
        return {'raw_reply':canonical_bytes(reply).decode(),'usage':{},
                'provider_call_id':f'local-mock-{self.calls}','mocked':True}


def prepare_provider_command(invocation,request,*,codex_bin='codex'):
    """Adapt reference fresh Codex invocation flags; return a human-run template."""
    invocation=Path(invocation).resolve()
    saved=json.loads((invocation/'evidence/request.json').read_bytes())
    if saved!=request:raise ValueError('Provider command must use its own staged request')
    settings=request['settings']
    if set(settings)-{'reasoning_effort'}:
        raise ValueError('Codex template supports only explicit reasoning_effort; qualify other settings separately')
    argv=[codex_bin,'exec','--model',request['model'],'--ephemeral','--json','--color','never',
          '--ignore-user-config','--ignore-rules','--skip-git-repo-check',
          '--sandbox','read-only','--cd',str(invocation/'workspace'),
          '--output-schema',str(invocation/'evidence/response-schema.json'),
          '--output-last-message',str(invocation/'output/reply.json')]
    if settings.get('reasoning_effort'):
        argv+=['--config','model_reasoning_effort='+json.dumps(settings['reasoning_effort'])]
    argv+=['-']
    template={'argv':argv,'stdin':'evidence/request.json','stdout':'output/events.jsonl',
              'stderr':'output/stderr.txt','private_home':'home','private_temp':'temp',
              'request_sha256':digest(request),'fresh_session':True,'history_policy':'none',
              'isolation_qualified':False,'local_cli_inspected':'codex-cli 0.160.0, 8 October 2026',
              'official_reference':'https://learn.chatgpt.com/docs/cli/reference',
              'required_before_campaign':['M1 and M2 acceptance','M3 frozen model/CLI/settings and enforced isolation qualification',
                                          'Provider retry/attempt accounting and generated-command tool restrictions']}
    _write(invocation/'provider-command.json',template)
    return template


class ManualProvider:
    """Human executes each staged command externally, then supplies a bound record.

    This waits for a local file, never launches Codex/network/subprocesses. Use only
    under the qualified M3 boundary for hosted campaign data. Timeout has unknown
    charging and is conservatively recorded by the controller as a provider error.
    """
    def __init__(self,*,timeout_seconds=1800,poll_seconds=0.5):
        if timeout_seconds<=0 or poll_seconds<=0:raise ValueError('Manual wait bounds must be positive')
        self.timeout_seconds=timeout_seconds;self.poll_seconds=poll_seconds

    def __call__(self,request,invocation):
        invocation=Path(invocation)
        prepare_provider_command(invocation,request)
        response=invocation/'output/provider-response.json'
        print(f'Awaiting human-run provider receipt: {response}',flush=True)
        started=time.monotonic()
        while not response.exists():
            if time.monotonic()-started>=self.timeout_seconds:
                raise TimeoutError('Human provider receipt timeout; provider charging unknown')
            time.sleep(self.poll_seconds)
        result=json.loads(response.read_bytes())
        if result.get('request_sha256')!=digest(request):raise ValueError('Manual provider request binding mismatch')
        return result


def _usage_candidates(value, *, explicit=False):
    """Adapt upstream recursive reported-usage search; do not infer missing usage."""
    if isinstance(value,dict):
        lowered={str(k).lower():v for k,v in value.items()}
        if explicit or any(a in lowered for names in ALIASES.values() for a in names):
            yield value
        for key,child in value.items():
            if str(key).lower() in {'usage','token_usage','tokenusage'} and not isinstance(child,(dict,list)):
                yield child
            else:yield from _usage_candidates(child,explicit=str(key).lower() in {'usage','token_usage','tokenusage'})
    elif isinstance(value,list):
        for child in value:yield from _usage_candidates(child)


def extract_usage(events):
    """Latest receipt, including partial/malformed usage; never backfill older calls."""
    for index in range(len(events)-1,-1,-1):
        for candidate in _usage_candidates(events[index]):
            observation=normalize_usage(candidate)
            status='unavailable' if observation['errors'] or not observation['available'] else 'reported' if observation['complete'] else 'partial'
            return {'usage':observation['values'],'usage_raw':deepcopy(candidate),
                    'usage_observation':observation,'usage_status':status,'source_event_index':index}
    observation=normalize_usage({})
    return {'usage':{},'usage_raw':{},'usage_observation':observation,'usage_status':'unavailable','source_event_index':None}


def collect_provider_response(invocation,*,provider_call_id,usage=None,exit_code=0):
    """Record exact human-run output and raw event log without launching a provider."""
    invocation=Path(invocation)
    request=json.loads((invocation/'evidence/request.json').read_bytes())
    output=invocation/'output'
    raw=(output/'reply.json').read_text(encoding='utf-8') if (output/'reply.json').exists() else ''
    raw_events=(output/'events.jsonl').read_text(encoding='utf-8') if (output/'events.jsonl').exists() else None
    events=[];event_errors=[]
    for index,line in enumerate((raw_events or '').splitlines()):
        if not line.strip():continue
        try:events.append(json.loads(line))
        except ValueError:event_errors.append({'line':index+1,'reason':'Malformed provider event JSON'})
    extracted=extract_usage(events)
    observation=extracted['usage_observation'] if usage is None else normalize_usage(usage)
    value={'request_sha256':digest(request),'raw_reply':raw,'provider_call_id':provider_call_id,
           'usage':deepcopy(observation['values']),'usage_raw':deepcopy(observation['raw']),
           'usage_observation':observation,'raw_events':raw_events,
           'stderr':(output/'stderr.txt').read_text(encoding='utf-8') if (output/'stderr.txt').exists() else None,
           'usage_status':extracted['usage_status'] if usage is None else 'human_supplied',
           'usage_source_event_index':extracted['source_event_index'],'event_diagnostics':event_errors,
           'no_unreported_reasoning_retries':'Must be qualified from provider event/attempt receipts before M3 campaign.'}
    if exit_code or not raw:
        value['failure']={'exit_code':exit_code,'reason':'Human provider invocation failed or produced no final reply; charging unknown.'}
    _write(output/'provider-response.json',value)
    return value
