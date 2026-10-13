# Etiq Verify Python

Independent M2 tester reassessment (11 October 2026), frozen `6dd91fa`: **T07/T08/T09 PASS within local scope; F01/F02 closed.** 616 submitted, 73 unchanged independent and 207 additional checks pass; fresh native replay/dependency/reuse audits pass. Final acceptance belongs to the Overseer. Two ignored legacy T02 smoke files have an explicit tester preservation exception; the report records it. No semantic-model or OS/provider-isolation qualification is claimed. M3B remains gated. See complete independent report (local record: `instructions_between_agents/m2-tester-report-v4-f01-f02-corrections.md`).


M2 tester assessment at `1f1c7c1` finds two T09 gaps despite 529 submitted passes:
case-colliding usage metadata can erase invalid counters, and resealed final
assessment summaries can disagree with retained raw replies while replay passes.
Existing wrapper/native disclosure and accepted M1 integration checks pass.
Do not infer verified final assessment consistency from the current M2 replay
command alone. See the report (local record: `instructions_between_agents/m2-tester-report-v4.md`).
No wrapper, capture command, dependency or production source changed in testing.

Current authoritative M1 status (8 October 2026): **accepted within tested scope at `7178692`**, following complete independent reassessment. See final overseer acceptance (local record: `instructions_between_agents/m1-overseer-acceptance-v4.md`). Earlier pending/rejected statements are historical. M2 still requires its own corrections, corrected-source integration and acceptance; M3B remains gated.

Independent complete M1 reassessment at `7178692` (8 October 2026) passes T01–T06
within tested scope: 430 milestone tests, 20 additional contracts, seven retained
native scans, four nonexecuting abstentions and both exact audits pass. Recorded
modality/statistics fixes are verified; no new inference or production fix occurred.
Use corrected summary 4.1.0 and normalizer/compiler 2.2.0 for current packages.
Native entry/capture-producer validity alone does not establish complete package
policy currency; verify its full source manifest and summary identity separately.
See tester report (local record: `instructions_between_agents/m1-tester-report-v4-corrections.md`).
The shared wrapper/capture producers and dependency pins remain unchanged.

M1 V4-F01/V4-F02 developer corrections pass 430 complete checks and `pip check`.
Current source agreement/normalizer/compiler are 2.2.0; current summary is 4.1.0
with safe finite numeric arithmetic and strict encoding before cache creation.
Current packages are `.etiq/artifacts/m1-v4-fixes/`: six native scans and three
abstentions, zero new model requests. Use `annotations/m1-v4-fixes-capture-plan.json`
and a fresh `--output-root` with the existing recipe. Historical snapshots/cache
seals/reuse hashes validate against exact predecessors; corrected current evidence
requires current producer equality. The exact audit now records two new reports
under `evidence/validation-v4-fixes/` and passed twice without rewriting equal bytes/
mtimes. Earlier delivery/audit status below is historical. Acceptance remains pending;
M2's separate checkout must reconcile the changed versions and policy hashes.

Independent M1 reassessment at `c7c0a5f` (8 October 2026) confirms the shared
single-scan native capture/disclosure path and closes the recorded V2-F01/V4-O01
reproductions, but recommends changes for V4-F01 source modality and V4-F02 summary
overflow. Two finite `1e308` rows capture successfully while derived mean/median
become infinity and strict-JSON describe/cache fails. Inspect packaging errors
after successful scans; a completed capture does not imply usable summaries.
Uncertain approval can also survive compilation as mandatory despite unrelated
dispatch abstention. See tester report (local record: `instructions_between_agents/m1-tester-report-v4.md`).
Production wrapper commands, source versions and dependency pins are unchanged.

Revision-4 developer integration is implemented and focused-tested on the existing
Python 3.11.9/Etiq 2.3.1 environment. Use the same wrapper with --native-export and
a fresh empty output directory to serialize supported live state values/function
mappings from that same scan. Native IDs/edges remain authoritative. Complete M1
developer packages are in .etiq/artifacts/m1-v4-delivery/; independent milestone
acceptance remains pending. See instructions_between_agents/m1-developer-handoff-v4.md.
Example:

```powershell
$env:INTENTLINEAGE_PROMPT_RUNTIME = (Resolve-Path '.etiq/artifacts/m1-v4-delivery/native-pay-dev01/runtime.json').Path
.\.venv\Scripts\python.exe etiq_agent_wrapper.py --workspace-root . --entry examples/native_payment_workflow.py --output-dir .tmp/fresh-native-payment --lineage-format json --native-export
```

Inspect scan status/errors first, then native_export_status/path/hash and the exact
native graph binding. load_native(..., workspace_root=...) verifies current source
hashes; audit replay omits current-source checking. Controller catalogue, raw export,
source snapshots and signing key are private audit evidence, not visible packages.
Visible producer metadata excludes full source; absent native locations stay unknown.
Private catalogue 4.0.2 uses JSON-native index keys and deterministic eligible-group
ordering. Every saved opened view passed JSON replay audit. Identical job values
may have differing native alias labels/cluster sizes; do not promise graph identity.
The initial .etiq/artifacts/m1-v4/ packages are diagnostic due to the earlier key-type
defect. The second matrix in m1-v4-final/ is diagnostic due to opened-group ordering.
Current fresh default is .etiq/artifacts/m1-v4-delivery/; use a new --output-root
when repeating the submitted matrix. Validate every saved opening after JSON reload.

