"""Three source-linked categories kept outside ordinary workflow values."""
from copy import deepcopy

from .prompt_compiler import validate_compiled, semantic_hash
from .native_capture import digest


def inventory_from_spec(spec, *, fixture_policies=()):
    spec = validate_compiled(spec)
    if not spec.get('provenance'):
        raise ValueError('Inventory requires compiler/model/source provenance')
    inventory = {'format_version': '4.0.0', 'prompt': deepcopy(spec['prompt']),
                 'provenance': deepcopy(spec['provenance']), 'elements': [],
                 'categories': {c: [] for c in ('intent', 'ontology', 'business_rules')},
                 'conditions': deepcopy(spec['conditions']),
                 'rejected_records': deepcopy(spec['rejected_records']),
                 'diagnostics': deepcopy(spec['diagnostics']),
                 'fixture_policies': [], 'review_status': 'pending_overseer_review'}
    for original in spec['elements']:
        if original['semantic_sha256'] != semantic_hash(original):
            raise ValueError('Inventory element meaning/grounding integrity mismatch')
        e = deepcopy(original)
        source = e['source']
        if source['kind'] == 'prompt':
            if spec['prompt']['text'][source['start']:source['end']] != source['quote'] or source['prompt_sha256'] != spec['prompt']['sha256']:
                raise ValueError('Inventory prompt source span/hash mismatch')
            e['source_revision'] = spec['prompt']['version']
            e['scope'] = {'kind': 'prompt_requirement', 'source_id': source['source_id']}
        elif source['kind'] == 'ontology_axiom':
            if not source.get('commit') or not source.get('sha256') or not source.get('axiom_id'):
                raise ValueError('Inventory ontology source provenance missing')
            e['source_revision'] = source['sha256']
            e['scope'] = {'kind': 'ontology_axiom', 'axiom_id': source['axiom_id']}
        else:
            raise ValueError('Unsupported inventory source kind')
        inventory['elements'].append(e)
        inventory['categories'][e['category']].append(e)
    for policy in fixture_policies:
        if policy.get('source', {}).get('kind') != 'fixture' or not policy.get('source', {}).get('sha256'):
            raise ValueError('Fixture policies require explicit fixture source provenance')
        inventory['fixture_policies'].append(deepcopy(policy))
    inventory['inventory_sha256'] = digest(inventory)
    return inventory
