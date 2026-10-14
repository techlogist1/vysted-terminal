# Regression battery — set-10 (batch-4/W1-agent-runtime)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar on `:52345` (source, data
dir = fresh copy of the iso seed). Every id re-run against its own original repro (batch-4
VERDICTS.md "Per-entry evidence"), not judged from the diff.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-006 | In-process replay of `_split_system_and_contents` with 3 tool calls (signed non-ASCII bytes, unsigned, signed ASCII) through the real gemini adapter code | Round-2 `contents` carry each signature on its own `function_call` part; the unsigned call carries none | holds |
| R15-AGENT-008 | In-process `_window_tool_subset` with the real copilot catalog (55 tools) + the exact "Screen nse-all for stocks with P/E under 15..." prompt at window=16384 | Full schema ~10.4k tok collapses to a 32-tool, ~6.8k tok subset; `screener_run` is included (cued) | holds |
| R15-AGENT-009 | Live `screener_tools._screener_run` (india-all, roe>0.25) against the running sidecar, vs. `services.screener.run_screener` (HTTP shape) same request | Tool payload: no `skip_details` key, `skip_summary` counts + 5 `skip_examples`, 26,269 bytes total. HTTP-shape result: 1,494 full `skip_details` rows, 109,533 bytes | holds |
| R15-AGENT-011 | Live `POST /backtest/run` (custom DSL, RELIANCE.NS) on the running sidecar → real runId → `GET /backtest/runs/{id}`; then `_auto_open_backtest_event` on the tool's own success/failure JSON shapes | Real run resolves via GET; synthetic `open_panel {panel:backtest, run_id}` fires on success, `None` on a failed run; frontend `loadRun` (`store/backtest.ts:331`) fetches the same route and sets `activeRunId` | holds |
| R15-DATA-041 | Live `compare_symbols._compare_symbols` on the running sidecar: `[RELIANCE.NS, RENTOMOJO.NS]` (RENTOMOJO 7 bars since 2026-09-17) | `relative.best`/`worst` both `null`, note: "windows not comparable: RENTOMOJO has 7 bars since 2026-09-17" | holds |
| R15-DATA-046 | Live `GET /macro/NY.GDP.MKTP.KD.ZG?provider=world-bank` with `X-Vysted-Region: IN` vs `US` vs no header, plus a second indicator `FP.CPI.TOTL.ZG` | IN → "— IND" 2025=7.5667 (matches World Bank API); US → "— USA" 2025=2.1614; no header defaults to IN (region default is IN, per `config._DEFAULT_REGION`) — consistent, region-aware in both directions | holds |
| R15-LEAD-007 | In-process: `services.agent_tools.catalog.agent_selectable_tool_ids()` (56 ids) → `schemas.gemini_tools(...)` → `google.genai.types.GenerateContentConfig(tools=...)` | Constructs cleanly (one Tool, 56 `function_declarations`, `parameters_json_schema`); no `8 validation errors` | holds |
| R15-LEAD-008 | In-process `native_search.native_search_available("xai", None, "grok-4")` | Returns `False` (xai excluded from every native-search set) | holds |
| R15-RESEARCH-005 | In-process `deep._safe_llm` with `LLM_CALL_TIMEOUT` set to 0.2s and a fake 5s-sleeping `llm_call` | Returns `""` (degrades, does not hang/raise); `deep.SYNTHESIS_TIMEOUT_REASON == "synthesis_timeout"`; full req/resp path pinned by `test_research_synthesis_timeout.py::test_synthesis_timeout_reaches_the_execution_record` (asserts `execution.degraded_reason == SYNTHESIS_TIMEOUT_REASON`, not null) | holds |

COVERAGE (set-10): 9/9 ids raw.
