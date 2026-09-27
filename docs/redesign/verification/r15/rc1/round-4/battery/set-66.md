# set-66 — batch-14/W1-agent-runtime-ratio-guard-class-tool_result-stream-event (rc1-battery-4, round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Raw: `battery/raw/set-66/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-AGENT-033 | (1) Code check: `models/llm.py` `LLMToolResultEvent` (kind=`tool_result`, keyed on `tool_call_id`, `ok`, `error`), `services/agent_runtime.py` `_tool_result_event` emitted after every dispatched tool call, `scripts/agent_eval/grader.py` checking the last `tool_result` per tool name and failing the trial when `ok is False`. (2) In-process: called `grader.grade()` directly on the exact event shapes the pinned tests use (`test_a_trial_whose_tool_call_errored_fails` / `test_a_successful_retry_of_the_errored_tool_passes`). (3) Live end-to-end: `vy.py invoke copilot "What's the nearest expiry option chain for AAPL?" --provider ollama --model llama3.1:8b` against this round's own sidecar (`:52344`), under the Ollama single-lane lock | (2) `grader.grade()` on the errored-call event list returns `["option_chain errored: 422: expiry 'nearest' is not a date"]` (fails, as certified); on the successful-retry event list returns `[]` (passes). (3) Live stream (202.3s under heavy shared-lane contention from concurrent roles) carried `tool_use option_chain {"symbol":"AAPL"}` immediately followed by `tool_result option_chain ok:true error:null` — the `tool_result` frame is genuinely on the live SSE wire for this candidate, matching the batch-14 certification's "every live invoke carries a `tool_result` frame immediately after `tool_use`" | holds |

COVERAGE: 1/1 ids raw; no raw: none.
