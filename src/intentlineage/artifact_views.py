"""Frozen artifact views and native disclosure adapted from use_case_icp.

Adaptation of _payload_lazy_catalogue/expand_native_subtree: private values are
separated from allowlisted descriptors, and only advertised native groups open.
No review model, fabricated graph edge, raw source treatment or Python executor.
"""
from copy import deepcopy
import hmac
import json
import secrets
from pathlib import Path

from ._reference.artifact_operations import inspect_catalogue_artifact
from .native_capture import digest, validate_graph, file_hash, ROOT
from ._reference.lazy_catalogue import _payload_lazy_catalogue

SUMMARY_VERSION = '4.1.0'
BODY_KEYS = {'artifact_content', 'value_preview', 'raw_value', 'value', 'content', 'rows', 'text'}


def _coverage(artifact):
    return {'captured_subset': bool(artifact.get('artifact_truncated')),
            'original_size': deepcopy(artifact.get('artifact_size')),
            'basis': 'frozen_captured_artifact', 'redaction': 'reference_sensitive_field_policy'}


def _operation(artifact, request):
    node = {**artifact, 'node_ref': 'own', 'raw_metadata': {}}
    return inspect_catalogue_artifact(
        {'assigned_job_id': 'own', 'jobs': {'own': {'nodes': [node]}}},
        {'available_operations': ['artifact_inspection'], 'runtime_evidence': {'nodes': [{'node_ref': 'own'}]}},
        {'node_ref': 'own', **request})


def _summary_identity(artifact, capture_sha256, options, version):
    options = dict(options or {})
    maximum = options.get('max_chars', 2000)
    if type(maximum) is not int or not 1 <= maximum <= 10000 or set(options) - {'max_chars'}:
        raise ValueError('Summary options require max_chars between 1 and 10000')
    return {'capture_sha256': capture_sha256, 'artifact_sha256': digest(artifact),
            'summary_version': version, 'options': {'max_chars': maximum},
            'policy_sources': {p: file_hash(ROOT/p) for p in
                ('src/intentlineage/artifact_views.py', 'src/intentlineage/_reference/artifact_operations.py')}}


def summarize_artifact(artifact, *, capture_sha256, options=None, version=SUMMARY_VERSION):
    identity = _summary_identity(artifact, capture_sha256, options, version)
    maximum = identity['options']['max_chars']
    if artifact.get('artifact_content') is None:
        raise ValueError('Artifact has no supported captured value')
    kind = artifact['artifact_kind']
    content = artifact['artifact_content']
    request = {'inspection': 'describe'}
    if kind == 'table': request['columns'] = content['columns']
    result = _operation(artifact, request)
    stats = {k: v for k, v in result.items() if k in ('row_count', 'column_count', 'columns',
             'json_value_types', 'null_counts', 'character_count', 'line_count', 'json_value_type', 'artifact_size')}
    if kind == 'table':
        stats['numeric'] = result['numeric_statistics']
        text = f"Captured table: {stats['row_count']} rows; {stats['column_count']} columns; " + ', '.join(stats['columns'])
    elif kind == 'document':
        text = f"Captured document: {stats['character_count']} characters; {stats['line_count']} lines."
    else:
        stats['captured_items'] = len(content) if isinstance(content, (dict, list)) else 1
        text = f"Captured {kind}: {stats['captured_items']} items; JSON type {stats['json_value_type']}."
    if artifact.get('artifact_truncated'): text += ' Statistics cover the captured subset.'
    sample = read_artifact(artifact, count=3)['content']
    text += ' Observed captured sample: ' + json.dumps(sample, ensure_ascii=False, sort_keys=True)
    return {'summary_version': version, 'cache_key': digest(identity), 'identity': identity,
            'description': text[:maximum], 'description_truncated': len(text) > maximum,
            'statistics': stats, 'coverage': _coverage(artifact)}


def read_artifact(artifact, *, start=0, count=20, columns=None):
    if type(start) is not int or start < 0 or type(count) is not int or not 1 <= count <= 1000:
        raise ValueError('Artifact read bounds require a nonnegative start and count 1..1000')
    if artifact.get('artifact_content') is None:
        raise ValueError('Artifact has no supported captured value')
    result = _operation(artifact, {'inspection': 'read', 'start': start, 'count': count,
                                   'columns': columns or []})
    actual_count = result.get('returned_rows', result.get('returned_document_characters', result.get('returned_records', 0)))
    return {'content': result['content'], 'count': actual_count, 'start': start,
            'more_available': result['more_available'], 'coverage': _coverage(artifact)}


