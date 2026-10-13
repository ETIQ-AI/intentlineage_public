"""Development-only extraction evaluation against independently authored targets."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from .compiler import write_json
from .extraction import ROOT, replay_extraction


def _matches(record, target):
    if record['role'] != target['role'] or not record.get('source'):
        return False
    span = record['source']
    if not (span['start'] <= target['start'] and span['end'] >= target['end']):
        return False
    for key, value in target['attributes'].items():
        actual = record['meaning'].get(key)
        if key == 'value' and target['attributes'].get('field') == 'amount':
            if actual is None or Decimal(actual) != Decimal(value):
                return False
        elif actual != value:
            return False
    return True


def evaluate_packet(packet, targets):
    accepted = [r for r in packet['records'] if r['status'] == 'accepted']
    matched, used, exact = [], set(), 0
    for index, target in enumerate(targets):
        candidates = [i for i, r in enumerate(accepted) if _matches(r, target)]
        if candidates:
            matched.append(index)
            used.update(candidates)
            exact += any(accepted[i]['source']['start'] == target['start'] and
                         accepted[i]['source']['end'] == target['end'] for i in candidates)
    return {'target_count': len(targets), 'recovered_targets': len(matched),
            'omitted_targets': len(targets)-len(matched), 'exact_span_target_matches': exact,
            'unmatched_accepted_proposals': len(accepted)-len(used),
            'rejected_records': len(packet['records'])-len(accepted),
            'accepted_records': len(accepted), 'total_records': len(packet['records']),
            'omitted_target_indices': [i for i in range(len(targets)) if i not in matched],
            'grounding_counts': dict(Counter(r['grounding']['status'] for r in accepted))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, default=ROOT/'evidence/extraction-v2-development')
    parser.add_argument('--output', type=Path, default=ROOT/'annotations/prompt-development-results-v2.json')
    args = parser.parse_args()
    target_file = ROOT/'annotations/prompt-development-v2.json'
    taxonomy = json.loads((ROOT/'resources/ontology/generated/taxonomy-v2.json').read_bytes())
    rows = []
    for target in json.loads(target_file.read_bytes())['prompts']:
        path = args.evidence_root/target['source_id']/'extraction.json'
        packet = replay_extraction(path, taxonomy)
        if packet['prompt']['sha256'] != target['sha256']:
            raise ValueError('Evaluation input differs from frozen target prompt')
        rows.append({'source_id': target['source_id'], 'evidence': path.relative_to(ROOT).as_posix(),
                     'evidence_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     **evaluate_packet(packet, target['targets'])})
    keys = ['target_count', 'recovered_targets', 'omitted_targets', 'exact_span_target_matches',
            'unmatched_accepted_proposals', 'rejected_records', 'accepted_records', 'total_records']
    result = {'format_version': '2.0.0', 'review_status': 'developer_checked_pending_overseer_review',
              'private_evaluation_only': True, 'target_sha256': hashlib.sha256(target_file.read_bytes()).hexdigest(),
              'method': 'Role and partial target attributes with covering source span; exact boundaries counted separately.',
              'limitations': ['Targets are minimum candidates, not exhaustive gold; unmatched proposals are not automatically false positives.',
                             'Grounding acceptance does not establish semantic correctness. No examples were retuned.'],
              'prompts': rows, 'totals': {key: sum(row[key] for row in rows) for key in keys}}
    write_json(args.output, result)
    print(json.dumps(result['totals']))


if __name__ == '__main__':
    main()
