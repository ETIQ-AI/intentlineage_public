# IntentLineage — latest completed experiment

## Experiment and results

Can intermediate execution evidence reveal violations that endpoint review misses? We evaluated IntentLineage on a synthetic Python payment workflow captured by Etiq. A natural-language payment request was compiled into 24 overlapping intent, ontology and rule records. Six variants of that request covered clean and decimal-equivalent benign executions, persistent amount/account mutations, and mutations repaired before the final output.

Five arms compared one endpoint review (E), seven high-level function reviews (H), the same initial reviews with bounded nested opening (A), and endpoint-only repetitions matched to H/A's actual call counts (R-H/R-A). All used client-effective `gpt-5.5` with low reasoning effort in fresh isolated reviewer sessions. Each arm ran once per case. A call jointly assessed multiple elements; multiple calls within an evaluation were review steps, not independent experimental repeats.

The 30 case/arm evaluations used **172 charged calls: 171 structurally valid replies and one invalid reply**. All arms detected both persistent faults. A detected **4/4 fault cases**; H detected **three, with one invalid outcome**; E and both repeated-endpoint controls detected **2/4**. H/A detected the repaired amount fault, and A detected the repaired account fault. Endpoint arms missed both because the intermediate mutations were absent from their repaired endpoint evidence. H's invalid reply violated the citation-format restriction; it remains counted in costs and is not a semantic miss. No arm produced a scored alarm on either nonfault case. Calls totaled E6/H38/A45/R-H38/R-A45, using 3,274,768 tokens over approximately 2 h 30 min.

These observations support the feasibility of execution-grounded intent checking in this fixture. All A detections preceded nested opening, so additional detection benefit from nesting was not demonstrated. All six A evaluations retained incomplete software coverage. One payment request, six dependent variants and one repeat support descriptive findings, not generalized accuracy or statistical significance. The workflow's business roles were programmed; autonomous multi-agent payment coordination was not evaluated.

See the [experiment report](experiments/latest/README.md), [all 30 outcome and cost rows](experiments/latest/complete-outcome-coverage-cost-rows.csv) and [reviewed interpretation](experiments/latest/interpretation.md).

## Experiment snapshot

This snapshot contains the completed **14 October 2026 single-review experiment**:
six cases, five arms, 30 scheduled outcomes and **172 fresh charged campaign calls**.
There were zero separate qualification calls. It replaces the previous experiment
in the current files; normal Git history and local originals remain preserved.

The reviewer used ChatGPT-authenticated Codex gpt-5.5/low. One H arm is invalid;
all six adaptive arms have incomplete semantic coverage. One dependent payment
pair and one repeat limit interpretation. Full milestone/scientific acceptance
remains pending. Later citation-fix reruns were interrupted; their partial
results are excluded from this completed-experiment snapshot.

Read [the experiment report](experiments/latest/README.md),
[outcomes](experiments/latest/complete-outcome-coverage-cost-rows.csv),
[score](experiments/latest/score-summary.json),
[protocol](experiments/latest/protocol.json) and
[reviewer interpretation](experiments/latest/interpretation.md).

## Setup and offline checks

Use Python 3.11 with the verified dependency pins; Etiq is installed separately.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e . --no-deps
.venv\Scripts\python.exe -m pytest -q
```

The self-contained offline contracts check runtime boundaries, native replies,
accounting and compatible routing without inference. The full historical/private
test archive remains local. Exact 63-file executed controller source is recorded
in [publication provenance](resources/publication-sanitization.json). One legacy
unit fixture uses an authored minimal manifest; production assertions/gates and
all 63 executed source bytes remain unchanged.

Full original sealed replay and historical campaign re-launch require private
evidence, account/runtime bindings and authority records retained locally. Public
protocol/result records are reduced or redacted derivatives and do not issue live
launch authority. Old captures, previous experiment outputs, private signing keys,
raw replay bundles, agent handoffs and Laya code/results are excluded. The eight
selected root project documents remain as project/planning history.

The wrapper has a public upstream at
[ETIQ-AI/etiq-demo-scripts](https://github.com/ETIQ-AI/etiq-demo-scripts).
Source attribution and licence records remain included; no new licence grant is
invented. No new model call or qualification is part of publication preparation.
