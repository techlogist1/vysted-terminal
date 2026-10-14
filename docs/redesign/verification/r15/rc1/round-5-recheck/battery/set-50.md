# set-50 — batch-11/W2-runtime-schema (rc1-battery-22, shard 22)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-AGENT-009 | live `ast.walk` line-span count of `invoke_agent`/`_dispatch_round` in `services/agent_runtime.py` + grep census of `test_runtime_phases.py` | `invoke_agent` is 101 lines (488 pre-fix; 95 at batch-11's base — small drift from later unrelated commits); `_dispatch_round` is 193 lines; 9 direct phase tests present (`test_prepare_run_...`, `test_open_round_...`, `test_consume_round_...` x3, `test_finish_turn_...` x2, `test_finish_unterminated_...`, `test_dispatch_round_...`) | holds |

Notes: the register's own repro field for this entry is "design" (a structural
god-function defect, not a runtime repro) — the acceptance bar is line-count +
direct-unit-testability, both re-measured live above rather than read
statically. The pytest suite itself was not run (role restriction; that's the
heavy lane's job). No regression found in this set.
