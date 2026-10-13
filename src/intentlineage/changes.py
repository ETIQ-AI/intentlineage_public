"""Deterministic simulation inputs; contains no detector or oracle labels."""
from decimal import Decimal
import json

SCENARIOS = ('nominal', 'amount_mutation', 'account_substitution', 'stale_approval',
             'wrong_po', 'constraint_drop', 'amount_repaired', 'account_repaired',
             'stale_approval_repaired', 'wrong_po_repaired', 'constraint_reintroduced',
             'benign_representation', 'observation_gap', 'unfinished_draft')
REPAIRS = ('amount_repaired', 'account_repaired', 'stale_approval_repaired',
           'wrong_po_repaired', 'constraint_reintroduced')


def routing_values(row, scenario):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown simulation input')
    values = row.copy()
    if scenario in ('amount_mutation', 'amount_repaired'):
        values['amount'] = str(Decimal(row['amount']) + Decimal('1.00'))
        values['revision'] += 1
    elif scenario in ('account_substitution', 'account_repaired'):
        values['account_id'] += '-ALT'
        values['revision'] += 1
    elif scenario in ('wrong_po', 'wrong_po_repaired'):
        values['purchase_order_id'] += '-OTHER'
        values['revision'] += 1
    elif scenario in ('constraint_drop', 'constraint_reintroduced'):
        constraints = json.loads(row['required_constraints'])
        constraints.remove('approval_binding')
        values['required_constraints'] = json.dumps(constraints)
    elif scenario == 'benign_representation':
        values['amount'] = row['amount'] + '0'
        constraints = json.loads(row['required_constraints'])
        constraints.reverse()
        values['required_constraints'] = json.dumps(constraints, separators=(',', ':'))
    return values


def approved_revision(row, scenario):
    return row['revision'] + 1 if scenario in ('stale_approval', 'stale_approval_repaired') else row['revision']


def ready_values(row, fixture, scenario):
    values = row.copy()
    if scenario in REPAIRS:
        for field in ('amount', 'currency', 'supplier_id', 'account_id', 'purchase_order_id'):
            values[field] = fixture['invoice'][field]
        values['required_constraints'] = json.dumps(fixture['constraints'])
        if scenario != 'constraint_reintroduced':
            values['revision'] += 1
    return values
