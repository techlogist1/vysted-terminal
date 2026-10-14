# R15 Stage C: Batch 4 Verdicts (fresh-context verifier)

- **Target:** `worktree-agent-batch-4-int@0d16e8fd50011a1f47df36d578eda15e543c85b4` (base `1999844`).
- **Verifier:** Opus, fresh context. Evidence comes from the running app and the outside world, not from the diff.
- **Rig:**
  - A scratch worktree of the target ran its own sidecar from source on `127.0.0.1:52310` (data dir: a copy of `vysted-iso/data`; MCP env at `:52153`/`:52154`).
  - A second target sidecar on `:52311` ran under launchd's GUI `PATH` (`/usr/bin:/bin:/usr/sbin:/sbin`, `env -i`) with its openbb-mcp endpoint on `:52399`, where I started and later killed my own openbb-mcp child.
  - A **base-code** sidecar (`1999844`, main repo source) on `:52312`, same launchd `PATH` and same `:52399` child, gave the side-by-side "before" for every lifecycle entry.
- **LLM lanes:**
  - Local `llama3.1:8b` (Ollama) served every agent-side entry except one.
  - `nvidia/nemotron-3-super-120b-a12b:free` (OpenRouter free, via vy.py) served the AGENT-011 live turn, because llama3.1:8b twice could not form `run_custom_backtest` arguments (it passed a string for `symbols`, then invented a `run_id`).
  - No OpenAI-direct spend. Gemini was reached with a fake key only (no funded key, D35); no live xAI turn (no funded key).
- **Frontend:** scratch vitest files drove the real modules against the live `:52310` sidecar with real `fetch` (`?sidecar-port=` resolution or a mocked `getSidecarBaseUrl`): palette-built workflows, the screener preset, the Agent Builder, the Portfolio panel, `open_panel(backtest)`, a real Delegate run through the poller, and the census P2 and streaming proofs. The files were never committed and were removed with the worktree.
- **Outside world:** screener.in (ELCIDIN, ABBOTINDIA, VIYASH), NSE corporate actions (ABBOTINDIA), the live BSE bhavcopy (2026-09-23), World Bank API (IND GDP growth), Yahoo RSS, live NSE/BSE announcement feeds, the Ollama server log (`/opt/homebrew/var/log/ollama.log`), and Google's Gemini endpoint (fake key). `api.bseindia.com` HighLow returned 403 (Akamai) from this IP, so the 52-week truth came from screener.in.

## Verdict: approve

| Result                | Count | Entries                                        |
| --------------------- | ----- | ---------------------------------------------- |
| Certified             | 45    | listed below                                   |
| Not certified         | 3     | R15-DATA-015, R15-DATA-020, R15-DATA-032       |
| needs_gui             | 2     | R15-UI-009, R15-UI-025                         |
| Proposed not-a-defect | 0     | none proposed (PLAN §0): nothing to concur with or refuse |

The chain is green at the target, 45 entries certify, and no certified entry regresses its surface. The three not-certified entries are partial or undelivered fixes; none makes the product worse than base. Issues found outside the entries are listed at the end, not in the diff.

## Chain (re-run at 0d16e8f in the scratch worktree)

The integrator's last full `ci-local` (b4-ci-2, EXIT 0) predates the last two commits (`0664ec4`, `0d16e8f`, 22:59), so I re-ran the gates at the target.

