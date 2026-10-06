# R15 Stage C: Batch 5 Verdicts (fresh-context verifier)

- **Target:** `worktree-agent-batch-5-int@a4c5039a1463109f9465c4b0030fd64258502349` (base `2edcae9`).
- **Verifier:** Opus, fresh context. Evidence comes from the running app and the outside world, not from the diff.
- **Rig:**
  - A scratch worktree of the target ran its own sidecar from source on `127.0.0.1:52310`, with a copy of `vysted-iso/data` as its data dir and stdin held by a sleep pipe.
  - A second target sidecar ran on `:52311` against a fresh data dir, for the boot-warm and cache-version entries.
  - A local stub on `:52399` answered 200 with SSE headers and then went silent (AGENT-025), and another stub returned HTTP 500 to MCP list calls (AGENT-059).
  - Base behaviour came from base source (`2edcae9`) run the same way, wherever an entry needed a "before".
  - The operator's ISO stack on 52152-52154 was left untouched.
- **LLM lanes:**
  - Local `llama3.1:8b` (Ollama) served every agent-side entry it could.
  - `nvidia/nemotron-3-super-120b-a12b:free` (OpenRouter free, through vy.py) served these:
    - AGENT-026: a `max_tokens` length cap.
    - AGENT-031: `publish_brief`.
    - DATA-028: llama3.1:8b passed string args to the events tool.
    - RESEARCH-014: a real length finish.
  - No OpenAI-direct spend.
  - Anthropic received only a header-only fake key (CODE-AGENT-012), and it rejected that key.
- **Frontend:** a scratch vitest file drove the real modules against the live sidecar. The file was never committed and was removed with the worktree.
- **Outside world:**
  - Live NSE feeds: announcements, corporate actions, bulk/block/SAST deals, the SHP pledge register, the event calendar, and the `index=sme` endpoints.
  - Live BSE feeds: announcements, corporate actions, deals, and the SHP XBRL, fetched through curl_cffi.
  - screener.in for ELCIDIN, CREST and the DHANBANK quarters.
  - Yahoo chart/search, SEC EDGAR through sec-edgar-mcp, and the Ollama server.
  - `api.bseindia.com` SHP index answers 403 (Akamai) to the app's httpx transport from this IP (pre-existing, same at base).

## Verdict: approve

| Result                | Count | Entries |
| --------------------- | ----- | ------- |
| Certified             | 48    | listed below |
| Not certified         | 6     | R15-LEAD-010, R15-DATA-017, R15-CODE-PLATFORM-018, R15-AGENT-052, R15-AGENT-051, R15-CODE-FRONTEND-015 |
| needs_gui             | 2     | R15-CODE-AGENT-001, R15-LIFECYCLE-008 |
| Proposed not-a-defect | 0     | none proposed (PLAN): nothing to concur with or refuse |

The chain is green at the target and 48 entries certify. No certified entry regresses its surface.

**One not-certified entry is a real regression. It should be fixed before or right after merge.**
- R15-LEAD-010 widens the unhinted `get_filing` lookup to a 1,000-row unfiltered window.
- sec-edgar-mcp cannot serve a window that size.
- The agent/MCP `sec_filing_content` tool never passes a form hint, so it now fails for filings that work at base.

Why this is not a block:
- The regression is confined to one agent tool.
- The panel path (with a hint) is fixed.
- The other 48 fixes are clear wins, and holding them back costs more.

The integrator should land the one-line follow-up below: pass `form_type` from `sec_tools.py`, and/or try a window of 100 or fewer before widening.

## Chain (re-run at a4c5039 in the scratch worktree)

