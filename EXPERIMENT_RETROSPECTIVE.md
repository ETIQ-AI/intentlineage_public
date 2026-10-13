# Making the next execution-graph experiment faster

12 October 2026. Overseer retrospective and proposed process, based on this conversation, project instructions, developer/tester reports and repository history. **Planning analysis only: do not interrupt or expand the current authentication correction.** No actual campaign result exists yet. The current priority remains a successful real ChatGPT-authenticated qualification followed by the approved experiment.

## Main finding

We validated a substantial offline framework before proving the actual authenticated reviewer boundary. The framework was useful, but its passing tests did not establish the dependency most likely to prevent execution. API-key routing, actual model access, CLI permission parsing and sandbox invocation should have been settled first. The most valuable speed improvement is an early thin end-to-end path, followed by reuse of a qualified framework across experiments.

The Overseer owns much of this process failure. I prescribed an API-key path without confirming the user's existing Codex access; accepted offline readiness without enough emphasis on real-client compatibility; gave estimates that were not based on comparable task scope; and repeatedly added current-status banners over obsolete instructions. These choices caused avoidable rework and handoff ambiguity. Correctness defects uncovered independently were real and still needed correction.

## What actually consumed time

| Source of delay | Observed evidence | Change for next experiment |
| --- | --- | --- |
| Intent scope initially wrong | Conversation moved from Spec Kit/adapted/manual intent records to prompt decomposition using an extraction model. | Specify the source prompt, automatic extraction output and one success/failure example before choosing a package. |
| Misunderstood graph/state semantics | User repeatedly clarified that states are actual intermediate function outputs and requested native graph/nesting. | Inspect one actual native graph and one opened nested function before designing retrieval/assessment. |
| Wrong authentication assumption | API-only implementation accepted at 4896fce; actual setup found only ChatGPT OAuth and no API key; user then corrected the route. | Record authentication, model ceiling, available platform and execution owner in the first launch configuration. |
| Real CLI checked too late | EXP-SETUP-01 quotes filesystem override keys incorrectly; EXP-SETUP-02 sandbox argv tries to execute linux. Offline test doubles had passed. | Run actual credential-free parser/sandbox probes before implementing the full transport. Then perform one bounded authenticated invocation. |
| Mutable dependency baseline | M3A moved from old M1/M2 through 1f1c7c1 and later accepted 6dd91fa; M3B merged provisional then reviewed M3A. | Build adapters against a small versioned interface; integrate accepted exact commits once where possible. Provisional work must have a named owner and reconciliation budget. |
| Genuine accounting/replay defects | Partial usage incorrectly complete, case-collision validation and resealed false terminal summaries. | Keep these regressions in a reusable core qualification suite; future experiment adapters inherit them instead of rediscovering them. |
| Repeated verification/evidence work | Large suites, preserved snapshots and archives were repeated at multiple submission/review stages. | Cache results against exact source/environment/input identities; rerun affected checks on change and full suite at a meaningful integration boundary. Independent final tester remains independent. |
| Fragile ignored fixtures/temp paths | Missing worktree fixtures and reused basetemp-derived paths; two ignored smoke outputs irrecoverably overwritten. | Package minimal immutable test prerequisites and enforce globally unique output roots. A fresh outer temp directory is insufficient. |
| Conflicting living documents | Active briefs still contained superseded API/human-launch/pending-acceptance instructions below newer banners. | One current status/contract at the top, history in linked archives; rewrite superseded active instructions rather than accumulating overlays. |
| Execution ownership settled late | Implementation initially included experiment completion; user later assigned a separate Experiment Developer and direct launch authority. | Name implementation and execution owners from the start; state who can launch, what requires review and what the deliverable is. |

Evidence anchors: M1 tester report (local record: `instructions_between_agents/m1-tester-report-v4-corrections.md`), M2 defect report (local record: `instructions_between_agents/m2-tester-report-v4.md`), M2 final tester report (local record: `instructions_between_agents/m2-tester-report-v4-f01-f02-corrections.md`), M3A integrated review (local record: `instructions_between_agents/m3a-overseer-clearance-20261012.md`), M3B integrated preparation review (local record: `instructions_between_agents/m3b-integrated-overseer-review-20261012.md`), real implementation review (local record: `instructions_between_agents/m3b-execution-implementation-overseer-review-20261012.md`), actual setup failures (local record: `instructions_between_agents/m3b-experiment-qualification-review-request-20261012.md`).

