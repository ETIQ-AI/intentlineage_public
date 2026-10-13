"""Stdlib runtime mechanics; no compiler, scanner or private oracle imports."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import uuid

from .payment import ROOT, WorkflowRun, write_json
from .changes import SCENARIOS, routing_values

ENTRY = 'examples/prompt_payment_workflow.py'
EXTRA_SCENARIOS = ('intent_drop', 'intent_reintroduced', 'ontology_association_change',
                   'ontology_association_repaired', 'ontology_missing_witness')
PROMPT_SCENARIOS = SCENARIOS+EXTRA_SCENARIOS
REPRESENTATION_REPAIRS = ('intent_reintroduced', 'ontology_association_repaired')


def route_prompt_values(row, scenario):
    values = routing_values(row, 'nominal' if scenario in EXTRA_SCENARIOS else scenario)
    if scenario == 'benign_representation':
        expanded = format(Decimal(row['amount']), 'f')
        values['amount'] = expanded+('0' if '.' in expanded else '.0')
    return values


def validate_runtime(runtime):
    data = dict(runtime)
    expected = data.pop('integrity_sha256', None)
    actual = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    if expected != actual:
        raise ValueError('Runtime integrity mismatch')
    if runtime['operation'] not in {'pay', 'draft'}:
        raise ValueError('Dispatcher abstains: '+','.join(runtime['reasons']))
    return runtime


def make_prompt_fixture(runtime, seed):
    validate_runtime(runtime)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('Seed must be a nonnegative integer')
    invoice = dict(runtime['values'])
    invoice['payment_id'] = 'P-'+f'{random.Random(seed).getrandbits(32):08x}'
    invoice['revision'] = int(invoice.get('revision', 1))
    constraints = []
    for element in runtime['specification']['elements']:
        if element['kind'] == 'rule':
            constraints.append('approval_binding' if element['operator'] == 'bind' else element['element_id'])
    invoice['required_constraints'] = json.dumps(constraints)
    invoice['element_representations'] = json.dumps(runtime['specification']['elements'], sort_keys=True)
    invoice['ontology_assertions'] = '[]'
    fixture = {'invoice': invoice, 'constraints': constraints,
               'approval_policy_version': runtime['mechanics_provenance']['approval_policy_version'],
               'specification': runtime['specification']}
    if runtime['operation'] == 'pay':
        fixture['purchase_order'] = {'purchase_order_id': invoice['purchase_order_id'], 'order_amount': invoice['amount'], 'order_currency': invoice['currency']}
        fixture['supplier_registry'] = {'supplier_id': invoice['supplier_id'], 'registry_account_id': invoice['account_id']}
    return fixture


def relation_witness(row, fixture):
    rule = next(e for e in fixture['specification']['elements'] if e['operator'] == 'exists_typed_relation')
    params = rule['parameters']
    return json.dumps([{'subject': row['payment_id'], 'subject_types': [params['subject_class']],
                       'predicate': params['property'], 'object': row['payment_id']+':amount',
                       'object_types': [params['target_class']], 'value': row['amount'], 'currency': row['currency']}], sort_keys=True)


def routed_representations(row, scenario):
    elements = json.loads(row['element_representations'])
    if scenario in {'constraint_drop', 'constraint_reintroduced'}:
        bind = [e for e in elements if e['operator'] == 'bind']
        removed = set()
        for e in bind:
            removed.add(e['element_id'])
            removed.update(e['supporting_elements'])
        elements = [e for e in elements if e['element_id'] not in removed]
    elif scenario in {'intent_drop', 'intent_reintroduced'}:
        elements = [e for e in elements if e['role'] != 'goal']
    elif scenario in {'ontology_association_change', 'ontology_association_repaired'}:
        for element in elements:
            if element['role'] == 'object':
                element['grounding'] = {'status': 'resolved', 'candidates': ['https://spec.edmcouncil.org/fibo/ontology/FND/ProductsAndServices/PaymentsAndSchedules/Payee']}
    return json.dumps(elements, sort_keys=True)


def finish_prompt_run(runtime, seed, fixture, frames, payload_dir=None, execution_id=None, observation=None, runtime_file=None):
    states = {}
    for name, frame in frames.items():
        rows = frame.to_dict(orient='records')
        if len(rows) != 1:
            raise ValueError('Prompt handoff requires exactly one invoice')
        states[name] = rows[0]
    observation = observation or {'complete': True, 'omitted_states': [], 'workflow_end': list(states.values())[-1]['stage']}
    for name in observation['omitted_states']: states.pop(name)
    if payload_dir:
        sources = dict(runtime['input_sources'])
        for relative in [ENTRY, 'src/intentlineage/prompt_runtime.py', 'src/intentlineage/payment.py', 'src/intentlineage/changes.py']:
            sources[relative] = hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
        if runtime_file:
            path = Path(runtime_file).resolve()
            if not path.is_relative_to(ROOT): raise ValueError('Runtime source escapes workspace')
            sources[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_json(Path(payload_dir)/'payloads.json', {'format_version': '1.0.0',
             'evidence_kind': 'executed_synthetic_runtime_snapshot', 'execution_id': execution_id or str(uuid.uuid4()),
             'seed': seed, 'entry': ENTRY, 'sources': sources, 'observation': observation, 'states': states})
    return WorkflowRun(seed=seed, fixture=fixture, states=states)
