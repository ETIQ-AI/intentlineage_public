# Overseer results assessment: direct-start single-review experiment

14 October 2026. Reviewed delivery9c41294 and instructions_between_agents/m3-single-review-experiment-developer-handoff.md; actual campaign .tmp/m3b-chatgpt-correction-20261012/.tmp/actual-m3-single-review-campaign-eb36cd56f47f4a268d4f179a0da0abec. Completed six cases,30 scheduled rows,172 new charged calls; no separate qualification pair. Final campaign digest8cc670e7d5e184eb2e5f371ecf8fb116f9ed15e49a062f7c2b037d24e76ec834.

## Independent evidence review

Loaded the actual campaign and verified its canonical campaign seal. Revalidated all172 raw replies against their saved request evidence using the delivered single-review validator:171 pass; case006/H/call3 reproduces the sole reported invalid response. Inspected target-element judgments and their citations for all four fault cases, checked all30 scored outcomes and reconciled all12 treatment/control count matches. Counts sum172: E6,H38,A45,R-H38,R-A45. The developer's full native isolation/file-set/export/relocated replay and offline-test results remain delivered evidence; this review did not independently repeat the full multi-thousand-file replay or commission tester work.

## What the results support

Persistent amount and account faults are detected by E,H,A and their endpoint-only repeat controls. The actual target contradictions cite GBP amount100 versus10000.0 and accountACC-17 versusACC-18, rather than missing representation objects or ontology serialization. Both repaired faults disappear from the endpoint; E and endpoint-only repeat controls report support/no contradiction and are scored missed with respect to injected intermediate faults. This does not mean the endpoint reviewer could have observed hidden intermediate behavior from its evidence.

For repaired amount case004,H andA cite approve_payment boundary values100 and10000.0 before later repair. For repaired account case006,A cites boundary accountACC-17 andACC-18 before repair. H is invalid and stopped before its later initial scopes; do not count it as a semantic miss or assume it would have detected the fault. Clean/benign cases have no scored alarms in any arm. These are actual inspected payment-target detections; this is not an adjudication of every one of the24 elements across every scope.

Descriptive outcome summary: A detects4/4 fault cases; H detects3/4 with one invalid; E and repeat controls detect2/4, missing both repaired cases. Six dependent variants of one pair, one repeat: no general accuracy, statistical significance or robust A-versus-H superiority inference. All six A sessions are semantically incomplete; valid detected outcomes do not establish complete satisfaction/verification of the remaining elements.

## Adaptive opening did not cause initial detection

Independently traced validated A replies in call order. First target contradiction: case003 call1, case005 call1, case004 call2, case006 call4. All occur within initial seven high-level calls. Disclosure happens afterward: case003 one follow-up (call8); case006 two follow-ups (calls8/9). A asks to locate/explain the mutation, not to discover a fault unseen in the initial phase. Thus this run supports intermediate evidence beyond endpoints, but does not demonstrate extra detection benefit of nested adaptive opening or a cheaper selective search. A still checks the same initial seven scopes as H. Only one nested child review is exercised; deeper child request is budget-denied. No live artifact-inspection actions are exercised.

## Sole rejection and execution behavior

Case006/H/call3 cites /sample/0/execution_receipt/decoded as a complete observed receipt dictionary. Its canonical observed value is145 bytes, exceeding the declared64-byte small-value cap, so the pointer is outside the generated permitted-small-reference list. This is a real supplied receipt, not evidence of a fabricated ID/value. The answer fails the compact wire constraint; its semantic interpretation is not adjudicated by that rejection. A formatting violation invalidates the whole call and terminates H, leaving four initial functions unchecked. The charge and two earlier valid replies remain; R-H matches3calls. The campaign continues as authorized. Do not repair this historical answer or rerun it to improve the score.

This is a remaining response-contract reliability limitation: a compact-citation rule can censor useful assessment when the model cites a genuine modest-size object. It does not establish a production validator defect because the rule was frozen and the model was instructed to use permitted small citations. A future contract may prefer scalar/field references or deliberately allow small bound composite values; any change requires an explicit new protocol, not altered historical scoring.

## Delivery and next decision

Execution lasted10:21:35Z–12:52:04Z (~2h30m30s), per the retained launch record. Token total3274768, including rejected call; monetary cost unknown. No separate qualification charges, transport failures, duplicate-opening failures or technical hard stop are reported. The repaired interface is exercised without duplicate-opening rejections in this run, but comparing failure rates to the old run is not a controlled ablation: prompt, inventory and contract changed.

Disposition: useful completed descriptive experiment, with target-detection evidence supporting the endpoint-versus-intermediate distinction. No immediate developer fix is identified as necessary to preserve or interpret these results. Full milestone/software acceptance and broad semantic accuracy remain separate. Scientific interpretation is owned by Overseer/reviewer, not tester. Further work should be selected by the user: improve citation robustness, investigate localization from openings, or design genuinely selective checking; do not automatically launch more inference or retrofit results.
