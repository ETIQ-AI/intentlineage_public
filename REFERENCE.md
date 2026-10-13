# Latest published experiment — 13 October 2026

This snapshot contains the delivered amended M3 experiment: six cases,
30 scheduled arm outcomes and 178 charged campaign calls. Execution
finished; scientific completeness and final acceptance remain pending.
Historical milestones below are planning/research history. Old captures,
QA outputs and private replay bundles stay local. See
[the current experiment](experiments/latest/README.md).

# Reference

## House pattern: private audit keys and publication

Wrapper source clarification: the recovered `etiq_improvements2` checkout has
remote `etiq_demo1` pointing to the public repository
https://github.com/ETIQ-AI/etiq-demo-scripts. Its recorded remote-tracking
branch `etiq_demo1/etiq_demo_library2` points to recovered commit
`1a544516c44ae21547e1814338ff3f31ab604f7a`. The public repository lists
`etiq_agent_wrapper.py`, `scripts/scan_entry.py` and `etiq_runner/`.
Earlier uncertainty reflected incomplete provenance inspection. Public
visibility is established; a redistribution licence was not established
by the recovered checkout inspection. Preserve attribution without treating
missing licence text as proof that the user lacks publication rights.

13 October 2026: controller `catalogue.json` embeds a random `projection_key`
used for HMAC signatures. It is private even though it grants no provider-account
access. Ignore `**/controller/catalogue.json` as well as credentials/authentication
files. `.gitignore` does not remove tracked files or their historical versions;
untrack with `git rm --cached` while retaining local immutable evidence. Raw-blob
scanning of all 171 local commits (9,014 unique blobs) found 23 distinct key-bearing
JSON blobs; remaining raw-blob credential matches were synthetic test fixtures.
No provider token, JWT or PEM private-key match was found in raw blob contents.
Compressed members require separate handling: three of four current raw-evidence
archives contain private catalogue files. Ignore `/evidence/**/*.zip`; remove the
two tracked archives from the index but preserve their bytes locally. A raw-blob
pattern scan cannot certify compressed or arbitrarily encoded secrets.

For the first publication, use `publish-ready/intentlineage/` with a fresh history.
Keep the original reviewed commit identities and private audit evidence local.
The publication snapshot follows current `main`, includes eligible untracked
documents/evidence and excludes private catalogues. Historical signed-view replay
needs those locally retained files; publishing a redacted/re-signed catalogue would
change evidence bytes and invalidate preservation hashes. Separate development
branches/worktrees are not imported by a current-tree publication snapshot.

Windows House Pattern: a longer export directory can push retained evidence paths
past Git's default Windows path limit. Set local `core.longpaths=true` before
staging; use `git -c core.longpaths=true clone <repository-url>` for future Windows
clones. Publication verification checked 28 ignore cases, unchanged bytes for all
23 untracked private files/archives, zero content-pattern matches in exported files,
all 50 members of the initially included provenance wheel (now retained locally
with excluded Laya results) and clean Git repository integrity.
See the publication safety report (local record: `instructions_between_agents/repository-publication-safety-report-20261013.md`).

User publication selection: retain PLAN.md, Agents.md, SKILL.md,
PROJECT_DESCRIPTION.md, PROJECT_GUIDE.md, REFERENCE.md,
EXPERIMENT_RETROSPECTIVE.md and README.md. Ignore `instructions_between_agents/`
at every depth, untrack existing copies and preserve local bytes. Amend the fresh
publication commit so ignored coordination files are absent from reachable history;
do not rewrite original reviewed branches. In published root/project documentation,
render references to excluded coordination records as plain local-record references.
Extraction inputs and saved capture fixtures remain included for the existing
regression/replay tools. Internal tester output folders, generated validation
reports/logs and capture command records/logs stay local; retain the Python
validation helpers referenced by tests. Exclude `/evidence/laya-pilot-*/`, including
predictions, metrics, input/provenance files, failed attempts and the archived
package wheel. Retain local bytes and standalone pilot implementation. Private
catalogue keys and ZIP audit archives stay excluded. Do not label saved fixtures
as final M3 results. Development-worktree outputs are not imported implicitly.

Results House Pattern: distinguish reusable fixtures from generated QA output.
Extraction inputs and native capture graph/state/value/source fixtures support
regression tests and replay. Tester summaries, repeated QA runs, command records
and validation logs document local development and do not need publication.
Exclude these outputs using Git ignore rules and `git rm --cached`; preserve
original bytes and reviewed history locally. Keep validation source used by tests.
Historical preservation/sealed-audit checks still require the local archive; do
not change manifests or claim that the reduced snapshot passes those full audits.
Update the publication sanitization manifest when redacted files are excluded.

12 October user steering: **experiment uses existing ChatGPT-authenticated Codex access; no API keys or Platform API fallback.** Fresh isolated reviewer sessions and model ceiling 5.5 remain. API-only implementation now requires ChatGPT adapter/native CLI corrections EXP-SETUP-01/02; prior API qualification proposal is historical. See correction brief (local record: `instructions_between_agents/developer_m3b-chatgpt-correction-20261012.md`).


12 October 2026: execution implementation `4896fce` passes scoped overseer review (75 local execution/operator checks; source/reuse audit). No new developer correction requested. Experiment Developer must set up native Linux CLI/API access and propose exact qualified model <=5.5/budgets; exact qualification review, actual provider qualification, frozen protocol and campaign release remain. See review (local record: `instructions_between_agents/m3b-execution-implementation-overseer-review-20261012.md`).


12 October 2026 integrated M3B preparation: `37a3bca` passes scoped overseer review; source/reuse/infrastructure audit and 11,016 archive hashes verify. Combined checks: 98 passed/one runtime-identity restart refusal; targeted rerun passed. Actual provider qualification, real-results path and protocol freeze remain required, including user model ceiling 5.5. No experiments authorized. See review (local record: `instructions_between_agents/m3b-integrated-overseer-review-20261012.md`).


12 October 2026 M3A disposition: **integrated infrastructure at `fbedf3e` passes overseer review and is cleared for M3B integration coding.** Accepted M1/M2 are integrated; 43 focused checks, current audit and 20,620 archive hashes verify. M3B must import this delivery and qualify its integrated actual-provider path before experiments. Final M3 acceptance/testing remains after M3B. See M3A clearance (local record: `instructions_between_agents/m3a-overseer-clearance-20261012.md`). Prior M3A integration-pending statements are historical.


12 October 2026: M3B coding-only preparation at `330fd4e` passes overseer review (66 offline tests; archive/source/preservation/reuse verified). Corrected M3A review/integration and actual provider qualification remain outstanding; experiment gates stay closed. See preparation review (local record: `instructions_between_agents/m3b-preparation-overseer-review-20261012.md`).


11 October 2026 final M2 disposition: **accepted within tested local scope at `6dd91fa`; T07-T09 PASS and F01/F02 closed.** Tester: 896 final executions; overseer verified 14,246 evidence hashes and reran 207 additional checks. Two overwritten ignored smoke outputs remain an explicit preservation exception; no further M2 production correction required. M3A integration/review and real-provider/protocol qualification still gate M3B experiments. See M2 acceptance (local record: `instructions_between_agents/m2-overseer-acceptance-v4.md`). Earlier M2 pending/rejected statuses below are historical.


Independent M2 tester reassessment (11 October 2026), frozen `6dd91fa`: **T07/T08/T09 PASS within local scope; F01/F02 closed.** 616 submitted, 73 unchanged independent and 207 additional checks pass; fresh native replay/dependency/reuse audits pass. Final acceptance belongs to the Overseer. Two ignored legacy T02 smoke files have an explicit tester preservation exception; the report records it. No semantic-model or OS/provider-isolation qualification is claimed. M3B remains gated. See complete independent report (local record: `instructions_between_agents/m2-tester-report-v4-f01-f02-corrections.md`).

House Pattern — test temp paths: use a globally unique pytest basetemp basename, even when its full outer path is fresh. Several integration tests graft that basename under the submission .tmp directory. Native export/recipe paths refuse reuse, while legacy smoke captures can overwrite. Snapshot ignored capture paths before a run and retain setup failures. Current 4.2 replay and archived 4.0/4.1 replay remain separate contracts.