| Gate | Result |
| ---- | ------ |
| `pnpm install --frozen-lockfile` | EXIT 0 |
| `pnpm lint` | EXIT 0 |
| `pnpm format:check` | EXIT 0 |
| `pnpm typecheck` | EXIT 0 |
| `ruff check sidecar` / `ruff format --check sidecar` | all checks passed / EXIT 0 |
| vitest | 125 files, 1485 tests passed, EXIT 0 |
| `cargo fmt --check` / `cargo clippy --all-targets -D warnings` / `cargo test` | EXIT 0 / EXIT 0 / all ok |
| pytest (sidecar) | 2729 passed, 1 skipped (the pre-existing live-key check), EXIT 0 |
| LEAD-001: clean-venv build of openbb-mcp + sec-edgar-mcp binaries | rc 0 both (fastmcp 3.3.1, mcp 1.27.1, httpx 0.28.1) |
| `node scripts/smoke-test-sidecars.mjs` (all three built sidecars) | all booted cleanly, EXIT 0 |

## Certified (48)

### W1: disclosures, ownership, market context

- **R15-DATA-020 (BSE/NSE announcement dedupe).**
  - HDFCBANK merged feed: 8 of 40 rows are BSE, leaving about 2 residual same-day pairs (about 15 at base).
  - The TCS HyperVault filing and the 09-17 newspaper filing each collapse to one row.
  - Fresh cases: ICICIBANK and RELIANCE leave 1-2 residual pairs each, all with mismatched categories (listed under Issues).
- **R15-DATA-023 (promoter pledge).**
  - The app's parser run on the live ADANIENT SHP XBRL gives pledge `0.79%` with basis `filed`, the same as NSE's pledge register.
  - RPOWER, DAL and CSL give `0.0` with basis `filed`.
  - End to end, with only the transport swapped to curl_cffi, the route serves ADANIENT pledge 0.79.
  - The live route itself is blocked by the pre-existing BSE httpx 403 (see Issues).
- **R15-DATA-024 (deals).**
  - KOPRAN returns bulk and SAST rows.
  - ADANIENT returns block and SAST rows.
  - CCDL returns its BSE-only bulk deal.
  - Fresh case: IGARASHI returns its deals.
- **R15-DATA-025 (corporate actions).**
  - JONJUA shows both bonuses: 7:24 (record 2026-09-04) and 5:40 (record 2026-01-23).
  - ELCIDIN's Rs 25 dividend on NSE and BSE is deduped to one row.
  - The RELIANCE dual listing is deduped.
  - Fresh case: AMAL shows Rs 1.50.
- **R15-DATA-056 (derived FII/DII leg).**
  - CREST DII is derived as 0; screener.in shows 0.00.
  - VERTEX has both legs 0 and TTC has FII 0.
  - Negative case: RELIANCE 2019 has both legs null and stays `None`, so nothing is fabricated.
- **R15-AGENT-060:** the misleading note is gone, and the tool description names FII/DII and pledge.
- **R15-AGENT-062:**
  - AAPL returns 90 of 127 bars with `window_start`.
  - RELIANCE 1mo returns 27 of 27.
- **R15-AGENT-058:**
  - Test setup: news hosts made unreachable through a dead proxy.
  - The market-context tool returns `ok:true` with `headlines_error: "news feed unavailable: all news sources failed"` and live ^NSEI/^BSESN levels.
- **R15-CODE-RESEARCH-001:**
  - An ultra budget of 360 is kept.
  - Deep defaults to 180.
  - The schema has no default and states "30-360".
- **R15-DATA-074:** the tool path now goes through `data_cache`; a row written by the router served the later tool call.
- **R15-DATA-026:**
  - DHANBANK quarterly returns ISO periods, including Q1 FY27 `2026-06-30`, and screener.in agrees.
  - Unmocked llama3.1:8b called `financial_statements` with the quarterly period and got those rows.

### W2: resolver, history, caching

- **R15-DATA-057:**
  - "Dhanalakshmi Bank" resolves to DHANBANK first; DHAN-RE is absent.
  - `is_bse_symbol('DHAN-RE')` is `False`.
- **R15-DATA-097:**
  - A real empty Yahoo search result is queried again after a 301 s time-travel, matching the 300 s TTL.
  - Non-empty results stay cached.
- **R15-LEAD-011:** ^NSEI, ^BSESN and (fresh case) ^NSEBANK each return 20 bars.
- **R15-DATA-064:**
  - 30m history returns 286 bars each for SPY, RELIANCE and TCS.
  - `in_eod_only` appears only for intraday on a known IN listing (DAL 5m).
  - Reason is `None` for DAL daily and for an unknown symbol.
