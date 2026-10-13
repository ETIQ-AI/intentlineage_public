# IntentLineage — latest M3 experiment

This repository contains the latest delivered amended payment-workflow experiment
from 13 October 2026: **six cases, five arms, 30 scheduled outcomes and 178 charged
campaign calls** using ChatGPT-authenticated Codex gpt-5.5/low. Execution finished;
scientific completeness and final independent testing/acceptance remain pending.
Three adaptive arms returned invalid responses, and every arm has incomplete
semantic coverage. One dependent payment pair and one repeat limit interpretation.

Read [the experiment report](experiments/latest/README.md), the
[outcome table](experiments/latest/complete-outcome-coverage-cost-rows.csv),
[score summary](experiments/latest/score-summary.json) and
[protocol](experiments/latest/protocol.json). Original results are retained locally;
public reductions/redactions are documented in
[publication provenance](resources/publication-sanitization.json).

## Setup and offline checks

Use Python 3.11 with the verified dependency pins. Etiq is installed separately.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e . --no-deps
.venv\Scripts\python.exe -m pytest -q
```

The included tests cover current native transport, strict reply validation,
runtime boundaries and continuation accounting without inference. The larger
historical/private evidence-dependent test archive stays local. Source under
`src/intentlineage/`, the payment workflow and wrapper are the executed/reused
implementation. Source identity is pinned in the publication provenance.

This compact snapshot supports code inspection, offline tests and analysis of
delivered results. Complete raw-call replay and re-launching the historical
campaign require the local private evidence and account/runtime/authorization
bindings. Live qualification and launch gates are preserved in code. This cleanup
does not initiate new model calls, replay qualification as science or imply
acceptance. Public protocol records are descriptive derivatives, not fresh launch
authority.

## Repository scope

Old `.etiq` captures, previous experiment/QA outputs, predecessor snapshots, agent
handoffs, Laya pilot code/results, private signing keys, credentials and raw replay
bundles are excluded. The eight user-selected planning/project documents remain;
their older milestone references describe local research history. No original Git
history is copied because it contains private keys. Push only this fresh snapshot;
no remote or push has been configured.

Wrapper and adapted reference-source attribution/notices remain included. Their
publication ownership/licence question remains recorded in
[wrapper provenance](resources/etiq-wrapper-provenance.json) and the
[reference notice](src/intentlineage/_reference/NOTICE.md). No redistribution grant
or project licence has been invented. The Etiq dependency retains its own terms.
