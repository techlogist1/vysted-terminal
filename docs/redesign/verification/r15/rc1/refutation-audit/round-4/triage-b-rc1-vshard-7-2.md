# triage-b — rc1-vshard-7:2 (tie R15-AGENT-092)

Audited 07:18 IST at HEAD bed3b166. Code tree equals 01015033: `git diff --name-only 01015033 HEAD -- sidecar src src-tauri types plugins scripts package.json pnpm-lock.yaml` printed nothing. The only non-docs path in `git diff --name-only 01015033 HEAD | grep -v '^docs/'` is `CHANGELOG.md`, from the lead's docs commit d76a61be. No code changed.

## Claim (shard 7)
A Delegate round halted by a budget ceiling still delivers its undispatched `publish_brief` as a proposed change.

## Code at HEAD
`sidecar/services/run_manager.py:181-184`: the R15-AGENT-092 fix adds an `undispatched` buffer. Host actions wait there until `_on_tool_result` (:203-206) moves them into `host_actions` on dispatch.

`sidecar/services/run_manager.py:299-306`:
```python
                    if name == "publish_brief":
                        brief = dict(event.input)
                    elif name in HOST_ACTION_TOOLS:
                        undispatched[event.tool_call_id] = {
```
`publish_brief` IS a host action. `python -c "from services.agent_tools.schemas import HOST_ACTION_TOOLS; print('publish_brief' in HOST_ACTION_TOOLS)"` printed `True`, and the catalog entry is `kind="host_action"`. The `if` branch runs first, so the brief is stored when the `tool_use` event arrives and never passes through the `undispatched` buffer. `agent_runtime._consume_round` (agent_runtime.py:2912-2915) yields the `tool_use` before the round's terminator. The halt check comes after it (:2928-2946) and returns without dispatching.

`src/lib/delegate-runs.ts:282-289`: `deliverRunOutput` runs for status `done` or `error` and enqueues `output.brief` as a `publish_brief` proposed change, whatever the status. `types/proposed-change.ts:31,38-42`: `publish_brief` has kind `panel`, which is in `AUTO_APPLIED_KINDS`. So in AUTO it is applied without review.

## Repro at HEAD (in-process, the repo's own test fixtures)
Script: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/a092/test_a092_brief.py`. It imports `_isolated`, `_patch` and `_await_terminal` from `sidecar/tests/test_run_manager.py`. A two-round provider sends round 1 with 10 tokens and round 2 with 100k tokens. `RunBudget(max_tokens=1000)` is set and `_dispatch_tool` is recorded.

Command: `cd sidecar && ./.venv/bin/python -m pytest /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/a092/test_a092_brief.py -q -s -p no:cacheprovider --rootdir=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-b/a092`

Output:
```

CASE1 STATUS error | token ceiling 1000 reached (100010 used) | DISPATCHED [('write_note', 'A')] | HOST_ACTIONS [('write_note', {'scope': 'NVDA', 'text': 'A'})] | BRIEF {'symbol': 'MSFT', 'title': 'halted brief', 'markdown': 'x'}
.
CASE2 STATUS error | DISPATCHED [('publish_brief', 'dispatched brief')] | BRIEF {'symbol': 'MSFT', 'title': 'halted brief', 'markdown': 'b'}
.
CONTROL STATUS done | DISPATCHED [('write_note', 'A'), ('publish_brief', 'ok brief'), ('publish_brief', 'ok brief'), ('publish_brief', 'ok brief'), ('publish_brief', 'ok brief'), ('publish_brief', 'ok brief')] | BRIEF {'symbol': 'MSFT', 'title': 'ok brief', 'markdown': 'x'}
.
3 passed in 2.05s
```

- CASE1 is the shard's repro. The run halted with `error`. Only round 1's `write_note` was dispatched, and `host_actions` correctly holds only that note, so the AGENT-092 fix works for the other host actions. Yet `row.brief` is the halted round's undispatched brief.
- CASE2 is new and worse. Round 1's `publish_brief` ("dispatched brief") was dispatched. Round 2's halted `publish_brief` ("halted brief") overwrote it. The run delivers the brief the model never got a result for and loses the one that was actually published.
- The CONTROL run, with no halt, dispatches the brief and stores it. That is correct.

## Duplicate search
A register scan for 'halt'+'brief' and 'undispatched' found only R15-AGENT-003 (the tool-cap trigger, foreground) and R15-AGENT-092 itself. No entry covers the brief field on a Delegate budget halt.

## Classification: partial on R15-AGENT-092
AGENT-092's defect_class is `announced-but-undispatched-tool`, and its title says "undispatched host_actions". `publish_brief` is in `HOST_ACTION_TOOLS`. The fix_shape also names the general mechanism: "have _consume_round buffer tool_use events until the round's done". The entry's own repro (a `write_note`) no longer reproduces. The same class still reproduces on the one host action that the `if name == "publish_brief"` branch routes around the new buffer. That is a stated part of the tie's class, so the tie is reopened.

## Severity: medium
I kept the shard's medium and did not inherit AGENT-092's high. The leaked payload is the model's own brief, not a data write. In review mode it is staged, and the user can reject it. In AUTO it auto-applies as `panel` kind, and in CASE2 it replaces the brief that really was dispatched. That degrades a stated guarantee (a halt stops before dispatch), but no data is written.

## Certification failures
Baseline for R15-AGENT-092 is 0. Its note has no 'certification failures so far' clause. `batch-12/VERDICTS.json` has it under `certified`, not `not_certified`. Neither REFUTATION_AUDIT.json has a regression_confirmed or partial verdict for it. This partial adds 1, for a total of 1.