- **R15-DATA-063:** `/indicators` on an empty series returns 200 with an empty payload (base: 502). Minor: there is no typed reason (Issues).
- **R15-DATA-015:**
  - ELCIDIN's 52-week high 137,000 and low 102,210 are both flagged, with a shared-window reason.
  - screener.in shows 1,44,500 / 87,003, so the flag is the honest outcome.
- **R15-DATA-037:**
  - BTC/USDT returns 30 bars for 1mo, 365 for 1y and 1826 for 5y.
  - ETH/USDT 1h over 1mo returns 720.
- **R15-LEAD-009:**
  - The earnings estimates cache keys are now region-distinct: `earnings:INFY.NS:estimates` vs `earnings:INFY:estimates`.
  - Ratings differ by region (IN buy / US hold).
- **R15-DATA-072:** with the breaker open, one successful yfinance MSFT 1h history call closes it (`open:false`).

### W3: agent runtime

- **R15-AGENT-020:**
  - llama3.1:8b called `read_notes({scope:"BDL"})` and quoted the note back.
  - vitest confirms the send carries `__notes__`.
- **R15-AGENT-040:**
  - A live multi-turn run emitted the compaction notice ("4 earliest messages folded").
  - The model still answered with the turn-1 constraint and named the tool that had failed.
  - vitest covers the marker/meter and `historyForSend`.
- **R15-AGENT-026:** nemotron with `max_tokens: 60` ends with `finish_reason: length` and a typed notice step.
- **R15-RESEARCH-014:**
  - A real OpenRouter length finish through `deep._synthesis_llm` is flagged truncated.
  - The same call without the cap is not flagged.
  - The Anthropic ceiling table was read in code; no live Anthropic key was available.
- **R15-AGENT-025:**
  - Against the silent stub, the run emits 17 heartbeats and then an error frame at 200 s (20 s planner timeout plus 180 s adapter idle).
  - Base emitted zero events in 150 s.
  - Copy nit in Issues.
- **R15-AGENT-048:**
  - Real repairs against local llama are capped at 2 of 5, and each is timed and metered into usage.
  - The other 3 get the invalid-args sentinel.
- **R15-AGENT-033:**
  - Autonomy ASK emits the notice "Staged for your review, not applied yet: set_chart_symbol BDL".
  - AUTO emits none.
- **R15-AGENT-031:** a nemotron `publish_brief` run emits the notice "The brief panel did not confirm the publish" with `step_kind: notice`.
- **R15-UI-054:** the frontend matches notices by kind; vitest is green.

### W4: workflows, platform, MCP, lifecycle

- **R15-CODE-PLATFORM-004:**
  - The condition values "false", "off", "0" and "no" route false.
  - The notify node, and the node two hops downstream, are both skipped with a node-skipped event.
  - Base ran both branches.
- **R15-CODE-PLATFORM-019:**
  - Independent node C started at 0.0 s while A finished at 4.01 s (FIRST_COMPLETED).
  - `timeout_seconds: 2` gives node-error at 2.01 s.
- **R15-CODE-PLATFORM-005:**
  - Test: an in-process race between option pricing and bond pricing on the QuantLib evaluation date.
  - Base shows 5,135 mismatches; the target shows 0.
- **R15-CODE-AGENT-012:**
  - The target's MCP invoke schema is `agent_id` and `prompt` only; base also exposed `api_key`.
  - A header-borne key reached Anthropic (which rejected it) and was not logged.
- **R15-AGENT-059:**
  - Against a server returning 500, `list_agents`, `list_workflows` and `list_runs` return `ok:false`.
  - Base returned empty lists.
- **R15-CODE-PLATFORM-020:**
  - A corrupt row and a v2 row appear under `unreadable`.
  - Loading the v2 row returns 409 with a named reason.
- **R15-LEAD-001:** clean-venv builds of both MCP sidecars exit rc 0 on the pinned stack (see Chain), and the smoke test exits 0.
- **R15-LEAD-003:**
  - A cache stamped with build 0.7.9 cleared its sentinel on boot and was re-stamped 0.8.0.
  - A boot at the same version kept the next sentinel.

