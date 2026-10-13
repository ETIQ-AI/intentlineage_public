"""Compile validated prompt extraction without substituting manual specifications."""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from typing import Literal

from pydantic import Field, StrictInt, StrictStr, model_validator

from .compiler import digest, wire_schema, write_json
from .contracts import Contract, Version, OPERATOR_PARAMETERS
from .extraction import ROOT, PromptDocument, PromptSpan, validate_extraction_packet, replay_extraction
from .taxonomy import validate_rule_source

PAYMENT = 'https://spec.edmcouncil.org/fibo/ontology/FND/ProductsAndServices/PaymentsAndSchedules/Payment'
PROPERTY = PAYMENT.removesuffix('Payment')+'hasPaymentAmount'
CATEGORIES = {'intent': 'intent', 'concept': 'ontology', 'rule': 'business_rules'}
COMPILER_VERSION = '2.2.0'
OPERATIONALIZATION_VERSION = '2.1.0'
CORE_FIELDS = ['kind', 'role', 'meaning', 'grounding', 'operator', 'parameters', 'supporting_elements']
# Each operator owns its due stages. Carried representations have a separate lifecycle.
DUE_STAGES = {
    'equals': ['intake', 'po_matched', 'supplier_validated', 'joined', 'approved', 'execution', 'reconciled'],
    'preserve': ['intake', 'po_matched', 'supplier_validated', 'joined', 'approved', 'execution', 'reconciled'],
    'carry': ['intake', 'po_matched', 'supplier_validated', 'joined', 'approved', 'execution', 'reconciled'],
    'bind': ['approved', 'execution', 'reconciled'],
    'reconcile': ['execution', 'reconciled'],
}


class PromptSource(PromptSpan):
    kind: Literal['prompt'] = 'prompt'


class AxiomSource(Contract):
    kind: Literal['ontology_axiom'] = 'ontology_axiom'
    axiom_id: StrictStr
    source_id: StrictStr
    file: StrictStr
    sha256: StrictStr
    commit: StrictStr
    licence: StrictStr
    start_line: StrictInt
    end_line: StrictInt


class Grounding(Contract):
    status: Literal['resolved', 'ambiguous', 'unmapped']
    candidates: list[StrictStr]


class PromptElement(Contract):
    element_id: StrictStr
    identity_key: StrictStr
    revision: StrictInt = Field(ge=1)
    supersedes: StrictStr | None
    semantic_sha256: StrictStr
    kind: Literal['intent', 'concept', 'rule']
    category: Literal['intent', 'ontology', 'business_rules']
    role: StrictStr
    meaning: dict
    source: PromptSource | AxiomSource
    grounding: Grounding
    operator: Literal['equals', 'preserve', 'bind', 'carry', 'reconcile', 'exists_typed_relation'] | None
    parameters: dict
    supporting_elements: list[StrictStr]
    operationalization: dict | None

    @model_validator(mode='after')
    def consistent(self):
        if self.category != CATEGORIES[self.kind]:
            raise ValueError('Category and kind disagree')
        if self.kind == 'rule':
            if self.operator == 'exists_typed_relation':
                if set(self.parameters) != {'subject_class', 'property', 'target_class'} or not all(isinstance(v, str) and v for v in self.parameters.values()):
                    raise ValueError('Invalid typed relation parameters')
            elif self.operator in OPERATOR_PARAMETERS:
                OPERATOR_PARAMETERS[self.operator].model_validate(self.parameters)
            else:
                raise ValueError('Rule requires a supported operator')
            if not self.supporting_elements or not self.operationalization:
                raise ValueError('Rule requires evidence and operationalization')
        elif self.operator is not None or self.parameters or self.operationalization:
            raise ValueError('Only rules have operational parameters')
        return self


class PromptSpecification(Contract):
    format_version: Version
    compiler_version: Version
    prompt: PromptDocument
    provenance: dict
    status: Literal['compiled', 'conflicted']
    elements: list[PromptElement]
    conditions: list[dict]
    rejected_records: list[dict]
    diagnostics: list[dict]
    review_status: Literal['pending_overseer_review']

    @model_validator(mode='after')
    def sources_and_links(self):
        ids = [e.element_id for e in self.elements]
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate persistent element identity')
        for element in self.elements:
            source = element.source
            if isinstance(source, PromptSource):
                if source.source_id != self.prompt.source_id or source.prompt_sha256 != self.prompt.sha256 or self.prompt.text[source.start:source.end] != source.quote:
                    raise ValueError('Compiled prompt span mismatch')
            if not set(element.supporting_elements) <= set(ids):
                raise ValueError('Missing supporting element')
            if element.semantic_sha256 != semantic_hash(element.model_dump(mode='json')):
                raise ValueError('Compiled semantic hash mismatch')
        return self


