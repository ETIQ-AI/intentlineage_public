# M3 Developer/Experimenter handoff — execution finished; acceptance pending

13 October 2026. The amended real campaign finished all six scheduled cases and all 30 arm rows, exiting 0 at 20:14:50 UTC. It used 178 charged campaign calls: 79 verified retained observations and 99 fresh calls. Three A arms terminated with genuine duplicate-opening rejections; all other arms completed their scheduled calls. `execution_finished=true`, `scientific_complete=false`. All sessions retain incomplete semantic coverage. This is a completed execution and evidence delivery, with scientific completeness and complete-M3 testing/acceptance still pending.

## Corrections and retained lineage

Implemented the active response/resume brief (local authorization record), SHA `47641495bef60c8dc2a19cacd9886492db2f6e86c36a5bdb6540b1769373b510`. The honest source-bound user continuation mechanism authorizes this amendment and automatic execution; no new Overseer decision was fabricated.

`review_failures.py` records versioned structured fields and canonical failure text. The narrow legacy parser uses safe literal parsing for exact supported field families, rejecting changed reasons/exit codes, duplicate keys, unknown families and malformed input. The original case-006/A failure now replays deterministically without changing any historical byte or treating its answer as valid.

Completed, isolated, model-attributed assessment-content failures become terminal `invalid_response` arms. Earlier valid assessments, rejected-call usage and remaining coverage are retained. Isolation, model/source/runtime drift, infrastructure, corrupted evidence, invalid charging/usage, or exceeded fixed limits still stop the campaign. Reasoning retries remain zero; only the existing positively confirmed no-turn transport retry is permitted. No answer repair, deduplication, replacement calls or resumed reviewer threads occurred. R controls match actual charged treatments, including rejected calls.

`experiment_resume.py` validates the original 79-call prefix and admits call identities exactly once, including strict boolean charging and bound case/arm/request/source/transcript references. It preserves the two complete matrices and case-006 E/H/A, runs only its missing R-H7/R-A5, then runs case-005, case-001 and case-004 in the original order. The original 198-call ceiling leaves 119 calls after the prefix; the concrete continuation maximum was 111, and actual new work was 99. Unused allowance was not spent.

RED commits `2a4f88d` and `9c9db2d` precede response/replay/admission fixes in `21f7a643440c3397fef39e1b5819b1577ece749b`. That source passed two genuine qualifications, then a cost-checkpoint filename collision stopped setup before any new scientific call. The launch and qualification remain preserved. Checkpoint RED `314cd56` precedes the narrow fix in **`005383bab020ac52a04f0a0d4713d87377c4bd64`**: immutable per-unit `cost-checkpoints/<unit_id>.json`, preserving exclusive creation. The corrected source received its own fresh qualification pair; the prior pair was not relabelled.

## Exact package and unchanged reviewer protocol

Execution checkout/branch: `.tmp/m3b-chatgpt-correction-20261012`, `m3b-chatgpt-correction-20261012`. Source commit `005383bab020ac52a04f0a0d4713d87377c4bd64`; full 58-source digest **`8c3369b80d6c36f5757dcb7cafe0447480270a76df194f9db22137b7d1b9e5a9`**, unchanged after execution and final checks. Parent code `6392862925ff1803ac784e34a6f58d36be80bcf9`, digest `f5df2dadd1cb1f13dbbc37ab3765f06b94768a852ef5d317dd68b979e757192b`; parent report `19d31f0`. Reviewed integration ancestry and accepted M1/M2 are preserved.

- Qualification launch: `662cd3a608be2eba84d668179bfffbbb77a1c0b8f54da30fc664cfa55882b781`.
- Current genuine qualification: `3f1ef1311d3ce01021de7b1650f8ad3d4f155522af6120f7ba3544234573fc02`.
- Frozen amended reviewer protocol: `30de9172bbcc9f41880ef78ac0487126201e4b526d8f977ebf2e6adc80cdaf94`.
- Enclosing campaign protocol: `b50ba93045dfdab4740aa5e3f4e728c585ca731c8250636e451336c812e88e3b`.
- Original reviewer/campaign protocols: `bc033ba73edab345a362002cb5351681a5419058be54bbe76d775e7f0bc67f04` / `e2301e63d71b07976f6b46cd0b8ecf21184e4d92f8000af53469a8f3746ee5dc`.
- Continuation manifest: `3faaa4018dcd9d150cfffc5304cb269265e1849d4e9e9b720992778e812d1fce`; retained private bundle `6fb50d8513260decf165a5ccb02c078d8ede29df7c89c0bc601aabdd512c9b8f`.
- Bank: `00823f3f8cbf10e8a8ca0b017b32d022d86b7fd255c766f310a89bd46846a00d`; profile `8701657b4a8c8ea0351ea30cf5cdb1c75b16a0e586771bac29132047049ac6ae`.
- Final campaign: `5988fca873f1d1af1fe1bbbfba51fee58155ae4f9ee0b52779d2d987709cc924`; delivered score: `e063b9a5a110687d3f24feb0aa686cb6c4086478ab6c2da8f3b29bd086689e7c`.

