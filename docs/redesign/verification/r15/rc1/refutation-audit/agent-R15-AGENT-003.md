# R15-AGENT-003 refutation audit (group agent)

HEAD: `git rev-parse --short=8 HEAD` -> `6741387b` (branch 004-r4-experience-rebuild). Read-only audit; scratch under `$SCRATCH/refaudit-agent/`.

## Entry and certification
- Entry: at the 6-round tool cap the capped round's tool_use is yielded to the UI (AUTO may apply it) but never dispatched; the turn ends with no text. Repro: scripted provider, one tool_use per round -> 7 rounds, 7 yielded, 6 dispatched, 0 text.
- Certified in stage-c/batch-3/VERDICTS.md:60 (7 rounds, 6 yielded, 6 dispatched, closing text; capped-round portfolio_delete_position under AUTO never yielded).

## Verifier refutation (rc1-verifier:4, evidence agent003-rerun.txt)
A different trigger: a Delegate **budget halt** (`on_round_usage` returns False from round 2, 3 tool calls per round) -> 6 yielded, 3 dispatched. Its own cap test in the same file PASSED ("multi yielded 18 dispatched 18"). The halt path (`HALT_NOTICE_TOOL`, `_consume_round` agent_runtime.py:2036-2046) was added by the R15-AGENT-037 fix in batch 7 (e81c9e7), after this entry was fixed in batch 3.

## 1. Entry's own repro at HEAD
Command: `cd sidecar && VYSTED_DATA_DIR=$SCRATCH/refaudit-agent/data .venv/bin/python $SCRATCH/refaudit-agent/agent003.py`
(scripted provider patched at `agent_runtime.get_provider`, `_dispatch_tool_with_progress` replaced by a recorder; no network)
```
ENTRY REPRO (6-round cap, one price_data per round, autonomy None):
  provider rounds=7 yielded=6 dispatched=6 undispatched_announced=[]
  text frames=1 last_text='I stopped after 6 tool rounds without reaching a final answer. Ask me to continue, or narr' last_event=LLMDoneEvent notices=[]
ENTRY REPRO variant (autonomy auto, write_note every round):
  provider rounds=7 yielded=0 dispatched=6 undispatched_announced=[]
  text frames=1 last_text='I stopped after 6 tool rounds without reaching a final answer. Ask me to continue, or narr' last_event=LLMDoneEvent notices=[]
VERIFIER REPRO (budget halt: 3 calls/round, on_round_usage False from round 2, mode delegate):
  provider rounds=2 yielded=4 dispatched=3 undispatched_announced=[('call_75120c021f254eba9e32b71b3e9ad18f', 'price_data'), ('call_1e587d10e9ad42bc8f773407e48cced6', 'fundamentals')]
  text frames=0 last_text=None last_event=LLMDoneEvent notices=[('run_halt', 'Stopped before running 3 tool call(s).')]
```
(The "variant" leg sends write_note with args that fail its schema, so it is withheld as invalid-args and dispatched for the {ok:false} result - still yielded 0 == 0 host actions announced. Leg 1 is the entry's exact repro.)

Existing regression tests at HEAD:
`cd sidecar && .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_b3_runtime_capped_round.py tests/test_runtime_phases.py -k "cap or halt"`
```
......                                                                   [100%]
6 passed, 5 deselected in 0.07s
```
Result: the entry's defect does NOT reproduce. 7 provider rounds, 6 yielded == 6 dispatched, the turn ends with the honest close text. Fix holds (agent_runtime.py:1954 `_open_round` capped flag, :1988-1989 capped tool_use dropped before yield, :2076-2078 `_finish_turn` close text).

## 2. Verifier's refutation at HEAD
Same script, third leg (3 calls/round, on_round_usage False from round 2, mode delegate): output above -> provider rounds 2, 4 tool_use yielded, 3 dispatched; round 2's price_data + fundamentals yielded but never dispatched; notice `run_halt` "Stopped before running 3 tool call(s)". (Round 2's write_note had schema-invalid args in my script so it was withheld.)

End-to-end through run_manager with a valid host action (`$SCRATCH/refaudit-agent/agent003_rm.py`: provider emits a valid write_note + done(100k tokens), RunBudget(max_tokens=1000)):
```
status error | token ceiling 1000 reached (100000 used)
provider calls 1 dispatched []
host_actions [{"tool_call_id": "call_7cbce54ccdfd437194be5a75e5ed1aa6", "name": "write_note", "input": {"scope": "TCS", "text": "sell-side view is stretched", "mode": "replace"}}]
```
The run halts before dispatching (dispatched []), yet the persisted run row carries the undispatched write_note in `host_actions`. `src/lib/delegate-runs.ts:277-281 (loop at :279)` enqueues every `host_actions` entry into the proposed-changes gate regardless of `status` (the loop is not gated on status === "done"), so the user is offered a write_note the model never saw a result for.

Code: `sidecar/services/agent_runtime.py:2016` yields each tool_use as it streams (before the round's done); the halt check at :2036-2046 comes after; `sidecar/services/run_manager.py:294-301` appends every yielded host action to `host_actions` with no retraction on `HALT_NOTICE_TOOL` (:302 only sets `halted`). Foreground chat never passes `on_round_usage` (grep: only run_manager.py:272), so this is Delegate-only.

## Classification: adjacent_finding
The entry's defect (cap round announced-but-undispatched, no closing text) is fixed at HEAD for its stated repro and the verifier's own cap test passed. The refutation exercises a different trigger (budget halt) introduced later by R15-AGENT-037's fix; it is the same defect class (announced-but-undispatched-tool) but a new, real defect that should be registered separately:

**New defect**: A Delegate run halted by a budget ceiling persists the halted round's undispatched host actions in `host_actions`, and delegate-runs.ts enqueues them as proposed changes. Root cause: run_manager.py:294-301 collects host actions from yielded tool_use events and never drops the ones from a round that `HALT_NOTICE_TOOL` says was not run (agent_runtime.py:2016 yields before the :2036 halt check). Fix shape: in run_manager, collect host actions per round and discard the pending round's on `HALT_NOTICE_TOOL` (or have `_consume_round` buffer tool_use events until the round's done when `on_round_usage` is set). Acceptance test: `sidecar/tests/test_run_manager.py::test_a_halted_rounds_host_actions_are_not_proposed` - provider emits a valid `write_note` + done(100k tokens), `RunBudget(max_tokens=1000)` -> assert `row.status == "error"`, dispatched == [], and `row.host_actions == []`.