Current overseer status ? 11 October 2026: M1 remains accepted. M2 `6dd91fa` passes correction review (186 M2 checks and 73 unchanged independent checks) and requires complete independent tester reassessment. M3A `6edec09` closes original partial-accounting correction but must import corrected M2 and requalify current integrated evidence before M3B. No live campaign authorized. Earlier statuses below are historical. See M2 review (local record: `instructions_between_agents/m2-review-20261011.md`), M2 tester brief (local record: `instructions_between_agents/tester_m2-reassessment-20261011.md`), M3A review (local record: `instructions_between_agents/m3a-review-20261011.md`) and M3A developer brief (local record: `instructions_between_agents/developer_m3a-integration-20261011.md`).


M2 tester disposition (8 October 2026): **changes required at `1f1c7c1`: T07/T08 PASS in local scope; T09 FAIL, M2-V4-F01/F02.** Accepted M1 integration already passes. See active developer correction (local record: `instructions_between_agents/developer_m2.md`) and tester report (local record: `instructions_between_agents/m2-tester-report-v4.md`). Earlier ready-for-testing statements are historical. M3A must consume the forthcoming corrected M2 delivery; M3B remains gated.


## M2 independent tester lessons — 8 October 2026

- Normalize recognized usage aliases without overwriting raw case collisions.
  At `1f1c7c1`, `input_tokens=-1` plus `INPUT_TOKENS=5` becomes complete valid
  input=5 and derived total=7 when output=2. Validate all contributing raw entries
  first; retain invalid-field diagnostics and incomplete coverage (M2-V4-F01).
- A matching session/matrix checksum does not establish that a derived assessment
  matches retained replies. Current replay accepts a replaced complete/supported
  terminal summary alongside an unchanged no-match raw/parsed reply. Reconstruct
  and compare arm-specific terminal/coverage/status metadata (M2-V4-F02); this is
  transcript validation, not semantic model evaluation.
- Positive access canaries must use fields outside the reference sensitive-field
  redaction policy. A `secret` field is correctly redacted even after native
  disclosure; the independent fixture uses `memo` for a bounded positive read.

See the complete report (local record: `instructions_between_agents/m2-tester-report-v4.md`) and
preserved evidence (local record: `evidence/m2-tester-v4/summary.json`). These are tester findings;
production remains unchanged and final disposition belongs to the Overseer.

M2 status (8 October 2026): **`1f1c7c1` passes overseer correction review and is ready for complete independent tester assessment; final acceptance pending.** M2-O01/O02 are closed, accepted M1 is integrated, and 105 focused checks plus source/reuse/native replay audits pass. See current review and handoff (local record: `instructions_between_agents/m2-overseer-correction-review-v4.md`). Earlier correction-required statements below are historical.


Current authoritative M1 status (8 October 2026): **accepted within tested scope at `7178692`**, following complete independent reassessment. See final overseer acceptance (local record: `instructions_between_agents/m1-overseer-acceptance-v4.md`). Earlier pending/rejected statements are historical. M2 still requires its own corrections, corrected-source integration and acceptance; M3B remains gated.

Latest independent complete M1 reassessment (8 October 2026), `7178692`: **PASS
within tested scope**, all T01–T06; 430 milestone checks and 20 independent contracts
pass. V4-F01/V4-F02 recorded reproductions are corrected; previous negation/audit
reproductions remain closed. Seven native captures, four abstentions and two exact
audits validate without new inference. See tester report (local record: `instructions_between_agents/m1-tester-report-v4-corrections.md`)
and durable evidence (local record: `evidence/m1-tester-v4-corrections/summary.json`).
Final acceptance is the overseer's; existing M2/M3A scheduling exceptions remain.

Current M1 developer corrections (V4-F01/V4-F02) are resubmitted: 430 tests pass
including both unchanged tester files, `pip check` passes, six fresh native scans
and three abstentions pass, and two exact historical/current audits preserve equal
bytes/mtime. Normalizer/compiler 2.2.0 and summary 4.1.0 change M2 dependencies;
schema/operationalization/package formats remain unchanged. 5,004 protected files
and 23 exact predecessors verify. The first full-suite compatibility failure is
retained; saved scoring now uses a temporary current revision against the archive.
See complete handoff (local record: `instructions_between_agents/m1-developer-handoff-v4.md`).
Acceptance remains pending overseer review and complete independent reassessment.

Current M3 scheduling: implementation-only M3A may start now; M3B experiments remain gated on accepted M1/M2. See M3A (local record: `instructions_between_agents/developer_m3a.md`) and M3B (local record: `instructions_between_agents/developer_m3b.md`).

Latest independent M1 tester reassessment (8 October 2026), baseline `c7c0a5f`:
**changes required**, V4-F01 source modality and V4-F02 finite numeric summary
overflow. The submitted 386 tests pass; four new tester regressions fail.
V2-F01 and V4-O01 recorded reproductions are closed. See the
tester report (local record: `instructions_between_agents/m1-tester-report-v4.md`) and
durable evidence (local record: `evidence/m1-tester-v4/summary.json`). Final disposition is the
overseer's; early M2 development remains governed by PLAN's existing authorization.

Latest overseer reassessment (8 October 2026): M1 correction V4-O01 closed at `c7c0a5f`; complete M1 commissioned for independent testing. Final acceptance remains pending; subsequent early-M2 development authorization is recorded in PLAN. See review (local record: `instructions_between_agents/m1-overseer-review-v4.md`). Earlier pending-correction statements are historical.

Current planning authority: [PLAN.md](PLAN.md) revision 4 (8 October 2026), and the active briefs in `instructions_between_agents/`. Earlier revision-3 planning passages below are superseded; verified implementation history remains unchanged. See the revision-4 reconciliation at the end.

## Current overseer gate ? 7 October 2026

M1 is **not accepted** and M2 cannot begin. Independent tester finding V2-F01 is
confirmed: a negative approval clause becomes a positive executable requirement.
Overseer reproduced both failing regressions and verified 940 evidence-manifest
hashes. R2 remains closed; extraction quality and truncation remain explicit limits.
The developer must correct source/negation fidelity in the existing M1 brief,
resubmit complete M1, then obtain whole-milestone tester reassessment and acceptance.
See tester disposition (local record: `instructions_between_agents/m1-overseer-tester-disposition-v2.md`).


## Latest tester assessment — 6 October 2026

Complete revised M1 testing at `15b194b` recommends **changes required** for
V2-F01. Actual local inference quoted “Do not require approval for the current
revision” exactly but omitted negative polarity; the accepted record became a
positive user-explicit rule and reached ten states. See the
tester report (local record: `instructions_between_agents/m1-tester-report-v2.md`) and
two failing regressions (local record: `instructions_between_agents/m1-tester-regressions-v2.py`).

Tester lesson: exact spans, valid schemas, stable IDs and complete captures can
preserve the provenance of a semantic error. Review constraint negation as well
as goal negation at the source-to-execution boundary. Keep unquoted example
additions and abstention failures in evaluation evidence. A successful runner exit
can coexist with a recorded per-input inference failure; inspect each result and
the model's output-limit completion reason.

## Latest overseer decision ? R2 closed, 6 October 2026

Correction review at `15b194b` passes: 32 focused tests, 23 valid fresh R2 bundles,
12 exact dispatch/specification replays, 1,532 protected-file hashes and 14 archived
predecessor hashes. Approval is due from approved; reconciliation means receipt-field
agreement from execution. Complete revised M1 is ready for independent milestone-end
testing. No exhaustive gold approval or milestone acceptance is implied; fresh
revised-stack inference/setup and full semantic assessment remain tester duties.
See R2 review (local record: `instructions_between_agents/m1-overseer-r2-review.md`) and
tester specification (local record: `instructions_between_agents/tester_m1.md`). M2/M3 remain inactive.


## Latest overseer decision ? revised M1, 6 October 2026

Reviewed developer implementation `3e3c5bf`: correction requested for R2,
operator-specific rule applicability. Current approval is incorrectly declared due
before the workflow creates approval. Receipt/reconciliation semantics also need
an explicit stage criterion. Overseer checks: 51 focused tests pass, twelve saved
extraction/compiled replays match, all 23 final bundles validate and all 140
historical evidence hashes match. These checks do not promote candidate labels
to gold or replace independent complete milestone testing. M1 acceptance and tester
commissioning remain pending; M2/M3 remain inactive.
See review (local record: `instructions_between_agents/m1-overseer-review-v2.md`).


## Revision-2 prompt adapter findings

- Rule applicability depends on the operator's evidence lifecycle. Approval is
  due only from approved onward (ready_df retains stage approved); carrying its
  representation earlier does not make the check due. Before due is not_applicable,
  missing due evidence is unknown, and observed stale approval is violated.
- Receipt-field agreement starts at execution and compares the six current fields
  with receipt fields using decimal equality for amount and typed equality for
  the others. This authored scope does not require the later reconciliation action
  marker; review must not silently switch between agreement and action completion.
