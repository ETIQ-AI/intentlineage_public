"""Local LangExtract inference and conservative, replayable source grounding."""
import argparse
from collections import Counter
from copy import deepcopy
import dataclasses
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import time
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, StrictBool, StrictInt, StrictStr, ValidationError, model_validator

from .compiler import digest, write_json
from .contracts import Contract, Version
from .taxonomy import resolve_taxonomy
from .source_scope import agreement_reasons

ROOT = Path(__file__).resolve().parents[2]
FIELDS = Literal['invoice_id', 'amount', 'currency', 'supplier_id', 'account_id', 'purchase_order_id', 'revision']
ROLES = {'goal', 'object', 'parameter', 'constraint', 'condition'}
NEGATION = re.compile(r"\b(?:do\s+not|don't|never|not)\b", re.I)
NORMALIZER_VERSION = '2.2.0'


class PromptDocument(Contract):
    source_id: StrictStr = Field(min_length=1)
    version: Version
    text: StrictStr = Field(min_length=1)
    sha256: StrictStr

    @model_validator(mode='after')
    def input_hash(self):
        if hashlib.sha256(self.text.encode('utf-8')).hexdigest() != self.sha256:
            raise ValueError('prompt hash does not match exact input text')
        return self


class PromptSpan(Contract):
    source_id: StrictStr
    prompt_sha256: StrictStr
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    quote: StrictStr = Field(min_length=1)

    @model_validator(mode='after')
    def ordered(self):
        if self.end <= self.start:
            raise ValueError('Prompt span end must follow start')
        return self


class ExtractionAttributes(Contract):
    action: StrictStr | None = None
    field: FIELDS | None = None
    value: StrictStr | None = None
    operator: Literal['equals', 'preserve', 'bind', 'carry', 'reconcile'] | None = None
    negated: StrictBool = False
    condition: StrictStr | None = None
    ontology_term: StrictStr | None = None