| Gate                                       | Result                                   |
| ------------------------------------------ | ---------------------------------------- |
| `pnpm install --frozen-lockfile`           | EXIT 0                                   |
| `eslint .` (incl. the new restricted-properties rule) | EXIT 0                        |
| `prettier --check .`                       | clean, EXIT 0                            |
| `tsc --noEmit`                             | EXIT 0                                   |
| `ruff check` / `ruff format --check` (sidecar) | all checks passed / 382 files formatted |
| vitest                                     | 125 files, 1462 tests passed, EXIT 0     |
| pytest (sidecar)                           | 2596 passed, 1 skipped (the pre-existing `OPENROUTER_LIVE_KEY` live check), EXIT 0 |
| cargo fmt / clippy / cargo test            | not re-run: the batch touches nothing under `src-tauri/`; b4-ci-2 had them green |
| Tier-1 files (CLAUDE.md, tauri.conf.json, .github, LICENSE*, types/plugin.ts, r15-fanout.js) | untouched |
| Trading re-add                             | none (no order/broker/paper symbols added) |
| Plan §3.5 greps                            | all clean; the one `"parameters"` in `schemas.py` is the OpenAI projection, and `config.get_region()` in `routers/history.py:27` is the empty-series reason, not the freshness label |
| Removed test assertions                    | each one encoded a fixed defect (xAI `search_parameters`, the agent-node sentinel, the builder allow-list filter, the old palette keys) or was replaced by a tighter assertion; none weakened |

## Per-entry evidence

### W1: agent runtime

- **R15-AGENT-008: certified.** Same prompt ("Screen nse-all for stocks with P/E under 15 and tell me the top names"), llama3.1:8b, AUTO:
  - Target `:52310`: `screener_run` was in the subset and called; the final round's usage was `input_tokens=5784`; the Ollama log has **no** `truncating input prompt` line for the run (23:26:25–23:28:06); the answer named 10 real low-P/E NSE stocks.
  - Base `:52312`: the Ollama log shows `truncating input prompt limit=16384 prompt=21737` at 23:29:52, usage `in=16384` (the whole window), and the answer was off-task ("we would need to know what questions you are trying to answer").
- **R15-AGENT-009: certified.** The real `screener_run` handler over india-all (`roe > 0.25`, real data): the tool payload is 26,256 bytes with `skip_summary {missing_field:roe: 1038, rate_limited: 90}` and 5 examples, while the same run's HTTP shape carries all 1,128 `skip_details` rows (83,837 bytes).
- **R15-AGENT-006: certified (wire shape; live Gemini 3 outstanding, no key per D35).** Fresh replay through the real runtime and the real Gemini adapter, with real `google.genai.types` parts and a fake transport: round 1 returns three calls, signed with non-UTF-8 bytes, unsigned, and signed. Round 2's `contents` carry each signature on its own `function_call` part, the unsigned one carries none, `types.Content.model_validate` accepts every replayed turn, and `provider_meta` never appears on the SSE frames. Base code replays all three without signatures.
- **R15-LEAD-007: certified.** In-process, `GenerateContentConfig(tools=gemini_tools(all 48))` constructs on the target and raises `8 validation errors` on base. Live: a copilot turn with provider `gemini` and a fake key now reaches Google and returns `400 API key not valid`; base fails client-side with the 8 validation errors. Google's acceptance of the JSON-schema declarations themselves still needs a funded key.
- **R15-LEAD-008: certified (request shape; no live xAI turn).** `native_search_available("xai", None, "grok-4")` is False and `xai` is in neither native-search set. A captured copilot request to xAI carries no `search_parameters` (the Live Search trigger that 410s) and keeps the local `web_search` tool; base sends `search_parameters` and withholds `web_search`.
- **R15-RESEARCH-005: certified.** Live runs of the real `research` tool (llama3.1:8b, IN region, "Do a deep research brief on CG Power: order book, margins, valuation vs peers"). The local-LLM call timeout was forced to 3 s so synthesis times out (Ollama log shows the calls cut at about 3 s):
  - DEEP (168 s): the engine stated `degraded_reason: synthesis_timeout`, and the record reads `execution {loop: iter, degraded_reason: "synthesis_timeout"}`.
  - ULTRA (262 s; fresh case, heavy loop): `execution {loop: heavy, degraded_reason: "synthesis_timeout"}`.
  - Neither brief carries the thin-coverage copy.
  - Base `_stamp_execution` on the same engine payloads (iter and heavy, both stating `synthesis_timeout`) writes `degraded_reason: null`; the target writes `synthesis_timeout`.
  - Limit: the 3 s cut also starved the live runs of web sources (0 counted), so "timeout with web sources present" is pinned by the committed stub test (`test_research_synthesis_timeout.py:109,123`), not live.
