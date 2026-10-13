"""Ordinary payment values with actual native function input/output boundaries.

Matching, approval and receipt mechanics remain synthetic fixtures; no ontology
policy or intent/rule representation is injected into workflow output values.
"""
import json
import os
import pandas as pd

from intentlineage.native_workflow import ordinary_fixture
from intentlineage.payment import approval_for, receipt_for, reconciliation_for


def match_order(invoice, orders):
    matched = invoice.merge(orders, on='purchase_order_id', validate='one_to_one')
    if len(matched) != 1 or matched.iloc[0]['amount'] != matched.iloc[0]['order_amount'] or matched.iloc[0]['currency'] != matched.iloc[0]['order_currency']:
        raise ValueError('Synthetic purchase-order mismatch')
    return matched.assign(po_checked=True)


def validate_supplier(invoice, registry):
    validated = invoice.merge(registry, on='supplier_id', validate='one_to_one')
    if len(validated) != 1 or validated.iloc[0]['account_id'] != validated.iloc[0]['registry_account_id']:
        raise ValueError('Synthetic supplier-registry mismatch')
    return validated.assign(supplier_checked=True)


def join_branches(matched, validated):
    return matched.merge(validated[['payment_id', 'registry_account_id', 'supplier_checked']],
                         on='payment_id', validate='one_to_one')


def approve_payment(payment, policy):
    def approval_value(frame):
        row = frame.to_dict(orient='records')[0]
        return approval_for(row, policy)
    return payment.assign(approval=approval_value(payment))


def execute_payment(payment):
    row = payment.to_dict(orient='records')[0]
    receipt = receipt_for(row)
    return payment.assign(execution_receipt=receipt)


def reconcile_payment(payment):
    row = payment.to_dict(orient='records')[0]
    reconciliation = reconciliation_for(row)
    return payment.assign(reconciliation=reconciliation)


with open(os.environ['INTENTLINEAGE_PROMPT_RUNTIME'], encoding='utf-8') as stream:
    runtime = json.load(stream)
fixture = ordinary_fixture(runtime, int(os.environ.get('INTENTLINEAGE_SEED', '17')))
invoice_df = pd.DataFrame([fixture['invoice']])
if runtime['operation'] == 'draft':
    output_df = invoice_df.assign(status='draft')
else:
    orders_df = pd.DataFrame([fixture['purchase_order']])
    registry_df = pd.DataFrame([fixture['supplier_registry']])
    matched_df = match_order(invoice_df, orders_df)
    validated_df = validate_supplier(invoice_df, registry_df)
    joined_df = join_branches(matched_df, validated_df)
    approved_df = approve_payment(joined_df, fixture['approval_policy_version'])
    executed_df = execute_payment(approved_df)
    output_df = reconcile_payment(executed_df)