- Criteria edits change rule semantics/revisions, not the unchanged prompt's
  version/hash. Gate source meaning edits with prompt versions and criteria edits
  with both compiler and operationalization versions. Historical unversioned
  criteria remain unversioned in their archive. Regenerate using predecessors.
- Dispatch must consume the exact registered compiled revisions and record their
  file hash. Recompiling without predecessors resets rule revisions to one, making
  capture bindings disagree with regenerated specifications even if criteria match.
- Preserve predecessor specification bytes and a path/hash map before regeneration:
  older index paths name the then-current file, so their hashes now resolve through
  `resources/evidence/m1-r2-preservation.json` rather than the changed generated file.

- `Decimal.normalize()` uses the ambient precision and rounds values longer than
  that precision. Canonical prompt money uses context-free fixed formatting and
  trims only fractional trailing zeros. Supplied revision literals become typed
  integers; raw quoted spelling remains separate.
- The legacy benign injector assumes a decimal point. Prompt normalization can
  produce `100`, so blindly appending `0` changes the value to `1000`. Adapt its
  spelling in the prompt runtime, guard actual decimal equivalence, preserve the
  failed capture and recapture into fresh paths. Do not relabel the failure benign.

- Validate and compile outside the selected Etiq entry. Its imports remain stdlib
  mechanics and dataframe operations; imported Pydantic/compiler comprehensions
  trigger unrelated scanner paths. Scalars are computed before dataframe assign.
- Tie aligned LangExtract records back to exact recorded local HTTP request and
  response, not only to a normalized packet. Conditional scope is preserved but
  execution abstains until the bounded dispatcher supports that condition.
- A partial draft needs only a supplied invoice ID. Do not invent payment amounts
  or accounts to make a negative-payment development prompt fit the old fixture.

- Keep code-point prompt offsets distinct from old TOML line spans. Normalize
  decimal meaning without changing raw quotes. Persistent source/key identity
  allows offset changes without revisions; repeated same-role atoms use occurrence
  identity and need review if reordered ambiguously.
- A pay operation's Payment class binding is an authored adapter decision, not
  an inferred user statement or ontology axiom. Only the inventoried existential
  supplies the typed-relation rule. Missing witnesses remain unknown under OWL
  open-world semantics; user preservation/approval requires explicit prompt evidence.
- Preserve extraction/log/source snapshot bytes with Git attributes. Line-ending
  rewriting breaks otherwise correct archived evidence hashes across checkouts.

## Initial findings: 1 October 2026

- This is a documentation-only starting point. `git status --short` reported
  `fatal: not a git repository`; establish the intended checkout before requiring
  failing-test commits. Planning did not initialise Git.
- The working-agreement file is named `Agents.md`. References to `AGENTS.md`
  identify this file on the current Windows filesystem.
- `SKILL.md` assumes a shared Etiq wrapper, demos and artifacts absent here.
  Recover the supported path and establish capture granularity first. Do not
  spend implementation time designing around an imagined scan schema.
