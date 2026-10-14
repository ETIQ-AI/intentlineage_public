"""Private payment-source injections and mechanical native-capture qualification.

Adapted from use_case_icp n27pb._mutant_source/_hard_fault_qualification.
Faults are payment-specific; neither source mutations nor truth enter review input.
"""
import ast
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import os

from .native_capture import ROOT, digest, file_hash, load_native
from .prompt_dispatch import prepare_dispatch
from .evidence_inventory import inventory_from_spec
from .artifact_views import build_catalogue
from .evidence_packages import build_packages
from .review_batches import build_review_plan
from .review_contract import canonical_bytes
from .extraction import replay_extraction
from .review_runner import SESSION_VERSION,MATRIX_VERSION

VARIANTS = ('clean', 'benign', 'amount-persistent', 'amount-repaired',
            'account-persistent', 'account-repaired')


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical_bytes(value) + b'\n')


def source_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _replace_function(source, function, old, new):
    """Reuse unique-site substitution, scoped to a declared actual AST boundary."""
    tree = ast.parse(source)
    candidates = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function]
    if len(candidates) != 1:
        raise ValueError('Declared function boundary is absent or ambiguous: ' + function)
    node = candidates[0]
    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[:node.lineno-1])
    end = sum(len(line) for line in lines[:node.end_lineno])
    body = source[start:end]
    if body.count(old) != 1:
        raise ValueError('Mutation site is not unique within declared boundary')
    changed = source[:start] + body.replace(old, new, 1) + source[end:]
    if ast.dump(tree) == ast.dump(ast.parse(changed)):
        raise ValueError('Mutation did not change the AST')
    line = source.count('\n', 0, start + body.index(old)) + 1
    return changed, {'function':function, 'start_line':line, 'original_snippet':old,
                     'mutant_snippet':new, 'candidate_count':1,
                     'operator':'scoped_single_source_substitution'}


def inject_source(source, variant, *, seed=17):
    if variant not in VARIANTS or type(seed) is not int or seed < 0:
        raise ValueError('Unsupported fault/control or seed; bank supports only declared amount/account injections')
    changed = source
    sites = []
    anchor = '    def approval_value(frame):'
    if variant.startswith('amount'):
        prefix = "    value = str(float(payment.to_dict(orient='records')[0]['amount']) * 100)\n    payment = payment.assign(amount=value)\n"
    elif variant.startswith('account'):
        prefix = f"    payment = payment.assign(account_id='ACC-{seed+1}')\n"
    elif variant == 'benign':
        prefix = "    value = payment.to_dict(orient='records')[0]['amount']\n    spelling = value + ('.0' if '.' not in value else '0')\n    payment = payment.assign(amount=spelling)\n"
    else:
        prefix = ''
    if prefix:
        changed, site = _replace_function(changed, 'approve_payment', anchor, prefix + anchor)
        sites.append(site)
    if variant.endswith('repaired'):
        field, authority = ('amount','order_amount') if variant.startswith('amount') else ('account_id','registry_account_id')
        anchor = "    row = payment.to_dict(orient='records')[0]\n    receipt = receipt_for(row)"
        replacement = (f"    payment = payment.assign({field}=payment['{authority}'])\n"
            "    row = payment.to_dict(orient='records')[0]\n"
            "    policy = json.loads(row['approval'])['policy_version']\n"
            "    payment = payment.assign(approval=approval_for(row, policy))\n"
            "    receipt = receipt_for(row)")
        changed, site = _replace_function(changed, 'execute_payment', anchor, replacement)
        sites.append(site)
    return changed, {'variant':variant,'seed':seed, 'original_sha256':source_hash(source),
        'injected_sha256':source_hash(changed),'sites':sites,
        'expected_effect':'amount scaled by 100' if variant.startswith('amount') else
             'account associated to a different entity' if variant.startswith('account') else
             'equivalent decimal spelling' if variant == 'benign' else 'matched clean execution',
        'repair_function':'execute_payment' if variant.endswith('repaired') else None,
        'qualification':'pending_actual_native_execution'}