### W5: screener and events

- **R15-DATA-110:**
  - A cold, throttled sp500 screen evaluates 487 of 506 names and skips 19 (3.75%).
  - Every row is a snapshot with `as_of`; the run took 35 ms.
- **R15-UI-055:**
  - The response carries `partial:true` with `evaluated: 0`.
  - The table rendered live shows "Nothing could be screened" and the throttled copy.
- **R15-UI-056:** vitest.
- **R15-CODE-DATA-004:**
  - The live store picks nifty50 for IN and sp500 for US.
  - A universe the user chose is kept.
- **R15-CODE-DATA-006:** vitest.
- **R15-LIFECYCLE-017:** pytest plus a code read.
- **R15-LIFECYCLE-020:**
  - Neither sidecar warms anything before the first request.
  - After an IN request, the warm run covers `.NS` names only.
  - Base warmed at boot.
- **R15-UI-045:** vitest, both editors.
- **R15-DATA-028:**
  - The IN events tool returns exactly NSE's 7 results events and leaves out non-results purposes.
  - A nemotron agent turn listed them.
  - llama3.1:8b could not form the args (it passed strings).
- **R15-DATA-032:**
  - Live INFY median and stddev are `null` (no fabricated value).
  - Revenue has 16 estimates and EPS has 8.
  - The grid renders "—".
- **R15-DATA-067:** `fiscal_period` is `null` on the US calendar, estimates and history rows.

## needs_gui (2)

- **R15-CODE-AGENT-001 (Origin allow-list).**
  - Sidecar side verified live on both `/health` and `/mcp/`, including preflight:
    - An evil Origin and the `null` Origin get 403.
    - `tauri://localhost`, `http(s)://tauri.localhost` and `localhost:5173` get 200 with ACAO.
    - No Origin gets 200.
  - **GUI check:** launch the packaged app (macOS and Windows) and `pnpm tauri:dev`. Confirm every panel loads and the sidecar log shows no 403 for the webview's origin.
- **R15-LIFECYCLE-008 (diagnostics).**
  - `/system/diagnostics` was verified live: version, status and a redacted `logTail`.
  - No planted canary leaked (key, public IP, query, prompt).
  - `cargo test` diag_log tests pass.
  - **GUI check:** on the packaged app, confirm `<data-dir>/logs/vysted.log` receives timestamped `[sidecar]`/`[vysted]`/MCP lines and rotates. Confirm Settings "Copy diagnostics" previews and then copies.

## Not certified (6)

- **R15-LEAD-010 (REGRESSION).**
  - The panel path with a form hint works: AAPL 10-K `0000320193-25-000079` opened through the real sec store.
  - The no-hint path now asks sec-edgar-mcp for 1,000 unfiltered filings (`_WIDEST_RECENT_WINDOW`). Every limit of 200 or more times out or fails with "cannot unpack non-iterable NoneType"; limits of 40, 60 and 100 succeed.
  - `services/agent_tools/sec_tools.py:101` calls `get_filing(accession, cik_or_symbol=identifier)` without `form_type`, so every filing now goes down that path. Copilot and researcher both use this tool.
  - Fresh cases: an AAPL Form 4 (`0001140361-26-036226`) and an MSFT 10-Q (`0001193125-26-191507`) return `ok:false` on the target and `ok:true` at base.
  - `GET /sec/filings/{acc}` without `form_type`: 502 in 14 s on the target, 200 in 1 s at base.
- **R15-DATA-017 (half fixed).**
  - Fixed:
    - JNPR and DHOOTTRANS disclosures return data.
    - SUMAX quote and history come through NSE.
    - "Sumax Engineering Limited" resolves to SUMAX (yahoo `SUMAX-SM.NS`).
  - Not fixed: every NSE Emerge name's disclosures now come back 200 and empty where base returned 502.
    - `nse_provider._fetch_corporate_list` (line 595) hard-codes `index=equities`, and NSE serves SME filings only under `index=sme`.
    - Live on NSE: SUMAX has 7 announcements and 1 SHP, QUALIANCE 7, SHANTIINOR 2. The app returns 0 with no error.
    - The old 502 has become a silent false-empty.