def normalize_extractions(prompt, raw, taxonomy, provenance=None, *, normalizer_version=None):
    policy_version = normalizer_version or NORMALIZER_VERSION
    if policy_version not in {'2.0.0', '2.1.0', NORMALIZER_VERSION}:
        raise ValueError('Unsupported normalizer version')
    source = PromptDocument.model_validate(prompt)
    if raw.get('text') != source.text or not isinstance(raw.get('extractions'), list):
        raise ValueError('Raw extraction envelope does not match its prompt')
    records, counters = [], Counter()
    condition_spans = []
    for item in raw['extractions']:
        if item.get('extraction_class') == 'condition' and (item.get('attributes') or {}).get('condition'):
            try:
                interval = item['char_interval']
                candidate = PromptSpan(source_id=source.source_id, prompt_sha256=source.sha256,
                    start=interval['start_pos'], end=interval['end_pos'], quote=item['extraction_text'])
                if source.text[candidate.start:candidate.end] == candidate.quote:
                    condition_spans.append(candidate)
            except (KeyError, TypeError, ValidationError):
                pass
    for index, item in enumerate(raw['extractions']):
        role, reasons, span, meaning = item.get('extraction_class'), [], None, {}
        quote = item.get('extraction_text')
        if role not in ROLES:
            reasons.append('unsupported_extraction_class')
        interval = item.get('char_interval')
        if not isinstance(interval, dict):
            reasons.append('missing_span')
        else:
            try:
                span = PromptSpan(source_id=source.source_id, prompt_sha256=source.sha256,
                                  start=interval['start_pos'], end=interval['end_pos'], quote=quote)
                if span.end > len(source.text) or source.text[span.start:span.end] != quote:
                    reasons.append('span_alignment_mismatch')
            except (ValidationError, KeyError, TypeError):
                reasons.append('invalid_span')
        try:
            attrs = ExtractionAttributes.model_validate(item.get('attributes') or {})
            meaning = attrs.model_dump(mode='json', exclude_none=True)
            if role == 'parameter':
                if attrs.field is None or attrs.value is None:
                    reasons.append('missing_parameter')
                elif attrs.field == 'amount':
                    try:
                        quoted = re.fullmatch(r'(?:[A-Z]{3}\s+)?([+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)', quote or '')
                        if not quoted or Decimal(quoted[1]) != Decimal(attrs.value) or not Decimal(attrs.value).is_finite():
                            reasons.append('unsupported_value')
                    except InvalidOperation:
                        reasons.append('unsupported_value')
                elif not re.search(r'(?<![\w-])'+re.escape(attrs.value)+r'(?![\w-])', quote or ''):
                    reasons.append('unsupported_value')
            if role == 'goal':
                if attrs.action is None:
                    reasons.append('missing_action')
                elif attrs.action == 'pay' and not re.search(r'\b(?:pay|settle|payment)\b', quote or '', re.I):
                    reasons.append('unsupported_action')
                elif attrs.action == 'draft' and not re.search(r'\bdraft\b', quote or '', re.I):
                    reasons.append('unsupported_action')
                if policy_version == '2.0.0':
                    # Exact historical replay only; compiler/dispatch upgrade before use.
                    has_negation = bool(NEGATION.search(quote or ''))
                    if has_negation != attrs.negated:
                        reasons.append('negation_scope_mismatch')
                    if span and NEGATION.search(source.text[max(0, span.start-16):span.start]) and not has_negation:
                        reasons.append('negation_scope_not_quoted')
            if role == 'constraint' and attrs.operator is None:
                reasons.append('missing_operator')
            if role == 'condition' and attrs.condition is None:
                reasons.append('missing_condition')
            if policy_version != '2.0.0' and role in {'constraint', 'goal'} and span and 'span_alignment_mismatch' not in reasons:
                reasons.extend(agreement_reasons(source.text, span, role, meaning, condition_spans, policy_version=policy_version))
        except ValidationError as error:
            reasons.append('attribute_schema: '+str(error))
        term = meaning.get('ontology_term') or ('urn:intentlineage:action:'+meaning['action'] if role == 'goal' else quote if role == 'object' else '')
        grounding = resolve_taxonomy(taxonomy, term) if term else {'status': 'unmapped', 'candidates': []}
        key_base = f"{role}:{meaning.get('field') or meaning.get('action') or meaning.get('operator') or meaning.get('ontology_term') or 'element'}"
        counters[key_base] += 1
        records.append({'element_key': key_base+':'+str(counters[key_base]), 'raw_index': index,
                        'role': role, 'raw_text': quote, 'source': span.model_dump() if span else None,
                        'meaning': meaning, 'grounding': grounding, 'alignment_status': item.get('alignment_status'),
                        'status': 'rejected' if reasons else 'accepted', 'reasons': reasons})
    metadata = dict(provenance or {})
    metadata['taxonomy_version'] = taxonomy['version']
    metadata['taxonomy_semantic_sha256'] = taxonomy['semantic_sha256']
    metadata['normalizer_version'] = policy_version
    return {'format_version': '2.0.0', 'prompt': source.model_dump(), 'provenance': metadata,
            'raw_result': deepcopy(raw), 'records': records,
            'limits': ['Accepted means structurally grounded, not independently correct extraction.',
                       'Rejected and unmapped outputs remain visible; no automatic completion from examples.']}


def validate_extraction_packet(saved, taxonomy, *, current=False):
    policy_version = saved['provenance'].get('normalizer_version')
    if policy_version not in {'2.0.0', '2.1.0', NORMALIZER_VERSION}:
        raise ValueError('Unsupported saved normalizer version')
    replayed = normalize_extractions(saved['prompt'], saved['raw_result'], taxonomy,
                                    saved['provenance'], normalizer_version=policy_version)
    if replayed != saved:
        raise ValueError('Saved extraction differs from deterministic normalization replay')
    if current and policy_version != NORMALIZER_VERSION:
        targets = ['2.1.0', NORMALIZER_VERSION] if policy_version == '2.0.0' else [NORMALIZER_VERSION]
        for target in targets:
            prior = {'normalizer_version': replayed['provenance']['normalizer_version'],
                     'packet_semantic_sha256': digest(replayed)}
            provenance = {**replayed['provenance'], 'normalization_predecessor': prior}
            if target == NORMALIZER_VERSION:
                lineage = list(replayed['provenance'].get('normalization_predecessors', []))
                previous = replayed['provenance'].get('normalization_predecessor')
                if previous and previous not in lineage: lineage.append(previous)
                if prior not in lineage: lineage.append(prior)
                provenance['normalization_predecessors'] = lineage
            replayed = normalize_extractions(replayed['prompt'], replayed['raw_result'], taxonomy,
                                            provenance, normalizer_version=target)
        return replayed
    return replayed


