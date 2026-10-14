# R15 Stage C batch 10 - fresh-context verifier verdicts (Fable 5.1)

Verified against the batch-10 integration branch booted from source on 127.0.0.1:52310 (data copy of the iso stack), llama3.1:8b via ollama for agent runs, the OpenRouter free nemotron lane, NSE/screener.in/IMF/SEC as outside truth, and the vitest-executed frontend. Merge target: `worktree-agent-batch-10-int@f4ef5673` (6c5b49d3 + the DATA-054 meta fix).

Verdict: **approve** - chain green, 50 certified, 1 needs GUI, 4 not certified (none a regression), 1 concurred decision.

## Chain
- pytest 3054 passed / 1 skipped at 6c5b49d3 (prior attempt, `b10v-pytest.log`); re-run at f4ef5673 (`b10v-pytest-final.log`).
- vitest 1753 passed at 6c5b49d3; the 30 batch test files re-run 590/590.
- prettier clean; ruff format + check clean after the fix.

## Certified
- **R15-AGENT-050** - probe5: `_split_system_and_messages` emits system blocks [persona(cache_control ephemeral), date, terminal preamble] - the stable persona is the breakpoint, the changing preamble rides after it; anthropic.py:129 puts a second breakpoint on the last sent tool result (D-B10-10 immutability). test_llm_anthropic.py green.
- **R15-LEAD-018** - Live OpenRouter free lane, nvidia/nemotron-3-super-120b-a12b:free, 'is NVDA a good long-term hold? Think step by step' (b10v-vy-nemotron2.jsonl): 536 thinking events, 71 delta events, 3 tool_use; zero delta text contains 'produce final'/'the user asks'; the visible answer is one clean paragraph. Fixture tests/fixtures/llm/nemotron_cot.jsonl + test_reasoning_split.py pin the echo case.
- **R15-CODE-PLATFORM-029** - probe1 (engine from source): buy 10 every bar, 4 flat bars at 100, capital 100000 -> totalReturn -4e-05 (the four fees only), one merged lot of 40, final equity 99996. Was -3.0%.
- **R15-CODE-PLATFORM-030** - probe1: buy 10 on bar 2, sell -100 on bar 5 at a flat 100 -> totalReturn -2e-05 (fees), trades [('buy', 10.0, -2.0)]; no phantom cash. Fresh class case: buy 10@100, buy 10@120, sell 20@110, no fees -> one lot entry 110.0 (weighted average), pnl 0.0, totalReturn 0.0.
- **R15-LIFECYCLE-015** - probe6: three puts -> list_runs() newest first (ids reversed == True); three JSON files under <data>/backtests/; after reset_for_tests() (restart) list still newest-first and get(oldest) is not None. D-B10-9.
- **R15-UI-010** - Running sidecar POST /backtest/run mean_reversion params {window:0} -> 422 '`window` must be between 5 and 200'; {window:-5} same; {window:''} -> 422 '`window` must be an integer'; {window:1000000} -> 422 bound. GET /backtest/strategies advertises minimum/maximum. vitest: BacktestPanel 'clamps an out-of-range entry to the bound and a cleared one to the default on blur'; store 'shows the sidecar's 422 detail naming the bad param'.
- **R15-UI-011** - vitest BacktestPanel.test.tsx: 'swaps Run for Stop while a backtest is streaming' and 'Stop aborts the live stream, idles the run, and Retry runs on a fresh controller' pass (b10v-vitest-batch.log, 590/590).
- **R15-CODE-AGENT-013** - probe1: internal_tool_ids 55, agent_selectable_tool_ids 55, default_grant_tool_ids 54 (catalog.py:1176 default_grant=False is live); aliases are read by resolve_tool_ids (catalog.py:1780); mcp_capabilities 31 projected from kind, no post-hoc overwrite; test_capability_catalog + test_mcp_catalog_parity green.
- **R15-RESEARCH-030** - Live tool earnings_call_transcript: KPITTECH -> NSE transcript PDF filed 2026-08-04 (call of July 29, 2026), INFY -> filed 2026-07-28; llama3.1:8b agent run (b10v-vy-concall2.log) called the tool with KPITTECH and quoted the CEO on H2 growth and margins. Entry's `grep -in transcript catalog.py` now hits.
- **R15-AGENT-084** - Live llama3.1:8b run 'draw a support line at 1,450 on the RELIANCE chart' (b10v-vy-draw.jsonl): tool_use add_chart_drawing {kind: horizontal-line, points:[{price:1450}]} -> research_step 'Staged for your review, not applied yet' (proposed-changes gate). host-actions.test.ts + hand-action-inventory.test.ts pass.
- **R15-CODE-PLATFORM-021** - Running sidecar: POST /portfolio/positions 405, PUT/DELETE /portfolio/positions/AAPL 404, GET /portfolio/positions 200 [] - the sidecar ledger write routes are gone; the frontend store is the one truth.
- **R15-DATA-048** - GET /fundamentals/RELIANCE.NS carries roce 0.0899 (field_meta: provider derived, basis_note 'annual EBIT / (total assets - current liabilities)'); CREST.NS 0.0369; AMAL.NS 0.2233 (EBIT 279.5M / (1541.8M-290.0M) - internally consistent with the served statements). ISSUE: screener.in reads 10.3% / 5.67% / 7.11% - the derivation differs from the desk convention (average capital employed, PBIT) and is unwitnessed; label or witness it.
- **R15-DATA-054** - GET /fundamentals/RELIANCE.NS basis 'consolidated', CREST.NS 'consolidated' (NSE filed-basis read, exchange_financials.filed_basis), AMAL.NS/ELCIDIN.NS null when no filing says. Defect found in the fix: field_meta.basis said status 'unavailable' / 'provider did not publish this field' beside the served value - fixed in f4ef5673 (router stamps the filings leg; two tests pin ok and no-filing).
- **R15-DATA-055** - listing_date vs NSE EQUITY_L.csv (fetched live): AMAL 2026-08-17 = 17-AUG-2026, DHOOTTRANS 2026-08-17 = 17-AUG-2026, RELIANCE 1995-11-29 = 29-NOV-1995, TCS 2004-08-25 = 25-AUG-2004; Yahoo's value is a separate first_trade_date (AMAL 2026-08-18). D-B10-7. Minor: field_meta.listing_date still names provider 'yfinance'.
- **R15-DATA-053** - GET /quotes/ICON.BO (BSE-only) -> provider bse, price 64.45, volume 1200, open/high/low 64.45, prev_close 63.06; fresh case ICONIKSPEV.BO -> volume 5967, open 33.95, high 33.95, low 32.57. Dual-listed .BO (RELIANCE.BO) is served by nse_direct by rank, as before.
- **R15-DATA-096** - GET /fundamentals/AAPL/income 2.54 s then 0.01 s (cached); /ratings 0.0 s repeat; data_cache.MAX_ROWS 20000 with test_a_set_past_the_ceiling_evicts_the_oldest_rows.
- **R15-DATA-068** - GET /earnings/AAPL/history -> as_of 2026-09-24T19:25:22Z; /fundamentals/AAPL/ratings/history, /ratings/individual, /ratings/price-target-history each carry as_of (the cache row's write time). vitest AnalystRatingsPanel as-of chip. ISSUE: the base /fundamentals/{symbol}/ratings consensus envelope still has no as_of.
- **R15-LEAD-024** - GET /macro/WEO%2FUSA.NGDP_RPCH.A?provider=imf -> 2023 2.93 is_projection false, 2024 2.79 false, 2025 2.12 true, 2026 2.32 true ... 2031 true. Fresh case WEO/IND.PCPIPCH.A: 2024 false, 2025+ true. vitest MacroChart dashed segment.
- **R15-DATA-061** - GET /macro/NOT.A.REAL.WB.ID?provider=world-bank -> 502 'The data provider returned an unexpected response.' (no upstream text); same for ecb; GET /quotes/ZZQXNOTASYM -> 404 not_found copy; GET /macro/CPIAUCSL?provider=fred keyless -> authored FRED-key copy. test_errors + test_provider_error_mapper.
- **R15-DATA-087** - GET /macro/CPIAUCSL (no provider) -> 422 'provider is required for a series id'; with provider=fred the route dispatches. D-B10-2.
- **R15-RESEARCH-025** - POST /screener/formula/validate: '(pe > 10) + 1' -> ok false 'a boolean expression can't be used in arithmetic'; 'abs(pe > 10)', 'max(pe > 10, 1)' rejected; fresh '(pe > 10) * 2 + 1' rejected at position 10; 'pe > 10 and pb < 3' ok.
- **R15-CROSS-PLATFORM-003** - hardware_fit.py now calls GlobalMemoryStatusEx via ctypes; test_detect_windows_uses_real_ram_via_ctypes / _falls_back_when_the_api_call_fails / test_detect_unknown_os_is_estimated green; a faked Windows on this Mac falls back to 8 GiB flagged estimated:true; live GET /system/hardware on the M1 Pro: 16 GiB, estimated:false.
- **R15-DATA-095** - probe4: a DB created without the last three columns (seed_updated_at, eod_updated_at, provider) gets all three on _connect(); _migrate ALTERs every column of the one _ALL_COLUMNS vocabulary.
- **R15-DOCS-016** - CURRENT_STATE.md:78-80 states 'the catalog's 19 host actions ... no order action exists, D81 - none auto-apply under ASK'; the catalog on this branch has exactly 19 host_action capabilities (add_chart_drawing included).
- **R15-DOCS-017** - CURRENT_STATE.md:358-365: sp500 '506 symbols, static snapshot dated 2026-06-04 ... R15-LEAD-013 open' (sp500.json has 506), criteria 'nested AND/OR via CriterionGroup - OR-grouping is no longer reserved'.
- **R15-DOCS-018** - CURRENT_STATE.md:92-95: provider_registry 'resolves by standard model key + preference order (not the asset-class chain); every result carries its serving provider' - matches GET /data-sources (ranked keys per provider).
- **R15-AGENT-082** - Live done frames carry spend_usd (0.0 on ollama, b10v-vy-*.jsonl); vitest streaming.test 'parses a priced model's spend_usd', 'free model's 0 is a real zero', 'unpriced yields undefined'; ChatSidebar.test 'footer shows tokens and estimated spend'.
- **R15-AGENT-088** - vitest slash-commands.test: 'a bare base with one suffixed known match resolves to the suffixed symbol', 'M&M.NS and BAJAJ-AUTO.NS resolve', 'ambiguous bare base stays raw'; ChatSidebar.tsx:731 takes the bare-ticker result without an LLM round trip.
- **R15-UI-027** - vitest keybindings.test: 'mod+p and meta+p conflict on macOS (same resolved chord)', 'shift+mod+p beside mod+p does NOT conflict', class pin shift+mod+k; keybindings.ts resolveChord collapses mod per platform.
- **R15-RESEARCH-028** - Live GET /search/searxng/status on this Mac -> state 'degraded', detail 'SearXNG is running but its search engines are blocked', reason 'brave: Suspended: too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA', container running. SettingsPanel label 'Degraded - engines blocked' (vitest).
- **R15-AGENT-063** - build_aliases: BTC/USDT -> [BTC/USDT, BTC, bitcoin], ETH -> ethereum, SOL -> solana, DOGE -> dogecoin. Live GET /news?symbols=BTC/USDT tags the Bitcoin options-expiry headline BTC/USDT positive. Fresh cases via _tag_symbols: 'Ethereum ETF inflows surge' -> ETH/USDT, 'Solana outage' -> SOL/USDT, 'Ethereal plans IPO' -> [], 'SOLID results for Solar firm' -> [].
- **R15-CODE-PLATFORM-017** - Server evaluate_code: 2^3^2=512, -2^2=-4, 2+3*4^2=50, round(2.5)=3, round(-2.5)=-3, 'a > 1 ? a ^ 2 : 0'=4 with bindings; vitest code-node-run.test (editor defers to the server, D-B10-3).
- **R15-CODE-RESEARCH-004** - git diff 6b91b8f..HEAD sidecar/services/search: 196 deletions (searxng.py -102, scrub.py); no autodetect/locale caller remains outside searxng_manager comments; search tests green.
- **R15-LEAD-026** - GET /history/ZZQXNOTASYM -> 200 bars [] reason 'unknown_symbol' provider none. Note: a suffixed unknown (QQZZFAKE.NS) still returns reason null by the documented rule (a suffix addresses a market explicitly).
- **R15-UI-048** - vitest ChartPanel.test: 'a fresh panel (no persisted view) opens on the settings chart default', 'a persisted per-panel view still wins', '"Make default" persists symbol/timeframe/indicators'; settings.ts chartDefaults slice.
- **R15-UI-024** - NotesPanel.tsx:129 registers TaskList + TaskItem; vitest NotesToolbar.test 'the Task list button toggles a task list (extension is registered)', 'Insert [[wikilink]] WRAPS a selection', 'no selection still opens the picker'.
- **R15-DOCS-004** - PRODUCT_DESIGN_DECISIONS.md opens with the SUPERSEDED (R15-DOCS-004) banner naming the two reversals and the binding sections; src/lib/design-doc-citations.test.ts fails a dead-section citation (passes). D-B10-11.
- **R15-DOCS-005** - BLUEPRINT.md:20 '20 modules shipped in 0.9 (see §4 for the ~37-module v1.0 roadmap)'; 20 src/modules/*/index.ts* register a VystedModule. D-B10-4.
- **R15-DATA-078** - BLUEPRINT.md:266 'yfinance fallback ... R15-DATA-078 - alpha_vantage was [never built]' - the non-existent fallback is no longer claimed.
- **R15-CODE-PLATFORM-024** - BLUEPRINT.md:77-81 describes exports through write_text_atomic/write_bytes_atomic, which exist in src-tauri/src/lib.rs:391/:422, with the Blob download as the non-Tauri fallback. D-B10-5.
- **R15-AGENT-053** - vitest context-provider.test: 'carries a backtest AND a news publish, each as a generic summary', 'caps a generic summary to 200 characters', 'never duplicates chart/watchlist/portfolio sources into otherPanels'.
- **R15-UI-032** - Live GET /sec/filings/search?q=Apple -> [{cik 0000320193, Apple Inc., AAPL}, Apple Hospitality REIT, ...] exact ticker first; q=Nvidia -> NVDA; q=zzqxnotacompany -> [] (no swallowed exception, no MCP round trip: reads SEC company_tickers.json).
- **R15-UI-028** - units.ts:25 rho: { value: rho / 100, unit: 'per 1%' }; vitest units.test 'reads rho per 1% rate move'.
- **R15-UI-018** - ScreenerPanel.tsx:388 and MarketplacePanel.tsx:282 wrap delete/remove in ConfirmButton; vitest MarketplacePanel 'a single click on Remove does not remove the plugin; a second click confirms it'.
- **R15-CODE-PLATFORM-072** - Live GET /data-sources -> ccxt/openbb-mcp/nse_direct/nse/bse/yfinance with served keys and rank; marketplace.ts:172-236 derives rows from that fetch; vitest 'maps the wire's snake_case fields', 'degrades to an empty map on a fetch failure - never a stale hand row'. D-B10-6.
- **R15-DATA-077** - vitest marketplace.test 'declares the three India keyless lanes with a stable id (matches the resolver)'; D-B10-6 records the vendor deferral; /data-sources lists nse_direct/nse/bse as the lanes.
- **R15-CODE-PLATFORM-012** - vitest PluginManagerPanel.test 'toggling an active plugin off persists enabled:false and detaches it'; plugin-runtime.test 'disablePlugin persists enabled:false and detaches the plugin's contributions'.
- **R15-CODE-PLATFORM-013** - vitest workspace.test 'never persists plugin:* flags, and a blob with plugin:x=false keeps an enabled plugin on'.
- **R15-CODE-PLATFORM-014** - vitest plugin-runtime.test 'loadPlugin is idempotent, while reloadPlugin re-runs initialize with fresh secrets', 'loadPlugin honours a persisted disabled config'.
- **R15-AGENT-057** - vitest plugin-agents.test 'updates an already-registered agent via PUT on a 409 so a revised spec replaces it'; plugin-agents.ts:67/:78 check status and response.ok.

## Needs GUI
- **R15-UI-084** - agent-dock store: 'maximize takes the full cockpit and restore returns the prior width' passes (vitest); whether the maximized dock actually takes the full cockpit without the 1200 px clamp and restores cleanly is a layout fact - GUI check: open the dock, maximize, confirm it spans the cockpit at 2560 wide, un-maximize, confirm the prior width returns.

## Not certified
- **R15-CODE-AGENT-009** - invoke_agent is still a 488-line function (537 on the batch base, ~400 at census); the tool-surface, native-search and planner pre-pass extractions (test_runtime_prepass.py) are real but the entry's defect - a single function owning the defect-bearing branches - still reproduces.
- **R15-UI-091** - Sidecar side is done (_suggested_indicators is timeframe/asset-aware, indicators.py parses ema:9 / vwap:week) but the chart never sees it: research/fast.py's two call sites pass no timeframe (default 1d), no frontend consumer of suggested_indicators exists, the chart catalog has only a fixed 'ema'/'vwap' key, and host-actions.ts:574 drops 'ema:9' as an unknown indicator. The entry's repro (open an intraday equity chart -> no EMA9/21; no request can yield EMA9/21 on the chart) still holds.
- **R15-DATA-071** - Left open by the writers (D-B10-8, one leg): the registry fall-through is not delivered. Observed: cold 1y BSE-only history (ICONIKSPEV.BO) served 246 bars, partial false - the ≤8-bar case did not reproduce today, but nothing certifies the flagged fall-through.
- **R15-LEAD-013** - Reverted out of batch 10 (d5370601); register status stays open, CURRENT_STATE says so.

## Concur not-a-defect / decision
- **R15-AGENT-083** - D-B10-1: the external MCP surface is read-only in 0.9 and spec.md:329 now says so; host actions stay behind the proposed-changes gate. Concur: the contradiction the entry names is resolved by the amended spec, opening the surface is an operator decision.

## Fixes applied
- R15-DATA-054 - f4ef5673: the route set `basis` from the exchange filings but the yfinance provider's field_meta entry still read `unavailable / provider did not publish this field` beside `consolidated`; the router now stamps the filings leg (`exchange-filings`, ok/unavailable with a reason). Two tests in test_fundamentals.py pin it. ruff clean, test_fundamentals + test_fundamentals_basis 47 passed.

## Issues found outside the entries
1. ROCE values diverge from screener.in (RELIANCE 8.99% vs 10.3%, CREST 3.69% vs 5.67%, AMAL 22.3% vs 7.11%): the derivation is stated but unwitnessed; a witness/flag like the ownership and BVPS legs would keep the desk honest.
2. `GET /fundamentals/{symbol}/ratings` (the consensus summary) still carries no `as_of`; the three extended analyst routes and the earnings routes do.
3. `field_meta.listing_date.provider` says `yfinance` while the value now comes from the NSE master (same shape of mismatch as the basis fix).
4. A suffixed unknown symbol (`QQZZFAKE.NS`) returns `reason: null` on an empty series by the documented rule; the chart states nothing for it.
5. BSE scrip-code addressing (`506597.BO`, `544774.BO`) 404s; only the BSE symbol form resolves.
6. `suggested_indicators` from research/fast has no frontend consumer at all (see UI-091).
7. `POST /backtest/run` for AAPL 2025-01..03 reports 'all providers returned no data' on this iso stack (yfinance history lane) - the run-error path itself is honest; the store checks were done from source.

## Artefacts
Scratchpad `b10v-*.log/.py/.jsonl`: probe1/4/5/6/7 (engine, store, catalog, anthropic split, evaluator, migrate), http1-4 (routes), vy-concall2 / vy-draw / vy-nemotron2 (agent runs), vitest-batch, pytest-basis, pytest-final.