- **R15-DATA-041: certified.** Real providers, IN region: `compare_symbols([RELIANCE.NS, RENTOMOJO.NS])` returns `best: null, worst: null, note: "windows not comparable: RENTOMOJO.NS has 5 bars since 2026-09-17"` (RENTOMOJO listed 2026-09-17). Before, RENTOMOJO (-2.41%) would rank best over RELIANCE (-10.7%). Fresh case: with TCS added and ARCIL (listed 2026-09-17, +9.3%) as the short window, the ranking is RELIANCE best, TCS worst, and ARCIL is named in the note.
- **R15-DATA-046: certified.** Region IN, `GET /macro/NY.GDP.MKTP.KD.ZG?provider=world-bank` returns "— IND", 2025 = 7.5667; the World Bank API gives India 2025 = 7.56666179284244. Base returns "— USA", 2.1614. Fresh: `FP.CPI.TOTL.ZG` in IN is IND (2.3988); US stays USA.
- **R15-AGENT-011: certified (both halves).**
  - Live turn (nemotron free): `run_custom_backtest` succeeded and the runtime emitted a synthetic `tool_use open_panel {panel: backtest, run_id: 3e3827e3-…}` with id `auto-backtest-call-08d239fa-…`. `GET /backtest/runs/3e3827e3-…` returns the run (6 trades, 497 equity points).
  - Frontend, live: `applyHostActionAsync("open_panel", {panel: "backtest", run_id})` returned "Opened Backtest", set `activeRunId` to the run and stored it `complete` with 6 trades and 497 points; an unknown run id returns null.

### W2: workflows, backtest, feeds

- **R15-CODE-PLATFORM-002 and R15-AGENT-015: certified.** A graph built only from the palette's own specs (`BUILT_IN_NODE_SPECS` handles, `defaultConfigFor`) through `flowToSpec`, run by the store on the live sidecar: `json_path.extracted = 337.315` (was None), `logic.compare op "neq"` returns false (was "unknown op ne"), `branch.true_path` carries the value (was None), `flow.sleep` slept 1 s (was 0.0), `notify_desktop.message = "AAPL 337.315"` (was ""), run `run-complete`. Fresh: `fetch_history → compute.indicator {indicator_id: rsi}` returns RSI(14) lines. AGENT-015: the palette Invoke Agent node with a typed `prompt_template` ("Reply with exactly the word PONG and the price…") answered `"PONG $337.46"`, so the typed prompt, not `{context}`, reached the agent.
- **R15-AGENT-016 and R15-CODE-PLATFORM-003: certified.** Live runs of `fetch_quote → ai.agent_invoke → log`:
  - No creds (strategy_critic, Anthropic default): `node-error "ai.agent_invoke (strategy_critic): Something went wrong with Anthropic."` and `run-error`. It was `ok` with the sentinel.
  - Fresh: unknown agent id ends `run-error` ("unknown agent").
  - Run-request creds (`provider: ollama, model: llama3.1:8b`) reach the node: `content "PONG $337.46"`, `run-complete`.
  - A node config carrying `api_key` is rejected 422 ("node config must not carry 'api_key'").
