# Set batch-4/W1-agent-runtime (set-10)

Candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd, sidecar :52348 (own data dir), in-process python with the candidate venv. Raw: battery/raw/set-10/<id>.txt

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-008 | in-process get_agent('copilot') + `_window_tool_subset` at the 16384 Ollama window (measurement repro) | 55 tools / 41,643 schema chars full; screener prompt -> 32 tools (27,163 chars, screener_run kept), 'hello' -> 29; est 8.4k / 7.2k tokens vs 16k window (my stand-in system msg is 6.5k chars, real prompt larger; not a live Ollama truncation run) | holds |
| R15-AGENT-009 | real `_screener_run` over india-all roe>0.25 | tool payload 787 B, no skip_details, skip_summary {missing_field:roe 5515, timeout 12, no_data 234, not_found 129}, 5 examples; HTTP-shape run still carries 5,890 ledger rows (311 KB) | holds |
| R15-AGENT-006 | real `_split_system_and_contents` replay of 3 calls (signed, unsigned, signed) + types.Content.model_validate | each signature on its own function_call part, unsigned has none, all Content turns validate, provider_meta absent from SSE dump | holds |
| R15-LEAD-007 | in-process `GenerateContentConfig(tools=gemini_tools(copilot's 55 ids))` | constructs, no validation errors | holds |
| R15-LEAD-008 | xai provider stream_chat web_search=True against a MockTransport; native_search_available | available=False; request keys messages/model/stream/stream_options/tools; no search_parameters; local web_search tool kept | holds |
| R15-RESEARCH-005 | real `_research(depth=deep)` on ollama llama3.1:8b (lock held), local-LLM cap forced to 3 s so synthesis times out | execution loop=iter degraded_reason=synthesis_timeout, note states the timeout, no thin-coverage copy, no raw floats (0 web sources counted under the 3 s cap, same limit as the batch verifier; pinned by test_research_synthesis_timeout.py) | holds |
| R15-DATA-041 | synthetic ESTABLISHED/NEWLY_LISTED `_rank` + live compare_symbols RELIANCE/RENTOMOJO/TCS | synthetic: best/worst null, "NEWLY_LISTED has 2 bars since 2026-10-01"; live: RENTOMOJO (11 bars) named and excluded, TCS best, RELIANCE worst | holds |
| R15-DATA-046 | GET /macro/NY.GDP.MKTP.KD.ZG?provider=world-bank, X-Vysted-Region IN vs US | IN: "— IND" 2025=7.56666 (matches api.worldbank.org IND); FP.CPI IN is IND; US control stays USA | holds |
| R15-AGENT-011 | grep backtest/runs in src/types/plugins + real run_custom_backtest(SPY) -> `_auto_open_backtest_event` | frontend caller src/store/backtest.ts:313 now exists; run ok, synthetic open_panel{panel:backtest,run_id} emitted, failed run -> None (frontend apply half pinned by host-actions.test.ts:1641, not run) | holds |

COVERAGE: 9/9 ids raw; no raw: none