def _canonical_row(row):
    row = deepcopy(row)
    for field in ('amount','order_amount'):
        if field in row:
            number = Decimal(str(row[field]))
            row[field] = format(number, 'f').rstrip('0').rstrip('.') if '.' in format(number,'f') else format(number,'f')
    for field in ('approval','execution_receipt'):
        if field in row:
            row[field] = _canonical_row(json.loads(row[field]))
    return row


def _native_row(cat, name):
    candidates = [(ref,a) for ref,a in cat['artifacts'].items()
                  if name in a['names'] and a['artifact_kind'] == 'table'
                  and a['artifact_content'].get('rows')]
    if len(candidates) != 1:
        raise ValueError('Mechanical witness must bind one native table: ' + name)
    ref, artifact = candidates[0]
    return artifact['artifact_content']['rows'][0], {'artifact_ref':ref,
        'native_ids':artifact['native_ids'],'artifact_value_sha256':artifact['artifact_value_sha256']}


def _target_ids(inventory, field):
    result=[]
    for element in inventory['elements']:
        params=element.get('parameters') or {}
        if element['category'] == 'intent' and params.get('operation') == 'pay':
            result.append(element['element_id'])
        elif element['category'] == 'intent' and field in params:
            result.append(element['element_id'])
        elif field in params.get('fields',[]) or params.get('field') == field:
            result.append(element['element_id'])
    if not result:
        # The existing payment goal carries the source-supported named parameters.
        result=[e['element_id'] for e in inventory['elements'] if e['category']=='intent' and e.get('operator')=='pay']
    return sorted(set(result))


def qualify_native_values(cat,variant,*,seed,clean_input=None,clean_endpoint=None):
    """Mechanical truth only. Absent native witnesses explicitly unqualify a case."""
    kind='clean' if variant=='clean' else 'benign' if variant=='benign' else 'repaired' if variant.endswith('repaired') else 'persistent'
    try:
        initial,input_witness=_native_row(cat,'invoice_df')
        row,witness=_native_row(cat,'approved_df')
        executed,repair_witness=_native_row(cat,'executed_df')
        endpoint,end_witness=_native_row(cat,'output_df')
    except ValueError as error:
        return {'qualified':False,'activated':False,'endpoint_equivalent':None,'input_equivalent':None,
                'native_witnesses':[],'unqualified_reason':'Missing native mechanical witness: '+str(error)}
    if variant=='clean':
        clean_input=_canonical_row(initial);clean_endpoint=_canonical_row(endpoint)
    field='account_id' if variant.startswith('account') else 'amount'
    expected=Decimal(str(initial['amount']))*100 if field=='amount' else f'ACC-{seed+1}'
    activated=(Decimal(str(row[field]))==expected if field=='amount' else row[field]==expected) if kind not in {'clean','benign'} else False
    equivalent=_canonical_row(endpoint)==clean_endpoint
    input_equal=_canonical_row(initial)==clean_input
    repair_agrees=_canonical_row(executed)=={k:v for k,v in clean_endpoint.items() if k!='reconciliation'} if kind=='repaired' else None
    qualified=input_equal and (equivalent if kind in {'clean','benign'} else activated and (equivalent and repair_agrees if kind=='repaired' else not equivalent))
    return {'qualified':bool(qualified),'activated':activated,'endpoint_equivalent':equivalent,
            'input_equivalent':input_equal,'repair_boundary_equivalent':repair_agrees,
            'native_witnesses':[input_witness,witness,repair_witness,end_witness],
            'unqualified_reason':None if qualified else 'Missing activation, matched input, repair or endpoint agreement'}


