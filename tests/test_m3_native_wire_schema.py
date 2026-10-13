"""Native strict-output framing; original accepted M2 validation remains required."""
from copy import deepcopy
import json
import base64
import pytest
from jsonschema import Draft202012Validator
from intentlineage import experiment_chatgpt as m
from intentlineage.review_contract import REPLY_SCHEMA,build_request,canonical_bytes,validate_reply


def reply():
 return {'assessments':[],'no_relevant_element':True,'uncovered_elements':[],
         'unresolved_questions':[],'requested_openings':[]}


def test_closed_string_envelope_avoids_unsupported_provider_schema_and_preserves_prompt():
 request=build_request({'elements':[]},model='gpt-5.5',settings={'reasoning_effort':'low'})
 original=deepcopy(request)
 turn=m.chatgpt_rpc_requests(request,thread_id='fresh')[5]['params']
 schema=m.chatgpt_wire_schema()
 assert turn['outputSchema']==schema and schema!=REPLY_SCHEMA
 assert schema['type']=='object' and schema['additionalProperties'] is False
 assert schema['required']==['reply_json'] and set(schema['properties'])=={'reply_json'}
 assert schema['properties']['reply_json']['type']=='string'
 assert turn['input']==[{'type':'text','text':canonical_bytes(original).decode()}]
 assert request==original and request['response_schema']==REPLY_SCHEMA
 assert m.chatgpt_rpc_requests(request,thread_id='fresh')[4]['params']['developerInstructions']==m.WIRE_PACKAGING_INSTRUCTIONS
 assert 'reply_json' in m.WIRE_PACKAGING_INSTRUCTIONS
 assert not list(Draft202012Validator(schema).iter_errors({'reply_json':json.dumps(reply())}))


@pytest.mark.parametrize('value',[None,True,12,12.5,'plain "quoted" text',[1,{'nested':[False,None]}],{'amount':12,'items':[1,2]}])
def test_wire_preserves_all_typed_citation_values_for_original_m2(value):
 evidence={'elements':[{'element_id':'e1'}], 'job_inputs':[{'artifact_ref':'input','value':value}]}
 inner=reply();inner['no_relevant_element']=False
 inner['assessments']=[{'element_id':'e1','relevance':'relevant','assessment':'supported','uncertainty':'bounded',
                      'citations':[{'evidence_id':'input','pointer':'/value','observed':value}]}]
 text=json.dumps(inner,ensure_ascii=False)
 wire=json.dumps({'reply_json':text},ensure_ascii=False)
 assert m.decode_chatgpt_wire_reply(wire)==text
 assert validate_reply(m.decode_chatgpt_wire_reply(wire),evidence)==inner


@pytest.mark.parametrize('wire', ['{}','{"reply_json":{}}','{"reply_json":"{}","extra":1}',
    '{"reply_json":"{}","reply_json":"{}"}', '{"reply_json":"{bad"}', '{"reply_json":"{\"x\":NaN}"}'])
def test_wire_rejects_invalid_extra_duplicate_or_non_json_transport(wire):
 with pytest.raises(ValueError):validate_reply(m.decode_chatgpt_wire_reply(wire),{'elements':[]})


def test_original_m2_duplicate_coverage_and_citation_validation_are_not_relaxed():
 evidence={'elements':[{'element_id':'e1'}]}
 inner=reply();inner['uncovered_elements']=['e1','e1']
 decoded=m.decode_chatgpt_wire_reply(json.dumps({'reply_json':json.dumps(inner)}))
 with pytest.raises(ValueError):validate_reply(decoded,evidence)


def native_records(wire):
 request=build_request({'elements':[]},model='gpt-5.5',settings={'reasoning_effort':'low'})
 commands=m.chatgpt_rpc_requests(request,thread_id='new-thread')
 records=[{'id':2,'result':{'account':{'type':'chatgpt'}}},
  {'id':3,'result':{'data':[{'model':'gpt-5.5'}]}},
  {'id':4,'result':{'thread':{'id':'new-thread','turns':[],'ephemeral':True},'model':'gpt-5.5','modelProvider':'openai','reasoningEffort':'low'}},
  {'id':5,'result':{'turn':{'id':'new-turn','status':'inProgress'}}},
  {'method':'turn/started','params':{'threadId':'new-thread','turn':{'id':'new-turn'}}},
  {'method':'item/completed','params':{'threadId':'new-thread','turnId':'new-turn','item':{'type':'agentMessage','phase':'final_answer','text':wire}}},
  {'method':'turn/completed','params':{'threadId':'new-thread','turn':{'id':'new-turn','status':'completed','error':None}}}]
 return request,commands,b'\n'.join(canonical_bytes(e) for e in records)+b'\n'


