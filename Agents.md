# IntentLineage 

A harness that compiles intent/ontology/rules into structured elements, maps and verifies them against Etiq execution states, labels their propagation, and experimentally compares endpoint versus intermediate-state verification and different LLM context regimes on a multi-agent payment workflow. Uses the Etiq library.

**Stack:** python

## Key Documents

| File | Purpose |
| :---- | :---- |
| `Agents.md` *(this file; referred to as `AGENTS.md`)* | Project-level working agreements and entry point for AI assistants |
| `PROJECT_DESCRIPTION.md` | Description of project, this might be modified as project is developed  |
| `REFERENCE.md` | Accumulated knowledge, initial integration findings and House Patterns |
| `SKILL.md` | Verified shared Etiq wrapper commands, inspection order and capture limits |
| `README.md` | Project entry point, local setup commands and implementation status |
| `PLAN.md` | Serial project plan, behavioural tests and overseer acceptance gates |
| `PROJECT_GUIDE.md` | Current files, implemented capabilities and integration status |
| `requirements.txt` | Dependency manifest; add verified versions as implementation uses them |

`PROJECT_GUIDE.md` explains what exists. `REFERENCE.md` explains what bites you. When you learn something that would have saved you an hour, it goes in `REFERENCE.md`.

## Working Agreements

**Project roles** — The overseer owns briefs, acceptance and handoffs. The developer
implements tasks and performs TDD checks. The tester independently tests only at
milestone end, including reassessment of a complete revised milestone. The paper
writer receives results only at project end from the overseer. Work is serial;
store complete developer briefs in `instructions_between_agents/`. M1/M2 each
have one complete brief; user-requested M3 phases have separate M3A code and M3B
experiment briefs, while remaining one milestone.
User-authorized exception (8 October 2026): M2 development may overlap M1
end-of-milestone testing against reviewed commit `c7c0a5f`, in separate checkouts.
M1 acceptance is still pending; M2 acceptance requires accepted M1 and resolved
dependency findings. User-authorized M3A infrastructure coding may also start now using existing M1
and mocked M2 contracts. M3B experiments require accepted corrected M1, accepted
M2 and reviewed integrated infrastructure. Tester remains complete-milestone-end
only. See PLAN.md and the phase briefs.

**Ask for help early** — If you fail 3 times, stop and ask for help.

**Requirements file \-** Keep and constantly add a requirements file 

**Never push, never deploy** — Anything that leaves this machine is the human's to run: `git push`, opening or merging a PR, posting review comments, and every deploy command (`railway up` and anything else touching a hosted environment). Commit as freely as the work needs, then stop at that boundary and hand back, saying what you would have run. This holds even when the change is finished, obviously correct, and tested — the point is that a human chooses the moment work becomes visible to other people, and that choice is not delegated.

**User-authorized experiment execution exception (12 October 2026)** ? The separate Experiment Developer is authorized to set up and directly launch M3B provider qualification and the actual experiment, using available credentials and the reviewed implementation. No human command-launch handoff is required for this scope. Reviewed integration, actual isolation qualification, Overseer-approved frozen protocol and experimental model ceiling 5.5 remain required. This exception does not authorize pushes, PRs, review messages, deployment or publication. M3B implementation developer delivers code/qualification support; Experiment Developer owns setup, execution, analysis and evidence. Tester remains complete-M3-end; paper writer receives accepted results from Overseer only.

**Incremental progress** — Make small changes that maintain a working state, without regression.

**TDD** — Specify tests in your plans, write and commit them as failing, before implementation.

**Docs** — Review and update all appropriate Key Documents at every natural pause.

**Docs travel with the commit** — On any code commit, update the Key Documents accordingly, in the same diff. Not a follow-up, not a separate docs pass.

**Merges are a pause** — A merge lands the largest volume of unfamiliar code in one go, and it reads as *preparation* for work rather than the end of it, so the "natural pause" agreement never fires exactly when it matters most. After merging, run `git diff --stat ORIG_HEAD` and reconcile the Key Documents against what actually arrived, before building on it.

**Capture context** — After significant research or changes, ask "What do I wish I'd known at the start?" and capture the answer into a Key Document.

**Put the "why" in the commit message** — Commit bodies should start with a brief summary of *what* changed, followed by “Why:” which heads a section which carries summarised reasoning, rejected alternatives and evidence and can be much longer. This is deliberate: the rationale stays attached to the diff and cannot drift from the code. A decision that constrains future work also gets a line in `REFERENCE.md` under House Patterns, because nobody finds a commit message they don't already know to look for.

**Do not use plan mode** — Create plans for major tasks as user-visible MD files, so they can be read and challenged before any code is written.

**Do not use the memory system** — Assistant memory is per-user and invisible to everyone else. Anything worth remembering goes in a Key Document, where the whole team and their agents can see it, review it, and correct it.

**No parallel agents** — Sub-agents only for context window efficiency or specialisation. Never run in parallel.


**User-authorized automatic campaign continuation (13 October 2026)** ? After both genuine qualification calls pass, Developer/Experimenter is authorized to freeze and directly run the existing agreed M3 campaign without further Overseer review/release. Follow `instructions_between_agents/m3-auto-run-after-qualification-20261013.md`; native isolation, model ceiling 5.5, fixed bounds, real-result validation, failure stops and final complete-M3 testing/acceptance remain. Do not fabricate legacy approvals; represent this explicit user authorization honestly in machine gates.
