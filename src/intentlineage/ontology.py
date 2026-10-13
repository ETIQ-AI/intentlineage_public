"""Resolve only pinned declarations; keep ambiguity and local policy explicit."""
import argparse
import hashlib
import json
from pathlib import Path

from open_ontologies_lite import OntologyEngine, vocab_check
from open_ontologies_lite.shacl import shacl_validate
from rdflib import BNode, Graph, OWL, RDF, URIRef
from rdflib.compare import to_canonical_graph

DECLARATIONS = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty}
EPO = 'http://data.europa.eu/a4g/ontology#'


class OntologyCatalog:
    def __init__(self, manifest_path: Path):
        self.root = manifest_path.parent
        self.manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        self.sources = {source['id']: source for source in self.manifest['sources']}
        self.graphs = {}
        for source in self.sources.values():
            path = (self.root / source['file']).resolve()
            if not path.is_relative_to(self.root.resolve()):
                raise ValueError('Ontology source escapes resource root')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != source['sha256']:
                raise ValueError(f"Ontology source hash mismatch: {source['id']}")
            self.graphs[source['id']] = Graph().parse(data=raw, format='xml' if path.suffix == '.rdf' else 'turtle')
        for binding in self.manifest['bindings']:
            graph = self.graphs[binding['source_id']]
            if not any((URIRef(binding['iri']), RDF.type, kind) in graph for kind in DECLARATIONS):
                raise ValueError(f"Missing declaration: {binding['key']}")

    def resolve(self, term: str) -> dict:
        for extension in self.manifest['local_extensions']:
            if term in {extension['key'], extension['iri']}:
                return {'status': 'local_extension', 'iri': extension['iri'], 'candidates': [],
                        'provenance': {key: extension[key] for key in ['source', 'version', 'definition']}}
        exact = [item for item in self.manifest['bindings'] if term in {item['key'], item['iri']}]
        matches = exact or [item for item in self.manifest['bindings'] if item['key'].split(':', 1)[1] == term]
        if len(matches) != 1:
            return {'status': 'unresolved', 'iri': None, 'provenance': None,
                    'reason': 'ambiguous' if matches else 'not_in_pinned_slice',
                    'candidates': sorted(item['iri'] for item in matches)}
        binding = matches[0]
        return {'status': 'resolved', 'iri': binding['iri'], 'candidates': [],
                'declaration_line': binding['declaration_line'],
                'provenance': dict(self.sources[binding['source_id']])}

    def slice_text(self) -> str:
        selected = Graph()
        for source_id, graph in self.graphs.items():
            pending = [URIRef(item['iri']) for item in self.manifest['bindings'] if item['source_id'] == source_id]
            pending.extend(graph.subjects(RDF.type, OWL.Ontology))
            seen = set()
            while pending:
                subject = pending.pop()
                if subject in seen:
                    continue
                seen.add(subject)
                for triple in graph.triples((subject, None, None)):
                    selected.add(triple)
                    if isinstance(triple[2], BNode):
                        pending.append(triple[2])
        # Sorted canonical N-Triples are also valid Turtle. Blank-node IDs must
        # not vary between compilations; imports remain references, never fetched.
        canonical = to_canonical_graph(selected)
        return ''.join(sorted(canonical.serialize(format='nt').splitlines(keepends=True)))


def check_operations(catalog: OntologyCatalog) -> dict:
    text = catalog.slice_text()
    engine = OntologyEngine()
    triples = engine.load(text)
    query = 'SELECT DISTINCT ?s WHERE { ?s a ?k . VALUES ?k { <http://www.w3.org/2002/07/owl#Class> <http://www.w3.org/2002/07/owl#ObjectProperty> <http://www.w3.org/2002/07/owl#DatatypeProperty> } }'
    declarations = {row['s'] for row in engine.query(query)['rows']}
    path = engine.query(f'SELECT ?parent WHERE {{ <{EPO}MonetaryValue> <http://www.w3.org/2000/01/rdf-schema#subClassOf>+ ?parent }}')['rows']
    prefix = f'@prefix epo: <{EPO}> . @prefix ex: <urn:example:> . '
    valid = prefix + 'ex:invoice a epo:Invoice; epo:hasAmountDueForPayment ex:money . ex:money a epo:MonetaryValue .'
    invalid = prefix + 'ex:invoice a epo:Invoice .'
    shapes = prefix + '@prefix sh: <http://www.w3.org/ns/shacl#> . ex:shape a sh:NodeShape; sh:targetClass epo:Invoice; sh:property [sh:path epo:hasAmountDueForPayment; sh:minCount 1] .'
    return {
        'engine': catalog.manifest['engine'], 'syntax_valid': engine.validate(text).ok,
        'malformed_rejected': not engine.validate('this is malformed RDF').ok,
        'triples': triples, 'selected_terms_found': sum(item['iri'] in declarations for item in catalog.manifest['bindings']),
        'subclass_path_found': any(row['parent'] == EPO + 'MaskableObject' for row in path),
        'declared_vocab': vocab_check(text, valid),
        'undeclared_vocab': vocab_check(text, prefix + 'ex:invoice a epo:InventedPaymentClass .'),
        'shacl_valid': shacl_validate(valid, shapes),
        'shacl_invalid': shacl_validate(invalid, shapes),
        'shacl_no_focus': shacl_validate(prefix + 'ex:money a epo:MonetaryValue .', shapes),
        'imports_resolved': False,
        'limits': ['Selected declarations and reachable blank-node axioms only.',
                   'No import closure, OWL-DL consistency, or payment business verification.',
                   'SHACL shape is a local operation demonstration, not an upstream rule.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('resources/ontology/manifest.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('resources/ontology/generated'))
    args = parser.parse_args()
    catalog = OntologyCatalog(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    text = catalog.slice_text()
    (args.output_dir / 'slice.ttl').write_bytes(text.encode('utf-8'))
    report = check_operations(catalog)
    report['slice_sha256'] = hashlib.sha256(text.encode('utf-8')).hexdigest()
    (args.output_dir / 'operations.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    terms = [item['key'] for item in catalog.manifest['bindings']] + [item['key'] for item in catalog.manifest['local_extensions']] + catalog.manifest['unresolved']
    (args.output_dir / 'bindings.json').write_text(json.dumps({term: catalog.resolve(term) for term in terms}, indent=2)+'\n', encoding='utf-8')
    print(f"Saved {report['selected_terms_found']} selected terms and {report['triples']} RDF triples")


if __name__ == '__main__':
    main()
