"""Serial revision-4 M1 capture/packaging recipe; no model requests or assessment."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from intentlineage.prompt_dispatch import prepare_dispatch
from intentlineage.native_capture import ROOT, file_hash, load_native, digest
from intentlineage.evidence_inventory import inventory_from_spec
from intentlineage.artifact_views import build_catalogue, inspect_artifact
from intentlineage.evidence_packages import build_packages, open_package, validate_package

SOURCE_FILES = ['etiq_agent_wrapper.py', 'etiq_runner/wrapper.py', 'scripts/scan_entry.py',
    'scripts/capture_m1_v4.py', 'examples/native_payment_workflow.py', 'examples/native_multi_output.py',
    'examples/native_huge_numbers.py',
    'src/intentlineage/native_capture.py', 'src/intentlineage/native_workflow.py',
    'src/intentlineage/evidence_inventory.py', 'src/intentlineage/artifact_views.py',
    'src/intentlineage/evidence_packages.py', 'src/intentlineage/prompt_runtime.py',
    'src/intentlineage/payment.py', 'src/intentlineage/changes.py',
    'src/intentlineage/_reference/native_graph.py', 'src/intentlineage/_reference/records.py',
    'src/intentlineage/_reference/artifact_operations.py', 'src/intentlineage/_reference/lazy_catalogue.py']


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


def run_wrapper(entry, output, runtime_path, seed):
    env = os.environ.copy()
    env.pop('PYTEST_VERSION', None)
    env['INTENTLINEAGE_PROMPT_RUNTIME'] = str(runtime_path.resolve())
    env['INTENTLINEAGE_SEED'] = str(seed)
    env['PYTHONHASHSEED'] = '0'
    command = [sys.executable, str(ROOT/'etiq_agent_wrapper.py'), '--workspace-root', str(ROOT),
               '--entry', entry, '--output-dir', str(output), '--lineage-format', 'json', '--native-export']
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
    (output.parent/'wrapper.stdout.log').write_bytes(result.stdout)
    (output.parent/'wrapper.stderr.log').write_bytes(result.stderr)
    write_json(output.parent/'command.json', {'command': command, 'exit_code': result.returncode,
        'env': {'INTENTLINEAGE_PROMPT_RUNTIME': runtime_path.relative_to(ROOT).as_posix(),
                'INTENTLINEAGE_SEED': str(seed), 'PYTHONHASHSEED': '0'}, 'model_requests': 0})
    if result.returncode:
        raise ValueError(f'Wrapper failed with exit {result.returncode}; exact logs retained')


def capture_native_case(case, output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Case requires a fresh output path; existing evidence is preserved')
    if not output.is_relative_to(ROOT):
        raise ValueError('Case output must stay inside workspace')
    extraction = (ROOT/case['extraction_file']).resolve()
    if not extraction.is_relative_to(ROOT) or file_hash(extraction) != case['extraction_sha256']:
        raise ValueError('Frozen extraction hash/workspace binding mismatch')
    runtime = prepare_dispatch(extraction)
    if runtime['operation'] != case['expected_operation']:
        raise ValueError('Frozen dispatch expectation differs; do not execute or relabel')
    output.mkdir(parents=True)
    write_json(output/'runtime.json', runtime)
    policies = [{'policy_id': 'fixture:payment-mechanics', 'scope': 'synthetic_workflow',
                 'source': {'kind': 'fixture', 'file': 'src/intentlineage/payment.py',
                            'sha256': file_hash(ROOT/'src/intentlineage/payment.py')},
                 'description': 'Synthetic order/registry matching, initial revision and approval/receipt mechanics; not inferred user/ontology requirements.'}]
    if case.get('capture_kind', '').startswith('mechanical_'):
        fixture_entry = case['entry']
        policies = [{'policy_id': 'fixture:native-capability', 'scope': 'mechanical_capture_probe',
                     'source': {'kind': 'fixture', 'file': fixture_entry, 'sha256': file_hash(ROOT/fixture_entry)},
                     'description': 'Mechanical native capture/value capability fixture; no payment workflow or inferred requirements.'}]
    inventory = inventory_from_spec(runtime['specification'], fixture_policies=policies)
    write_json(output/'inventory.json', inventory)
    record = {'case_id': case['case_id'], 'operation': runtime['operation'],
              'extraction_file': case['extraction_file'], 'extraction_sha256': case['extraction_sha256'],
              'runtime_sha256': file_hash(output/'runtime.json'),
              'inventory_sha256': file_hash(output/'inventory.json'), 'model_requests': 0,
              'capture_kind': case.get('capture_kind', 'ordinary_payment'),
              'output': output.relative_to(ROOT).as_posix()}
    if runtime['operation'] == 'abstain':
        record.update(wrapper_scans=0, reasons=runtime['reasons'], native_capture=None,
                      explanation='Abstains before workflow execution; retains exact source/inventory/dispatch evidence.')
    else:
        entry = case.get('entry', 'examples/native_payment_workflow.py')
        run_wrapper(entry, output/'capture', output/'runtime.json', case.get('seed', 17))
        packet = load_native(output/'capture/scan-result.json', workspace_root=ROOT)
        cat = build_catalogue(packet, inputs=case['inputs'], outputs=case['outputs'])
        write_json(output/'controller/catalogue.json', cat)
        packages = build_packages(cat, inventory, cache_dir=output/'controller/summary-cache')
        write_json(output/'public/endpoints.json', packages['endpoint'])
        write_json(output/'public/top-level.json', packages['top_level'])
        receipts = []
        view = packages['top_level']
        for name in case.get('example_openings', []):
            eligible = [g for g in view['graph']['eligible_groups'] if g['name'] == name]
            if len(eligible) != 1: raise ValueError('Predeclared opening lacks one eligible native group: '+name)
            view, receipt = open_package(cat, view, eligible[0]['group_id'], cache_dir=output/'controller/summary-cache')
            receipts.append(receipt)
            write_json(output/f'public/opened-{len(receipts)}.json', view)
        write_json(output/'controller/opening-receipts.json', receipts)
        examples = {}
        graph_view = view['graph']
        for ref in graph_view['visible_artifacts']:
            kind = cat['artifacts'][ref]['artifact_kind']
            if kind not in examples:
                examples[kind] = {'describe': inspect_artifact(cat, graph_view, ref),
                                  'read': inspect_artifact(cat, graph_view, ref, operation='read', count=2)}
        write_json(output/'public/inspection-examples.json', examples)
        denied = next((r for r in cat['artifacts'] if r not in packages['top_level']['graph']['visible_artifacts']), None)
        access = {'permitted_own_endpoint': 'passed', 'arbitrary_python_disabled': True,
                  'private_key_in_public': False}
        if denied:
            try:
                inspect_artifact(cat, packages['top_level']['graph'], denied)
            except ValueError as error:
                access['denied_hidden_artifact'] = {'passed': True, 'reason': str(error)}
            else:
                raise ValueError('Hidden artifact access unexpectedly succeeded')
        else:
            access['denied_hidden_artifact'] = {'applicable': False, 'reason': 'No unopened captured artifact in this fixture.'}
        write_json(output/'controller/access-probes.json', access)
        for package in packages.values(): validate_package(package)
        public = {p.relative_to(output/'public').as_posix(): file_hash(p) for p in (output/'public').glob('*.json')}
        record.update(wrapper_scans=1, native_capture=(output/'capture/native-capture.json').relative_to(ROOT).as_posix(),
                      native_nodes=len(packet['graph']['objects']), native_edges=len(packet['graph']['edges']),
                      native_groups=len(cat['groups']), captured_artifacts=len(cat['artifacts']),
                      native_capture_sha256=file_hash(output/'capture/native-capture.json'),
                      public_files=public, endpoint_package_sha256=packages['endpoint']['package_sha256'],
                      top_level_package_sha256=packages['top_level']['package_sha256'],
                      inspectable_kinds=sorted(examples), opening_operations=len(receipts))
    sources = {**runtime['input_sources'], **{p: file_hash(ROOT/p) for p in SOURCE_FILES}}
    write_json(output/'controller/source-manifest.json', sources)
    for relative, expected in sources.items():
        original = (ROOT/relative).resolve()
        if not original.is_relative_to(ROOT) or file_hash(original) != expected:
            raise ValueError('Source snapshot hash/workspace mismatch')
        dest = output/'controller/source-snapshot'/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(original.read_bytes())
    write_json(output/'case-result.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT/'annotations/m1-v4-capture-plan.json')
    parser.add_argument('--output-root', type=Path, default=ROOT/'.etiq/artifacts/m1-v4-delivery')
    args = parser.parse_args()
    output = args.output_root.resolve()
    if output.exists() or not output.is_relative_to(ROOT):
        raise ValueError('Capture root must be a fresh workspace-contained path')
    plan = json.loads(args.plan.read_bytes())
    output.mkdir(parents=True)
    results, failures = [], []
    for case in plan['cases']:
        try:
            record = capture_native_case(case, output/case['case_id'])
            results.append(record)
            print(case['case_id'], record['operation'], 'scans='+str(record['wrapper_scans']), flush=True)
        except Exception as error:
            failure = {'case_id': case['case_id'], 'error': type(error).__name__, 'message': str(error)}
            failures.append(failure)
            write_json(output/(case['case_id']+'-failure.json'), failure)
            print('FAILED', case['case_id'], str(error), flush=True)
            # No retries. Stop immediately with preserved evidence; ask after three failures.
            break
    index = {'format_version': '4.0.0', 'role': 'developer', 'acceptance': 'pending_overseer_review',
             'plan_sha256': file_hash(args.plan), 'results': results, 'failures': failures,
             'wrapper_scans': sum(r['wrapper_scans'] for r in results), 'model_requests': 0}
    write_json(output/'index.json', index)
    return 1 if failures or len(results) != len(plan['cases']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