def test_native_replay_binds_exact_wire_then_validates_original_m2():
 wire=json.dumps({'reply_json':json.dumps(reply())})
 request,commands,events=native_records(wire)
 observed=m.chatgpt_event_facts(events,commands,request,wire,exit_code=0)
 assert observed['complete'],observed['errors']
 assert observed['decoded_m2_reply_sha256']==m.digest(reply())
 assert observed['native_wire_schema_sha256']==m.digest(m.chatgpt_wire_schema())


def test_native_replay_refuses_old_schema_even_for_valid_wire_reply():
 wire=json.dumps({'reply_json':json.dumps(reply())})
 request,commands,events=native_records(wire)
 commands[5]['params']['outputSchema']=deepcopy(REPLY_SCHEMA)
 observed=m.chatgpt_event_facts(events,commands,request,wire,exit_code=0)
 assert not observed['complete'] and 'Own prompt/schema binding differs' in observed['errors']


@pytest.mark.parametrize('inner',['{bad','{}','[]',json.dumps(json.dumps(reply())),
    '{"assessments":[],"assessments":[],"no_relevant_element":true,"uncovered_elements":[],"unresolved_questions":[],"requested_openings":[]}',
    '{"assessments":[],"no_relevant_element":true,"uncovered_elements":[],"unresolved_questions":[],"requested_openings":[],"unexpected":1e999}'])
def test_inner_reply_is_not_repaired_or_recursively_decoded(inner):
 wire=json.dumps({'reply_json':inner})
 request,commands,events=native_records(wire)
 observed=m.chatgpt_event_facts(events,commands,request,wire,exit_code=0)
 assert not observed['complete']


@pytest.mark.parametrize('change',['native_text','packaging','prompt'])
def test_raw_message_packaging_and_own_evidence_are_exactly_bound(change):
 wire=json.dumps({'reply_json':json.dumps(reply())})
 request,commands,events=native_records(wire)
 if change=='native_text':wire+=' '
 elif change=='packaging':commands[4]['params']['developerInstructions']='alter assessment'
 else:commands[5]['params']['input'][0]['text']='different evidence'
 assert not m.chatgpt_event_facts(events,commands,request,wire,exit_code=0)['complete']


def fixture_call(tmp_path):
 """Recorded parser fixture only; dummy runtime cannot qualify any provider."""
 wire=json.dumps({'reply_json':json.dumps(reply(),indent=2)})
 request,commands,events=native_records(wire)
 output=tmp_path/'output';controller=tmp_path/'.controller';evidence=tmp_path/'evidence'
 output.mkdir();controller.mkdir();evidence.mkdir()
 (evidence/'request.json').write_bytes(canonical_bytes(request))
 limits={'max_input_bytes':300000,'max_output_bytes':1048576,'max_input_tokens':196608,
         'max_output_tokens':8192,'max_seconds_per_invocation':300,'qualification_max_calls':2}
 worker=m.chatgpt_worker_source(request,metadata_only=False,timeout_seconds=300,max_output_bytes=1048576)
 (controller/'chatgpt-worker.py').write_bytes(worker.encode())
 runtime={'scope':'recorded parser fixture, deliberately not real runtime identity'}
 raw={'runtime':runtime,'cli':{'native_elf':True,'binary_sha256':'a'*64},'result':{'transport':{
     'stdout_base64':base64.b64encode(events).decode(),'stderr_base64':''}}}
 (controller/'raw-client-launch.json').write_bytes(canonical_bytes(raw))
 (output/'stdout.bin').write_bytes(events);(output/'stderr.bin').write_bytes(b'')
 (output/'events.jsonl').write_bytes(events);(output/'stderr.txt').write_bytes(b'')
 (output/'client-requests.json').write_bytes(canonical_bytes(commands))
 (output/'reply.json').write_bytes(wire.encode())
 (output/'decoded-m2-reply.json').write_bytes(json.dumps(reply(),indent=2).encode())
 (output/'real-transport-response.json').write_bytes(canonical_bytes({'raw_reply':json.dumps(reply(),indent=2),'native_wire_reply':wire}))
 from intentlineage.experiment_execution import controller_source_digest
 launch={'authentication':'chatgpt','provider_kind':'actual-chatgpt-codex','data_class':'empirical',
  'request_sha256':m.digest(request),'model':request['model'],'settings':request['settings'],
  'limits':limits,'controller_source_sha256':controller_source_digest(),'raw_events':raw,
  'worker_source_sha256':m.file_hash(controller/'chatgpt-worker.py'),'native_cli_sha256':'a'*64,
  'runtime':runtime,'exit_code':0,'timed_out':False,'logical_turns_submitted':1,'provider_call_id':'parser-fixture'}
 return request,launch,limits


