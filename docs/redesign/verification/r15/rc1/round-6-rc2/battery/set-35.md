# Battery shard 1 (batch-9/W1-agent-runtime) at ace7dd76 [set-35]

 | id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-046 | live vy.py invoke copilot 'Research NVDA briefly.' ollama | tool ids call_9bec189a...(research) and call_9bec189a...__autobrief (publish_brief); no empty ids | holds |
| R15-CODE-AGENT-008 | in-process _auto_publish_event + live research auto-brief | input == tool brief verbatim (2 sources kept, unknown field kept); live auto brief carries structured keys price/fundamentals/derived/news/filings/source_floor, note/web_reason. Live sources [] because keyless web leg timed out (upstream, adjacent) | holds |
| R15-RESEARCH-027 | live research steps with latency_ms | 'filings timed out after 6s - dropped' 6002 ms, 'pulled 3/4 data sources' 6020 ms; engine ~10 s (started->finished 9.9 s) | holds |
| R15-CODE-AGENT-005 | live POST /llm/chat openrouter fake key options {depth, brandNewComposerControl} | auth 401 error frame, no TypeError from unknown kwarg | holds |
| R15-LIFECYCLE-025 | live: sqlite-insert v0.8.0-era agent tools [price_data,macro,news]; GET; PUT; openai_tools | GET shows stored tools, PUT same tools 200 with macro->macro_series; schemas gives price_data, macro_series, news | holds |

COVERAGE: 5/5 ids raw; no raw: none
