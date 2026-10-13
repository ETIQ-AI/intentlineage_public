"""Inventory pinned declarations/axioms without inventing operational policy."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from rdflib import BNode, Graph, OWL, RDF, RDFS, SKOS, URIRef
from rdflib.compare import to_canonical_graph

from .compiler import digest, write_json
from .ontology import DECLARATIONS, OntologyCatalog

QUANTIFIERS = ('someValuesFrom', 'allValuesFrom', 'cardinality', 'qualifiedCardinality',
               'minCardinality', 'maxCardinality', 'minQualifiedCardinality', 'maxQualifiedCardinality')
EXTENSIONS = [
    {'iri': 'urn:intentlineage:action:pay', 'kind': 'action_extension', 'labels': ['pay', 'settle'],
     'definition': 'User goal to simulate payment of an invoice.', 'source': 'authored extraction taxonomy', 'version': '2.0.0'},
    {'iri': 'urn:intentlineage:action:preserve', 'kind': 'action_extension', 'labels': ['preserve', 'do not change'],
     'definition': 'User-explicit preservation request; not an OWL implication.', 'source': 'authored extraction taxonomy', 'version': '2.0.0'},
]


def source_span(root, source, iri):
    text = (root/source['file']).read_text(encoding='utf-8')
    lines = text.splitlines()
    local = re.split(r'[/#]', str(iri))[-1]
    patterns = [re.compile(r'^\s*\w+:'+re.escape(local)+r'\s+a\s+owl:'),
                re.compile(r'<owl:(?:Class|ObjectProperty|DatatypeProperty)\s+rdf:about="(?:&[^;]+;)?'+re.escape(local)+r'"')]
    starts = [i for i, line in enumerate(lines) if any(p.search(line) for p in patterns)]
    start = starts[0] if starts else 0
    if '<owl:' in lines[start]:
        tag = re.search(r'<(owl:\w+)\b', lines[start]).group(1)
        end = next((i for i in range(start, len(lines)) if f'</{tag}>' in lines[i]), start)
    else:
        end = next((i-1 for i in range(start+1, len(lines)) if not lines[i].strip()), start)
    return {'source_id': source['id'], 'file': 'resources/ontology/'+source['file'],
            'sha256': source['sha256'], 'commit': source['commit'], 'licence': source['licence'],
            'start_line': start+1, 'end_line': end+1}


def build_taxonomy(catalog, supplemental_manifest, previous=None):
    supplement = json.loads(Path(supplemental_manifest).read_bytes())
    sources, graphs = dict(catalog.sources), dict(catalog.graphs)
    root = catalog.root.resolve()
    for source in supplement['sources']:
        path = (root/source['file']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Supplement source escapes ontology root')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('Supplement source hash mismatch')
        sources[source['id']] = source
        graphs[source['id']] = Graph().parse(data=raw, format='xml' if path.suffix == '.rdf' else 'turtle')
    terms, rules, imports, ontology_ids = {}, {}, [], set()
    for graph in graphs.values():
        ontology_ids.update(str(s) for s in graph.subjects(RDF.type, OWL.Ontology))
    for source_id, graph in sorted(graphs.items()):
        source = sources[source_id]
        canonical = to_canonical_graph(graph)
        for iri, _, kind in graph.triples((None, RDF.type, None)):
            if kind not in DECLARATIONS or not isinstance(iri, URIRef):
                continue
            key = str(iri)
            record = terms.setdefault(key, {'iri': key, 'kind': {OWL.Class: 'class', OWL.ObjectProperty: 'object_property', OWL.DatatypeProperty: 'datatype_property'}[kind],
                'labels': [], 'definitions': [], 'parents': [], 'domains': [], 'ranges': [], 'sources': []})
            for field, predicates in [('labels', [RDFS.label, SKOS.prefLabel]), ('definitions', [SKOS.definition]),
                                      ('parents', [RDFS.subClassOf, RDFS.subPropertyOf]), ('domains', [RDFS.domain]), ('ranges', [RDFS.range])]:
                values = [str(v) for p in predicates for v in graph.objects(iri, p) if not isinstance(v, BNode)]
                record[field] = sorted(set(record[field]+values))
            record['sources'].append(source_span(root, source, iri))
            for restriction in canonical.objects(iri, RDFS.subClassOf):
                if not isinstance(restriction, BNode) or (restriction, RDF.type, OWL.Restriction) not in canonical:
                    continue
                prop = canonical.value(restriction, OWL.onProperty)
                for quantifier in QUANTIFIERS:
                    target = canonical.value(restriction, OWL[quantifier])
                    if target is None:
                        continue
                    expression = sorted((str(p), o.n3()) for p, o in canonical.predicate_objects(restriction))
                    axiom = {'subject_class': key, 'property': str(prop), 'quantifier': quantifier,
                             'target_class': str(target) if isinstance(target, URIRef) else None,
                             'expression': expression}
                    axiom_id = 'urn:intentlineage:axiom:'+digest(axiom)
                    supported = quantifier == 'someValuesFrom' and isinstance(target, URIRef)
                    rules[axiom_id] = dict(axiom, axiom_id=axiom_id, source=source_span(root, source, iri),
                        operator='exists_typed_relation' if supported else 'unsupported_ontology_predicate',
                        supported=supported, open_world_missing_result='unknown',
                        operationalization_review_status='pending_overseer_review',
                        observation_assumptions=['Asserted class and typed relation witnesses are observable.',
                            'Absent witness is unknown under OWL open-world semantics.',
                            'Closed-observation completeness is an extra, explicitly reviewed harness assumption.'])
        for imported in graph.objects(None, OWL.imports):
            imports.append({'source_id': source_id, 'iri': str(imported), 'resolved': str(imported) in ontology_ids})
    result = {'version': supplement['version'], 'category_mapping': {'intent': 'intent', 'concept': 'ontology', 'rule': 'business_rules'},
              'terms': dict(sorted(terms.items())), 'rules': [rules[k] for k in sorted(rules)],
              'extensions': EXTENSIONS, 'sources': [sources[k] for k in sorted(sources)],
              'imports': sorted(imports, key=lambda i: (i['source_id'], i['iri'])),
              'unresolved_imports': [i for i in sorted(imports, key=lambda i: (i['source_id'], i['iri'])) if not i['resolved']],
              'import_closure_complete': all(i['resolved'] for i in imports)}
    result['semantic_sha256'] = digest(result)
    if previous and previous['version'] == result['version'] and previous['semantic_sha256'] != result['semantic_sha256']:
        raise ValueError('Changed taxonomy semantics require a new version')
    return result


def resolve_taxonomy(taxonomy, term):
    records = list(taxonomy['terms'].values())+taxonomy['extensions']
    candidates = sorted({r['iri'] for r in records if term == r['iri'] or
                         term.casefold() in {label.casefold() for label in r['labels']} or
                         term.casefold() == re.split(r'[/#]', r['iri'])[-1].casefold()})
    return {'status': 'resolved' if len(candidates) == 1 else 'ambiguous' if candidates else 'unmapped', 'candidates': candidates}


def validate_rule_source(taxonomy, proposal):
    axiom = next((r for r in taxonomy['rules'] if r['axiom_id'] == proposal.get('axiom_id')), None)
    if not axiom or not axiom['supported']:
        raise ValueError('No supported source axiom justifies the proposed rule')
    if proposal != axiom:
        raise ValueError('Rule translation differs from the inventoried axiom')
    if axiom['target_class'] not in taxonomy['terms'] or axiom['property'] not in taxonomy['terms']:
        raise ValueError('Rule axiom depends on unresolved declarations')
    return proposal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('resources/ontology/generated/taxonomy-v2.json'))
    args = parser.parse_args()
    catalog = OntologyCatalog(Path('resources/ontology/manifest.json'))
    result = build_taxonomy(catalog, Path('resources/ontology/prompt-sources.json'))
    write_json(args.output, result)
    print(f"Saved {len(result['terms'])} terms, {len(result['rules'])} restrictions and {len(result['unresolved_imports'])} unresolved imports")


if __name__ == '__main__':
    main()
