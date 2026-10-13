"""Export live Etiq state values after the existing wrapper's single scan."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import uuid

from ._reference.native_graph import serialize_etiq_result
from .capture import load_capture, _contained_file

EXPORT_VERSION = '4.0.0'
ROOT = Path(__file__).resolve().parents[2]
ADAPTER_FILES = ('src/intentlineage/native_capture.py',
                 'src/intentlineage/_reference/native_graph.py',
                 'src/intentlineage/_reference/records.py',
                 'etiq_runner/wrapper.py', 'scripts/scan_entry.py')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_graph(graph):
    if not isinstance(graph, dict) or not isinstance(graph.get('objects'), list) or not isinstance(graph.get('edges'), list):
        raise ValueError('Native graph needs original objects and edges')
    nodes = {}
    for node in graph['objects']:
        if not isinstance(node, dict) or type(node.get('_gvid')) is not int or node['_gvid'] in nodes:
            raise ValueError('Native graph node identifiers must be unique integers')
        nodes[node['_gvid']] = node
    edge_ids = set()
    for edge in graph['edges']:
        if edge.get('tail') not in nodes or edge.get('head') not in nodes or edge.get('_gvid') in edge_ids:
            raise ValueError('Native edge references an absent node or duplicate edge')
        edge_ids.add(edge.get('_gvid'))
    groups = {i: n for i, n in nodes.items() if str(n.get('name', '')).startswith('cluster_')}
    def visit(i, active):
        if i in active:
            raise ValueError('Native cluster membership contains a cycle')
        for child in groups[i].get('nodes', []):
            if child not in nodes:
                raise ValueError('Native cluster references an absent member')
            if child in groups:
                visit(child, active | {i})
    for i in groups:
        visit(i, set())
    return nodes


def _finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _finite_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite_json(v) for v in value]
    return value


def serialize_capture(result, graph, *, run_id, entry_file_hash):
    """Adapt upstream native serializer, retaining the wrapper's exact JSON graph.

    State/function records complement the graph. Bind values only by raw native
    identifiers; labels and sidecar rows are never used to invent a value binding.
    """
    nodes = validate_graph(graph)
    try:
        snapshot = _finite_json(asdict(serialize_etiq_result(job_id='payment', run_id=run_id, result=result)))
    except RuntimeError as error:
        raise ValueError(str(error)) from error
    bindings = {}
    for state in snapshot['nodes']:
        raw = state['raw_id']
        try:
            raw_hex = uuid.UUID(raw).hex if raw is not None else None
        except (ValueError, AttributeError):
            raw_hex = raw
        matches = [i for i, n in nodes.items() if raw is not None and
                   (n.get('name') in {'node_' + raw, 'node_' + raw_hex, raw}
                    or str(n.get('name', '')).endswith(',' + raw))]
        bindings[state['node_ref']] = matches
        if state['artifact_kind'] == 'record' and isinstance(state['artifact_content'], str) and state['value_type'] != 'str':
            state['artifact_content'] = None
            state['artifact_status'] = 'unsupported'
        else:
            state['artifact_status'] = ('truncated' if state['artifact_truncated'] else
                                        'captured' if state['artifact_content'] is not None else 'unavailable')
    unmatched = sum(not v for v in bindings.values())
    limits = ['Only executed, Etiq-supported values are captured; absence is not inferred from a sidecar.',
              'Non-finite JSON numeric values are represented as null; statistics describe captured content.',
              'Reference previews/artifacts are bounded and redact sensitive field names.']
    if unmatched:
        limits.append(f'{unmatched} serialized records have no exact raw-ID binding in the native graph.')
    return {'format_version': EXPORT_VERSION, 'origin': 'etiq_live_result', 'run_id': run_id,
            'scan_count': 1, 'entry_file_hash': entry_file_hash,
            'graph': deepcopy(graph), 'graph_sha256': digest(graph),
            'serialized': snapshot, 'state_bindings': bindings,
            'adapter_sources': {p: file_hash(ROOT/p) for p in ADAPTER_FILES}, 'limits': limits}


def load_native(scan_path, *, workspace_root=None):
    """Validate status first, then native export integrity and exact run bindings."""
    scan_path = Path(scan_path).resolve()
    capture = load_capture(scan_path, workspace_root=workspace_root)
    scan = capture.scan
    if scan.get('native_export_status') != 'completed':
        raise ValueError('Native export absent or incomplete; legacy sidecars cannot replace it')
    path = _contained_file(scan_path.parent, scan.get('native_export_path'), 'native_export_path')
    if file_hash(path) != scan.get('native_export_sha256'):
        raise ValueError('Native export hash/integrity mismatch')
    packet = json.loads(path.read_bytes())
    if packet.get('format_version') != EXPORT_VERSION or packet.get('origin') != 'etiq_live_result':
        raise ValueError('Unsupported native export version/origin')
    if packet.get('entry_file_hash') != scan.get('entry_file_hash'):
        raise ValueError('Native export entry binding mismatch')
    if packet.get('graph') != capture.lineage or packet.get('graph_sha256') != digest(capture.lineage):
        raise ValueError('Native export differs from original lineage')
    validate_graph(packet['graph'])
    if packet.get('scan_count') != 1 or packet['serialized']['scan_errors']:
        raise ValueError('Native export is not a complete single-scan result')
    if workspace_root is not None:
        root = Path(workspace_root).resolve()
        for relative, expected in packet['adapter_sources'].items():
            source = _contained_file(root, relative, 'adapter_sources')
            if file_hash(source) != expected:
                raise ValueError('Native adapter source is stale: ' + relative)
    return packet