The exact developer audit command is:
`.venv/Scripts/python.exe evidence/validation-v4/audit-source.py`.
V4-O01 corrects strict JSON comparison of tuple-derived report signatures. The
corrected report uses evidence/validation-v4-o01/audit.json; original reports and
the submitted native matrix stay unchanged. Replaying an equal saved report never
rewrites it; real differences fail. Two exact executions passed with the same
corrected report hash. The corrected handoff links to complete regression results;
independent M1 acceptance remains pending.

Current planning authority: [PLAN.md](PLAN.md) revision 4 (8 October 2026), and the active briefs in `instructions_between_agents/`. Earlier revision-3 planning passages below are superseded; verified implementation history remains unchanged. See the revision-4 reconciliation at the end.

## Planned revision-3 capture adaptation (not verified capability)

The user requests reference-style native state/value/function serialization as
specified in PLAN.md revision 3. Extend the existing approved shared capture
integration's post-scan serializer or reuse an explicitly approved adapter; do not
add an unrelated scanner. Native graph remains authoritative, actual supported
state.value and function mappings need compatibility tests before claiming capture.
Reference Etiq 2.3.0/Python 3.12 is not yet verified here; retain current proven
commands below until developer evidence justifies an update. Runtime sidecars remain
supplementary evidence. Bound stats/descriptions and keep truncation/coverage explicit.
See instructions_between_agents/reference-use-case-icp-review.md.


Use this skill when a task needs runtime evidence from executed Python code through Etiq.
Etiq is useful for execution lineage, intermediate-state verification, debugging observed
transformations, and retracing how a Python workflow produced or transformed supported
objects.

Do not use Etiq as the primary tool for ordinary logging, static linting, non-Python code
review, or correctness certification. Never claim that a scan or lineage graph proves a
program, final answer, model output, or business conclusion is correct.

## Required Capture Path

V2-F01 normalizer/compiler 2.1.0 validate source clause polarity before dispatch;
historical replay cannot authorize old positive meanings. Matrix defaults now use
current-normalization evidence and fresh `.etiq/artifacts/m1-v2-f01/` captures.
The completed sixteen-attempt developer reassessment captured two successful positive
controls through this same wrapper; 23 additional current matrix scans also completed
without errors. Source/negation correction uses the unchanged model and instructions. Negative/uncertain extraction abstention has
no authorized payment execution; retain raw inference/dispatch evidence instead
of capturing the previously incorrect workflow as though it were corrected.

Revision-2 prompt entry: `examples/prompt_payment_workflow.py`. Validate and prepare
its runtime outside scanning with `intentlineage.prompt_dispatch`; then supply
`INTENTLINEAGE_PROMPT_RUNTIME` and invoke the same shared wrapper. The local recipe
`scripts/capture_prompt_m1.py` and serial matrix recipe
`scripts/capture_prompt_matrix.py` call that wrapper and the existing payload
binding CLI. They are orchestration recipes, not replacement scanners. Archived
source snapshots preserve earlier entries; only fresh paths establish new-source
execution. Full element representations and explicit typed-relation witnesses are
value-sidecar evidence, not native Etiq serialization or semantic certification.
The dispatcher consumes current compiled revisions and rejects stale/tampered
specifications. R2 compiler 2.0.2 / operationalization 2.1.0 define approval due
from approved (ready rows retain that stage) and receipt-field agreement due from
execution; these are proposed criteria, separate from carried representation and
independent review. The historical R2 matrix remains at `.etiq/artifacts/m1-v2-r2/`
with its original candidate packet. Current defaults are described above; all earlier
captures remain unchanged.

Code must run through `etiq-copilot` for Etiq evidence to be captured. In this repo, use the
shared wrapper command. Do not implement another scanner, runner, or raw
`DebuggerCodeScanner` helper in the skill.

For an ad hoc Python workflow entry file, run from the repository root:

```powershell
.\.venv\Scripts\python.exe etiq_agent_wrapper.py --workspace-root . --entry examples/capture_spike.py --output-dir .etiq/artifacts/capture_spike --lineage-format json
```

This command is verified here on CPython 3.11.9 with `etiq-copilot==2.3.1`.
Replace the entry/output arguments for another actual local workflow. Always
supply `--entry`: the recovered CLI's original default Iris demo and protected
runner are absent from this project. Source commit/file hashes for the unchanged
shared wrapper are in `resources/etiq-wrapper-provenance.json`.

## Entry File Selection

Select the smallest workspace-relative `.py` file that actually executes the workflow path
under review. Prefer a documented repo runner or CLI entry when one exists.

Do not scan a helper module that only defines functions unless that module also executes the
target workflow when run. Do not scan tests, notebooks, generated artifacts, or unrelated
wrappers unless the user's question is specifically about those files.