All arms use native Linux ELF Codex 0.160.0, binary SHA `12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad`, read-only `/usr/local/bin/intentlineage-codex`, existing ChatGPT login, client-effective **gpt-5.5/low**. No API keys. Backend-served identity, internal provider attempts and monetary charges remain unavailable rather than inferred.

Reviewer prompts, common compact substantive inventory, request views, permitted evidence, concise guidance, M2 schema/citation/element/unique-target checks and `reply_json` envelope are unchanged from the original one-function campaign. Endpoint/function qualification input SHAs remain `d13d253ebb9e52c0db5c354d81e7c2a5f29c6fc7911371961eea9cda930bf553` / `466a3c1f4f5af59348396d62c422f4cc98d2c3313a48b728239d367b04a43b36`. Etiq capture, transport, worker and native isolation remain unchanged. Only controller response policy, replay and continuation bookkeeping are amended; the execution is explicitly not claimed under the original unmodified protocol.

Fixed population: six mechanically qualified variants from one payment pair, five arms, one repeat, seed 20261012, original order 002/003/006/005/001/004. H batch size one, N=7; A cap9, two operations/100000 disclosure bytes. Fixed observed input/output limits196608/8192 tokens, 300 seconds per native invocation, raw events exactly33554432 bytes, encoded common/H caps300000/200000 bytes. Mandatory evidence and raw events were not truncated. Each new call used a fresh isolated process/thread/turn, without own-answer/cross-arm history. Hidden truth, registry, ledger and continuation manifest stayed outside reviewer mounts.

Both current-source qualifications passed unchanged native envelope/M2/concise validation, model/settings bindings, complete usage and all14 isolation probes. Endpoint:13077 input/5164 output/18241 total/cache0; representative function:18095/5072/23167/cache1536. Current qualification total31172/10236/41408/cache1536. Original/relocated qualification export replay passed; private ZIP SHA `7b2d712268784bb27a958a4098ec280978c73804a27ac9854f9261f4a9083406`.

## All scheduled outcomes, calls and coverage

Cells show delivered outcome and actual charged calls. No scheduled row is dropped.

| Case | Kind | E | H | A | R-H | R-A |
| --- | --- | --- | --- | --- | --- | --- |
| case-002 | benign | no_alarm (1) | no_alarm (7) | no_alarm (9) | no_alarm (7) | no_alarm (9) |
| case-003 | persistent | detected (1) | detected (7) | detected (9) | detected (7) | detected (9) |
| case-006 | repaired | missed (1) | detected (7) | invalid_response (5) | missed (7) | missed (5) |
| case-005 | persistent | detected (1) | detected (7) | invalid_response (7) | detected (7) | detected (7) |
| case-001 | clean | no_alarm (1) | no_alarm (7) | invalid_response (5) | no_alarm (7) | no_alarm (5) |
| case-004 | repaired | missed (1) | detected (7) | detected (9) | missed (7) | missed (9) |

Every invalid arm rejected a duplicate opening target under unchanged M2. Valid earlier replies remain partial observations, not repaired terminal findings.

| Case/A | Rejected call | Prior valid replies | Prior assessments | Unchecked functions | R-A calls | Rejected-call tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| case-006 | 5 | 4 | 104 | 3 | 5 | 23871 |
| case-005 | 7 | 6 | 156 | 1 | 7 | 22499 |
| case-001 | 5 | 4 | 104 | 3 | 5 | 23485 |

No control failed; all R-H/R-A counts match actual H/A treatment counts. All30 sessions report incomplete semantic coverage, with95 insufficient-element entries, one uncovered-element entry and198 unresolved-question entries across rows. The invalid arms leave3/1/3 functions unchecked for cases006/005/001. Missing or insufficient evidence never becomes preservation or a negative finding. Full per-row lists, partial assessments, scopes and costs are retained in the delivered score and `scheduled-observation-coverage.json`; CSV/JSON cost/coverage tables accompany it.