- Open Ontologies has distinct Rust and Python paths; their suitability for this
  project's required operations needs a spike. Harbor's local example uses
  Docker. Their upstream descriptions are not local compatibility evidence.
  Sources: [Open Ontologies](https://github.com/fabio-rovai/open-ontologies),
  [Harbor](https://github.com/harbor-framework/harbor).

## T01 foundation findings: 5 October 2026

- The user requested T01 in the supplied documentation-only folder. Reinspection
  found no `.git`, parent checkout, environment, application code or configured
  remote. This is the intended new local project; initialise history here and
  preserve the supplied files. No existing checkout was replaced.
- `python` resolves to CPython 3.14.2 on this machine. `py -3.11` selects the
  installed CPython 3.11.9. Use explicit `.venv/Scripts/python.exe` commands so
  tests and installation share the isolated interpreter. This verifies T01's
  tools only; T02 must still establish Etiq's supported Python version.
- Candidate pytest/build pins installed successfully and `pip check` found no
  broken requirements. Installed metadata confirms the names, versions, Python
  requirements and licences below. The dependency closure is frozen after
  resolution instead of leaving later setup to select new transitive releases.

| Distribution | Validated version | Python requirement | Licence from installed metadata |
| --- | --- | --- | --- |
| pytest | 8.4.2 | >=3.9 | MIT |
| setuptools (build backend) | 80.9.0 | >=3.9 | MIT |
| colorama (Windows only) | 0.4.6 | >=2.7, excluding 3.0–3.4 | BSD classifier; installed licence text retained |
| iniconfig | 2.3.0 | >=3.10 | MIT |
| packaging | 26.3 | >=3.9 | Apache-2.0 OR BSD-2-Clause |
| pluggy | 1.6.0 | >=3.9 | MIT |
| Pygments | 2.21.0 | >=3.9 | BSD-2-Clause |
| pip (venv bootstrap tool) | 24.0 | >=3.7 | MIT |

Upstream checks: [pytest 8.4.2](https://pypi.org/project/pytest/8.4.2/) and
[setuptools 80.9.0](https://pypi.org/project/setuptools/80.9.0/) publish Python
requirements compatible with 3.11 and MIT licences. These are tested foundation
pins, not a claim to be the latest releases. No untested Etiq/Pydantic/ontology
version is added. The project publication licence remains a later human decision.

- A sandboxed pip download returned no available distributions; the normal
  escalated retry downloaded and installed the packages successfully. Local
  editable installation with `--no-build-isolation --no-deps` uses the pinned
  backend and requires no dependency download.
- The sandbox permits project files but blocks Git index writes. Use normal
  command approval for local staging/commits; this does not authorise publishing.
- A `src/` layout with an editable installation and pytest importlib mode avoids
  adding source directories to `PYTHONPATH`. The subprocess contract uses `-I`
  from a temporary directory, so checkout-root imports cannot hide installation
  mistakes. The initial RED is an assertion on the missing public version, not
  a missing import or test environment.
- GREEN derives `intentlineage.__version__` from installed distribution metadata.
  Both tests and `pip check` pass in `.venv/` and in the independently created
  `.venv-t01-check/`. Fresh setup used only `requirements.txt` and local editable
  installation; it selected the same pinned dependency versions. These checks
  establish the local foundation, not Etiq or later payment semantics.

## Playground question: 5 October 2026

The current plan names Harbor as the experiment harness; `requirements.txt`
mentions it as a future dependency, without an executable pin. There is no
explicit playground/environment-catalog requirement, and OpenReward has not
been selected or added to the developer brief.

[OpenReward's description](https://www.gr.inc/openreward) distinguishes environment
serving from evaluation harnesses. Its Open Reward Standard exposes tasks, tools,
sessions and rewards; compatible servers can run locally, while managed hosting
is optional. Assess an environment library separately from the runner if the
project needs a reusable agent playground. No compatibility or licence validation
for an OpenReward integration has been performed here.

## T02 capture findings: 5 October 2026

- Recovered five wrapper files unchanged from the clean tracked checkout recorded
  in `resources/etiq-wrapper-provenance.json`. The wrapper repository contains no
  licence file. Etiq itself has a proprietary Etiq AI Software Licence; retain it
  as separately installed background IP, with human publication review pending.
- Etiq 2.3.1's CPython-3.11 Windows wheel installed successfully. Installed
  metadata requires Python >=3.10. The resolved tree added 143 distributions;
  Pydantic AI, NetworkX and scientific libraries are declared Etiq dependencies,
  not new harness requirements or implemented research baselines. `pip check`
  passes, and all observed versions/wheel hashes/licence pointers are recorded in
  `resources/environment-m1.json`; requirements now freeze the full Windows tree.
- The bootstrap entry completed with `status=completed`, `scan_errors=[]`, one
  dataframe named `input_df`, source line 5/scope `Module`, and a JSON lineage
  edge from constructor to state. This is real wrapper capture, not a fixture.
  This was the bootstrap checkpoint; the subsequent transformation capture below
  completes the required intermediate evidence.
- The wrapper JSON graph contains `objects` keyed by `_gvid` and `edges` using
  `tail`/`head`; object-array order is not identity. Labels/IDs and source evidence
  are preserved, but the wrapper does not save dataframe row contents. Settle
  explicit executed payload artifacts and their source/run binding in T05 rather
  than assuming that raw graph JSON supplies payment values.
- Use UTF-8 explicitly when reading Python-written JSON on Windows. Create the
  parent directory before pip's `--report`; it does not create it. The first
  install stopped before installation for this missing directory; the corrected
  normal approved retry succeeded. Normal package startup is used for capture,
  including licence checks; the integration subprocess removes pytest's version
  marker instead of inheriting the library's test-only startup shortcut.

T02 GREEN: all 11 developer checks pass. The saved real scan in
`.etiq/artifacts/capture_spike/scan-result.json` reports completed status, no scan
errors or limitations, and the three dataframe names at module lines 5–7.
`lineage.json` has five original edges, with constructor/operation nodes on causal
paths from input through intermediate to output. The entry hash is
`9bbd32cfa95769e8a0fbd2ca9841b1ae73df667c1d1a0c7f1e94a203e34e449c`.
Raw artifacts record the HEAD present at execution (the RED checkpoint); the
entry hash binds the actual changed source, which is included with GREEN.

Fresh workspace-local output directories and a zero wrapper exit are required by
the integration check, preventing stale success from masking a failed execution.
`.gitattributes` keeps Python/project-JSON line endings as LF across checkouts so
source hashes survive Windows Git conversion. Raw capture artifacts and ontology
Turtle files retain their emitted/source bytes, including Windows CRLF in the
wrapper's raw JSON output. No independent tester has been involved.

## M1 final developer evidence: 5 October 2026

102 developer checks pass; all 14 normal shared-wrapper matrix captures complete
with no scan errors. The original wrapper's five file hashes still match. The
exact resource/dependency inventory and RED/GREEN commits are in the handoff.
ePO v5.2.0 and FIBO master_2026Q2 are immutable source pins; Lite 0.5.0 / PyOxigraph
0.5.11 / pySHACL 0.40.1 / RDFLib 7.6.0 execute the selected small operations.
Pydantic 2.13.5 validates contracts outside scanned dataframe helpers.

What would have saved time: raw lineage does not include dataframe values;
capture imports and helper calls need their own real probe; and a source hash
must be preserved with historical evidence before modifying the entry. The
matrix's Git HEAD is the RED commit because capture precedes GREEN; saved byte
hashes/source copies identify the actual executed implementation.

Candidate annotations are manual, primary-rule-scoped and unreviewed. A missing
intermediate payload makes trace coverage unknown without negating a satisfactory
observed final state. Observation completeness concerns declared handoff states,
not every raw helper/input node. No semantic verifier, LLM experiment or general
payment-correctness claim is implemented in M1.

## House Patterns

- Validate the producer scope actually recorded by an artifact. `load_native`
  binds the entry and five capture producers; these did not change in the V4-F01/
  F02 correction, so an old mechanical native capture can still validate there.
  Its older summary/compiler/full-package producers are separate: compare the
  complete source manifest and policy versions before claiming a package current.
  Keep historical frozen-source audits separate from current-source package audits.

- Saved-attempt scoring upgrades current extraction provenance and compiles a
  separate temporary current revision from the archived predecessor. The strict
  dispatcher validates that revision; original packets/specs remain immutable.
  Equality with a historical packet checks prompt/raw data, not current provenance.
- Mean and even median use stdlib statistics.mean's exact-ratio accumulation:
  scaling every value or adding first can lose cancellation/subnormal values or
  overflow. Keep original finite numeric inputs, exclude bool, and diagnose values
  beyond finite support. Seal and strictly encode a summary before opening its final
  cache file. Summary 4.1.0 and source-policy hashes prevent reuse of old semantics.
- When correction sources change, historical captures verify their exact archived
  producers and snapshots, including cache identity/seals, without requesting new
  cache entries in old folders. Fresh correction captures independently require
  current source equality. Retain both reports under versioned new paths.
- Current normalization upgrades 2.0→2.1→2.2 canonically. Retain all predecessor
  packet hashes: direct jumps from different saved versions otherwise produce
  different registered specification provenance. Compiler interpretation correction
  checks the matching predecessor hash/version without inventing a prompt edit.
- Modal force belongs to the containing predicate clause, even when a model span
  omits "Maybe" or "may". Current 2.2 rejects unsupported optional/uncertain force,
  retains raw proposals/diagnostics, and limits shared modality to coordination;
  unrelated optional clauses do not erase definite requirements. Historical replay
  uses its declared source policy, while compiler/dispatch upgrade independently.
- Exact spans do not preserve modal force by themselves. At normalizer/compiler
  2.1.0, “Maybe require”, “may require” and “only optionally” become mandatory
  approval rules (V4-F01). Keep actual inference separate from synthetic contracts:
  the actual tester request abstained for unrelated model errors, while retaining
  the wrong rule. Do not treat that accidental abstention as source fidelity.
- Finite captured numbers do not guarantee finite derived statistics. Two `1e308`
  values overflow upstream-style mean and even-length median calculations;
  strict-JSON cache/inspection fails (V4-F02). This is distinct from converting
  non-finite captured values to null. Preserve the actual native table reproduction.

- Normalize generated audit reports to strict JSON before comparing saved evidence.
  Counter keys create nested tuples which JSON reloads as lists. Direct Python
  equality rejects unchanged reports (V4-O01); compare normalized values, retain
  rejection of real signature/count changes, and never rewrite an equal saved file.
  Correcting the audit source changes its provenance hash: write the new audit in
  a fresh correction folder while retaining the submitted report/source archive.
- A fixed runtime/seed/hash seed does not establish native graph identity. Revision-4
  dev-01 and its repeat have equal captured job values but two aliased edge labels
  and validate_supplier/approve_payment cluster member counts differ. Preserve both
  native graphs exactly and report graph variation separately from value repeatability.
- Eligible-group arrays sort by numeric native ID, not dictionary insertion order.
  JSON writers sort object keys lexically, putting ID 15 before 2. Catalogue 4.0.2
  and an opened-view replay RED correct the second persistence defect. Revalidate
  every saved opened projection against its reloaded catalogue before delivery.
- Private catalogue indices use JSON-native string keys even for numeric graph IDs.
  JSON reload otherwise changes canonical ordering and lookup types. Catalogue 4.0.1
  and saved-file replay regressions correct this; the initial 4.0.0 package matrix
  and its 377-pass suite remain diagnostic evidence. In-memory tests alone do not
  establish persisted evidence replay.

- Revision-4 native export extends the existing wrapper after its single live scan;
  opt in with --native-export. Archive the exact original wrapper before extending
  it; older captures remain bound to their own snapshots. Native export is mandatory
  for revision-4 packages and a sidecar cannot substitute for missing native values.
- Etiq 2.3.1 state IDs are hyphenated UUIDs, while native data graph names use UUID
  hex. Bind the same UUID identity, retaining both original forms and graph IDs.
  Human labels alone are not sufficient value bindings.
- Reference inspectable_artifact can exceed its budget for one giant row/header.
  The local adaptation omits the oversized body and marks truncation. Repr-only
  unknown objects have unsupported status and no claimed structured artifact value.
- Keep raw values/source and projection-signing key controller-private. Visible
  projections allowlist producer metadata and disclose only native memberships and
  edges with visible endpoints. Recompute descriptions on opening; hashing a forged
  client projection alone does not authorize access, so verify its controller signature.
- Immutable summary cache keys bind capture/content, options, version and policy
  source hashes. Cache hits verify the saved summary seal and avoid recomputing
  statistics. Captured-subset statistics, bounded observed samples and truncated
  descriptions are explicit; summaries contain no expected assessment labels.
- Imported example code must retain upstream function/file hashes, notices and an
  adaptation/compatibility map. M1 reuses serializer, catalogue and describe/read;
  reference provider review and OS isolation runners remain later-milestone scope.

An empty aligned packet is not successful inference when raw model JSON is
truncated. The provider can log and suppress its parse error; dispatch's raw-output
validation then raises. Validate the raw response before scoring minimum targets,
classify this as inference failure and retain its targets as unscored. Preserve
the live report and derive a separate saved-evidence report without another request.

Tester minimum targets use `meaning`, development targets use `attributes`. Adapt
the key without changing source spans/values. A scoring-orchestration failure after
a completed model response reuses that exact hashed packet with an explicit resume
record; preserve the failed recipe evidence and do not issue an unreported retry.

Quote alignment does not establish constraint polarity. Validate the extracted
predicate inside its source clause, keep neighboring positive requirements, and
reject ambiguous shared negation/omitted condition scope. Negative approval means
an unsupported negative requirement, not positive binding or a ban on approval.
Historical normalizer replay is audit-only; production compilation/dispatch always
revalidate current policy. Preserve predecessor hashes and source bytes when fixing
interpretation without changing the user's prompt version. Do not tune fixed model
instructions/settings against tester probes or hide inference failures/repeats in
quality denominators. Bounded source guards do not prove general language fidelity.

Test negation on constraints as well as goals against the exact source. Valid
provenance can carry an incorrect polarity through the complete workflow;
V2-F01 demonstrates why accepted model attributes need semantic boundary checks.

Declare each operator's due stages from its evidence lifecycle. Approval starts at
approved (including ready rows at that stage); receipt-field agreement starts at
execution without requiring a reconciliation-action marker. Carried representation
is separate from applicability. Before due is not_applicable; missing due evidence
is unknown. Criteria changes advance compiler/operationalization versions and rule
revisions while unchanged prompts retain their versions/hashes. Dispatch consumes
the exact versioned compiled file and records its hash. Archive predecessor bytes
before regeneration and bind revised executions in fresh paths.

Prompt money canonicalization must not use ambient Decimal precision. Format
exactly and trim only fractional trailing zeros; preserve raw spelling/source
separately. Adapt legacy mechanics to normalized representations rather than
assuming a decimal point. A failed control keeps its artifacts and labels as
diagnostic evidence; freeze the proposed source-backed design and recapture into
fresh paths after correction.

Prompt-runtime inputs are validated outside the selected Etiq entry. Observable
views allowlist specification and runtime values; annotation tables, case settings,
injector code and whole audit snapshots never enter those views. Source-backed
operationalization and independent review remain distinct from structural validity.

LangExtract 1.7.0 uses the official Ollama provider and supports explicit model
instances. Its Ollama provider permits per-instance transport inspection for
complete raw requests/responses. Configure one worker/pass, loopback only,
cloud disabled, and no environment proxy/credentials. Alignment can be fuzzy or
absent: retain such records and reject unsupported spans instead of discarding
them. Qwen2.5 1.5B is Apache-2.0; the 3B variant has a different research licence.
Model/provider versions and exact manifest digest are in `resources/extraction/`.

Revision-2 ontology work inventories formal restrictions before proposing rules.
FIBO Payment has an explicit someValuesFrom hasPaymentAmount MonetaryAmount axiom;
the imported CurrencyAmount module is pinned at the same FIBO commit. Its existential
does not justify exact amounts, preservation, approval policy or closed-world failure
from an absent observation. Proposed translation and observation assumptions require
overseer review. Original ontology manifests and all historical artifacts stay intact.

Revision-2 T01 policy: preserve scalar equality JSON and require strict Pydantic
JSON ingestion after the JSON Schema structural gate. Standard Schema integers
include integral numeric values such as 1.0; schema-only validation does not enforce
lexical integer representation. Equality conflicts compare both scalar type and
value, so true and 1 (or false and 0) are distinct. F01/F02 tests precede the fix.

Independent tester findings, 6 October 2026: the complete fresh M1 environment
reproduces all 157 pins and 178 existing passes; current fourteen-case captures
reproduce archived rows and reviewed primary labels. See
tester report (local record: `instructions_between_agents/m1-tester-report.md`). Two T04 findings
remain open despite those passes: F01 (schema/runtime scalar representation) and
F02 (boolean/integer conflict comparison). Five independent regressions fail.

- Draft 2020-12 `integer` describes mathematical integers, so `jsonschema`
  accepts `1.0`, while Pydantic `StrictInt` rejects that JSON float. A strict
  runtime contract and standard exported schema need an explicit representation
  boundary; do not claim identical acceptance merely from generated union types.
- Python treats `True == 1` and `False == 0`. Direct `!=` comparison therefore
  misses conflicts between distinct supported boolean/integer equality literals,
  even though canonical JSON and semantic revisions distinguish their types.
  The overseer must settle this scalar-equality policy before a correction.
- Await environment creation and completed trace artifacts before dependent
  installation/comparison commands. Package-install output can stay quiet while
  a large dependency tree is still being installed; retain command duration and
  completion evidence rather than assuming absence of output means completion.

R1 developer correction, 6 October 2026: **178 checks pass in 86.65 seconds**;
`pip check` reports no broken requirements. Compiler 1.0.1 rejects malformed
operator parameter structures in source and compiled JSON, and regenerated
schemas carry operator conditions. Empty field/constraint collections are
unsupported; lists contain nonblank string identifiers and preserve set semantics.
Equality literals are strict strings/integers/booleans, with decimal strings for
money. Field/source existence and observed-state evaluation remain M2 work.

The archived specification differs from the current compiled JSON only in
`compiler_version`; valid element IDs/revisions, spans, bindings, semantic and
source hashes, specification version and ontology version are identical. All 14
saved bundles validate against source snapshots and replay the same rows under
current code; 41 reviewed transition paths remain present. Current-source payload
checks reject the old contracts/specification hashes. The candidate and overseer
packets are preserved, with the latter still bound to the archived specification.
`instructions_between_agents/m1-r1-binding-audit.json` records 139 byte-preserved
evidence files and the exact changed bindings. Correction review/rebinding and
M1 testing/acceptance remain pending.

- Preserve review-packet bytes as well as parsed JSON. Changing Git attributes
  after a file was staged may retain its cached normalized blob; use
  `git add --renormalize <exact-file>` and compare the staged blob to the original
  bytes. R1 restores the overseer packet's incoming CRLF bytes without changing
  any review content; oracle JSON now uses byte-preserving attributes.
- R1 tests cover both TOML compilation and compiled-JSON/schema ingestion. A
  validation fix must reject malformed parameter values on each public surface,
  while preserving valid element identity, source spans and semantic revisions.
- M1 review found that checking operator parameter keys alone is insufficient:
  `fields = "amount"` and object-valued `expected_from` compile successfully.
  Validate parameter shapes/types before emitting a specification; this is an M1
  contract responsibility, separate from M2 semantic verification. Correction R1
  and review evidence are in `instructions_between_agents/m1-overseer-review.md`.
- Keep candidate and reviewed oracle packets separate and hash-bound. Overseer
  review of primary synthetic faults does not imply complete secondary-rule gold
  coverage or independent milestone tester acceptance.

- Raw Windows scan JSON retains CRLF bytes for its hashes. Scope Git's
  `cr-at-eol` whitespace handling to the raw artifact tree, retaining normal
  whitespace checks, so `diff --check` does not report every preserved CR as an
  error. The staged blobs were compared byte-for-byte with 148 evidence/resource
  files; none differed.

- Wire-schema RED `423a0bd` adds three guards after the initial 99-case pass.
  Exported schemas now describe serialized positive decimal strings, including
  scientific notation, instead of permissive Python-input schemas. All 102 cases
  pass. Compiled-spec JSON and captured source/value hashes remain unchanged;
  current-source validation still succeeds for all 14 payloads.

- Pydantic's default Decimal validation schema can permit JSON numbers despite a
  before-validator rejecting floats, and custom positive checks are not necessarily
  expressed as JSON Schema constraints. Export and test the emitted JSON contract
  explicitly; Python input coercion and wire representation are distinct surfaces.

- T06 uses neutral routed/ready checkpoints in every full trace, so state names
  and execution IDs do not disclose the selected case. Private annotations are
  manually specified from injection design, never generated by a semantic verifier.
  The original pending candidate remains separate from the overseer's accepted
  primary-scope packet; developer corrections require hash rebinding by the overseer.
- A completed scan can still have an explicitly incomplete payload observation.
  Preserve that distinction. Draft-stage requirements are not automatically
  applicable just because an execution stopped there.

- T05 also observed inconsistent downstream edges when passing dataframes to
  scalar helpers inside `assign`. Compute scalars from plain row dictionaries
  before dataframe assignments. The strengthened branch test checks the complete
  join-to-final path in three fresh processes with Python hash seeds 0, 1 and 2;
  it indexes original IDs rather than relying on graph output order.

- The real T05 capture failed with `'DictComp' object has no attribute 'name'`
  when the runtime helper imported compiler/Pydantic code. Replacing helper
  comprehensions alone did not resolve it. Removing those runtime imports and
  consuming the already compiled JSON made the same capture test pass. This is
  an observed integration boundary, not a diagnosis of every Etiq/Pydantic use.
  Keep strict Pydantic validation in compiler/preflight/developer checks and keep
  scanned dataframe helpers simple. Do not modify the shared wrapper or Etiq.

- T05 branch probe: ordinary dataframe merges inside a scanned function produce
  named states and both original causal parent paths. Keep role dataframe operations
  in the selected entry's source, rather than assuming imported helper internals
  will be captured. No row values appear in the raw graph.
- Runtime snapshots are additional evidence from the same invocation. Associate
  them with raw capture using names, source hashes, execution ID and artifact
  hashes; do not present a snapshot sidecar as native Etiq value serialization.

- T04 GREEN treats source locations/hashes as provenance, separate from semantic
  identity/revision. Shared payment parameters and pinned resource contents also
  affect document semantics. Reject duplicate identities before validating an
  individual rule so malformed duplicates do not obscure the identity conflict.
- Exact contract amounts are strictly positive finite decimals. A three-letter
  currency format is structural validation, not a complete ISO currency registry.
  M1's fixture policy explicitly uses GBP; arbitrary financial validity is unclaimed.

- The M1 compiler consumes explicit TOML tables, not prose inferred by an LLM.
  Stable element keys identify requirements; content revisions and source hashes
  serve different purposes. Keep compiler, specification and ontology versions
  separate. Static Spec Kit adaptation does not require installing its CLI.
- Pydantic's Decimal coercion accepts floats by default. Explicitly reject
  float/bool monetary input before validation and retain decimal strings in JSON.

- T03 GREEN resolves qualified declarations only, preserves ambiguous/unresolved
  and local bindings, and rejects modified source bytes. Canonicalise blank-node
  labels before saving a selected RDF slice to keep repeated compilation stable.
- The small-slice operation report includes zero-focus SHACL as `conforms=null`.
  A syntax/vocabulary/SHACL pass cannot stand in for a payment-policy result.

- Pin source bytes and declaration provenance, not a guessed namespace. ePO's
  ontology headers specify EUPL 1.2 even though its README licenses documents
  under CC BY 4.0. Preserve the file notices and upstream licence separately.
- Open Ontologies Lite 0.5.0 is the tested Python distribution; the root Rust CLI
  is a different execution path. `shacl_validate` is in
  `open_ontologies_lite.shacl`, not a method on `OntologyEngine`.
- Imports are not resolved in the small M1 slice. Resource syntax, vocabulary
  and local SHACL examples do not establish OWL consistency or business validity.
- Required source declarations were inspected directly; a referenced superclass
  can be absent from a module. Do not fabricate a definition for such an IRI.

- T02 wrapper recovery candidate: the clean local `etiq_improvements2` checkout
  at `1a544516c44ae21547e1814338ff3f31ab604f7a` contains the same Etiq skill text,
  the tracked shared CLI and `etiq_runner` implementation. Recover that code
  unchanged rather than authoring another scanner. Its environment does not have
  `etiq-copilot` metadata, so it does not establish installed compatibility.
- The sandboxed package index reports no distributions when network access is
  denied. The approved online index query finds Etiq 2.3.1 and 2.3.2; distinguish
  this from an absent release and validate the selected wheel locally.

- T01 was accepted by the overseer on 5 October 2026 from artifact/history review
  and read-only inspection of both environments' installed metadata. Distinguish
  documented developer test outcomes from independent reruns; the milestone-end
  tester still owns independent acceptance testing. The review is in the M1 brief.

- Four project roles: overseer, developer, tester and paper writer. Developer-run
  TDD checks happen during implementation; independent tester review happens only
  at milestone end. The paper writer receives only final project results from the
  overseer after M3 acceptance, with no intermediate or direct developer handoffs.
- Keep all tasks for a milestone in one developer brief in
  `instructions_between_agents/`. The original `intructions_between_agents/`
  directory is misspelled and unused.

- Keep the PoC to one synthetic payment workflow; the funded-project scope is a
  separate programme. `PROJECT_DESCRIPTION.md` defines that boundary.
- Plan three deliverable milestones. Experiments include their saved evidence,
  exports and documentation; packaging alone does not warrant a separate
  milestone for this small PoC. Keep setup, integration checks and the
  lowest-priority Z3 example as tasks within them, with small TDD increments.
- Track implementation with explicit sequential task IDs and checklists in
  `PLAN.md`. A task closes with a reviewed output, relevant test evidence and
  documentation; listing activities in milestone prose is insufficient tracking.
- Follow the existing Etiq capture guidance: adapt observed artifacts, not a
  second scanner or replacement execution graph. Incomplete scans remain explicit.
- Keep independently reviewed ground truth outside detector/model inputs.
  Repaired final states must not erase annotated earlier violations.
- Plan verification outcome, mapping quality and propagation as separate fields.
  Missing observation is not proof of satisfaction or a dropped constraint.
- Use exact monetary values and pin specification, ontology, dependency and model
  versions. Store raw evidence alongside normalised results.
- Work serially with RED/GREEN commits once Git is established. Documentation
  accompanies tests and implementation; no assistant memory substitutes for it.
- Treat `pyproject.toml` as the single package-version authority; derive the public
  version from installed distribution metadata and test outside-checkout imports.
- Add dependencies when their task uses and validates them. T01 pins only the
  build/test foundation; later integrations do not inherit assumed compatibility.
- Prepare all external publication and hosted-run steps locally for human
  execution, as required by `Agents.md`.

Distinguish the observed T01 foundation evidence above from later planning
decisions. Record evidence and justified revisions as implementation proceeds;
do not label proposed behaviour as tested capability.

## Overseer R1 decision ? 6 October 2026

R1 passes correction review at `4b56d62`: both original malformed inputs are
rejected and the overseer rerun of all 76 R1 regressions passes. Fourteen archived
bundles retain valid source bindings; the compiled specification changes only
compiler_version to 1.0.1. Archived evidence must not be represented as executing
current contracts. The v2 annotation packet keeps archive bindings and records
current semantic equivalence separately. Complete M1 is ready for independent
milestone-end testing; acceptance remains pending.
See correction review (local record: `instructions_between_agents/m1-overseer-review.md`) and
tester brief (local record: `instructions_between_agents/tester_m1.md`).

## Prompt decomposition requirement ? planning clarification, 6 October 2026

The user clarified that intent decomposition must start with the natural-language
prompt and automatically produce source-grounded elements. Manually authored TOML
is not completion of that requirement. Spec Kit template reuse is documentation,
not the decomposition engine. LangExtract is the proposed OSS extraction spike,
with ontology-derived taxonomy mapping kept separate and unmapped intent retained.
No new dependency has been installed. See the
research proposal (local record: `instructions_between_agents/intent-decomposition-research.md`).
This scope gap must be reconciled in the next brief and acceptance criteria;
existing capture/compiler evidence remains valid for its narrower implemented scope.

## House pattern: prompt decomposition is not specification authoring

Revision 2 replaces manual TOML as the main intent input with actual LLM
extraction from the user's prompt, source-span grounding and ontology taxonomy
mapping. Keep authored taxonomy extensions, ontology axioms, user constraints and
legacy synthetic policies distinguishable by provenance within the same three
element categories. Taxonomy coverage does not bound user intent. Evidence mappings
are reviewed operationalizations, not additional invented requirements. A carried
ID cannot establish preservation and an observation gap cannot establish removal.
Archive prior briefs before changing scope; retain tester findings until corrected
and the whole revised milestone is independently reassessed. No installed
LangExtract/model or decomposition capability is implied by research documentation.

## House patterns ? graph context and isolation, revision 3

Etiq native graph/state objects are the evidence authority. State.value previews,
function mappings and parent/child relations need actual compatibility probes;
native JSON labels do not contain row values. Reference 2.3.0/Python 3.12 is not
an automatic replacement for current 2.3.1/3.11.9. Capture adaptation extends the
approved integration, not a replacement scanner. No capture is implied by planning.

Fresh session/ephemeral/CODEX_HOME/working folder alone do not prove cross-arm read
isolation. Test the control plane and generated-command boundary with canaries,
actual mounts/permissions and credential/network separation. Fixed retrieval and
target summaries prevent context treatments from changing multiple factors. Children
are retrospective context. Known qualified injected faults support bounded metrics;
reviewer-labelled semantic examples are not imposed. No broad accuracy claim from
schema, fault location or successful replay. Reference licence not established.

## Revision 4 reconciliation ? 8 October 2026

PLAN.md revision 4 and the six active milestone briefs supersede earlier proposed context matrices. Primary study: whole-pipeline input/output checks versus intermediate function input/output checks. E, R-H, H, R-A, A share prompt, element inventory and whole-job input/output. High-level batching and adaptive nested disclosure jointly retrieve and assess relevant elements. Uncovered requirements, contradictions and unresolved evidence select openings; budgets and unchecked areas stay explicit. Repeated-call controls preserve identical endpoint evidence; separate clean/benign controls measure false alarms. Native graph descriptions describe only visible nesting.

Reference https://github.com/raluca07/use_case_icp at `5bd37b1ca3e49e940fc885839fa56411203afee0`: require compatible source reuse for serialization, lazy catalogues, native expansion, artifact describe/read, review receipts/reconsideration and enforced runner boundaries. `fault_operations.inspect_catalogue_artifact` computes statistics on inspection; frozen-artifact precomputation/cache is our adaptation. Description coverage and captured-subset statistics must remain explicit. Reference source was inspected, not executed here. No milestone acceptance or new capability is implied.

## M1 overseer review ? 8 October 2026

Submission `54ed485` substantially meets revision-4 M1, but saved audit replay fails because generated Counter signatures are tuples while loaded JSON uses lists. Normalize strict JSON before comparison and test that real differences still fail. Capture/source/preservation/reuse/visibility checks completed successfully before that final comparison. M1 remains unaccepted, awaiting correction and complete independent tester reassessment. See review (local record: `instructions_between_agents/m1-overseer-review-v4.md`); the correction is in the complete developer M1 brief. Native alias/cluster variability is retained as a limitation, not hidden by rewriting captures.

## House pattern: authorized M2 overlap (8 October 2026)

The user permits M2 development during complete M1 tester reassessment. Bind M2 to reviewed `c7c0a5f`, freeze the tester checkout/evidence and develop separately. Pending M1 findings can require M2 rework; resolve dependencies before M2 acceptance. This exception changes development scheduling, not the milestone-end tester role or M3 acceptance gate.

## M1 tester findings V4-F01/V4-F02 (8 October 2026)

Exact spans and polarity checks do not preserve source modality: optional/uncertain approval can become mandatory. Guard clause/predicate force in normalization and compilation, or reject unsupported translation with provenance. Finite values can produce non-finite intermediate sums: mean/even median must avoid overflow while retaining strict JSON. Cache failure paths must not leave poisoned saved files. See the active complete M1 developer brief; old negation/audit findings remain closed.

## User-authorized M3 phase split ? 8 October 2026

M3 remains one milestone: M3A implements experiment infrastructure now against existing M1 and stubbed M2 contracts; M3B executes/analyses the real experiment only after accepted corrected M1, accepted M2 and reviewed integrated infrastructure. This supersedes a blanket restriction on starting M3 code. Tasks T10-T15 retain their scope, split into implementation versus final qualification/execution. No additional independent tester gate between phases; tester reviews the complete milestone at its end. T16 stays optional.

Briefs: M3A (local record: `instructions_between_agents/developer_m3a.md`), M3B (local record: `instructions_between_agents/developer_m3b.md`). All development uses separate checkouts from active correction/testing and preserves source/evidence versions. Current M1 defects must be reconciled before real campaign qualification. Mock outcomes are never experiment evidence.

## V4-F01/V4-F02 overseer correction verification

At `7178692`, bounded clause modality rejection and independent current compiler replay correct reported source-force errors. Exact-ratio mean/middle-pair averaging retains finite huge statistics; cache JSON encoding precedes file creation. Overseer suite: 430 passes; historical/current audits both pass twice. Full independent tester reassessment remains required. Tests/helpers are tester-owned; production fixes remain developer-owned.

## M2 usage completeness lesson

A nonempty usage dictionary is not complete token measurement. Input-only or unknown-key receipts must not turn missing fields into observed zeros or set usage_complete=true. Preserve raw metadata and per-field coverage; distinguish derived totals. M2 `c9fbff7` needs this correction and integration of corrected M1 before handoff. See the overseer review.

## M3A review lesson ? 8 October 2026

Offline namespace isolation must be checked with real OS probes; workspace-shell denial of the WSL service is distinct from a failing boundary. Final infrastructure/adapter rerun passes 34 tests with one host symlink privilege skip; Linux symlink probe passes. Partial token dictionaries still inherit falsely complete flags from old M2 into M3A rows; reconcile the corrected runner and verify per-field cost coverage end to end. Offline isolation does not qualify hosted provider transport. See instructions_between_agents/m3a-overseer-review.md.


### Tester output-path preservation ? 11 October 2026

A fresh outer pytest output directory does not guarantee fresh implicit capture paths: legacy integration tests graft the basetemp basename into worktree-local `.tmp` folders. Use a globally unique basetemp basename per role/commit/run and inspect derived output roots before running capture tests. Snapshot any potentially reused ignored capture files first. Never claim blanket preservation from a tracked/protected-file audit alone. M2 reassessment disclosed two overwritten ignored T02 smoke outputs whose original bytes cannot be restored; durable acceptance captures and frozen source were unaffected. See `instructions_between_agents/m2-tester-report-v4-f01-f02-corrections.md`.


## Experiment delivery lessons ? 12 October 2026

See [experiment retrospective](EXPERIMENT_RETROSPECTIVE.md). Confirm actual authentication/client/platform/model eligibility and execution owner before framework implementation; prove an isolated real reviewer call early. Offline passes do not establish actual client compatibility. Reuse versioned graph/review/accounting interfaces and immutable fixtures; rerun affected checks against exact bindings. Keep one current brief, archive superseded instructions, and record qualification versus runnable-campaign readiness distinctly. These are future process proposals; do not expand or interrupt the current correction.


## Research: Jev-style decomposed state labelling ? 13 October 2026

User clarified JEV means TypeSafe Jev (https://typesafe.ai/blog/introducing-system-one-models-and-jev). Official docs https://docs.typesafe.ai/introduction describe state plus atomic Choice/Score/Noul questions and typed probabilistic decisions, mixed questions per call. This fits a proposed per-element/per-visible-state probabilistic labeler, distinct from a deterministic Python rule checker. Type safety does not prove semantic truth; vendor speed/calibration claims and reference-LLM workflow comparisons are not independent evidence on this pipeline.

Primary-source OSS shortlist: https://github.com/NandhaKishorM/laya (Apache-2.0 typed non-autoregressive decisions; inspect context/checkpoint/calibration limits and benchmark provenance before selection), https://github.com/fastino-ai/GLiNER2 (Apache-2.0 local encoder classification/extraction; classification specialist family, not established a verifier of arbitrary numeric/business semantics). https://huggingface.co/openjev/openjev provides a close open-weight typed-decision interface but weights are CC BY-NC 4.0, 27B, not an unrestricted OSS model; card declares 16,384-token prompt cap. TypeSafe https://github.com/typesafe-ai/system-one-adapter-python is MIT comparison scaffolding backed by generative LLM APIs, not open Jev weights.

No plan/experiment change authorized or made by this research. Proposed comparison separates monolithic versus decomposed assessment from endpoint versus intermediate access and model identity; merely switching models cannot establish a decomposition effect. Labels should distinguish violation/support/insufficient evidence/not applicable, with explicit confidence/abstention and original evidence identity from controller, not generated prose citations. Missing capture or uncertainty is not a business violation. Actual supplied context can span 12k?35k tokens, so compact classifiers are not drop-in replacements: explicit local facts/graph neighbourhood, scope and input/output context must be selected without silently discarding requirements. Three elements over two intermediate states plus endpoint input/output yield twelve element-state label decisions, not necessarily twelve calls; batch supported questions and count model work separately from API calls. Keep testable numeric identities/contradictions, paraphrases/negation and missing-context controls; do not tune to hidden experiment truth.


### Local Laya inference feasibility ? 13 October 2026

Read-only hardware inspection: Intel Core Ultra 7 155H (16 cores/22 threads), 31.5 GiB RAM, NVIDIA RTX 500 Ada Generation Laptop GPU with 4094 MiB VRAM, ~645.3 GiB free C: disk. Existing project venv has no torch. CPU inference is feasible by model size; CUDA small-batch inference appears plausible but untested. No package/model installation or inference benchmark performed.

Current primary docs https://github.com/NandhaKishorM/laya and https://huggingface.co/convaiinnovations/laya-typed-decisions describe 421M typed-decision checkpoint, 1024-token configured context, local load/predict/predict_batch and CPU/CUDA support. One resident pinned model in a separate environment is the appropriate pilot; avoid automatic checkpoint routing as an experiment confound. Repository README and pyproject dependency descriptions differ; verify/pin an actual working installation rather than assuming prose version requirements. Weights-only estimate for 421M is ~1.57 GiB FP32/~0.78 GiB FP16; activations/runtime/batches need extra memory. Confidence is not certified calibrated: specialist card documents temperature issues and synthetic domain training. predict may silently truncate oversized input; detect encoded length and reject or use a validated compact/window policy. Window aggregation is not automatically valid for cross-window relational intent checks. Keep the current 12k?35k-token Codex packages distinct from compact Laya state/atomic-question inputs; changing context changes the comparison.


### Laya independent evidence and element-state batching ? 13 October 2026

Measured existing endpoint request (qualification-input package cafeb1): 41,441 canonical bytes; evidence 37,772; elements 28,446; job inputs 4,874; outputs 3,382; schema 2,264; original prompt 374. Element operationalization contributes 7,347, source metadata 4,590, semantic hashes 1,716 among other fields. This is serialized metadata/provenance as well as semantic content, not necessarily 41KB essential per-question reasoning context. Measurements exclude native framing/backend overhead and do not license silent removal in current campaign.

Future decomposition can build compact element x visible-state inputs, each retaining element meaning/parameters/applicability, relevant ontology/rules, function input/output/local graph facts and explicit missingness, while controller retains original evidence IDs/hashes/source registry. With E elements/S state packages there are E*S decisions before declared applicability filtering; batch decisions rather than equating them with separate hosted calls. Three elements/two intermediates plus input/output = twelve decisions, potentially four Python calls with three questions each. Batched encoder rows still cost compute, and independently separating relational facts can destroy evidence needed to judge a requirement. Any compact-context comparison with Codex must separate context/decomposition effects from model identity.

Independent primary reports reviewed: https://github.com/harrymunro/jev-laya-benchmark/blob/main/REPORT.md (September 21, synthetic 1,470 items/3,386 judgments, MLX on M3 Pro: Jev 92.9%, base Laya 65.3%, typed decisions 71.1%; short-question local speed benefit but calibration/context weaknesses; not today's pinned Windows/CPU model test). https://www.bks-lab.com/en/blog/laya-gegen-jev/ (own RTX4090 paired zero-shot 1,189-case study; short judgments more promising than large-choice/value-picking, poor invoice amount selection; checkpoint/threshold matter, synthetic data and no fine-tuning caveats). Reddit discussion https://www.reddit.com/r/LocalLLM/comments/1wmm8ql/jev_vs_laya_head_to_head_benchmark/ includes opposing views on zero-shot versus domain-tuned comparisons; claims of test-set training are not taken as established fact. https://github.com/NandhaKishorM/laya/issues/186 and model card document training/calibration separation concerns; distinguish training split use from test leakage.

Recommendation remains experimental pilot, not validated Jev replacement. Test short source-grounded supported/contradicted/missing/irrelevant cases, numeric/entity/polarity/conditional distinctions, checkpoint versions and shuffled/renamed options; assess calibration/abstention on held-out data. Do not fine-tune on the same fault cases used to claim detection benefit. No installs, inference or active experiment-policy changes made in this research.


Laya feasibility pilot is specified in small local pilot brief (local record: `instructions_between_agents/developer_laya_pilot_20261013.md`): separate pinned CPU environment, compact source-grounded element/state choice labels, 24 fixed balanced cases, no silent truncation or truth leakage, no training/prompt tuning, measured latency/quality/robustness. It does not alter current M3.

## Separate local Laya pilot
House Patterns from the separate Laya CPU pilot: compare complete token IDs against the pinned SDK sequence to refuse state, instruction and option clipping; retain truth/source/graph metadata in the controller. Dispatch multi-row requests from row count and persist timing/predictions per call. Preserve failed first attempts and identical-input reruns; distinguish Python calls, forward passes and encoder rows. Scope uncertainty must fit the declared insufficient-evidence definition: one missing-condition control was found ambiguous after prediction, preserved, and reported separately (24 planned / 23 unambiguous). Measured four-thread FP32 median/p95 was 4.384/6.469 s; 24-case batching saved Python calls but not CPU time. Amount/account and applicability failures support unsuitable-in-tested-scope, not a calibrated or general superiority claim. See handoff (local record: `instructions_between_agents/laya-pilot-developer-handoff.md`). No M3 changes.

House Pattern (13 October actual M3): M2 opening targets are unique by (kind, target_id), even across different questions. Preserve duplicate requests as invalid; do not deduplicate answers. Failure reasons built with str(dict) change after canonical JSON reload and can break strict policy replay; raw native/decoded verification and bundle integrity are separate from successful session-policy replay. See m3-failed-receipt-replay-defect-20261013.md.

M3 response-failure continuation (13 October 2026): dictionary strings are not stable failure identities; compare versioned structured fields and preserve historical receipt bytes. Ordinary validated-transport assessment-content failures terminate the affected arm, count toward matched controls and remain explicit invalid outcomes; isolation/provenance/drift/budget failures still stop the campaign. Resume only exact-bound retained observations under a declared protocol amendment, with unchanged reviewer inputs and cumulative budgets. Authority and developer instructions: instructions_between_agents/developer_m3-response-failure-and-resume-20261013.md.

Follow-up publication audit: 6,221 unique committed blobs (199,746,408 bytes)
matched no additional credential patterns or embedded archive/database signatures.
Before the latest redaction, Windows profile paths appeared in 166 published files;
corporate author email appeared in Git metadata and
evidence/m2-tester-v4/git-baseline.txt. These are privacy choices,
separate from credentials. Preserve sealed local evidence; anonymizing a publication
copy changes recorded hashes, so curated exports or excluding raw logs are preferable
to silently rewriting audit originals. Linux /home/index.html matches were public
ontology URL paths, not local home-directory disclosures; distinguish URI context
from filesystem paths before redacting.

Source publication review remains explicit in
[wrapper provenance](resources/etiq-wrapper-provenance.json) and
[reference adaptation notice](src/intentlineage/_reference/NOTICE.md). The wrapper
record says publication review is required; the reference notice records no located
top-level licence and authorized local adaptation without inventing redistribution
rights. These findings are reported for the human publication decision; credential
scanning does not establish publication permission.

User-authorized privacy removal: redact only the publication derivative, retaining
all local audit originals and original Git settings. Replace machine-specific
workspace/profile prefixes with JSON/XML-safe `WORKSPACE_ROOT`/`USER_HOME` markers;
replace corporate author email with a neutral project address. All 167 original
files are preserved and parsed JSON/XML stay valid. Application source is unchanged.
The publication repository uses `IntentLineage contributors` and
`noreply@example.invalid`; GitHub account association can use an owner-supplied
GitHub privacy address later. Public changed-file hashes and redaction categories
are in `resources/publication-sanitization.json`. Keep original recorded seals/
hashes tied to originals; do not claim that redacted copies retain those signatures.
Do not erase source attribution or invent redistribution grants to clear an IP note.

Permission-note interpretation: the wrapper recovery includes five source files
from `etiq_improvements2`; `_reference` helpers and upstream snapshots derive from
`use_case_icp`. No public redistribution terms were established by their inspections.
This is incomplete permission documentation, not a finding of unauthorized use.
The copyright owner or authorized publisher can approve distribution and choose
licensing; ownership/authorization remains unconfirmed here. The Etiq library is
separately installed and its proprietary terms remain separate. See
[GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
and [commit email privacy](https://docs.github.com/en/account-and-profile/reference/email-addresses-reference).


13 October user-selected QA-output exclusion: accumulated tester outputs,
generated developer validation reports/logs and capture command/log records
are local archive material. Remove them from both indexes and only amend the
fresh publication commit. Keep fixture data and validation Python source used
by regression tests; preserve all excluded bytes on disk. The sanitization
manifest now covers only redacted files still present in the publication.


## M3 amended actual execution finished — 13 October 2026

The Developer/Experimenter completed all six cases and all30 E/H/A/R-H/R-A rows under the explicit response-policy/retained-continuation amendment.178 charged campaign calls (79 verified retained,99 fresh), three terminal invalid A answers, zero hard-stop failures; complete reported campaign usage3641361 tokens. All223 affected checks pass. Complete raw/policy/score/accounting replay and private export/relocated replay pass; original79-call interrupted evidence now replays without byte edits. H detects both persistent and both repaired faults; endpoint arms miss both repaired faults. A has three invalid rows. One dependent pair and incomplete semantic coverage limit these descriptive results. Execution is finished; scientific completeness and complete-M3 testing/acceptance remain pending. See instructions_between_agents/m3-experiment-developer-handoff.md for exact code005383b/source8c3369, qualification/protocol/campaign hashes, all costs/coverage and evidence paths. Source21f successful qualifications and zero-new-call checkpoint setup failure remain preserved; qualification costs stay separate. No reviewer prompts/schema/Etiq/permissions/bounds changed in this amendment.

House Pattern: completed execution, valid assessments, semantic coverage and scientific acceptance are distinct. Report all scheduled invalid arms; compare only definitive paired observations. Reusable observations require immutable raw/request/source/transcript/usage bindings, exactly-once admission and the original cumulative ceiling. Reviewer history is never continuation state.
