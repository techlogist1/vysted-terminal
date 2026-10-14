# Set: batch-11/W2-runtime-schema (set-49) — rc1-battery-17, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-009 | design entry: AST measure of sidecar/services/agent_runtime.py + presence of the pinned phase tests (no suite run) | invoke_agent is 101 lines (488 at base; 95 at batch-11 certification), phases split into helpers; sidecar/tests/test_runtime_phases.py holds 9 direct phase tests (prepare_run, open_round, consume_round x3, finish_turn x2, finish_unterminated, dispatch_round) | holds (phase tests ci_pinned in the heavy lane) |

COVERAGE: 1/1 ids raw; no raw: none