@pytest.mark.parametrize('change',['decoded','response','missing_decoded','raw_wire'])
def test_replay_refuses_tampered_raw_to_decoded_relationship(tmp_path,change):
 request,launch,limits=fixture_call(tmp_path)
 output=tmp_path/'output'
 if change=='decoded':(output/'decoded-m2-reply.json').write_bytes(b'{}')
 elif change=='response':(output/'real-transport-response.json').write_bytes(canonical_bytes({'raw_reply':'{}'}))
 elif change=='missing_decoded':(output/'decoded-m2-reply.json').unlink()
 else:(output/'reply.json').write_bytes((output/'reply.json').read_bytes()+b' ')
 with pytest.raises(ValueError):m.validate_chatgpt_call_files(tmp_path,request,launch,limits=limits)


def test_replay_accepts_bound_wire_and_exact_decoded_original_json(tmp_path):
 request,launch,limits=fixture_call(tmp_path)
 result=m.validate_chatgpt_call_files(tmp_path,request,launch,limits=limits)
 assert result['complete'] and result['charging']=='unknown_or_charged'


def test_invalid_inner_reply_retains_decoded_text_and_observed_failed_call_costs(tmp_path):
 request,launch,limits=fixture_call(tmp_path)
 output=tmp_path/'output';(output/'decoded-m2-reply.json').unlink();(output/'real-transport-response.json').unlink()
 wire=json.dumps({'reply_json':'{bad inner JSON'})
 request,commands,events=native_records(wire)
 records=[json.loads(line) for line in events.splitlines()]
 records.insert(-1,{'method':'thread/tokenUsage/updated','params':{'threadId':'new-thread','turnId':'new-turn',
                  'tokenUsage':{'last':{'inputTokens':12,'outputTokens':7,'totalTokens':19}}}})
 events=b'\n'.join(canonical_bytes(e) for e in records)+b'\n'
 (output/'reply.json').write_bytes(wire.encode());(output/'stdout.bin').write_bytes(events);(output/'events.jsonl').write_bytes(events)
 launch['raw_events']['result']['transport']['stdout_base64']=base64.b64encode(events).decode()
 (tmp_path/'.controller/raw-client-launch.json').write_bytes(canonical_bytes(launch['raw_events']))
 response=m.collect_chatgpt_response(tmp_path,request,launch=launch,protocol={'limits':limits},qualification_only=True)
 assert response['failure'] and response['charging']=='unknown_or_charged'
 assert response['usage']['input_tokens']==12 and response['usage']['output_tokens']==7
 assert response['raw_reply']=='{bad inner JSON' and response['native_wire_reply']==wire
 assert (output/'decoded-m2-reply.json').read_bytes()==b'{bad inner JSON'
 assert (output/'reply.json').read_bytes()==wire.encode()


def test_collector_preserves_whitespace_and_replays_after_relocation(tmp_path):
 import shutil
 (tmp_path/'original').mkdir()
 request,launch,limits=fixture_call(tmp_path/'original')
 output=tmp_path/'original/output'
 (output/'decoded-m2-reply.json').unlink();(output/'real-transport-response.json').unlink()
 inner='\r\n'+json.dumps(reply(),indent=2)+'\r\n'
 wire=json.dumps({'reply_json':inner})
 _,commands,events=native_records(wire)
 (output/'reply.json').write_bytes(wire.encode());(output/'stdout.bin').write_bytes(events);(output/'events.jsonl').write_bytes(events)
 launch['raw_events']['result']['transport']['stdout_base64']=base64.b64encode(events).decode()
 (tmp_path/'original/.controller/raw-client-launch.json').write_bytes(canonical_bytes(launch['raw_events']))
 response=m.collect_chatgpt_response(tmp_path/'original',request,launch=launch,protocol={'limits':limits},qualification_only=True)
 assert response['raw_reply']==inner and (output/'decoded-m2-reply.json').read_bytes()==inner.encode()
 assert response.get('failure') is None
 shutil.copytree(tmp_path/'original',tmp_path/'relocated')
 assert m.validate_chatgpt_call_files(tmp_path/'relocated',request,launch,limits=limits)['complete']


@pytest.mark.parametrize('observed',['NaN','Infinity','-Infinity','1e999'])
def test_valid_m2_shape_cannot_hide_nonfinite_typed_citation_values(observed):
 evidence={'elements':[{'element_id':'e1'}], 'job_inputs':[{'artifact_ref':'input','value':1}]}
 inner=reply();inner['no_relevant_element']=False
 inner['assessments']=[{'element_id':'e1','relevance':'relevant','assessment':'supported','uncertainty':'bounded',
                      'citations':[{'evidence_id':'input','pointer':'/value','observed':'nonfinite-placeholder'}]}]
 text=json.dumps(inner).replace('"nonfinite-placeholder"',observed)
 wire=json.dumps({'reply_json':text})
 request,_,_=native_records(wire)
 request['evidence']=evidence
 commands=m.chatgpt_rpc_requests(request,thread_id='new-thread')
 _,_,events=native_records(wire)
 assert not m.chatgpt_event_facts(events,commands,request,wire,exit_code=0)['complete']
