# batch-9/W1-agent-runtime (set-35)

Live re-runs against the candidate sidecar on :52350 (candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad).
Ollama lane runs held the shared local-model lock for their duration.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-005 | `POST /llm/chat` (openrouter, fake api_key, `options: {depth, brandNewComposerControl}`, then a second call with a never-seen key `totallyNovelBatteryProbeKey`) | both return a clean humanized 401 auth SSE frame ("The OpenRouter API key was rejected"), never a TypeError from an unknown kwarg; router code confirms `scrub_adapter_options` (an allowlist) replaced the old 4-name denylist, with a comment citing the exact live repro this entry names | holds |
| R15-LIFECYCLE-025 | inserted a fresh `custom_agents` row (`custom:macro-hawk-b10`, tools `['price_data','macro','news']`) directly into this shard's DB copy, then `PUT /custom-agents/custom:macro-hawk-b10` with the same tools | 200 (not 422); response tools are `['price_data','macro_series','news']` — `macro` resolved, matching batch-9's evidence exactly | holds |
| R15-AGENT-046 | `vy.py invoke copilot 'What is the current price of AAPL?' --provider ollama --model llama3.1:8b` against :52350 | minted `tool_call_id: "call_4a13933e11d841c4a383cdb65e7f82e5"` on the price_data tool call/result pair — not `''` | holds |
| R15-CODE-AGENT-008 | `vy.py invoke copilot 'Research NVDA briefly.' --provider ollama --model llama3.1:8b` against :52350 | a synthetic `publish_brief` (tool_call_id `..._autobrief`) fired automatically after the research tool's ok-result, carrying `structured: {price, fundamentals, derived, news, filings}` and `execution` metadata, no markdown (fast loop) — the documented auto-publish behavior | holds |
| R15-RESEARCH-027 | same research run as above | engine wall-clock from "research:begin" to the synthesize step was ~10.5s (35.7s→46.2s in the run trace), pulling 4/4 data sources — well inside the <=15s FR-070 target and a large improvement on the pre-fix 33-38s baseline | holds |

COVERAGE: 5/5 ids raw; no raw: none.
