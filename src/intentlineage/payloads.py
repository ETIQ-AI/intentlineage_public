"""Read-only association of runtime payloads with original capture evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from .capture import load_capture
from .compiler import write_json


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_bundle(bundle_path, *, workspace_root):
    bundle = json.loads(Path(bundle_path).read_text(encoding='utf-8'))
    root = Path(workspace_root).resolve()
    def contained(relative):
        path = (root/relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Bundle reference escapes workspace')
        return path
    scan_path = contained(bundle['scan_file'])
    capture = load_capture(scan_path)
    for key in ('scan', 'lineage', 'payload'):
        if file_hash(contained(bundle[f'{key}_file'])) != bundle[f'{key}_sha256']:
            raise ValueError(f'Bundle artifact hash mismatch: {key}')
    if (scan_path.parent/capture.scan['lineage_path']).resolve() != contained(bundle['lineage_file']):
        raise ValueError('Bundle references a different lineage artifact')
    payload = json.loads(contained(bundle['payload_file']).read_text(encoding='utf-8'))
    if payload['execution_id'] != bundle['execution_id'] or payload['sources'] != bundle['source_hashes']:
        raise ValueError('Bundle and payload provenance differ')
    snapshots = bundle.get('source_snapshots', {})
    for relative, expected in bundle['source_hashes'].items():
        record = snapshots.get(relative)
        path = contained(record['file']) if record else contained(relative)
        if record and record['sha256'] != expected or file_hash(path) != expected:
            raise ValueError(f'Bundle source hash mismatch: {relative}')
    if capture.scan['entry_file_hash'] != payload['sources'][capture.scan['entry_file_path']]:
        raise ValueError('Bundle entry provenance differs from capture')
    for state in bundle['states']:
        if state['name'] not in payload['states'] or any(node_id not in capture.nodes_by_id for node_id in state['etiq_node_ids']):
            raise ValueError('Bundle references an absent payload or native node')
        if not state['etiq_node_ids'] or any(capture.nodes_by_id[node_id].get('label', '').rstrip('`') != state['name'] for node_id in state['etiq_node_ids']):
            raise ValueError('Bundle node identifiers do not match the captured state name')
        original = [item for item in capture.scan['source_evidence'] if state['name'] in item['names']]
        if not original or state['source_evidence'] != original:
            raise ValueError('Bundle source evidence differs from raw capture')
    return bundle


def validate_payloads(payload_path, *, workspace_root, execution_id):
    payload = json.loads(Path(payload_path).read_text(encoding='utf-8'))
    root = Path(workspace_root).resolve()
    if payload.get('execution_id') != execution_id:
        raise ValueError('Payload execution ID does not match the invocation')
    if payload.get('format_version') != '1.0.0' or payload.get('evidence_kind') != 'executed_synthetic_runtime_snapshot':
        raise ValueError('Unsupported runtime payload format')
    sources = payload.get('sources')
    if not isinstance(sources, dict) or payload.get('entry') not in sources:
        raise ValueError('Payload lacks selected entry source provenance')
    for relative, expected in sources.items():
        path = (root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or file_hash(path) != expected:
            raise ValueError(f'Payload source hash mismatch: {relative}')
    if not isinstance(payload.get('states'), dict) or not payload['states']:
        raise ValueError('Payload states are required')
    return payload


def bind_capture(scan_path, payload_path, *, workspace_root, execution_id):
    # Scan status/errors are inspected before either lineage or payloads.
    capture = load_capture(scan_path, workspace_root=workspace_root)
    payload = validate_payloads(payload_path, workspace_root=workspace_root, execution_id=execution_id)
    root = Path(workspace_root).resolve()
    scan_path, payload_path = Path(scan_path).resolve(), Path(payload_path).resolve()
    if not payload_path.is_relative_to(root):
        raise ValueError('Capture payload must be inside the workspace')
    if capture.scan['entry_file_path'] != payload['entry'] or capture.scan['entry_file_hash'] != payload['sources'][payload['entry']]:
        raise ValueError('Payload and scan selected different entry sources')
    names = set(capture.scan['captured_objects']['dataframes'])
    states = []
    for name, row in payload['states'].items():
        ids = [node_id for node_id, node in capture.nodes_by_id.items() if node.get('label', '').rstrip('`') == name]
        evidence = [item for item in capture.scan['source_evidence'] if name in item['names']]
        if name not in names or not ids or not evidence:
            raise ValueError(f'Runtime payload has no captured state/source: {name}')
        states.append({'state_id': f'urn:intentlineage:state:{execution_id}:{name}', 'name': name,
                       'stage': row['stage'], 'etiq_node_ids': ids, 'source_evidence': evidence})
    lineage_path = scan_path.parent/capture.scan['lineage_path']
    return {'format_version': '1.0.0', 'execution_id': execution_id,
            'observation': payload.get('observation', {'complete': True, 'omitted_states': []}),
            'scan_file': scan_path.relative_to(root).as_posix(), 'scan_sha256': file_hash(scan_path),
            'lineage_file': lineage_path.relative_to(root).as_posix(), 'lineage_sha256': file_hash(lineage_path),
            'payload_file': payload_path.relative_to(root).as_posix(), 'payload_sha256': file_hash(payload_path),
            'source_hashes': payload['sources'], 'states': states,
            'limits': ['Payload rows are explicit runtime snapshots, not native Etiq serialization.',
                       'Association records a same-invocation execution ID; raw Etiq graph does not encode that ID.',
                       'Etiq identifiers and edges remain original; no replacement execution graph.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan', type=Path, required=True)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--workspace-root', type=Path, default=Path('.'))
    parser.add_argument('--execution-id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--snapshot-sources', action='store_true')
    args = parser.parse_args()
    bundle = bind_capture(args.scan, args.payload, workspace_root=args.workspace_root, execution_id=args.execution_id)
    if args.snapshot_sources:
        snapshots = {}
        for relative, expected in bundle['source_hashes'].items():
            target = args.output.parent/'source-snapshot'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((args.workspace_root/relative).read_bytes())
            snapshots[relative] = {'file': target.resolve().relative_to(args.workspace_root.resolve()).as_posix(), 'sha256': expected}
        bundle['source_snapshots'] = snapshots
    write_json(args.output, bundle)
    print(f"Bound {len(bundle['states'])} runtime snapshots to completed capture")


if __name__ == '__main__':
    main()