def semantic_hash(element):
    return digest({k: element[k] for k in CORE_FIELDS+['operationalization']})


def validate_compiled(value):
    return PromptSpecification.model_validate_json(json.dumps(value)).model_dump(mode='json')


def _canonical(meaning):
    result = deepcopy(meaning)
    if result.get('field') == 'amount' and 'value' in result:
        expanded = format(Decimal(result['value']), 'f')
        result['value'] = expanded.rstrip('0').rstrip('.') if '.' in expanded else expanded
    elif result.get('field') == 'revision' and re.fullmatch(r'[+-]?\d+', result.get('value', '')):
        result['value'] = int(result['value'])
    return result


def _operation(operator, fields, expected):
    operation = {'version': OPERATIONALIZATION_VERSION,
            'provenance': 'user_explicit', 'review_status': 'pending_overseer_review',
            'fields': fields, 'applicability': DUE_STAGES[operator][:],
            'comparison': 'exact_decimal' if fields == ['amount'] else 'typed_equality',
            'criterion': {'equals': 'supplied_parameter_equality', 'preserve': 'initial_value_preservation',
                          'carry': 'requirement_representation_carriage', 'bind': 'current_revision_approval',
                          'reconcile': 'receipt_field_agreement'}[operator],
            'required_evidence': fields[:], 'before_due_result': 'not_applicable',
            'observation_assumptions': [expected], 'missing_result': 'unknown', 'mismatch_result': 'violated'}
    if operator == 'bind':
        operation['required_evidence'] = ['approval', 'revision']
        operation['observation_assumptions'].append(
            'Compare the observed approval.revision with the current row revision from approved onward, including ready rows at stage approved. Missing either revision is unknown; observed unequal revisions are violated. Earlier carriage does not make approval due.')
    elif operator == 'carry':
        operation['required_evidence'] = ['element_representations']
    elif operator == 'reconcile':
        operation['required_evidence'] = ['execution_receipt']+fields
        operation['require_action_completion'] = False
        operation['field_comparisons'] = {field: 'exact_decimal' if field == 'amount' else 'typed_equality' for field in fields}
        operation['observation_assumptions'].append(
            'Bounded interpretation: compare six current payment fields with the observed execution receipt from execution onward. The later reconciliation action marker is not required. Missing receipt or compared field is unknown; observed disagreement is violated.')
    return operation


def _version(value):
    return tuple(map(int, value.split('.')))