def replay_extraction(path, taxonomy, *, current=False):
    saved = json.loads(Path(path).read_bytes())
    if saved['provenance']['taxonomy_semantic_sha256'] != taxonomy['semantic_sha256']:
        raise ValueError('Extraction taxonomy provenance is stale')
    for record in saved['provenance'].get('raw_logs', []):
        for kind in ['request', 'response']:
            artifact = (ROOT/record[f'{kind}_file']).resolve()
            if not artifact.is_relative_to(ROOT) or hashlib.sha256(artifact.read_bytes()).hexdigest() != record[f'{kind}_sha256']:
                raise ValueError('Raw extraction log hash mismatch')
    return validate_extraction_packet(saved, taxonomy, current=current)


def require_local_endpoint(url):
    parsed = urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.path not in {'', '/'} or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('Extraction requires a local base endpoint')
    return url.rstrip('/')


class RecordingTransport:
    """Per-instance inspection of the official provider's local HTTP traffic."""
    def __init__(self, endpoint, output):
        import requests
        self.exceptions = requests.exceptions
        self.session = requests.Session()
        self.session.trust_env = False
        self.endpoint, self.output, self.logs = endpoint, output, []

    def post(self, url, **kwargs):
        if not url.startswith(self.endpoint+'/api/'):
            raise ValueError('Provider attempted a nonlocal endpoint')
        start = time.perf_counter()
        response = self.session.post(url, allow_redirects=False, **kwargs)
        ordinal = len(self.logs)+1
        paths = {'request': self.output/f'http-request-{ordinal:02d}.json',
                 'response': self.output/f'http-response-{ordinal:02d}.json'}
        body = response.request.body
        paths['request'].write_bytes(body.encode('utf-8') if isinstance(body, str) else body)
        paths['response'].write_bytes(response.content)
        self.logs.append({'url': url, 'status': response.status_code, 'seconds': time.perf_counter()-start,
                          **{f'{kind}_{field}': path.relative_to(ROOT).as_posix() if field == 'file' else hashlib.sha256(path.read_bytes()).hexdigest()
                             for kind, path in paths.items() for field in ['file', 'sha256']}})
        return response