- **R15-CODE-FRONTEND-006 and R15-CODE-PLATFORM-016: certified.** The live palette run above, driven through `useWorkflowStore.runWorkflow` (the one client `NodeEditorPanel` now calls, `NodeEditorPanel.tsx:407`; no private `consumeSse` remains), left the intent in `pendingNotifications` (`{nodeId: nt, title: b4v, message: "AAPL 337.315"}`), the slice the desktop bridge drains. The OS toast itself is only visible in a GUI; the bridge was not part of the defect.
- **R15-DATA-040: certified.** Live `POST /backtest/run` over `[AAPL, MSFT, ZZZZNOTREAL]`: warnings = "No price history loaded for ZZZZNOTREAL in 2025-01-01..2026-09-01 (provider error or empty series); metrics cover 2 of 3 symbols." Base: `warnings: null`.
- **R15-DATA-029: certified.** Live, IN session: `/earnings/INFY/estimates` resolves `INFY.NS` with INR EPS 19.58 (the census served the ADR's USD 0.205); `/earnings/RELIANCE.NS/estimates` returns real estimates (was `RELIANCE-NS`, empty). In-process lanes: `RELIANCE.NS`, `INFY → INFY.NS`, `BDL → BDL.NS` return INR earnings history. `/news?symbols=BDL` no longer surfaces Flanigan's. `532540.BO` passes through unchanged; Yahoo itself has no data for that code. See issue 1: the router cache keys are not region-aware.
- **R15-DATA-030: certified.** The router matcher on the entry's own strings: "Reliance Industries Q2 profit rises 10%" tags `RELIANCE.NS`; "TCS wins $1bn deal / Tata Consultancy Services" tags `TCS.NS` only; "Nvidia unveils a new chip / A report from a bank" does not tag `A`; the "T-bill" line tags none of T/F/C. Fresh: "State Bank of India raises lending rates" tags `SBIN`, "Bharat Dynamics bags order" tags `BDL`, "Hindustan Aeronautics wins deal" tags `HAL.NS`. Live `/news?symbols=SBIN` returns 8 SBI items and `symbols=A` returns Agilent items only. `/news?symbols=RELIANCE.NS` is `[]` today because Yahoo's own RSS for RELIANCE.NS and BDL.NS returns 0 items (checked directly) and none of 138 general items mention either company.
- **R15-DATA-032: not certified.** Not delivered (the integrator's CHANGELOG says so). Still reproduces live: `/earnings/INFY/estimates` has `eps_estimate_median == eps_estimate_mean == 19.58006` and `eps_estimate_stddev 0.2825 == (20.33 - 19.20) / 4`.

### W3: chat, runs, MCP

- **R15-CODE-FRONTEND-002: certified.** The census P2 proof re-run with the sender's abort registered (as `ChatSidebar` does): switching tabs mid-stream called the abort once, the partial came back `{content: "Partial ", pending: false, stopped: true}`, and a late delta did not land. Fresh: a stream live on a chat tab when a research space opens is stopped, the tab's conversation is parked, and on leaving the research space the tab shows its own two messages (not pending) while the research turn stays out of it.
- **R15-AGENT-013: certified.** A real Delegate run (llama3.1:8b) launched through `launchDelegateRun` from tab A; the user then opened tab B; `pollDelegateRuns` ran until `done`. The 1,722-char answer landed in tab A's archived thread (not tab B), marked brief-published, and the gate received two pending changes. The run record (`GET /runs/4cf5b9fd…`) shows `host_actions [add_to_watchlist NVDA]` and a brief for NVDA. An earlier REST-only run stored a 553-char answer untruncated. The census run was cut at exactly 500.
- **R15-AGENT-029 and R15-CODE-PLATFORM-037: certified.** Real `streaming.ts`:
  - `getSidecarBaseUrl` rejecting: `onError` once with "The data engine did not become ready in time." for both `streamAgentInvocation` and `streamChat`, and no rejection.
  - A consumer throw reaches `onError` as "consumer blew up" (not "unparseable SSE frame").
  - EOF without `done` on an agent invocation (the case not written against): `onError` once with "The stream ended before the answer finished."
  - `done` then `error`: only `done` is delivered.
- **R15-LIFECYCLE-005: certified.** Both sidecars connected to my live openbb-mcp child on `:52399` (status green on both), then I killed the child.
  - Base `:52312`: `/fundamentals/MAZDOCK` 500 after a 60.02 s stall, then KPITTECH, BEL, HAL, COCHINSHIP all 500 in 0.01 s; status stays `available: true`.
  - Target `:52311`: every one returns 200 (yfinance fallthrough) and status reads `available: false, lastError: "ProviderError: MCP server 'openbb-mcp' failed to open: ConnectError(…)"`.
  - A research turn on the target with the child dead ("Research MAZDOCK…", llama3.1:8b) ran `research` then `publish_brief` and ended with a `done` frame (118 events); no cancel-scope traceback in the log. The census stream died mid-run.
- **R15-CODE-AGENT-002: certified.** The register's own repro: a stub session raising `ClosedResourceError`, `BrokenResourceError`, `httpx.ReadError`, `EndOfStream` or a transport `CancelledError` now raises `ProviderError` with the session dropped; base re-raises each raw with the session kept. A genuine outer `task.cancel()` still propagates `CancelledError`.
- **R15-DATA-083: certified.** The register's own repro (ok call, then `isError: upstream 500`): target status flips to `available: false, lastToolCallOk: false, lastError: "…upstream 500…"` for both openbb-mcp and sec-edgar-mcp; base stays `true / null` for both.
- **R15-DATA-038: certified.** Target: ORCL's 10-K opened through the panel routes (`/sec/filings/0001193125-26-277521/sections?identifier=ORCL`) returns Business and Risk Factors (10,000 chars each, 20,000 total); base returns `{"sections": []}`. The parser also reads the entry's own AAPL 10-K payload (`…-25-000079`) as Business + Risk Factors. `/sec/insider/AAPL` returns 8 Form-4 rows with issuer "Apple Inc." and NVDA returns 24; base returns `[]`. A 10-Q's sections are `{}` upstream (only `has_financials`), a real empty. See issue 3 for the 10-K metadata window.
- **R15-DATA-039: certified.** `/sec/filings?symbol=INFY` lists 40 rows (6-K 16, 20-F 1, 3/A, F-6 …); base lists 0. Fresh: AAPL's list carries 144, 8-K/A, SD and SCHEDULE 13G/A rows.

### W4: market-data gate

- **R15-DATA-015: not certified.** The low is fixed: `/fundamentals/ELCIDIN` flags `fifty_two_week_low 102,210` with "…15% off the NSE + BSE exchange range 87,003.00-144,500.00 since 2025-09-08; kept, flagged". screener.in shows High/Low ₹1,44,500 / 87,003. The high half (raw DAT-P13-20) still reproduces: `fifty_two_week_high 137,000` is served `status: ok`, 5.2% under the exchange's 144,500, because the witness reuses research's 10% per-bound tolerance.
- **R15-DATA-016: certified.** `/fundamentals/DAL` withholds both bounds: "no trades in 52 weeks (last trade 2025-03-12); withheld" (BSE's own HighLow dates the print 12/03/2025). `/history/DAL` 1y: 0 bars (base: 251 flat 46.58 bars, 0 with volume); 5y: the 33 real traded bars ending 2023-12-07 (base: 1,238). Fresh: `^NSEI`/`^BSESN` raw Yahoo series with a zero-volume moving bar keep all 21 bars through the new filter.
- **R15-DATA-047: certified.** `/fundamentals/ABBOTINDIA`: `dividend_per_share 525` is `flagged` ("below the 656 actually paid in the trailing 12 months by 20% — the rate can omit a special dividend…") and `dividend_per_share_ttm 656`. NSE corporate actions: ex 24-Jul-2026 "Dividend Rs 525 + Special Dividend Rs 131" = 656. Base: 525 `ok`, TTM null.
- **R15-DATA-049: certified.** `/fundamentals/VIYASH` and `ICON`: `dividend_per_share_ttm 0.0` and `dividend_yield 0.0`, reason "no dividends paid (trailing 12m)" (screener.in VIYASH 0.00%); base: null / "provider did not publish". ELCIDIN: TTM 25, yield 0.0236% from "trailing-12m dividends paid (25) / price (105800)"; screener.in 0.02%.
- **R15-DATA-034: certified.** `fundamentals_from_v7` on rows with yield 1.5 and (fresh) 0.9 returns `None` with `field_meta withheld … exceeds the plausible fraction bound of 25%`; 0.03 passes. No local 2.0 bound remains.
- **R15-DATA-082: certified.** Through `provider_registry.get_quote("BTC/USDT", "crypto")` with a stubbed binance ticker: no price field raises `ProviderError` (no 0.0 quote); `last: 0, close: 0` is rejected by the now-running gate ("non-positive price 0.0"). The live `/quotes?symbols=BTC/USDT,ETH/USDT&asset_class=crypto` still serves real prices, `freshness: live`.
- **R15-LIFECYCLE-004: certified.** The census harness `parser_drift.py` section A re-run on the target against a real RELIANCE historicalOR window: renamed O/H/L/V now raise "historical row … lacks CH_OPENING_PRICE, … (payload shape changed)", and the registry falls through to `nse` with 26 real bars, 0 flat, 0 zero-volume. Census: 10/10 flat, zero-volume bars served as `nse_direct`. Fresh: the real 2026-09-23 BSE day file with `TtlTradgVol` renamed raises "bhavcopy header lacks the volume column(s)".
- **R15-DATA-035: certified.** In a temp cache: an HTML-200 answer writes no marker; a same-day 404 marker is not honoured (fresh); a marker with mtime on its own day (pre-fix poisoning) is not honoured; then a live fetch of 2026-09-23 got BSE's real 5,060-row file and it is served.
- **R15-DATA-036: certified.** Warm 1y KSE (BSE 519421) chart: 0.44 s / 0.32 s on the target vs 11.94 s / 11.91 s on base, byte-identical 254 bars. Last bar 179.15, matching BSE's bhavcopy (`ClsPric 179.15, TtlTradgVol 1163`).
- **R15-DATA-020: not certified.** Big improvement, residual still live. Real feeds, 40 rows per lane, target code: BSE rows collapsed RELIANCE 36/40, INFY 36/40, TCS 27/40, HDFCBANK 19/40 (batch 3: 23, 1, 12, 6). But HDFCBANK still has 15 BSE rows with an NSE item of the same filing within 10 minutes, and TCS has 10. Examples: BSE "Announcement under Regulation 30 (LODR)-Analyst / Investor Meet - Intimation" (18:02) vs NSE "HDFC Bank Limited has informed the Exchange about Schedule of meet" (18:09); ESG-rating intimations vs "General Updates". NSE's templated text shares under 60% of words with BSE's subject or body. The merged top 5 for HDFCBANK still holds three duplicate pairs, so research's 5-row cap still collapses to about 2–3 filings. HDFCBANK was the plan's own case not written against.
- **R15-UI-090: certified (both halves).** Live now (13:32 EDT, US open; NSE closed): target `/quotes/AAPL` under IN is `live` and `/quotes/RELIANCE.NS` under US is `eod`. Base inverts both: AAPL/IN `eod` (while the US trades) and RELIANCE.NS/US `live`, the census mislabel. Portfolio (jsdom, live sidecar): rows render "AAPL **live**" and "RELIANCE.NS **EOD Market closed**".

### W5: panels and screener

- **R15-UI-004: certified.** Portfolio panel (jsdom, live sidecar) with `/quotes` broken: "Couldn't refresh live quotes — values shown without market data." with one Retry button. Census: no banner, Retry unreachable. See issue 4 for not-found and crypto holdings.
- **R15-UI-005: certified.** Same replay: "Market value: — (no live quotes)" and the published context `{totalValue: null, totalValueNote: "no live quotes resolved"}`. Census: ₹0.00 and `totalValue: 0`. Partial (RELIANCE.NS priced + ZZZZNOTREAL): ₹12,480 with note "excludes ZZZZNOTREAL (no live quote)". An empty portfolio still publishes a real 0 (`panel-context-publishers.test.tsx`).
- **R15-UI-009: needs_gui.** jsdom shows `downloadCsv` going through `saveTextArtifact`, and `get_app_data_dir` and `write_text_atomic` are registered Tauri commands. The defect is WKWebView-only, though. **GUI check:** in the packaged macOS app, click Export CSV in Watchlist, Portfolio and (fresh) Screener. Each must show the saved path, and the file must exist under `<app data>/exports/csv/`, not silently no-op. See issue 5 for siblings still on the Blob path.
- **R15-UI-025: needs_gui.** No `window.prompt/alert/confirm` remains in `src/` and eslint bans them. The failure is WKWebView-only. **GUI check:** in the packaged app, select text in a note and click Link. An inline URL popover must appear, and applying it must set the link mark on the selection.
- **R15-UI-006: certified.** Live india-all, `0 < P/E < 40`, `sort_by pe_ratio asc`, limit 200: `result_count 200, matched_count 2613, evaluated 3843`, strictly ascending from P/E 0.03 (small caps such as SATCH.BO at ₹69 cr lead). `desc` is monotonic too. Fresh: `market_cap` sort keeps NULL caps last in both directions. See issue 11.
- **R15-UI-007: certified.** Real store + real `ScreenerPresets`, live sidecar: with a nested OR group, formula `pe < 12` and combinator "or" set, clicking "High insider holding (Yahoo)" sent exactly the preset's criteria (no group, no formula), identical to the clean-store request, and the same rows (TCS.NS, HCLTECH.NS, WIPRO.NS). The builder state reset to `advanced: false, group: null, formula: "", combinator: and`. The "or" preset is the fresh case.
- **R15-DATA-044: certified.** Live `nse-all`, `pe_ratio < 20`: 516 rows itemized `missing_field:pe_ratio`, coverage "screened 2,159 of 2,675 — 516 unavailable". Base: "screened 2,675 of 2,675 — 0 unavailable", no skips.
- **R15-DATA-093: certified.** The register's own condition (Yahoo circuit open) forced in-process on the same data: bare `RELIANCE TCS INFY HDFCBANK COCHINSHIP` → target evaluates 5/5 from the warm `.NS` rows; base: 0 evaluated, 5 `rate_limited`. Live `:52310` returns `RELIANCE.NS … COCHINSHIP.NS` INR rows; fresh: bare `KSE` canonicalises to `KSE.BO`.
- **R15-UI-003: certified.** Live: `GET /custom-agents/tool-ids` = 48 = `agent_selectable_tool_ids()`, including research, web_search and publish_brief. The real `AgentBuilderPanel` against the live sidecar, for an agent created with `[research, web_search, price_data]` and provider openrouter:
  - it rendered 48 tool toggles and showed "openrouter";
  - after a rename and Save, the PUT carried the same tools and provider, and the read-back confirms both. Census: `tools: [price_data]`, provider rewritten to anthropic.
- **R15-CODE-FRONTEND-020: certified.** The builder now renders from the live sidecar (48 toggles above). The suite pins it with mocked-response tests, including a `brand_new_tool` that the fallback array lacks, plus a pytest pinning the route to the catalog. So sidecar drift now fails a test instead of passing against the component's own constants.
- **R15-LIFECYCLE-007: certified.** The target sidecar under launchd's `PATH` (`env -i`, `/usr/bin:/bin:/usr/sbin:/sbin`) reports `docker.cli_present: true` ("docker CLI found…"). Base under the same `PATH` reports `cli_present: false`, "docker CLI not found — install Docker Desktop or OrbStack". The OrbStack daemon itself was not answering `docker info` on this Mac during the session, even from a login shell, so `daemon_running: false` is environmental and identical on both `PATH`s. The Finder launch itself is GUI; the measured sidecar behaviour under that `PATH` is what the entry names.

## Issues (outside the entries; for the register, not this diff)

1. **Earnings/ratings cache keys are not region-aware** (`routers/earnings.py`, `routers/fundamentals.py` ratings): the key is the raw symbol (`earnings:INFY:estimates`), while DATA-029 made resolution region-dependent (IN: INFY.NS; US: the ADR). A region switch within the TTL (6 h / 24 h) serves the other listing's data. A related upgrade transient: pre-fix cached empties persist until TTL (`earnings:RELIANCE.NS:history` "RELIANCE-NS" `[]`, 24 h; `sec:filing:*` empty sections, 24 h).
2. **DATA-015 residual:** a single 10% per-bound tolerance lets a 5% wrong 52-week high read `ok` when the low of the same pair is flagged. Flag the pair together when either bound diverges.
3. **SEC viewer can't open a 10-K it lists:** `get_filing` resolves metadata from the 40 most recent filings, ignoring the list's form filter, so AAPL's 10-Ks (`…-25-000079`, `…-24-000123`, listed via `form_type=10-K`) 404 "filing metadata unavailable". Heavy Form-4/144 filers push every annual report out of the window.
4. **Portfolio not-found / crypto:** `api.ts` counts every quote error as a failure, so D-B4-22's "a not-found does not raise the banner" is not implemented. In practice it can't be, because the sidecar answers an unknown symbol with **502** (`ZZZZNOTREAL`: yfinance `'PriceHistory' object has no attribute '_dividends'`), not 404. Crypto holdings can never price: `GET /quotes/BTC%2FUSDT` is a route 404, since the path param can't carry `/`. Both now show a permanent "Couldn't refresh live quotes" banner whose Retry never succeeds (before: a silent dash). That is honest but noisy; route crypto through `/quotes?symbols=`.
5. **UI-009 class siblings still on Blob + `<a download>`:** `SettingsPanel.tsx:1796-1810` (Export settings → "Exported vysted-settings.json") and `ChatSidebar.tsx:614-624` (`/export` → "Exported N messages to markdown") both report success in the webview, where the download silently no-ops. The lint rule covers `window.prompt/alert/confirm` only.
6. `_yahoo_symbol("^NSEI")` returns `^NSEI.NS` in the IN session, so index history is empty (`/history/%5ENSEI` → 0 bars, reason `in_eod_only`). The same reason also labels DAL's no-trade year, where "EOD only" is the wrong explanation.
7. `/health` keeps `"openbb-mcp": "available"` while `/openbb-mcp/status` says `available: false` (the health map is static).
8. News aliases include the bare ticker, so `RELIANCE` would also tag "Reliance Power"/"Reliance Communications" headlines to RELIANCE.NS.
9. The DATA-020 residual mechanism: NSE's templated "has informed the Exchange about <category>" text against BSE's category subject. Category-level pairing (NSE `desc` ↔ BSE `CATEGORYNAME`/`SUBCATNAME`) within the 10-minute window would close most of the HDFCBANK/TCS remainder.
10. `/quotes/DAL` 502s (yfinance quote error) and `/earnings/532540.BO` is empty (Yahoo does not know numeric `.BO` codes). Both pre-existing.
11. Screener P/E-ascending now surfaces implausible stale values first (ZSOUTGAS.BO P/E 0.029, SATCH.BO 0.058, rows on a snapshot basis). This is pre-existing data, newly visible at the top of the sort.

## Scratch rig teardown

Sidecars `:52310`, `:52311` and `:52312` and my openbb-mcp child `:52399` were stopped by killing their `sleep` pids. The scratch worktree `batch-4-verify` (with the scratch vitest files) was removed; the data copies stay in the scratchpad only.
