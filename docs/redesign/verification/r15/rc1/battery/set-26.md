# batch-7/W2-delegate-runs-runtime

Own sidecar: candidate `4c6dfe8c`, `127.0.0.1:52345` (same shard sidecar as every set in this
shard), data dir `rc1-data-rc1-battery-5`. Three entries (`AGENT-060`, `AGENT-062`, `AGENT-074`)
are `fixed`-status and re-run live end-to-end. `AGENT-064` is `blocked_tier4` (unchanged, no
route). The rest (`AGENT-066/068/070/072/076/078`, `CODE-AGENT-022`) are `open`+`low` in the
register — never certified as fixed, so there is nothing to regress; each is re-confirmed present
and unchanged (not silently fixed, not worse) via source inspection or a live/in-process probe,
per the register's own repro.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-060 | Read `disclosure_tools.py`'s `_shareholding_pattern` handler + the `shareholding_pattern` catalog description; live `GET /disclosures/shareholding?symbol=RELIANCE` (and DHANBANK/VIYASH/FUSION). | The false denial note ("promoter/public/employee-trust percentages come from the NSE master; the FII/DII split lives in each quarter's linked xbrl_url filing") is gone from the handler output entirely; the catalog description now correctly states "the FII/DII/institutions split ... source/split_source/split_as_of/split_basis state where each figure came from." The BSE-merge mechanism (`_merge_bse_split`) is unchanged/working as designed. Live calls this run had no case with an actual BSE split merged in (RELIANCE/DHANBANK/VIYASH/FUSION all `split_source: null` this run; several IN names 502'd transiently), but the fixed contract (no fabricated denial) holds regardless of whether a split is present. | holds |
| R15-AGENT-062 | In-process `services.agent_tools.price_data._price_data({"symbol":"AAPL"})` against live yfinance. | `bars_returned: 90`, `bars_available: 127`, `window_start: 2026-05-19` — the cut is now disclosed in the payload (was silent truncation with no signal). | holds |
| R15-AGENT-064 | `curl -X POST :52345/mcp/servers` (a hypothetical add-a-server route). | `404 Not Found` — still no config surface, route or UI for a user-chosen MCP server. Unchanged. | blocked_tier4 (unchanged, per DECISIONS; not a fix-round item) |
| R15-AGENT-066 | Read `catalog.py`'s `run_custom_backtest` capability declaration. | `read_only=True`, `kind="read_handler"` still declared while the tool persists a `BacktestResult` to the shared store — unchanged, still open/low. | holds (unchanged known-open) |
| R15-AGENT-068 | In-process `services.agent_tools.earnings_tools._earnings_upcoming({"days":"seven"})`. | Raises uncaught `ValueError: invalid literal for int() with base 10: 'seven'` — `days = int(args.get("days", 7) or 7)` still unguarded, escapes to the generic dispatch-catch instead of the tool's own range message. Unchanged, still open/low. | holds (unchanged known-open) |
| R15-AGENT-070 | Read `agent_runtime._tool_timeout_seconds`. | `if event.name == "research": return _research_guard_seconds(...)` still short-circuits before consulting `catalog.timeout_for("research")` — a `timeout_seconds` set on the research catalog entry is still silently ignored. Unchanged, still open/low. | holds (unchanged known-open) |
| R15-AGENT-072 | Live `GET /agents`, tools-array length per persona. | All 13 agents carry the identical 55-entry tools array (was 50 at certification time; catalog has grown, but every persona still gets the same belt regardless of its declared allow-list) — unchanged, still open/low. | holds (unchanged known-open) |
| R15-AGENT-074 | Live `POST /agents/copilot/runs` with no `provider`, `model:"llama3.1:8b"` ("What is the current price of AAPL? Use the price_data tool."), polled to completion (under the Ollama lock). | Run completed `provider: null`, `model: llama3.1:8b`, `tokens: 10730`, `spend_usd: 0.0` — priced at Ollama's $0/M rate via the resolved provider from `_on_round_usage` (comment cites R15-AGENT-074 by name in `run_manager.py`), not the $5/M unknown-provider default. | holds |
| R15-AGENT-076 | Read `services/llm/ollama.py`'s tools-stream open. | `except Exception: stream = None` (comment: "degrade gracefully, retry below") still swallows any tools-construction error with no log line before falling back to a no-tools stream. Unchanged, still open/low. | holds (unchanged known-open) |
| R15-AGENT-078 | Read `src/lib/layout-templates.ts`. | `requestAnimationFrame(run)` still wraps every layout re-tile with a synchronous return before the callback runs (4 call sites: lines 290/291, 322/323, 391/392, 599/600) — frontend-only, no backend counterpart, not re-run under vitest per the role's rules. Unchanged, still open/low. | holds (unchanged known-open) |
| R15-CODE-AGENT-022 | Live `GET :52152/mcp/status` (shared read-only main sidecar) and a real MCP `initialize` POST with `protocolVersion:"2025-11-25"`. | `/mcp/status` still reports `"protocolVersion":"2025-06-18"` while the live server negotiates and returns `"protocolVersion":"2025-11-25"` in the initialize response (`serverInfo.version 3.2.4`) — the reported/negotiated mismatch is unchanged, still open/low. | holds (unchanged known-open) |

Raw output: `raw/set-26/AGENT-060.txt`, `AGENT-062.txt`, `AGENT-064.txt`, `AGENT-066.txt`,
`AGENT-068.txt`, `AGENT-070.txt`, `AGENT-072.txt`, `AGENT-074-launch.log`,
`AGENT-074-run-final.json`, `AGENT-076.txt` (n/a — see set notes; grep captured inline above,
no separate raw file needed beyond the source excerpt already quoted), `AGENT-078.txt`,
`CODE-AGENT-022.txt`.
