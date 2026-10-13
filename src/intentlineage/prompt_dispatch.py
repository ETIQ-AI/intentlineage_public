"""Validated bounded dispatch preparation, outside the selected Etiq entry."""
import argparse
import hashlib
import json
from pathlib import Path

from .compiler import digest, write_json
from .contracts import PaymentRevision
from .extraction import ROOT, ROLES, replay_extraction
from .prompt_compiler import COMPILER_VERSION, OPERATIONALIZATION_VERSION, compile_prompt, validate_compiled


def _check_model_logs(packet):
    logs = packet['provenance'].get('raw_logs', [])
    if packet['provenance'].get('evidence_kind') != 'local_llm_extraction' or len(logs) != 1:
        raise ValueError('Dispatch requires an actual single-pass local extraction')
    request = json.loads((ROOT/logs[0]['request_file']).read_bytes())
    response = json.loads((ROOT/logs[0]['response_file']).read_bytes())
    if not request['prompt'].endswith('Q: '+packet['prompt']['text']+'\nA: '):
        raise ValueError('Raw model request differs from the compiled source')
    items = json.loads(response['response'])['extractions']
    raw = packet['raw_result']['extractions']
    if len(items) != len(raw):
        raise ValueError('Raw model output count differs from aligned extraction')
    for item, aligned in zip(items, raw):
        role = aligned['extraction_class']
        if role not in ROLES or item.get(role) != aligned['extraction_text'] or (item.get(role+'_attributes') or {}) != (aligned.get('attributes') or {}):
            raise ValueError('Aligned extraction differs from raw model output')


def prepare_dispatch(extraction_path, compiled_path=None):
    path = Path(extraction_path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Extraction input must be inside workspace')
    taxonomy = json.loads((ROOT/'resources/ontology/generated/taxonomy-v2.json').read_bytes())
    packet = replay_extraction(path, taxonomy, current=True)
    _check_model_logs(packet)
    for record in packet['provenance'].get('source_snapshots', {}).values():
        snapshot = (ROOT/record['file']).resolve()
        if not snapshot.is_relative_to(ROOT) or hashlib.sha256(snapshot.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Extraction source snapshot hash mismatch')
    # Consume registered revisions rather than resetting every rule to revision 1.
    if compiled_path is None:
        matches = [p for p in (ROOT/'specifications/generated/prompts').glob('*.json') if p.stem == packet['prompt']['source_id']]
        compiled_path = matches[0] if matches else None
    if compiled_path is not None:
        compiled_path = Path(compiled_path).resolve()
        if not compiled_path.is_relative_to(ROOT):
            raise ValueError('Compiled specification input must be inside workspace')
        spec = validate_compiled(json.loads(compiled_path.read_bytes()))
        if spec['compiler_version'] != COMPILER_VERSION or spec['provenance'].get('operationalization_version') != OPERATIONALIZATION_VERSION:
            raise ValueError('Stale compiled specification: regenerate with current versions')
        if compile_prompt(packet, taxonomy, spec) != spec:
            raise ValueError('Current compiled specification differs from extraction replay')
    else:
        spec = compile_prompt(packet, taxonomy)
    reasons, values = [], {}
    if spec['status'] == 'conflicted': reasons.append('conflicting_requirements')
    if spec['rejected_records']: reasons.append('rejected_model_records')
    if spec['diagnostics']: reasons.append('unresolved_compiler_diagnostics')
    if any(e['grounding']['status'] == 'ambiguous' for e in spec['elements']): reasons.append('ambiguous_ontology_binding')
    atoms = [e for e in spec['elements'] if e['kind'] == 'intent']
    goals = [e['meaning'] for e in atoms if e['role'] == 'goal' and not e['meaning']['negated']]
    actions = [g['action'] for g in goals]
    operation = actions[0] if len(actions) == 1 and actions[0] in {'pay', 'draft'} else 'abstain'
    if operation == 'abstain': reasons.append('unsupported_or_multiple_goals')
    if spec['conditions']: reasons.append('conditional_scope_not_supported_by_dispatcher')
    for element in atoms:
        if element['role'] == 'parameter': values[element['meaning']['field']] = element['meaning']['value']
    if operation == 'pay':
        missing = sorted({'invoice_id', 'amount', 'currency', 'supplier_id', 'account_id', 'purchase_order_id'}-values.keys())
        if missing: reasons.append('missing_parameters:'+','.join(missing))
        else:
            try:
                revision = int(values.get('revision', '1'))
                PaymentRevision.model_validate({**values, 'payment_id': 'validation-only', 'revision': revision})
            except ValueError:
                reasons.append('invalid_payment_values')
    elif operation == 'draft' and not values.get('invoice_id'):
        reasons.append('draft_requires_invoice_id')
    if reasons: operation = 'abstain'
    sources = [path.relative_to(ROOT).as_posix(), 'src/intentlineage/prompt_dispatch.py',
               'src/intentlineage/prompt_compiler.py', 'src/intentlineage/extraction.py',
               'src/intentlineage/source_scope.py',
               'src/intentlineage/taxonomy.py', 'src/intentlineage/contracts.py', 'src/intentlineage/compiler.py',
               'resources/ontology/generated/taxonomy-v2.json', 'resources/extraction/model-v2.json',
               'resources/extraction/instructions-v2.txt', 'resources/extraction/examples-v2.json']
    for log in packet['provenance']['raw_logs']:
        sources.extend([log['request_file'], log['response_file']])
    if compiled_path is not None:
        sources.append(compiled_path.relative_to(ROOT).as_posix())
    runtime = {'format_version': '2.0.0', 'operation': operation, 'reasons': reasons,
               'values': values, 'specification': spec,
               'input_sources': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
               'mechanics_provenance': {'initial_revision_default': 1, 'approval_policy_version': '1.0.0',
                    'role': 'synthetic_runtime_mechanics', 'requirements_inferred_from_mechanics': False}}
    runtime['integrity_sha256'] = digest(runtime)
    return runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiled', type=Path, help='Exact current versioned specification; otherwise use the registered source')
    args = parser.parse_args()
    runtime = prepare_dispatch(args.input, compiled_path=args.compiled)
    write_json(args.output, runtime)
    print(runtime['operation'], ','.join(runtime['reasons']))


if __name__ == '__main__':
    main()
