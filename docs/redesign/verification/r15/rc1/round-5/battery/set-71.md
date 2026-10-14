# batch-25/W6-sonnet — rc1-battery-15 (gate round 5, candidate 9bc600ec)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-093 | Live in-process: `services.agent_runtime._coerce(args, cap.input_schema)` for `option_chain`, `add_chart_drawing`, `yield_curve_value` against `services.agent_tools.catalog.CAPABILITY_CATALOG`, plus the full `_normalise_tool_args(LLMToolUseEvent(...))` path (`raw/R15-AGENT-093.raw.txt`) | `option_chain max_strikes:"5.0"` → `5` (int). `add_chart_drawing` nested `points[0].price:"185.5"` → `185.5` (float), and the same when `points` itself arrives as a stringified JSON array. `yield_curve_value` nested `instruments[0].tenor:"3"`/`rate:"0.05"` → `3` (int) / `0.05` (float). `max_strikes:"ten"` and `max_strikes:"2.5"` (non-integral for a declared integer) both correctly STAY strings and fail schema validation (sentinel applied) — the coercion only accepts an exact-literal or integral-float match, never a guess. Full-path `_normalise_tool_args` on a real `LLMToolUseEvent` for `option_chain max_strikes:"5"` produces `{'max_strikes': 5}` with no invalid-args sentinel. Source: `_coerce` (agent_runtime.py:908-944) recurses into `properties`/`items` at every depth, matching the round-2 fix exactly. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
