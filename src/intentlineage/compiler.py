"""Compile explicit TOML requirements without guessing intent from prose."""
import argparse
import hashlib
from itertools import combinations
import json
from pathlib import Path
import re
import tomllib

from .contracts import Approval, CompiledSpecification, OntologyBinding, PaymentRevision, SourceSpan, SpecificationElement, SpecificationInput
from .ontology import OntologyCatalog

COMPILER_VERSION = '1.0.2'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False)+'\n').encode('utf-8'))


def wire_schema(model):
    """Describe emitted JSON: positive exact money is a decimal string.

    Pydantic's Python-input validation schema can allow floats that our
    before-validator rejects. Its string schema also lacks a standard positive
    bound and scientific spelling, so make those wire constraints explicit.
    """
    schema = model.model_json_schema(mode='serialization')
    positive = r'^(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)(?:[eE][+-]?[0-9]+)?$'
    def visit(node):
        if isinstance(node, dict):
            amount = node.get('properties', {}).get('amount')
            if isinstance(amount, dict):
                node['properties']['amount'] = {'title': amount.get('title', 'Amount'), 'type': 'string', 'pattern': positive}
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)
    visit(schema)
    schema['$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    schema['x-intentlineage-ingestion'] = {
        'runtime_validation_required': True,
        'validator': f'{model.__name__}.model_validate_json',
        'schema_integer_semantics': 'mathematical; lexical syntax enforced at runtime',
    }
    return schema


class SpecificationConflict(ValueError):
    def __init__(self, conflicts):
        self.conflicts = conflicts
        super().__init__('Contradictory overlapping requirements')


def compile_spec(text, source_path, catalog, previous=None) -> CompiledSpecification:
    raw = tomllib.loads(text)
    raw_keys = [item.get('key') for item in raw.get('elements', []) if isinstance(item, dict)]
    valid_keys = [key for key in raw_keys if isinstance(key, str)]
    if len(set(valid_keys)) != len(valid_keys):
        raise ValueError('duplicate element keys')
    source = SpecificationInput.model_validate(raw)
    if source.ontology_version != catalog.manifest['version']:
        raise ValueError('Claimed ontology version differs from pinned manifest')
    keys = [item.key for item in source.elements]
    if len(set(keys)) != len(keys):
        raise ValueError('duplicate element keys')
    if previous and previous.document_id != source.document_id:
        raise ValueError('Previous specification belongs to a different document')
    lines = text.splitlines()
    starts = [index + 1 for index, line in enumerate(lines) if re.fullmatch(r'\s*\[\[elements\]\]\s*(?:#.*)?', line)]
    if len(starts) != len(source.elements):
        raise ValueError('Use one explicit [[elements]] table per source element')
    prior = {item.element_id: item for item in previous.elements} if previous else {}
    elements = []
    for index, item in enumerate(source.elements):
        element_id = f'urn:intentlineage:element:{source.document_id}:{item.key}'
        span = SourceSpan(document=source_path, start_line=starts[index], end_line=starts[index+1]-1 if index+1 < len(starts) else len(lines))
        bindings = [OntologyBinding(term=term, **catalog.resolve(term)) for term in sorted(set(item.ontology_terms))]
        parameters = {key: sorted(set(value)) if key in {'fields', 'required'} and isinstance(value, list) else value for key, value in item.parameters.items()}
        content = {'kind': item.kind, 'text': ' '.join(item.text.split()), 'stages': sorted(set(item.stages)),
                   'operator': item.operator, 'parameters': parameters,
                   'bindings': [binding.model_dump(mode='json') for binding in bindings]}
        revision = digest(content)
        old = prior.get(element_id)
        supersedes = old.revision if old and old.revision != revision else old.supersedes if old else None
        elements.append(SpecificationElement(element_id=element_id, key=item.key, revision=revision, supersedes=supersedes, source=span, **content))
    conflicts = []
    for left, right in combinations(elements, 2):
        overlap = sorted(set(left.stages) & set(right.stages))
        if left.operator == right.operator == 'equals' and overlap and left.parameters['field'] == right.parameters['field'] and (type(left.parameters['value']), left.parameters['value']) != (type(right.parameters['value']), right.parameters['value']):
            conflicts.append({'keys': [left.key, right.key], 'element_ids': [left.element_id, right.element_id],
                              'field': left.parameters['field'], 'stages': overlap,
                              'sources': [left.source.model_dump(), right.source.model_dump()]})
    if conflicts:
        raise SpecificationConflict(conflicts)
    # Include shared parameters and ontology provenance in document semantics,
    # while keeping formatting, version labels and source locations separate.
    payment_parameters = source.payment_parameters.model_copy(update={'approval_bind_fields': sorted(source.payment_parameters.approval_bind_fields)})
    ontology_hash = digest(catalog.manifest)
    semantic_hash = digest({'document_id': source.document_id, 'elements': sorted((item.element_id, item.revision) for item in elements),
                            'parameters': payment_parameters.model_dump(mode='json'), 'ontology_manifest_sha256': ontology_hash})
    if previous and previous.semantic_sha256 != semantic_hash and previous.version == source.version:
        raise ValueError('Semantic change requires a changed specification version')
    return CompiledSpecification(document_id=source.document_id, version=source.version, ontology_version=source.ontology_version,
                                 compiler_version=COMPILER_VERSION, source_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                                 semantic_sha256=semantic_hash, ontology_manifest_sha256=ontology_hash,
                                 payment_parameters=payment_parameters, elements=elements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('specifications/payment.toml'))
    parser.add_argument('--ontology', type=Path, default=Path('resources/ontology/manifest.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('specifications/generated'))
    parser.add_argument('--previous', type=Path)
    args = parser.parse_args()
    previous = CompiledSpecification.model_validate_json(args.previous.read_bytes()) if args.previous else None
    compiled = compile_spec(args.source.read_text(encoding='utf-8'), args.source.as_posix(), OntologyCatalog(args.ontology), previous)
    write_json(args.output_dir/'payment-spec.json', compiled.model_dump(mode='json'))
    for name, model in [('payment-spec', CompiledSpecification), ('payment-revision', PaymentRevision), ('approval', Approval)]:
        write_json(args.output_dir/f'{name}.schema.json', wire_schema(model))
    print(f'Saved specification {compiled.version} with {len(compiled.elements)} elements')


if __name__ == '__main__':
    main()