def extract_local(prompt, taxonomy, output, endpoint='http://127.0.0.1:11435'):
    import langextract as lx
    from langextract.factory import ModelConfig, create_model

    source = PromptDocument.model_validate(prompt)
    endpoint = require_local_endpoint(endpoint)
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError('Extraction evidence must stay inside the workspace')
    output.mkdir(parents=True, exist_ok=False)
    model_meta = json.loads((ROOT/'resources/extraction/model-v2.json').read_bytes())
    example_file = ROOT/'resources/extraction/examples-v2.json'
    instruction_file = ROOT/'resources/extraction/instructions-v2.txt'
    example_data = json.loads(example_file.read_bytes())
    examples = [lx.data.ExampleData(text=row['text'], extractions=[lx.data.Extraction(**e) for e in row['extractions']]) for row in example_data['examples']]
    settings = {'temperature': 0.0, 'seed': 17, 'num_ctx': 8192, 'max_output_tokens': 2048, 'timeout': 240, 'keep_alive': '10m'}
    model = create_model(ModelConfig(model_id=model_meta['model']['name'], provider='OllamaLanguageModel',
             provider_kwargs={'model_url': endpoint, 'api_key': None, **settings}), examples=examples, use_schema_constraints=True)
    transport = RecordingTransport(endpoint, output)
    model._requests = transport
    tags = transport.session.get(endpoint+'/api/tags', timeout=10).json()
    observed = next(m for m in tags['models'] if m['name'] == model_meta['model']['name'])
    if observed['digest'] != model_meta['model']['digest']:
        raise ValueError('Installed local model digest differs from the pinned model')
    start = time.perf_counter()
    try:
        aligned = lx.extract(source.text, prompt_description=instruction_file.read_text(encoding='utf-8'),
                             examples=examples, model=model, max_workers=1, batch_length=1,
                             max_char_buffer=2000, extraction_passes=1, show_progress=False,
                             use_schema_constraints=False)
        raw = json.loads(json.dumps(dataclasses.asdict(aligned), default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj)))
        provenance = {'evidence_kind': 'local_llm_extraction', 'created_at': datetime.now(timezone.utc).isoformat(),
             'langextract_version': version('langextract'), 'model_id': observed['name'], 'model_digest': observed['digest'],
             'backend': 'ollama', 'backend_version': model_meta['backend_version'], 'endpoint': endpoint,
             'instruction_version': '2.0.0', 'examples_version': example_data['version'],
             'instruction_sha256': hashlib.sha256(instruction_file.read_bytes()).hexdigest(),
             'examples_sha256': hashlib.sha256(example_file.read_bytes()).hexdigest(),
             'settings': settings, 'max_workers': 1, 'extraction_passes': 1, 'automatic_retries': 0,
             'seconds': time.perf_counter()-start, 'raw_logs': transport.logs,
             'private_targets_supplied_to_model': False}
        snapshots = {}
        for relative in ['src/intentlineage/extraction.py', 'src/intentlineage/source_scope.py', 'src/intentlineage/contracts.py',
                         'src/intentlineage/compiler.py', 'src/intentlineage/taxonomy.py',
                         'resources/extraction/instructions-v2.txt', 'resources/extraction/examples-v2.json',
                         'resources/extraction/model-v2.json', 'resources/ontology/generated/taxonomy-v2.json']:
            original = ROOT/relative
            sha = hashlib.sha256(original.read_bytes()).hexdigest()
            target = output.parent/'source-snapshots'/sha/original.name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                raise ValueError('Existing extraction source snapshot hash mismatch')
            if not target.exists():
                target.write_bytes(original.read_bytes())
            snapshots[relative] = {'file': target.relative_to(ROOT).as_posix(), 'sha256': sha}
        provenance['source_snapshots'] = snapshots
        result = normalize_extractions(source.model_dump(), raw, taxonomy, provenance)
        write_json(output/'aligned-result.json', raw)
        write_json(output/'extraction.json', result)
        return result
    except Exception as error:
        write_json(output/'failure.json', {'type': type(error).__name__, 'error': str(error), 'raw_logs': transport.logs,
                                          'seconds': time.perf_counter()-start})
        raise
    finally:
        transport.session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--source-id')
    parser.add_argument('--prompt-file', type=Path)
    parser.add_argument('--output-root', type=Path, default=Path('evidence/extraction-v2'))
    parser.add_argument('--only', help='Development source ID for a focused real spike')
    args = parser.parse_args()
    taxonomy = json.loads((ROOT/'resources/ontology/generated/taxonomy-v2.json').read_bytes())
    if args.development:
        rows = json.loads((ROOT/'annotations/prompt-development-v2.json').read_bytes())['prompts']
        sources = [{k: row[k] for k in ['source_id', 'version', 'text', 'sha256']} for row in rows if not args.only or row['source_id'] == args.only]
    elif args.prompt_file and args.source_id:
        text = args.prompt_file.read_text(encoding='utf-8')
        sources = [{'source_id': args.source_id, 'version': '1.0.0', 'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest()}]
    else:
        parser.error('Use --development or --prompt-file with --source-id')
    for source in sources:
        result = extract_local(source, taxonomy, ROOT/args.output_root/source['source_id'])
        print(source['source_id'], 'records', len(result['records']), 'rejected', sum(r['status'] == 'rejected' for r in result['records']), flush=True)


if __name__ == '__main__':
    main()
