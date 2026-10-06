# batch-18/W1-opus (rc1-battery-7, set-65)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, sidecar/.venv in-process.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-033 | In-process: `_without_step_trailers()` + `_history_tools()` on the register's AAPL turn-1/turn-2 history | `[tool steps: Using fundamentals]` is stripped from the assistant turn before it reaches the model; the tool name surfaces instead via `_EARLIER_TOOLS_NOTE` | holds |

COVERAGE: 1/1 ids raw; no raw: none.
