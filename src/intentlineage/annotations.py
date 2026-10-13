"""Private candidate oracle packet; never imported by the workflow/detectors."""
import argparse
import json
from pathlib import Path

from .compiler import write_json
from .payloads import file_hash, validate_bundle

CASE_IDS = ['nominal', 'amount_mutation', 'account_substitution', 'stale_approval',
            'wrong_po', 'constraint_drop', 'amount_repaired', 'account_repaired',
            'stale_approval_repaired', 'wrong_po_repaired', 'constraint_reintroduced',
            'benign_representation', 'observation_gap', 'unfinished_draft']


def oracle_for(case_id):
    if case_id not in CASE_IDS:
        raise ValueError('Unknown candidate annotation case')
    # This is the manual injection-design table, not a calculation over payloads.
    definitions = {
        'amount_mutation': ('amount_authority', 'routed_df', False),
        'amount_repaired': ('amount_authority', 'routed_df', True),
        'account_substitution': ('account_authority', 'routed_df', False),
        'account_repaired': ('account_authority', 'routed_df', True),
        'stale_approval': ('approval_binding', 'approved_df', False),
        'stale_approval_repaired': ('approval_binding', 'approved_df', True),
        'wrong_po': ('purchase_order', 'routed_df', False),
        'wrong_po_repaired': ('purchase_order', 'routed_df', True),
        'constraint_drop': ('constraint_carriage', 'routed_df', False),
        'constraint_reintroduced': ('constraint_carriage', 'routed_df', True),
    }
    result = {'case_id': case_id, 'annotation_basis': 'manual_injection_design',
              'review_status': 'pending_overseer_review', 'reviewer': None,
              'injected_state': None, 'primary_element_id': None, 'first_sufficient_state': None,
              'affected_transitions': [], 'restored_state': None, 'expected_trace_outcome': 'satisfied',
              'expected_final_outcome': 'satisfied', 'observation_limits': [],
              'label_scope': 'Primary injected rule only; other rule/intent consequences require review.'}
    if case_id in definitions:
        element, first, repaired = definitions[case_id]
        result['injected_state'] = first
        result['first_sufficient_state'] = first
        result['primary_element_id'] = 'urn:intentlineage:element:payment-policy:' + element
        result['restored_state'] = 'ready_df' if repaired else None
        result['expected_trace_outcome'] = 'contains_repaired_violation' if repaired else 'violated'
        result['expected_final_outcome'] = 'satisfied' if repaired else 'violated'
        transitions = [('joined_df', 'routed_df'), ('routed_df', 'approved_df'), ('approved_df', 'ready_df'), ('ready_df', 'execution_df'), ('execution_df', 'reconciled_df')]
        if first == 'approved_df':
            transitions = transitions[1:]
        if repaired:
            transitions = transitions[:2] if first == 'approved_df' else transitions[:3]
        for source, target in transitions:
            label = 'restored' if target == result['restored_state'] else 'violated'
            if case_id == 'constraint_reintroduced' and target == 'ready_df':
                label = 'reintroduced_and_restored'
            result['affected_transitions'].append({'from': source, 'to': target, 'expected': label})
    elif case_id == 'observation_gap':
        result['expected_trace_outcome'] = 'unknown'
        result['observation_limits'] = ['routed_df payload deliberately omitted; trace coverage is unknown although the observed final state remains satisfactory.']
        result['affected_transitions'] = [{'from': 'joined_df', 'to': 'routed_df', 'expected': 'unknown'}, {'from': 'routed_df', 'to': 'approved_df', 'expected': 'unknown'}]
    elif case_id == 'unfinished_draft':
        result['expected_trace_outcome'] = result['expected_final_outcome'] = 'not_applicable'
        result['observation_limits'] = ['Workflow intentionally ends at draft; listed business rules do not apply there.']
    elif case_id == 'benign_representation':
        result['affected_transitions'] = [{'from': 'joined_df', 'to': 'routed_df', 'expected': 'transformed_preserving_semantics'}]
    return result


def build_packet(capture_root, workspace_root, output_path):
    root, workspace = Path(capture_root).resolve(), Path(workspace_root).resolve()
    runs, annotations = [], []
    for index, case_id in enumerate(CASE_IDS):
        execution_id = f'm1-trace-{index:02d}'
        bundle_path = root/execution_id/'bundle.json'
        bundle = validate_bundle(bundle_path, workspace_root=workspace)
        if bundle['execution_id'] != execution_id:
            raise ValueError('Capture case index does not match its execution ID')
        record = {'execution_id': execution_id, 'bundle_file': bundle_path.relative_to(workspace).as_posix(), 'bundle_sha256': file_hash(bundle_path)}
        runs.append(record)
        oracle = oracle_for(case_id)
        oracle.update(record)
        by_name = {state['name']: state for state in bundle['states']}
        oracle['injection_source'] = by_name[oracle['injected_state']]['source_evidence'] if oracle['injected_state'] else None
        oracle['first_sufficient_ref'] = by_name[oracle['first_sufficient_state']] if oracle['first_sufficient_state'] else None
        oracle['restored_ref'] = by_name[oracle['restored_state']] if oracle['restored_state'] else None
        annotations.append(oracle)
    write_json(root/'index.json', {'format_version': '1.0.0', 'seed': 17, 'runs': runs,
                                 'evidence_kind': 'real_shared_wrapper_capture_with_runtime_snapshots'})
    write_json(output_path, {'format_version': '1.0.0', 'review_status': 'pending_overseer_review',
                            'reviewer': None, 'reviewed_at': None, 'annotation_method': 'Manual table from controlled injection design; no verifier or model generated labels.',
                            'specification_file': 'specifications/generated/payment-spec.json',
                            'specification_sha256': file_hash(workspace/'specifications/generated/payment-spec.json'),
                            'annotations': annotations})
    return len(runs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-cases', type=Path)
    parser.add_argument('--capture-root', type=Path)
    parser.add_argument('--workspace-root', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.write_cases:
        write_json(args.write_cases, [{'case_id': case, 'execution_id': f'm1-trace-{index:02d}'} for index, case in enumerate(CASE_IDS)])
    elif args.capture_root and args.output:
        if args.output.exists():
            raise ValueError('Keep existing review evidence; select a fresh oracle output path')
        print(f'Saved {build_packet(args.capture_root, args.workspace_root, args.output)} candidate annotations for overseer review')
    else:
        parser.error('Supply --write-cases or --capture-root and --output')


if __name__ == '__main__':
    main()