## Next time: prove the risky path first

Before a substantial implementation brief, the Overseer and implementation developer should produce one short launch/experiment contract:

- Scientific question and primary comparison; explicit arms and shared versus disclosed context.
- Domain workflow, original user prompt, ontology/rule sources and supported element meanings.
- Actual capture library/version, one dataset/function/dataset graph example and nesting behavior.
- Existing authenticated client, available platform, requested model ceiling and account access. Never infer a CLI-account model from the development chat's model.
- Execution owner, direct-launch authority, test schedule and cost/call limits.
- One concrete review input/output, required isolation boundaries and what receipts the real client exposes.

Then run a small vertical example through actual code: prompt -> decomposition -> existing graph capture -> whole-job input/output -> one joint relevance/assessment response -> validated saved replay. Include a small nested function, one clean execution and one real injected fault. Disclose/open the function and check that an additional fresh review can use the evidence without seeing hidden truth or sibling answers. This is technical qualification, not a scientific result or an independent tester phase.

Use actual CLI config parsing and native sandbox probes early. Supported authentication must work without leaking credentials/history. One bounded real model call follows only the necessary existing permission/qualification review. If access, an eligible model, client policy or graph capture fails, resolve it before building broad scheduling/archives/scoring. The current experiment still requires its two-call qualification; this proposal does not lower that requirement.

Only after that path works should we expand to all five arms, full failure accounting, qualified faults/repeats, analysis and final export. Start with an appropriate bounded pilot after protocol approval to measure call latency, request/context fit and rate limits before expanding the campaign. Keep pilot qualification/outcomes explicitly separate according to the frozen protocol.

## Reusable core versus per-experiment work

| Reusable core (qualify once per exact compatible environment/client) | Per-experiment adapter/configuration |
| --- | --- |
| Native graph IDs/edges, nesting and disclosure authorization | Workflow entry, actual graph/capture bindings and supported types |
| Frozen artifact descriptions/statistics/bounded reads | Sensitive columns, bounded sample policy and relevant domain summaries |
| Versioned joint-review schema and exact citation validation | Prompt, intent taxonomy, ontology sources and grounded business rules |
| Endpoint/fixed/adaptive review and neutral call-matched controls | Selection policy, batch size/counts, disclosure/call budgets |
| Supported auth/client launcher, private contexts and boundary probes | Available account/model/CLI/runtime and necessary qualification changes |
| Partial usage, failures, retry accounting and transcript-derived replay | Mechanically injected domain faults, repairs and matched controls |
| Serial scheduling, stopped-run retention, scoring and export/replay | Population/repeats/seed and exact scientific estimands/denominators |
| Known integrity/security regression contracts | Domain-specific observable fault witnesses and interpretation limits |

Existing M1/M2/M3A implementations provide much of this core. Reuse code through explicit interfaces rather than importing entire previous experiment archives into each new checkout. Keep reviewed historical evidence available centrally and immutable. A source bundle is provenance; it should not become the new experiment's implicit test prerequisite.

A graph adapter should expose stable concepts: job inputs/outputs, visible native functions/artifacts, nesting, describe/read and signed/open authorization. Do not force every application to carry intent/rule IDs in intermediate values. Actual native capture gaps stay explicit. A domain fault adapter should inject before execution, declare repair, qualify real witnesses and keep its truth private. Do not turn a workflow-specific fault list into generic core logic.

Use supported client authentication and its actual receipts. No hand-written OAuth-to-API conversion. Client routes must expose their real capabilities rather than mimic an API-only contract. Missing usage fields remain unknown. Account quotas/usage should not be presented as fabricated API dollar costs.

## Verification without multiplying full campaigns

Use three layers:

1. Fast contracts for changed pure functions and adapters, including existing F01/F02 regressions and strict schema/citation checks.
2. One real graph fixture and small isolated client/recorded transport integration paths, including actual config parsing and denial probes.
3. Full milestone/integrated suite at release boundaries and the independent tester's complete milestone-end assessment.

