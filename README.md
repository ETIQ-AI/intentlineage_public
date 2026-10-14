# IntentLineage — latest completed experiment

This snapshot contains the completed **14 October 2026 single-review experiment**:
six cases, five arms, 30 scheduled outcomes and **172 fresh charged campaign calls**.
There were zero separate qualification calls. It replaces the previous experiment
in the current files; normal Git history and local originals remain preserved.

The reviewer used ChatGPT-authenticated Codex gpt-5.5/low. One H arm is invalid;
all six adaptive arms have incomplete semantic coverage. One dependent payment
pair and one repeat limit interpretation. Full milestone/scientific acceptance
remains pending. A requested citation-fix rerun has no completed results in this
snapshot.

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