Verify `entry_file_path` and its SHA-256 in `scan-result.json` against the selected
entry. The read-only `intentlineage.capture.load_capture` can validate this binding
when called with `workspace_root`.

## Inspection Order

1. Run the selected Python workflow through the shared Etiq wrapper or protected runner.
2. Treat console output only as a pointer to the result file.
3. Open `<output-dir>/scan-result.json`.
4. Inspect `status` and `scan_errors` before interpreting captured objects or lineage.
5. If `status` is not `completed` or `scan_errors` is non-empty, report that first and do not
   present lineage as complete evidence.
6. Inspect `captured_objects` and `source_evidence` for stable object names, source snippets,
   scopes, and line numbers.
7. Read the separate lineage artifact named by `lineage_path` only after the scan result is
   understood.

## Evidence To Report

Cite the selected entry file, scan status, scan errors, captured object names, relevant
`source_evidence`, and the lineage artifact path. The verified T02 entry captures
`input_df`, `intermediate_df` and `output_df` at lines 5–7, scope `Module`, with
causal paths through the intermediate amount transformation.

The shared wrapper saves names/source/lineage but does not serialize dataframe
rows. Do not infer payment values from graph labels. Later workflow payload
artifacts must be explicitly bound to the executed entry/run and captured names.
Fixtures are synthetic contracts; only real wrapper executions establish capture.

State limitations clearly: Etiq only observed code that executed through the scanner;
unsupported object types or APIs may not be captured; generated graph IDs, ordering, and
exact graph text can vary by `etiq-copilot` version; lineage supports debugging and
retracing evidence, but it does not prove correctness.


## Verified M1 payment entry

Independent tester replay, 6 October 2026: fourteen fresh current-source captures
are retained at `.tmp/m1-tester-replay/`; all completed without scan errors and
validate against current sources. `.venv-m1-tester` reproduced the full pinned
installation and an additional nominal capture at `.tmp/m1-tester/fresh-nominal/`.
The serial matrix recipe still uses `.venv`. The
tester report (local record: `instructions_between_agents/m1-tester-report.md`) recommends T04
changes for separate compiler findings; these successful captures do not confer
M1 acceptance.

`examples/payment_workflow.py` executes the five deterministic roles. The serial
`scripts/capture_m1.ps1` recipe invokes this same shared wrapper for 14 cases and
then the read-only payload bundler; it is not another scanner/runner. Use fresh
output/review paths as documented in README. All matrix scans completed without
errors. Ten full-trace snapshots include invoice/intake, matched PO, validated
supplier, join, routed, approved, ready, execution and reconciled dataframe names.
The observation-gap control deliberately omits routed values; the draft control
ends after one snapshot. Always distinguish scan completion from payload coverage.

Compute scalar helpers from plain records before dataframe assignments. Runtime
compiler/Pydantic imports and embedded dataframe helper calls caused observed
AST/lineage problems; see REFERENCE. Raw graph IDs stay version/order dependent.
Runtime row sidecars are additional target-emitted evidence, bound to names,
source hashes and execution ID, not native Etiq serialization. Historical bundles
are audited against byte-preserved source snapshots. Candidate oracle packets and
injection configuration remain outside future detector/model inputs.

The R1 compiler-contract correction preserves the submitted matrix against its
archived sources. Current payload-source validation correctly rejects that
matrix's old contracts/specification hashes, although the workflow entry and all
saved rows are unchanged. Fresh nominal wrapper runs under three hash seeds pass
with current sources. See `instructions_between_agents/m1-r1-binding-audit.json`
for the original/current bindings; do not rewrite archived evidence to match HEAD.

## Revision 4 reconciliation ? 8 October 2026

PLAN.md revision 4 and the six active milestone briefs supersede earlier proposed context matrices. Primary study: whole-pipeline input/output checks versus intermediate function input/output checks. E, R-H, H, R-A, A share prompt, element inventory and whole-job input/output. High-level batching and adaptive nested disclosure jointly retrieve and assess relevant elements. Uncovered requirements, contradictions and unresolved evidence select openings; budgets and unchecked areas stay explicit. Repeated-call controls preserve identical endpoint evidence; separate clean/benign controls measure false alarms. Native graph descriptions describe only visible nesting.

Reference https://github.com/raluca07/use_case_icp at `5bd37b1ca3e49e940fc885839fa56411203afee0`: require compatible source reuse for serialization, lazy catalogues, native expansion, artifact describe/read, review receipts/reconsideration and enforced runner boundaries. `fault_operations.inspect_catalogue_artifact` computes statistics on inspection; frozen-artifact precomputation/cache is our adaptation. Description coverage and captured-subset statistics must remain explicit. Reference source was inspected, not executed here. No milestone acceptance or new capability is implied.


Test capture-path precaution (11 October 2026): use globally unique pytest basetemp basenames; some legacy tests derive worktree-local capture paths from that basename. Check/snapshot implicit destinations before testing. A fresh outer directory alone is insufficient. See REFERENCE.md tester output-path preservation lesson.