Overseer should review diffs, exact test/source/environment bindings and independent reproductions; avoid rerunning a long full suite merely because a documentation-only handoff commit exists. Changed capture/client/isolation/schema paths justify fresh affected integration checks. Changed source/environment/auth/settings invalidate the appropriate cached qualification. Do not use a test pass under one platform/auth route as evidence for another. Preserve failures; one successful rerun does not erase the first failed run.

Representative retained runs illustrate verification costs: M2 tester full suite 616 tests took 584.14 seconds; M3A guarded full suite 796 passes/one skip took 623.61 seconds; M3B integrated run 388 passes/one skip took 561.20 seconds. These are different scopes, not additive measures of total project effort. The M3B implementation commit window from first execution RED at 13:14 to handoff at 15:57 spans about 2h44m on 12 October; it does not measure continuous agent work or establish a future duration.

Avoid repeatedly hashing every unrelated historical file during every small check. Verify immutable archive identity once per checkout/run and retain exact member-hash manifests; verify newly produced files and affected bindings each submission. Do not weaken authenticity or replay checking. Evidence paths should be short, uniquely named and declared before tests. Artifacts should be referenced by content digest and copied only when an independent execution needs them, with credential/private-truth visibility explicit.

## Fewer handoffs, clear responsibility

Keep the existing role discipline: developer implements/TDD, tester independently tests at complete milestone end, Overseer owns acceptance, paper writer gets final results only. Experiment Developer is the execution-stage developer role, with explicit setup/run authority.

For similar future projects, retain few meaningful milestones: (1) usable capture/elements with thin real reviewer qualification, (2) verified graph assessment and ready-to-run integrated experiment, (3) executed experiment and analysed evidence. This is a future proposal, not a rewrite of accepted milestones. When authorized early development overlaps, freeze exact inputs and resolve dependencies at one explicit integration handoff rather than repeatedly describing provisional code as nearly ready.

At a run handoff deliver one coherent packet: reviewed source digest, auth/platform/model identity, qualified boundary evidence, concrete frozen scientific configuration, budgets and launch authority. Bundle implementation review and concrete protocol review when both are ready, while preserving distinct qualification and campaign decisions. Do not invent additional approvals for routine reversible setup already authorized. A missing model/access or isolation failure still requires a real decision; do not wave it through for speed.

Active briefs should say precisely: work now, immutable inputs, expected output, acceptance check and blocker owner. Remove superseded requirements from active prose and archive them. In particular, avoid 'ready' without scope: offline framework ready, authenticated call qualified, and experiment runnable are separate factual states.

## Measure speed instead of guessing

Record task timestamps for code start, first actual client call, first usable graph, first complete small replay, code review, qualification, protocol release and first/final campaign call. Log implementation, automated validation, external wait and rework separately. Include call counts/latency/context/usage and failure rates. Derive forecasts from a comparable completed adapter task or pilot; show uncertainty and unresolved dependencies. Do not infer implementation time from test count or commit timestamps alone.

Primary efficiency measures: elapsed time to first isolated real reviewer call; time from reviewed code to pilot; number of authentication/platform pivots; full-suite reruns per unchanged source; handoff count; time spent waiting for concrete decisions; capture/evidence copied or rehashed; corrective cycles for domain versus reusable-core defects. No exact savings percentage is justified by the available history.

## Priorities

| Priority | Change | Owner | Completion evidence |
| --- | --- | --- | --- |
| Now | Complete existing ChatGPT route/CLI correction, then bounded actual qualification | Implementation + Experiment Developer; Overseer review | Genuine eligible-model call and boundary receipts; no API-key request |
| Next experiment start | Confirm auth/client/model/platform/owner before package/framework choices | Overseer | Short launch contract with observed access and actual parser probe |
| Before framework expansion | One thin actual graph-to-review-to-replay example | Developer | Retained real qualification and native nesting evidence |
| After current campaign | Extract reviewed shared interfaces and minimal immutable fixtures | Developer | New experiment imports core without copying predecessor campaign trees |
| Before next handoff | One coherent current brief/status and archived history | Overseer | No contradictory active auth/launch/acceptance instructions |
| Continuously | Exact result reuse and scoped retesting; unique output paths | Developer/Overseer/Tester within roles | Changed-scope test records and intact evidence |

Do not start refactoring or another architecture project before this experiment runs. Finish current correction and qualification first. Use these lessons when packaging the completed framework and planning the next experiment.
