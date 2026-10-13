"""Reuse legacy synthetic inputs while keeping semantic inventory out of values."""
from .prompt_runtime import make_prompt_fixture


def ordinary_fixture(runtime, seed=17):
    fixture = make_prompt_fixture(runtime, seed)
    invoice = {k: v for k, v in fixture['invoice'].items()
               if k not in {'required_constraints', 'element_representations', 'ontology_assertions'}}
    return {'invoice': invoice, 'purchase_order': fixture.get('purchase_order'),
            'supplier_registry': fixture.get('supplier_registry'),
            'approval_policy_version': fixture['approval_policy_version']}
