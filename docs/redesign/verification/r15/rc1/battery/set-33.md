# batch-9/W1-agent-runtime (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 5 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-046 | live `vy.py invoke copilot 'Research NVDA briefly.' --provider ollama --model llama3.1:8b` | `tool_call_id: call_80dc50e027bd43f5a27a4b0169e43dee` (minted, unique — not `''`); auto-brief id `call_80dc50e027bd43f5a27a4b0169e43dee__autobrief` (suffix-derived, unique per run) | holds |
| R15-CODE-AGENT-008 | same run | the `research` tool_use auto-published a `publish_brief` call (`__autobrief` suffix) carrying `execution: {run_id, requested_depth: "normal", loop: "fast", backend, started_at, finished_at, degraded_reason, ...}` — the decoded-payload auto-brief shape the entry certifies (vy.py's own console print truncates the full JSON at ~420 chars, a client-side display limit, not a sidecar defect) | holds |
| R15-RESEARCH-027 | same run | engine ran the query, one leg ("filings") hit `"filings timed out after 6s — dropped"` at exactly 6000ms and the run still completed reporting `"pulled 3/4 data sources"` rather than hanging or failing whole — same time-boxing mechanism the cert observed on the news leg (a fresh leg, same 6s gate) | holds |
| R15-CODE-AGENT-005 | `POST /llm/chat` to `openrouter` with a fake `api_key` and unknown `options: {depth, brandNewComposerControl}` | `{"kind":"error","message":"The OpenRouter API key was rejected — check it in Settings.",...,"code":"auth"}` — a clean 401 auth frame, no `TypeError` from the unknown adapter kwargs (`scrub_adapter_options` strips them) | holds |
| R15-LIFECYCLE-025 | `POST /custom-agents` then `PUT /custom-agents/custom:zz-macro-hawk` with `tools:["price_data","macro","news"]`; in-process `schemas.openai_tools(['price_data','macro','news'])` | POST 201 and PUT 200 both resolve `tools` to `["price_data","macro_series","news"]`; `openai_tools()` gives the same resolved list — exact match to cert | holds |

Excluded (not certified in batch-9): R15-AGENT-049 (no live native-search lane reachable —
same as cert, no OpenAI/OpenRouter/Gemini/Anthropic key funded on this shard), R15-AGENT-082
(W1 sidecar leg — not certified in batch-9, superseded by batch-10's certified fix, see
set-42).

Raw output: `battery/raw/set-33/*`.