def capture_bank(output_dir, *, variants=VARIANTS, seed=17, extraction_file=None, batch_size=8, profile=None):
    """Run fresh copied entries through the existing wrapper, never edit captures."""
    output=Path(output_dir).resolve()
    if output.exists() or not output.is_relative_to(ROOT):
        raise ValueError('Fault bank requires a fresh workspace-contained directory')
    variants=list(variants)
    if len(set(variants)) != len(variants) or not variants or any(v not in VARIANTS for v in variants):
        raise ValueError('Unknown/duplicate fault-bank cases')
    if 'clean' not in variants:
        raise ValueError('Qualification requires a matched clean execution')
    extraction=Path(extraction_file or ROOT/'evidence/normalization-v2-f01-development/dev-01/extraction.json').resolve()
    if not extraction.is_relative_to(ROOT):
        raise ValueError('Extraction source outside workspace')
    current=replay_extraction(extraction,json.loads((ROOT/'resources/ontology/generated/taxonomy-v2.json').read_bytes()),current=True)
    output.mkdir(parents=True)
    write(output/'extraction-current.json',current)
    runtime=prepare_dispatch(output/'extraction-current.json',profile=profile)
    if runtime['operation'] != 'pay':
        raise ValueError('This fault bank requires source-authorized definite payment')
    inventory=inventory_from_spec(runtime['specification'])
    original=(ROOT/'examples/native_payment_workflow.py').read_text(encoding='utf-8')
    write(output/'runtime.json',runtime);write(output/'inventory.json',inventory)
    # Freeze exact source/environment dependencies, including the copied entry per case.
    sources={p.relative_to(ROOT).as_posix():file_hash(p) for p in (ROOT/'src/intentlineage').rglob('*.py')}
    for name in ['requirements.txt','etiq_agent_wrapper.py','etiq_runner/wrapper.py','scripts/scan_entry.py',
                 'scripts/capture_m1_v4.py','examples/native_payment_workflow.py']:
        sources[name]=file_hash(ROOT/name)
    sources.update(runtime['input_sources'])
    write(output/'source-manifest.json',sources)
    for name, expected in sources.items():
        source=(ROOT/name).resolve()
        if not source.is_relative_to(ROOT) or file_hash(source)!=expected:
            raise ValueError('Source snapshot binding mismatch')
        dest=output/'source-snapshot'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(source.read_bytes())
    cases=[];clean_endpoint=None;clean_input=None
    # Clean must precede qualification, regardless of requested presentation order.
    ordered=['clean']+[v for v in variants if v!='clean']
    for index,variant in enumerate(ordered):
        directory=f'case-{index+1:03d}'
        folder=output/directory;folder.mkdir()
        source,injection=inject_source(original,variant,seed=seed)
        entry=folder/'entry.py';entry.write_text(source,encoding='utf-8',newline='\n')
        write(folder/'controller/injection.json',injection)
        # Import the existing recipe, rather than adding a second capture/scanner.
        import importlib.util
        spec=importlib.util.spec_from_file_location('m3a_m1_recipe',ROOT/'scripts/capture_m1_v4.py')
        recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
        # Etiq treats shared dependencies outside sys.prefix as local source and
        # walks pandas internals. Use their verified interpreter with this checkout
        # first on PYTHONPATH; do not mutate either shared environment or wrapper.
        import pandas
        dependency_venv=Path(pandas.__file__).resolve().parents[3]
        capture_python=dependency_venv/'Scripts/python.exe'
        if not capture_python.is_file():capture_python=Path(sys.executable)
        if Path(sys.executable).resolve()==capture_python.resolve():
            recipe.run_wrapper(entry.relative_to(ROOT).as_posix(),folder/'capture',output/'runtime.json',seed)
        else:
            # Relay only interpreter selection; the exact accepted M1 recipe
            # still owns the wrapper command, environment, scan and raw logs.
            relay=folder/'controller/capture-recipe-relay.py'
            relay.write_text("import importlib.util,sys\nfrom pathlib import Path\n"
                "s=importlib.util.spec_from_file_location('accepted_m1_recipe',sys.argv[1])\n"
                "m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n"
                "m.run_wrapper(sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]),int(sys.argv[5]))\n",
                encoding='utf-8',newline='\n')
            command=[str(capture_python),str(relay),str(ROOT/'scripts/capture_m1_v4.py'),
                     entry.relative_to(ROOT).as_posix(),str(folder/'capture'),str(output/'runtime.json'),str(seed)]
            result=subprocess.run(command,cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'src')),
                                  capture_output=True,timeout=200)
            write(folder/'controller/capture-relay-command.json',{'command':command,'exit_code':result.returncode,
                'recipe_sha256':file_hash(ROOT/'scripts/capture_m1_v4.py'),'relay_sha256':file_hash(relay),
                'source_path':str(ROOT/'src'),'model_requests':0})
            (folder/'controller/relay.stdout.log').write_bytes(result.stdout)
            (folder/'controller/relay.stderr.log').write_bytes(result.stderr)
            if result.returncode:raise ValueError('Accepted M1 recipe relay failed; exact logs retained')
        packet=load_native(folder/'capture/scan-result.json',workspace_root=ROOT)
        cat=build_catalogue(packet,inputs=['invoice_df','orders_df','registry_df'],outputs=['output_df'])
        write(folder/'controller/catalogue.json',cat)
        packages=build_packages(cat,inventory,cache_dir=folder/'controller/summary-cache')
        plan=build_review_plan(packages['endpoint'],packages['top_level'],batch_size=batch_size)
        if profile:
            from .review_single import attach_contract
            plan=attach_contract(plan)
        write(folder/'controller/review-plan.json',plan)
        for key,value in packages.items():write(folder/'public'/f'{key}.json',value)
        if variant=='clean':
            clean_endpoint=_canonical_row(_native_row(cat,'output_df')[0]);clean_input=_canonical_row(_native_row(cat,'invoice_df')[0])
        field='account_id' if variant.startswith('account') else 'amount'
        qualification=qualify_native_values(cat,variant,seed=seed,clean_input=clean_input,clean_endpoint=clean_endpoint)
        kind='clean' if variant=='clean' else 'benign' if variant=='benign' else 'repaired' if variant.endswith('repaired') else 'persistent'
        targets=_target_ids(inventory,field)
        if not targets:
            qualification.update(qualified=False,unqualified_reason='No source-supported requirement target')
        record={'case_id':directory,'directory':directory,'pair_id':'payment-seed-'+str(seed),
            'variant':variant,'kind':kind,**qualification,'target_element_ids':targets,
            'source_sha256':file_hash(entry),'native_capture_sha256':file_hash(folder/'capture/native-capture.json'),
            'capture_sha256':cat['capture_sha256'],'review_plan_sha256':plan['plan_sha256'],
            'scan_status':'completed','scan_errors':packet['serialized']['scan_errors'],
        'qualification_scope':'mechanical single-payment captured values; accepted M1, reviewed M2 candidate'}
        write(folder/'controller/qualification.json',record);cases.append(record)
    result={'format_version':'m3a-bank.3','root':str(output),'cases':cases,'seed':seed,
        'wrapper_scans':len(cases),'model_requests':0,'m1_commit':'7178692b12c59a699c4fd7c1b0ed801759b3894d',
        'm1_pending':[],'m1_status':'accepted within tested scope','experiment_qualified':False,
        'm2_commit':json.loads((ROOT/'resources/evidence/m3a-m2-interface.json').read_bytes())['commit'],
        'summary_version':'4.1.0','normalizer_version':'2.2.0',
        'review_session_version':SESSION_VERSION,'review_matrix_version':MATRIX_VERSION,
        'source_manifest_sha256':file_hash(output/'source-manifest.json'),
        'runtime_sha256':file_hash(output/'runtime.json'),'inventory_sha256':file_hash(output/'inventory.json')}
    if profile:
        from .review_single import SESSION_VERSION as sv,MATRIX_VERSION as mv,contract
        result.update(format_version='m3-single-bank.1',inventory_profile=profile,
            review_contract=contract(),review_session_version=sv,review_matrix_version=mv)
    result['bank_sha256']=digest(result);write(output/'bank.json',result)
    return result
