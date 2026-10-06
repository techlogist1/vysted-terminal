# rc1-battery-9 — set-34 (batch-9/W1-agent-runtime)

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Sidecar `:52349` from source, same data dir.
Local model calls held `/tmp/vysted-r15-ollama.lock` for the duration of each run.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-046 | `vy.py invoke copilot 'Add NVDA to my watchlist.' --provider ollama --model llama3.1:8b --autonomy auto` against `:52349`. | Tool call minted `tool_call_id: "call_964596c0c9f847c6ad06e25e8eec7e27"` (not `''`); `tool_result` acked against the same id; run finished `ok`. | holds |
| R15-CODE-AGENT-005 | `POST /llm/chat` provider `openrouter`, fake key, `options:{depth:"deep","brandNewComposerControl":"x"}`. | SSE stream: one `error` frame, `"code":"auth"`, `"The OpenRouter API key was rejected..."`, `detail` shows the real 401 from OpenRouter (`Missing Authentication header`). No `TypeError`/unhandled-kwarg crash. `scrub_adapter_options` still gates `routers/llm.py:126`. | holds |
| R15-CODE-AGENT-008 | `vy.py invoke researcher 'Research NVDA briefly.' --provider ollama --model llama3.1:8b --autonomy auto`. | Auto-published `publish_brief` tool call with `structured` carrying all 5 keys (`price, fundamentals, derived, news, filings`) plus `backend`/`web_reason`/`execution` — the decode path did not silently empty anything. `sources:[]` here because this scratch sidecar has no web-search backend wired (`execution.backend:null`) — an environment gap, not the payload-decode defect the entry describes; the certified run's env had a working web lane and got 6 sources. Also saw an unrelated "brief panel did not confirm the publish" notice, expected since `vy.py` is a headless CLI with no frontend attached to ack the host action. | holds |
| R15-LIFECYCLE-025 | DB-inserted `custom:b9v-macro-hawk` row (tools `['price_data','macro','news']`, mirroring the v0.8.0-tag shape) directly into `custom_agents.db`; `GET` then `PUT` the same tools. | GET returns the raw stored list unchanged (`["price_data","macro","news"]`). PUT → **200** (not 422) with `tools:["price_data","macro_series","news"]` — `macro` resolved via `resolve_tool_ids`'s alias table, persisted resolved on GET after. | holds |

COVERAGE: 4/4 ids raw.
