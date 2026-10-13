"""Allowlisted observable prompt/capture view; no private case annotations."""
import json
from pathlib import Path

from .capture import load_capture
from .extraction import ROOT
from .payloads import validate_bundle
from .prompt_compiler import validate_compiled


def observation_view(bundle_path):
    bundle = validate_bundle(bundle_path, workspace_root=ROOT)
    candidates = [key for key in bundle['source_hashes'] if key.endswith('/runtime.json')]
    if len(candidates) != 1:
        raise ValueError('Prompt bundle needs one runtime source')
    source = candidates[0]
    runtime_path = ROOT/bundle.get('source_snapshots', {}).get(source, {}).get('file', source)
    runtime = json.loads(runtime_path.read_bytes())
    spec = validate_compiled(runtime['specification'])
    payload = json.loads((ROOT/bundle['payload_file']).read_bytes())
    capture = load_capture(ROOT/bundle['scan_file'])
    columns = {'payment_id', 'invoice_id', 'stage', 'amount', 'currency', 'supplier_id', 'account_id',
               'purchase_order_id', 'revision', 'approval', 'execution_receipt', 'reconciliation',
               'po_checked', 'supplier_checked', 'order_amount', 'order_currency', 'registry_account_id',
               'required_constraints', 'element_representations', 'ontology_assertions'}
    states = [{'name': state['name'], 'etiq_node_ids': state['etiq_node_ids'],
               'observed': {key: value for key, value in payload['states'][state['name']].items() if key in columns}}
              for state in bundle['states']]
    return {'format_version': '2.0.0', 'prompt': spec['prompt'], 'elements': spec['elements'],
            'states': states, 'causal_edges': list(capture.causal_edges), 'observation': bundle['observation'],
            'limits': ['Allowlisted observations only; candidate labels and injection programs are excluded.',
                       'Source code and original native artifacts remain separate audit evidence.']}