H detected both persistent and both repaired faults. E, R-H and R-A detected both persistent faults and missed both repaired faults. A detected case003 persistent and case004 repaired, but cases006 repaired,005 persistent and001 clean are invalid, not missed/no-alarm. Valid clean/benign rows have no false alarms; A has no valid clean result. No statement about general semantic accuracy follows from structural validation.

Paired fault contrasts require definitive observations. H/E and H/R-H each have denominator4: both detect2 persistent cases, H-only detects2 repaired cases, endpoint-only/neither0. A/E and A/R-A each have denominator2: both detectcase003, A-only detectscase004, endpoint-only/neither0. Invalid A cases are excluded only from those definitive contrasts, remaining in scheduled reporting. One dependent underlying pair, one repeat, no independence-based intervals, p-values or generalization claim. Adaptive invalidity is a material limitation; no prompt improvement or rerun was added to obtain nicer outcomes.

## Complete costs and checks

| Arm | Calls | Invalid arms | Input | Output | Total | Cached input |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E | 6 | 0 | 77383 | 32159 | 109542 | 20480 |
| H | 42 | 0 | 740320 | 217760 | 958080 | 53760 |
| A | 44 | 3 | 800964 | 218059 | 1019023 | 64512 |
| R-H | 42 | 0 | 540903 | 219090 | 759993 | 55296 |
| R-A | 44 | 0 | 566740 | 227983 | 794723 | 64512 |

All178 campaign calls, including all3 rejected answers, have complete reported usage:2726310 input +915051 output =3641361 total;258560 cached input is included in input. Invocation elapsed sum21909.307 seconds includes setup/probes, is separate from model latency, and spans original plus amended execution. No transport or reasoning retry occurred. Monetary cost remains unknown.

Qualification attempts are a separate ledger: four preserved historical failures plus four successful source-specific pairs,12 logical/conservatively accounted slots,10 usage-known and2 unavailable. Known qualification subtotals143994 input/57436 output/201430 total/cache4608 are not a complete imputed total. Current-source pair41408 is included there, not in campaign outcomes. Original HTTP400/uniqueItems, empty-input,1MiB event-capture and later token/citation failures remain unchanged. The intermediate checkpoint collision consumed zero new scientific calls. Combined campaign/qualification known token subtotal3842791 is descriptive only; provider billing/internal attempt counts remain unknown.

Final affected checks: **223 passed, zero failures/errors/skips**, covering deterministic/legacy failure replay, citation/element/duplicate content rejection, arm containment and hard stops, exactly-once/cumulative admission, neutral controls/scoring, native envelope/events/capture/accounting/qualification dispatch, original M2 behavior and checkpoint recording. Earlier RED and pre-fix failing JUnit files remain preserved. Full source digest rechecked after campaign and checks. Offline fixtures verify software only; the actual qualification and campaign receipts are genuine model outcomes. No midway tester was commissioned.

## Replay, private export and reproduction

Complete campaign read-only replay passes, recomputing all30 outcomes, contrasts, raw/envelope/decoded relationships, source/qualification/manifest lineage, costs and exactly-once identity. Complete private bundle SHA **`d0db6a42dbbcfe157995c7bd2713801a02a227d2f8aa911c05dddaff23958f92`**, 6199 exported files. Original and relocated complete bundle replay match exactly, with six units and the score above. Bundle `empirical_admissible` describes actual-provider provenance, not semantic completeness or milestone acceptance. Credential scan passed locally without printing/exporting token values. Bundle truth/source/registry/provenance remain controller-private and must never become reviewer evidence.

The original genuinely interrupted79-call campaign remains byte-identical and its13 sessions, including the duplicate-opening failure, now replay successfully. Current-code original and relocated interrupted-bundle replay match; exact2814-file membership and all79 observations remain valid, while the rejected answer remains invalid. See `original-interrupted-replay.json`, verification SHA `749b0c0472d3619a563c672cfa33736cbb0d7424cd9693db40fa54d86800ef64`. A separately labelled derived interruption fixture contains that retained prefix plus the first new actual case006/R-H/0001 call before session completion. It uses actual bytes, makes zero new model calls, reports80 known calls/no score, and passes private interrupted-bundle replay. It is not presented as a new genuine campaign interruption or synthetic outcome.



The repository contains compact public derivatives and the exact executed source.
Raw calls, account-bound qualification/authorization records, private signing
catalogues and complete historical replay bundles remain local. The public
records do not replace original signed audit evidence.
