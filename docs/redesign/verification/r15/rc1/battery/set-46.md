# unplanned-1

Candidate 4097dac4. Raw output: `raw/set-46/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-007 | `find sidecar -iname "*eval*" -o -iname "*golden*" -o -iname "*scenario*"` | `sidecar/tests/test_agent_eval.py` (204 lines, grades a real `scripts/agent_eval/grader.py` against `scenarios.json`, pass/fail per failure mode); `scripts/agent_eval/{run.py,grader.py,scenarios.json}` all present — a fixed scenario set + grader now exists, docstring cites R15-AGENT-007 | holds |
| R15-CODE-AGENT-009 | Read `sidecar/services/agent_runtime.py:2276-2370` (`invoke_agent`) | Function is ~94 lines, delegating to `_prepare_run`, `_plan_prepass`, `_open_round`, `_relay_provider`, `_consume_round`, `_dispatch_round` — the ~400-line monolith is decomposed into independently-testable helpers | holds |

Summary: 2 holds. No regressions.