- **R15-CODE-PLATFORM-018.**
  - The quant nodes and tools now use `asyncio.to_thread`, but QuantLib's SWIG calls hold the GIL.
  - A binomial `quant.price_option` workflow node with 20,000 steps blocked `GET /health` for 6.4 s (54 s at 60,000 steps).
  - The sync `/quant` route blocks the same way (6.4 s). Base: 9.1 s.
  - Needs a process pool.
- **R15-AGENT-052 (not delivered, per the integrator).** Publishers still key the bus by:
  - `chart-${panelId}` (ChartPanel.tsx:885)
  - `equity` (EquityOverviewPanel)
  - `backtest-panel` (BacktestResultView)
  - PanelHost, meanwhile, focuses the dockview ids.
- **R15-AGENT-051 (no live effect until AGENT-052).**
  - Chart panelIds in the live snapshot are bus keys (`chart-chart`), which never equal `focusedPanel` (`chart`).
  - A two-chart snapshot with chart-2 focused renders "Chart: SPY ... Focused panel: chart-2 ... they mean SPY", while chart-2 shows another symbol.
- **R15-CODE-FRONTEND-015 (no live effect until AGENT-052).**
  - `focusedSymbolFromBus` is now the single derivation, but it looks up the bus by dockview id, and publishers use other keys.
  - The committed test publishes under `equity-overview`; the real Equity Overview publishes `equity`.
  - Live, the badge and chips show no symbol, and the snapshot falls back to `charts[0]`.

## Issues found outside the entries

1. **BSE SHP index transport:**
   - `bse_provider._http_get` (httpx) gets 403 from Akamai on this IP, while curl_cffi Chrome impersonation gets 200.
   - As a result, FII/DII/pledge are silently absent live, and BSE-only names get 502.
   - Pre-existing (same at base). Fix: route the SHP index through `_bse_get_json`'s curl_cffi transport.
2. **NSE Emerge disclosures:** query `index=sme` for SM-series listings (DATA-017).
3. **LEAD-010 follow-up:** pass `form_type` from `sec_tools.py`, and/or try a window of 100 or fewer before widening.
4. **QuantLib:** move pricing to a process pool (PLATFORM-018).
5. **DATA-020 residual pairs:** NSE and BSE file the same event under different category names, so these pairs are not deduped:

   | NSE category | BSE category |
   | ------------ | ------------ |
   | "Outcome of Board Meeting" | "Result" |
   | "Link of Recording" | "Company Update" |
   | "Amendment to AOA/MOA" | "Company Update" |
   | "Shareholders meeting" | "AGM/EGM" |

6. **sp500 universe pack:**
   - Carries about 15 delisted names (MMC, FI, ANSS, CTLT, DAY, DFS, HES, HOLX, IPG, JNPR, K, MRO, WBA, CTRA, ...), which the screener labels `rate_limited`.
   - BXP, NVR and UDR are missing.
7. **AGENT-025 copy:** the idle-timeout error says "Could not reach OpenAI — check your network". The stream connected and then went silent, so "stopped responding" would be accurate.
8. **`/indicators` empty payload** carries no typed reason.
9. **Tool-arg repair** accepted a JSON-schema echo from the model as args.
10. **Financial statements:**
    - Quarterly statements skip a quarter (DHANBANK 2025-09-30) with no gap marker.
    - Annual period labels differ by provider (openbb ISO dates vs yfinance years).
11. **Anthropic output ceiling:** the fallback of 32,000 exceeds the Claude 3.x maxima if a user types a 3.x model id.
12. **Earnings history:** `reported_date` carries the quarter end.
13. **SHP:** CSL has a duplicate quarter row (2026-08-20).
14. **Corporate actions:** AMAL has a "Dividend 0.0" row with no dates.
15. **Model output:** nemotron's reasoning leaks into `content` on the OpenRouter free lane.

The verifier made no code changes. Scratch scripts, data dirs and the worktree were discarded.
