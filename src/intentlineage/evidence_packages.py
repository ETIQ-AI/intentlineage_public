"""M1 evidence packages; no model assessment or experiment policy."""
from copy import deepcopy

from .artifact_views import project_catalogue, open_group, summarize_artifact, cached_summary, _validate_catalogue
from .native_capture import digest


def _summary(cat, ref, cache_dir):
    artifact = cat['artifacts'][ref]
    if cache_dir is None:
        summary = summarize_artifact(artifact, capture_sha256=cat['capture_sha256'])
    else:
        summary, _ = cached_summary(cache_dir, artifact, capture_sha256=cat['capture_sha256'])
    return {'artifact_ref': ref, 'native_ids': artifact['native_ids'][:], 'summary': summary}


def _seal(package):
    package.pop('package_sha256', None)
    package['package_sha256'] = digest(package)
    return package


def validate_package(package):
    if not isinstance(package, dict) or digest({k: v for k, v in package.items() if k != 'package_sha256'}) != package.get('package_sha256'):
        raise ValueError('Evidence package integrity mismatch')
    if package.get('format_version') != '4.0.0' or package.get('mode') not in {'endpoints', 'top_level', 'opened'}:
        raise ValueError('Unsupported evidence package format/mode')
    if not package.get('job_inputs') or not package.get('job_outputs'):
        raise ValueError('Evidence package requires whole-job input and output')
    return package


def build_packages(cat, inventory, *, cache_dir=None):
    _validate_catalogue(cat)
    if digest({k: v for k, v in inventory.items() if k != 'inventory_sha256'}) != inventory.get('inventory_sha256'):
        raise ValueError('Inventory integrity mismatch')
    base = {'format_version': '4.0.0', 'mode': 'endpoints',
            'prompt': deepcopy(inventory['prompt']), 'elements': deepcopy(inventory['elements']),
            'conditions': deepcopy(inventory['conditions']),
            'inventory_sha256': inventory['inventory_sha256'], 'capture_sha256': cat['capture_sha256'],
            'job_inputs': [_summary(cat, r, cache_dir) for r in cat['job_inputs']],
            'job_outputs': [_summary(cat, r, cache_dir) for r in cat['job_outputs']],
            'limits': ['Synthetic workflow; capture is evidence, not an assessment result.',
                       'Summary samples/descriptions and subset statistics are explicitly bounded.',
                       'Legacy staged operationalizations are retained proposals, not native-state verdicts.']}
    endpoint = _seal(base)
    top = deepcopy(endpoint)
    top['mode'] = 'top_level'
    top['graph'] = project_catalogue(cat)
    top['intermediate_artifacts'] = [_summary(cat, r, cache_dir) for r in top['graph']['visible_artifacts']
                                   if r not in cat['job_inputs'] + cat['job_outputs']]
    return {'endpoint': endpoint, 'top_level': _seal(top)}


def open_package(cat, package, group_id, *, cache_dir=None):
    validate_package(package)
    if package['mode'] == 'endpoints':
        raise ValueError('Endpoint package has no native opening operation')
    if package['capture_sha256'] != cat['capture_sha256']:
        raise ValueError('Package belongs to another native capture')
    graph, receipt = open_group(cat, package['graph'], group_id)
    updated = deepcopy(package)
    updated['mode'] = 'opened'
    updated['graph'] = graph
    updated['intermediate_artifacts'] = [_summary(cat, r, cache_dir) for r in graph['visible_artifacts']
                                       if r not in cat['job_inputs'] + cat['job_outputs']]
    _seal(updated)
    receipt['before_package_sha256'] = package['package_sha256']
    receipt['after_package_sha256'] = updated['package_sha256']
    return updated, receipt
