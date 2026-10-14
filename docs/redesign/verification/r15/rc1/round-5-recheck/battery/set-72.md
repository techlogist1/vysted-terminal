# batch-25/W6-sonnet — rc1-battery-11 (shard 11)

Candidate sha `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Method: in-process
Python call against `sidecar/.venv` on the candidate worktree, importing
`services.agent_runtime` and `models.llm.LLMToolUseEvent` directly and
exercising `_normalise_tool_args` with the scenarios the register entry (and
its round-2 correction note) names — a live function call, not a pytest run.
Raw output: `battery/raw/set-72/R15-AGENT-093.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-093 | `_normalise_tool_args` over: (1) a numeric string nested inside an array-of-objects param, (2) the whole array sent as a stringified JSON string, (3) an integral-float string (`"5.0"`) for a declared integer param, (4) negative control — a genuinely non-numeric string (`"ten"`) | all three coercible cases resolve to the correctly-typed value with no `__vysted_invalid_args__` sentinel; the non-numeric negative control still correctly fails validation | holds |

COVERAGE: 1/1 ids raw; no raw: none.
