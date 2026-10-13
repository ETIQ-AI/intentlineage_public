"""Synthetic fixture and handoff serialization; no scanner or semantic verifier."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import random
import uuid

AUTHORISED_FIELDS = ('payment_id', 'revision', 'amount', 'currency', 'supplier_id', 'account_id', 'purchase_order_id')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2)+'\n').encode('utf-8'))

ROOT = Path(__file__).resolve().parents[2]
ENTRY = 'examples/payment_workflow.py'
DEPENDENCIES = [ENTRY, 'src/intentlineage/payment.py', 'src/intentlineage/contracts.py',
                'src/intentlineage/changes.py', 'specifications/generated/payment-spec.json']


@dataclass(frozen=True)
class WorkflowRun:
    seed: int
    fixture: dict
    states: dict


def make_fixture(seed):
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('Seed must be a nonnegative integer')
    parameters = json.loads((ROOT/'specifications/generated/payment-spec.json').read_text(encoding='utf-8'))['payment_parameters']
    suffix = f'{random.Random(seed).getrandbits(32):08x}'
    invoice = {'payment_id': f'P-{suffix}', 'invoice_id': f'I-{suffix}', 'revision': parameters['initial_revision'],
               'amount': parameters['amount'], 'currency': parameters['currency'], 'supplier_id': f'S-{suffix}',
               'account_id': f'ACCOUNT-{suffix}', 'purchase_order_id': f'PO-{suffix}',
               'required_constraints': '[]'}
    return {'invoice': invoice,
            'purchase_order': {'purchase_order_id': invoice['purchase_order_id'], 'order_amount': invoice['amount'], 'order_currency': invoice['currency']},
            'supplier_registry': {'supplier_id': invoice['supplier_id'], 'registry_account_id': invoice['account_id']},
            'constraints': ['amount_authority', 'account_authority', 'purchase_order', 'approval_binding'],
            'approval_policy_version': parameters['approval_policy_version']}


def approval_for(row, policy_version):
    data = {}
    for field in AUTHORISED_FIELDS:
        data[field] = row[field]
    data['approval_id'] = f"AP-{row['payment_id']}-{row['revision']}"
    data['policy_version'] = policy_version
    return json.dumps(data, sort_keys=True)


def receipt_for(row):
    data = {}
    for field in sorted(AUTHORISED_FIELDS):
        data[field] = row[field]
    return json.dumps(data, sort_keys=True)


def reconciliation_for(row):
    receipt = json.loads(row['execution_receipt'])
    return 'matched' if all(row[field] == receipt[field] for field in AUTHORISED_FIELDS) else 'mismatched'


def finish_run(seed, fixture, frames, payload_dir=None, execution_id=None, observation=None):
    states = {}
    for name, frame in frames.items():
        rows = frame.to_dict(orient='records')
        if len(rows) != 1:
            raise ValueError('M1 handoff requires exactly one synthetic payment')
        states[name] = rows[0]
    observation = observation or {'complete': True, 'omitted_states': [], 'workflow_end': list(states.values())[-1]['stage']}
    for name in observation['omitted_states']:
        states.pop(name)
    result = WorkflowRun(seed=seed, fixture=fixture, states=states)
    if payload_dir:
        execution_id = execution_id or str(uuid.uuid4())
        source_hashes = {}
        for path in DEPENDENCIES:
            source_hashes[path] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        write_json(Path(payload_dir)/'payloads.json', {'format_version': '1.0.0',
                   'evidence_kind': 'executed_synthetic_runtime_snapshot', 'execution_id': execution_id,
                   'seed': seed, 'entry': ENTRY, 'sources': source_hashes, 'observation': observation, 'states': states})
    return result