def compile_prompt(packet, taxonomy, previous=None):
    # Historical replay is audit evidence, never authority to execute old polarity.
    packet = validate_extraction_packet(packet, taxonomy, current=True)
    provenance = packet['provenance']
    if provenance['taxonomy_semantic_sha256'] != taxonomy['semantic_sha256']:
        raise ValueError('Extraction taxonomy provenance is stale')
    model = json.loads((ROOT/'resources/extraction/model-v2.json').read_bytes())
    if provenance.get('model_digest') != model['model']['digest']:
        raise ValueError('Model provenance differs from pinned local model')
    for key, filename in [('instruction_sha256', 'instructions-v2.txt'), ('examples_sha256', 'examples-v2.json')]:
        if provenance.get(key) != hashlib.sha256((ROOT/'resources/extraction'/filename).read_bytes()).hexdigest():
            raise ValueError('Extraction instruction/example provenance mismatch')
    if previous:
        previous = validate_compiled(previous)
        if previous['prompt']['source_id'] != packet['prompt']['source_id']:
            raise ValueError('Previous specification belongs to another source identity')
    old = {e['element_id']: e for e in previous['elements']} if previous else {}
    elements, conditions, diagnostics = [], [], []

    def add(key, kind, role, meaning, source, grounding, operator=None, parameters=None, support=None, operation=None):
        identity = 'pe-'+digest([packet['prompt']['source_id'], key])[:24]
        item = {'element_id': identity, 'identity_key': key, 'revision': 1, 'supersedes': None,
                'kind': kind, 'category': CATEGORIES[kind], 'role': role, 'meaning': meaning,
                'source': source, 'grounding': grounding, 'operator': operator,
                'parameters': parameters or {}, 'supporting_elements': support or [], 'operationalization': operation}
        item['semantic_sha256'] = semantic_hash(item)
        if identity in old:
            prior = old[identity]
            changed = prior['semantic_sha256'] != item['semantic_sha256']
            item['revision'] = prior['revision']+int(changed)
            item['supersedes'] = identity+'@r'+str(prior['revision']) if changed else prior['supersedes']
        elements.append(item)
        return item

    unmapped = {'status': 'unmapped', 'candidates': []}
    accepted = [r for r in packet['records'] if r['status'] == 'accepted']
    for record in accepted:
        source = {'kind': 'prompt', **record['source']}
        kind = 'concept' if record['role'] == 'object' else 'intent'
        atom = add(record['element_key'], kind, record['role'], _canonical(record['meaning']), source, record['grounding'])
        if record['role'] == 'condition':
            conditions.append({'element_id': atom['element_id'], 'meaning': atom['meaning'], 'source': source,
                               'scope': 'single_positive_goal_only', 'review_status': 'pending_overseer_review'})
    atoms = elements[:]
    for atom in atoms:
        meaning = atom['meaning']
        if atom['role'] == 'parameter':
            field = meaning['field']
            add('rule:'+atom['identity_key'], 'rule', 'requirement', {'requirement': 'supplied_parameter'}, atom['source'], unmapped,
                'equals', {'field': field, 'value': meaning['value']}, [atom['element_id']], _operation('equals', [field], 'Supplied value is binding for this single payment operation.'))
        if atom['role'] == 'constraint':
            operator, field = meaning['operator'], meaning.get('field')
            quote = atom['source']['quote'].casefold()
            supported = not meaning['negated'] and (
                operator == 'preserve' and field in {'amount', 'account_id'} and 'unchanged' in quote or
                operator == 'bind' and field == 'revision' and 'approval' in quote and 'current revision' in quote or
                operator == 'carry' and 'carry' in quote and 'requirements' in quote or
                operator == 'reconcile' and 'reconcile' in quote and 'receipt' in quote)
            if not supported:
                diagnostics.append({'type': 'unsupported_constraint_translation', 'element_id': atom['element_id'], 'source': atom['source']})
                continue
            fields = [field] if field else []
            if operator == 'carry':
                params = {'required': [a['element_id'] for a in atoms if a['role'] in {'parameter', 'constraint'}]}
            elif operator == 'reconcile':
                fields = ['amount', 'currency', 'supplier_id', 'account_id', 'purchase_order_id', 'revision']
                params = {'fields': fields, 'expected_from': 'execution_receipt'}
            else:
                params = {'fields': fields, 'expected_from': 'approval' if operator == 'bind' else 'initial_prompt_values'}
            add('rule:'+atom['identity_key'], 'rule', 'requirement', {'requirement': operator}, atom['source'], unmapped,
                operator, params, [atom['element_id']], _operation(operator, fields, 'Role payloads expose compared fields and complete requirement representations; no policies inferred from vocabulary.'))
    pay = next((e for e in atoms if e['role'] == 'goal' and e['meaning'].get('action') == 'pay' and not e['meaning']['negated']), None)
    if pay:
        concept = add('operation:Payment', 'concept', 'operation_binding', {'ontology_term': PAYMENT, 'mapping_provenance': 'authored_bounded_pay_adapter'}, pay['source'], {'status': 'resolved', 'candidates': [PAYMENT]}, support=[pay['element_id']])
        axiom = validate_rule_source(taxonomy, next(r for r in taxonomy['rules'] if r['subject_class'] == PAYMENT and r['property'] == PROPERTY))
        add('axiom:'+axiom['axiom_id'], 'rule', 'ontology_requirement', {'quantifier': 'someValuesFrom'},
            {'kind': 'ontology_axiom', 'axiom_id': axiom['axiom_id'], **axiom['source']},
            {'status': 'resolved', 'candidates': [PROPERTY]}, 'exists_typed_relation',
            {k: axiom[k] for k in ['subject_class', 'property', 'target_class']}, [concept['element_id']],
            {'provenance': 'ontology_derived', 'review_status': 'pending_overseer_review', 'fields': ['ontology_assertions'],
             'applicability': ['execution', 'reconciled'], 'comparison': 'explicit_typed_relation_witness',
             'missing_result': 'unknown', 'observation_assumptions': axiom['observation_assumptions'],
             'justification': 'A Payment has at least one hasPaymentAmount successor asserted as MonetaryAmount; no amount equality or preservation follows.'})
    parameters = [e for e in atoms if e['role'] == 'parameter']
    for i, left in enumerate(parameters):
        for right in parameters[i+1:]:
            if left['meaning']['field'] == right['meaning']['field'] and left['meaning']['value'] != right['meaning']['value']:
                diagnostics.insert(0, {'type': 'conflicting_parameter', 'field': left['meaning']['field'], 'sources': [left['source'], right['source']]})
    goals = [e for e in atoms if e['role'] == 'goal']
    if any(a['meaning'].get('action') == b['meaning'].get('action') and a['meaning']['negated'] != b['meaning']['negated'] for a in goals for b in goals):
        diagnostics.insert(0, {'type': 'conflicting_goals', 'sources': [g['source'] for g in goals]})
    if previous:
        core = lambda items: {e['element_id']: digest({k: e[k] for k in CORE_FIELDS}) for e in items}
        current_core, previous_core = core(elements), core(previous['elements'])
        predecessors = provenance.get('normalization_predecessors', [provenance.get('normalization_predecessor', {})])
        interpretation_correction = (
            packet['prompt'] == previous['prompt']
            and any(predecessor.get('packet_semantic_sha256') == previous['provenance']['extraction_semantic_sha256']
                    and predecessor.get('normalizer_version') == previous['provenance']['normalizer_version']
                    for predecessor in predecessors)
            and _version(provenance['normalizer_version']) > _version(previous['provenance']['normalizer_version'])
            and _version(COMPILER_VERSION) > _version(previous['compiler_version']))
        if current_core != previous_core and not interpretation_correction and _version(packet['prompt']['version']) <= _version(previous['prompt']['version']):
            raise ValueError('Semantic edit requires a newer prompt version')
        criteria_changed = any(e['element_id'] in old and current_core[e['element_id']] == previous_core[e['element_id']]
                               and e['operationalization'] != old[e['element_id']]['operationalization'] for e in elements)
        # Historical 2.0.1 criteria had no declared version; do not invent one for the archive.
        previous_operation_version = previous['provenance'].get('operationalization_version', '0.0.0')
        if criteria_changed and (_version(COMPILER_VERSION) <= _version(previous['compiler_version'])
                                 or _version(OPERATIONALIZATION_VERSION) <= _version(previous_operation_version)):
            raise ValueError('Operationalization criteria change requires newer compiler and operationalization versions')
        if _version(COMPILER_VERSION) < _version(previous['compiler_version']) or _version(OPERATIONALIZATION_VERSION) < _version(previous_operation_version):
            raise ValueError('Current compiler/operationalization version cannot downgrade a predecessor')
    result = {'format_version': '2.0.0', 'compiler_version': COMPILER_VERSION, 'prompt': packet['prompt'],
              'provenance': {**provenance, 'operationalization_version': OPERATIONALIZATION_VERSION,
                             'extraction_semantic_sha256': digest(packet), 'identity_policy': 'persistent source_id and role/field/action/occurrence key; ambiguous repeated atoms require review'},
              'status': 'conflicted' if any(d['type'].startswith('conflicting') for d in diagnostics) else 'compiled',
              'elements': elements, 'conditions': conditions,
              'rejected_records': [r for r in packet['records'] if r['status'] != 'accepted'],
              'diagnostics': diagnostics, 'review_status': 'pending_overseer_review'}
    return validate_compiled(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--previous-root', type=Path, help='Development predecessor directory; defaults to existing generated outputs')
    args = parser.parse_args()
    taxonomy = json.loads((ROOT/'resources/ontology/generated/taxonomy-v2.json').read_bytes())
    write_json(ROOT/'schemas/prompt-specification.schema.json', wire_schema(PromptSpecification))
    if args.development:
        for path in sorted((ROOT/'evidence/extraction-v2-development').glob('dev-*/extraction.json')):
            output = ROOT/f'specifications/generated/prompts/{path.parent.name}.json'
            predecessor = args.previous_root/(path.parent.name+'.json') if args.previous_root else output
            previous = json.loads(predecessor.read_bytes()) if predecessor.exists() else None
            write_json(output, compile_prompt(replay_extraction(path, taxonomy), taxonomy, previous))
    elif args.input and args.output:
        previous = json.loads(args.previous.read_bytes()) if args.previous else None
        write_json(args.output, compile_prompt(replay_extraction(args.input, taxonomy), taxonomy, previous))
    else:
        parser.error('Use --development or --input and --output')


if __name__ == '__main__':
    main()