def cached_summary(cache_dir, artifact, *, capture_sha256, options=None, version=SUMMARY_VERSION):
    identity = _summary_identity(artifact, capture_sha256, options, version)
    key = digest(identity)
    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (key + '.json')
    if path.exists():
        try:
            saved = json.loads(path.read_bytes())
        except (ValueError, OSError) as error:
            raise ValueError('Summary cache is unreadable') from error
        if (not isinstance(saved, dict) or set(saved) != {'summary', 'summary_sha256'} or
            saved['summary'].get('identity') != identity or saved['summary'].get('cache_key') != key or
            digest(saved['summary']) != saved['summary_sha256']):
            raise ValueError('Summary cache integrity mismatch')
        return saved['summary'], True
    summary = summarize_artifact(artifact, capture_sha256=capture_sha256, options=options, version=version)
    encoded = json.dumps({'summary': summary, 'summary_sha256': digest(summary)},
                         sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(encoded)
        stream.write('\n')
    return summary, False


def build_catalogue(packet, *, inputs, outputs):
    """Private controller catalogue; native IDs, scopes and membership are retained."""
    nodes = validate_graph(packet['graph'])
    capture_hash = digest(packet)
    run = packet['run_id']
    artifacts, node_artifacts, omissions = {}, {}, []
    for state in packet['serialized']['nodes']:
        bound = packet['state_bindings'].get(state['node_ref'], [])
        if not bound or state.get('artifact_content') is None:
            continue
        ref = run + ':artifact:' + state['node_ref']
        artifact = deepcopy(state)
        artifact.update(artifact_ref=ref, native_ids=bound,
                        artifact_value_sha256=digest(state['artifact_content']))
        artifacts[ref] = artifact
        for native_id in bound:
            if native_id not in nodes: raise ValueError('Artifact binds absent native node')
            node_artifacts.setdefault(str(native_id), []).append(ref)
        omissions.append({'artifact_ref': ref, 'omitted_fields': sorted(BODY_KEYS & state.keys())})

    # Use the upstream split/duplicate-omission mechanism on our frozen records.
    # Only our stricter allowlisted projection is ever made visible.
    native_nodes = [{**a, 'native_node_ref': a['node_ref']} for a in artifacts.values()]
    reviewer, disclosure, omission_manifest = _payload_lazy_catalogue(
        {'jobs': {'payment': {'native_graph': {'nodes': native_nodes}}}}, run)
    artifacts = {ref: value['complete_native_node'] for ref, value in disclosure['artifacts'].items()}

    def endpoints(names):
        refs = []
        for name in names:
            found = [ref for ref, a in artifacts.items() if name in a['names']]
            if len(found) != 1:
                raise ValueError(f'Job endpoint {name!r} must identify one captured native artifact, got {len(found)}')
            refs.extend(found)
        if not refs: raise ValueError('Whole-job input and output must be declared')
        return refs
    job_inputs, job_outputs = endpoints(inputs), endpoints(outputs)
    native_groups = {i: n for i, n in nodes.items() if str(n.get('name', '')).startswith('cluster_')}
    groups = {}
    def descendants(i):
        direct = set(native_groups[i].get('nodes', []))
        return direct | set().union(*(descendants(c) for c in direct if c in native_groups)) if direct else set()
    for i, n in native_groups.items():
        members = descendants(i)
        parents = [j for j, g in native_groups.items() if i in g.get('nodes', [])]
        if len(parents) > 1: raise ValueError('Native cluster has ambiguous parent membership')
        group_id = f'{run}:group:{i}'
        in_ids, out_ids = set(), set()
        for edge in packet['graph']['edges']:
            a, b = edge['tail'], edge['head']
            if a not in members and b in members:
                in_ids.update(k for k in (a, b) if str(k) in node_artifacts)
            if a in members and b not in members:
                out_ids.update(k for k in (a, b) if str(k) in node_artifacts)
        # Explicit job endpoint bindings supplement groups with no external graph edges.
        for ref in job_inputs:
            in_ids.update(k for k in artifacts[ref]['native_ids'] if k in members)
        for ref in job_outputs:
            out_ids.update(k for k in artifacts[ref]['native_ids'] if k in members)
        groups[group_id] = {'group_id': group_id, 'native_id': i, 'name': n.get('label'),
                            'parent_group': f'{run}:group:{parents[0]}' if parents else None,
                            'direct_members': list(n.get('nodes', [])), 'all_members': sorted(members),
                            'input_ids': sorted(in_ids), 'output_ids': sorted(out_ids),
                            'boundary_source': 'native_edges_and_declared_job_endpoints'}
    catalogue = {'format_version': '4.0.2', 'origin': packet['origin'], 'run_id': run,
                 'capture_sha256': capture_hash, 'graph': deepcopy(packet['graph']),
                 'artifacts': artifacts, 'node_artifacts': node_artifacts, 'groups': groups,
                 'job_inputs': job_inputs, 'job_outputs': job_outputs,
                 'field_omissions': omissions, 'projection_key': secrets.token_hex(32),
                 'reference_omission_manifest': omission_manifest,
                 'limits': ['Artifact values and producer source are controller-private.',
                            'Only native cluster membership supports nested opening; missing capture stays absent.']}
    if not groups: catalogue['limits'].append('This capture has no supported native function groups.')
    catalogue['catalogue_sha256'] = digest(catalogue)
    return catalogue


def _validate_catalogue(cat):
    if cat.get('format_version') != '4.0.2':
        raise ValueError('Unsupported private catalogue version; regenerate JSON-stable indices and disclosure ordering')
    value = {k: v for k, v in cat.items() if k != 'catalogue_sha256'}
    if digest(value) != cat.get('catalogue_sha256'):
        raise ValueError('Private catalogue integrity mismatch')


def _sign(cat, projection_hash):
    return hmac.new(bytes.fromhex(cat['projection_key']), projection_hash.encode(), 'sha256').hexdigest()


def project_catalogue(cat, *, opened=()):
    """Allowlist producer metadata and descriptors; never copy private source/value fields."""
    _validate_catalogue(cat)
    opened = sorted(set(opened))
    for group_id in opened:
        if group_id not in cat['groups']: raise ValueError('Unknown native group')
        parent = cat['groups'][group_id]['parent_group']
        if parent is not None and parent not in opened:
            raise ValueError('Native group is not visible until its parent opens')
    nodes = {n['_gvid']: n for n in cat['graph']['objects']}
    grouped = set().union(*(set(g['all_members']) for g in cat['groups'].values()))
    visible = set(nodes) - grouped
    for g in cat['groups'].values():
        if g['parent_group'] is None or g['parent_group'] in opened:
            visible.add(g['native_id'])
            visible.update(g['input_ids'] + g['output_ids'])
            if g['group_id'] in opened:
                visible.update(g['direct_members'])
    # A cluster descriptor is visible only if its immediate native parent is disclosed.
    for g in cat['groups'].values():
        if g['parent_group'] is not None and g['parent_group'] not in opened:
            visible.discard(g['native_id'])
    for ref in cat['job_inputs'] + cat['job_outputs']:
        visible.update(cat['artifacts'][ref]['native_ids'])
    descriptors, visible_artifacts = [], []
    for i in sorted(visible):
        n = nodes[i]
        descriptor = {'native_id': i, 'name': n.get('label', ''),
                      'type': 'native_function_group' if str(n.get('name', '')).startswith('cluster_') else n.get('shape', 'native_object'),
                      'scope': None, 'source_location': None, 'artifacts': []}
        for ref in cat['node_artifacts'].get(str(i), []):
            a = cat['artifacts'][ref]
            descriptor['artifacts'].append({'artifact_ref': ref, 'kind': a['artifact_kind'],
                                            'value_type': a['value_type'], 'scope': a['scope_type'],
                                            'line_no': a['line_no'],
                                            'artifact_value_sha256': a['artifact_value_sha256'],
                                            'truncated': a['artifact_truncated']})
            visible_artifacts.append(ref)
            descriptor['scope'] = a['scope_type']
            descriptor['source_location'] = {'line_no': a['line_no'], 'file': None,
                                              'availability': 'captured_line_only'}
        for g in cat['groups'].values():
            if g['native_id'] == i:
                descriptor['scope'] = {'native_parent_group': g['parent_group']}
        descriptors.append(descriptor)
    eligible = [{'group_id': g['group_id'], 'native_id': g['native_id'], 'name': g['name'],
                 'input_artifacts': sorted({r for i in g['input_ids'] for r in cat['node_artifacts'].get(str(i), [])}),
                 'output_artifacts': sorted({r for i in g['output_ids'] for r in cat['node_artifacts'].get(str(i), [])})}
                for g in sorted(cat['groups'].values(), key=lambda group: group['native_id'])
                if g['native_id'] in visible and g['group_id'] not in opened]
    relationships = [deepcopy(e) for e in cat['graph']['edges'] if e['tail'] in visible and e['head'] in visible]
    description = 'Visible native graph: ' + '; '.join(f"{n['native_id']} {n['name']} ({n['type']})" for n in descriptors)
    description += '. Visible edges: ' + ', '.join(f"{e['tail']} -> {e['head']}" for e in relationships)
    view = {'format_version': '4.0.0', 'run_id': cat['run_id'], 'capture_sha256': cat['capture_sha256'],
            'nodes': descriptors, 'relationships': relationships, 'eligible_groups': eligible,
            'opened_groups': opened, 'visible_artifacts': sorted(set(visible_artifacts)),
            'job_inputs': cat['job_inputs'][:], 'job_outputs': cat['job_outputs'][:],
            'graph_description': description,
            'limits': ['Visible projection only; unopened descendants, values and full producer source remain withheld.',
                       'Producer source location is captured line only where available; absent file/definition locations remain unknown.']}
    view['projection_sha256'] = digest(view)
    view['projection_token'] = _sign(cat, view['projection_sha256'])
    return view


def _validate_view(cat, view):
    _validate_catalogue(cat)
    body = {k: v for k, v in view.items() if k not in ('projection_sha256', 'projection_token')}
    expected = digest(body)
    if expected != view.get('projection_sha256') or not hmac.compare_digest(_sign(cat, expected), str(view.get('projection_token', ''))):
        raise ValueError('Visible projection integrity/authorization mismatch')
    if view != project_catalogue(cat, opened=view['opened_groups']):
        raise ValueError('Visible projection differs from its native disclosure')


def open_group(cat, view, group_id):
    """Adapt expand_native_subtree: advertise -> disclose native members -> receipt."""
    _validate_view(cat, view)
    advertised = {g['group_id'] for g in view['eligible_groups']}
    if group_id not in advertised:
        raise ValueError('Native group is not currently visible/eligible')
    updated = project_catalogue(cat, opened=view['opened_groups'] + [group_id])
    old_ids = {n['native_id'] for n in view['nodes']}
    added = [n['native_id'] for n in updated['nodes'] if n['native_id'] not in old_ids]
    old_edges = {e['_gvid'] for e in view['relationships']}
    receipt = {'operation': 'expand_execution_group', 'group_id': group_id,
               'native_id': cat['groups'][group_id]['native_id'], 'nodes_added': added,
               'relationships_added': [e['_gvid'] for e in updated['relationships'] if e['_gvid'] not in old_edges],
               'newly_disclosed_artifacts': sorted(set(updated['visible_artifacts']) - set(view['visible_artifacts'])),
               'before_sha256': view['projection_sha256'], 'after_sha256': updated['projection_sha256'],
               'model_calls': 0}
    return updated, receipt


def inspect_artifact(cat, view, artifact_ref, *, operation='describe', start=0, count=20, columns=None):
    _validate_view(cat, view)
    if artifact_ref not in view['visible_artifacts'] or artifact_ref not in cat['artifacts']:
        raise ValueError('Artifact is not currently visible in this capture')
    a = cat['artifacts'][artifact_ref]
    if operation == 'describe':
        result = {'summary': summarize_artifact(a, capture_sha256=cat['capture_sha256'])}
    elif operation == 'read':
        result = {'read': read_artifact(a, start=start, count=count, columns=columns)}
    else:
        raise ValueError('Only bounded describe/read artifact inspection is allowed')
    result['receipt'] = {'operation': 'artifact_inspection', 'inspection': operation,
                         'artifact_ref': artifact_ref, 'artifact_value_sha256': a['artifact_value_sha256'],
                         'projection_sha256': view['projection_sha256'], 'response_sha256': digest(result),
                         'model_calls': 0}
    return result
