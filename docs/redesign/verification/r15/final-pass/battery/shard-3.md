# Final-pass regression battery - shard 3 of 4

Candidate d38b5d1a2487bd52fe8a7e741a3a5266e3206611 (final-cand worktree, read-only). Ids: register at that sha, status 'fixed', sorted, p%4==3 (148; battery/shard-3.ids). Own sidecar :52863 (data dir scratch copy), reused; restarted once by LIFECYCLE-012. Run by claude-opus-5-5 (final-battery-3), 2026-10-03.

| id | repro run | observed | verdict | raw |
|---|---|---|---|---|
| R15-AGENT-004 | in-process b4_004.py: real anthropic SDK + MockTransport tool-use SSE through AnthropicProvider.stream_chat | tool_use get_quote {symbol: RELIANCE.NS}; news {symbol: TCS.NS, limit: 5}; done tool_use (args assembled, not {}) | holds | raw/R15-AGENT-004.txt |
| R15-AGENT-008 | in-process get_agent(copilot) + _window_tool_subset at the 16384 window | 55 tools / 41,643 schema chars full; screener prompt -> 32 tools (screener_run kept), 'hello' -> 29; est 8.4k / 7.2k tokens | holds | raw/R15-AGENT-008.txt |
| R15-AGENT-012 | in-process BudgetGuard.record metered openai usage + oneshot.complete_with_usage | cost() {tokens 43000, spend_usd 0.0258, steps 1}; token ceiling trips 'token ceiling 1000 reached (2000 used)' | holds | raw/R15-AGENT-012.txt |
| R15-AGENT-016 | live POST /workflow/run ai.agent_invoke: no creds, unknown agent, api_key in node config | node-error + run-error (unknown agent: 'nope_agent'); api_key config -> 422 'node config must not carry api_key' | holds | raw/R15-AGENT-016.txt |
| R15-AGENT-022 | in-process b16_w1.py (null/0/update-without-id) + live vy.py Sumax prompt x2 on ollama llama3.1:8b (lock-held) | in-process: missing cost_basis -> ok:false 'ask the user for it; do not guess'; update w/o position_id refused; live: model printed the tool call as text twice (no tool call, no write claimed) | holds | raw/R15-AGENT-022.txt |
| R15-AGENT-026 | in-process p17.py: invoke_agent with fake provider, 4 truncation shapes | length/max_tokens -> notice 'hit the model's output limit'; no-finish -> error code truncated | holds | raw/R15-AGENT-026.txt |
| R15-AGENT-031 | in-process p17b.py: publish_brief ack none/kept_previous/failed/applied | all three divergences emitted as step_kind notice; applied -> none | holds | raw/R15-AGENT-031.txt |
| R15-AGENT-035 | live (2 lock holds): launch ollama llama3.1:8b max_tokens=1000 -> error; POST /runs/{id}/resume | row keeps provider ollama / model llama3.1:8b; tokens 6453 -> 12991, steps 1 -> 2; resume 200 | holds | raw/R15-AGENT-035.txt |
| R15-AGENT-039 | in-process inproc_plan.py (plan half) + live ollama compound delegate launch (activity half, lock-held) | planned 'plan ready: start or discard it', 0 provider calls before Start; live run done with typed activity row write_screener_filters error+summary | holds | raw/R15-AGENT-039.txt |
| R15-AGENT-043 | source + pin grep (host-actions.test.ts) | tests 'write_screener_filters says which malformed criterion it dropped' / 'save_screen ... refuses' present | ci_pinned | raw/R15-AGENT-043.txt |
| R15-AGENT-047 | in-process b16_w1.py: groq-shaped 'ten', groq/ollama truncated-JSON parsers | runtime "'ten' is not of type 'number'"; both adapters return invalid-args sentinel; empty args {} | holds | raw/R15-AGENT-047.txt |
| R15-AGENT-052 | grep bus keys + named tests | BUS_SOURCE/panelId/busSource register+unregister pairs; panel-context-publishers.test.tsx, ChartPanel.test.tsx present | ci_pinned | raw/R15-AGENT-052.txt |
| R15-AGENT-056 | grep host-actions arrange_layout default + test block | 'Reset the panel arrangement (drawings and modules kept)'; describe block R15-AGENT-056 at host-actions.test.ts:1929 | ci_pinned | raw/R15-AGENT-056.txt |
| R15-AGENT-060 | in-process inv.py shareholding_pattern CREST | no 'note' key; fii 1.71 / dii 0.0 / split_source BSE | holds | raw/R15-AGENT-060.txt |
| R15-AGENT-066 | in-process p_lows.py a66 + live MCP list_tools on :52863/mcp/ | run_custom_backtest/backtest_summary/broker_portfolio off MCP; every projected tool read_only; live 39 tools, run_custom_backtest not listed | holds | raw/R15-AGENT-066.txt |
| R15-AGENT-070 | in-process p_lows.py a70: replace(research, timeout_seconds=60) | ValueError 'timeout_from_args derives the budget...'; research 390 s from args; flagged price_data 210 s | holds | raw/R15-AGENT-070.txt |
| R15-AGENT-074 | live launch with no provider (llama3.1:8b, lock-held) + in-process inproc_runs.py buffett | spend_usd 0.0 for 1801 tokens; buffett 0.0021 == opus rate (default-rate 0.00035) | holds | raw/R15-AGENT-074.txt |
| R15-AGENT-078 | grep rAF in layout appliers + test | requestAnimationFrame count 0; layout-templates.test.ts:269 'appliers run synchronously (R15-AGENT-078)' | ci_pinned | raw/R15-AGENT-078.txt |
| R15-AGENT-082 | grep spend footer test + sidecar spend_usd | ChatSidebar.test.tsx:1140 footer tokens+spend test; streaming.test.ts:232; agent_runtime sets event.spend_usd | ci_pinned | raw/R15-AGENT-082.txt |
| R15-AGENT-089 | in-process planner.PLAN_ACTIONS / _coerce_steps / _STAGEABLE_PLAN_ACTIONS | close_panel, focus_panel in PLAN_ACTIONS and stageable; kept by _coerce_steps, bogus dropped | holds | raw/R15-AGENT-089.txt |
| R15-AGENT-094 | in-process t094.py arrange_layout custom gate | bare names, {panel,direction,reference} objects, stringified array all accepted/parsed; no TypeError | holds | raw/R15-AGENT-094.txt |
| R15-CODE-AGENT-003 | live POST /llm/keys/validate fake openrouter/gemini/xai keys | all ok:false reason invalid '<Provider> rejected this key.'; direct openrouter /key 401 | holds | raw/R15-CODE-AGENT-003.txt |
| R15-CODE-AGENT-007 | in-process ag7.py registry vs dispatch base url, then edit rows | hosts equal registry; after edit dispatch follows edited.deepseek.example/v9, edited.x.example/v2 | holds | raw/R15-CODE-AGENT-007.txt |
| R15-CODE-AGENT-011 | live ollama delegate run told to ask (lock-held) -> paused; POST /runs/{id}/answer 'MSFT please' | paused with question 'Please enter a stock ticker'; answer 200 {resumed:true} -> done, resolve_symbol MSFT ok | holds | raw/R15-CODE-AGENT-011.txt |
| R15-CODE-AGENT-015 | in-process sec_tools limits 100000,-1,0,'x',None,15 with stubbed provider | provider saw 100,1,1,20/30,20/30,15 (clamped) | holds | raw/R15-CODE-AGENT-015.txt |
| R15-CODE-AGENT-019 | live POST /llm/keys/validate unreachable base_url (openai, anthropic) | 'Could not reach OpenAI - check your network. Check your internet connection and try again.' (no SDK repr/URL) | holds | raw/R15-CODE-AGENT-019.txt |
| R15-CODE-AGENT-023 | live MCP tools/call (b4_023.py ported to :52863): raising handler, unknown tool | price_data ZZZNOTASYMBOL999 -> isError:true "tool 'price_data' raised: correctness gate..."; unknown tool isError:true | holds | raw/R15-CODE-AGENT-023.txt |
| R15-CODE-AGENT-027 | in-process register_tool extra then reset_for_tests | import-time snapshot ['backtest_summary']; extra dropped, backtest_summary kept | holds | raw/R15-CODE-AGENT-027.txt |
| R15-CODE-AGENT-031 | in-process routers.runs TestClient over real runs_store (105 rows, temp dir) + live GET /runs | GET /runs 100 rows (LIST_LIMIT 100), 0 camelCase keys in list/detail, no checkpoint_json in list | holds | raw/R15-CODE-AGENT-031.txt |
| R15-CODE-DATA-001 | live GET /resolve?q=FOCUS, /disclosures/shareholding?symbol=FOCUS (IN) | NSE Focus Lighting isin/bse_code null (BSE Focus Business keeps INE0DXR01010/543312); shareholding split_source None on all 21 patterns | holds | raw/R15-CODE-DATA-001.txt |
| R15-CODE-DATA-005 | grep witness predicates | is_applicable = witness.is_india_listing in market_cap_witness/range_check; one is_block_error (witness.py); one is_india_target | holds | raw/R15-CODE-DATA-005.txt |
| R15-CODE-DATA-009 | in-process provider_health.is_rate_limit cases + caller grep | True/True/True/True/False; dividend_history, yfinance_provider, growth_check, symbol_resolver, earnings_quality call it | holds | raw/R15-CODE-DATA-009.txt |
| R15-CODE-DATA-013 | live GET /sec/filings/{acc}/sections + openapi paths | 404; no sections path in openapi (sibling /sec/filings/{acc} 200) | holds | raw/R15-CODE-DATA-013.txt |
| R15-CODE-DATA-017 | in-process b23_set109.py autocomplete TATASTEEL + decide() | rows[0] TATASTEEL score 1.0 band 6; outcome bound | holds | raw/R15-CODE-DATA-017.txt |
| R15-CODE-DATA-022 | in-process FieldMeta(status=...) | 'unavaliable' -> ValidationError; 'ok'/'unavailable' accepted | holds | raw/R15-CODE-DATA-022.txt |
| R15-CODE-FRONTEND-003 | source + pin (rc2 used a scratch vitest probe; battery runs no vitest) | host-actions.ts:773 write_note mode defaults to 'append' unless explicit 'replace' | ci_pinned | raw/R15-CODE-FRONTEND-003.txt |
| R15-CODE-FRONTEND-007 | grep lot-binding tests + source | host-actions.test.ts:1835 'accept changes the lot the diff showed in portfolio A' + :1862; lotOrdinal(portfolioId, holding) | ci_pinned | raw/R15-CODE-FRONTEND-007.txt |
| R15-CODE-FRONTEND-011 | grep parity test | describe 'describe/apply parity over one parsed intent (R15-CODE-FRONTEND-011)' host-actions.test.ts:1661 | ci_pinned | raw/R15-CODE-FRONTEND-011.txt |
| R15-CODE-FRONTEND-016 | node strip-types kb2.mts on candidate keybindings.ts | 13 defaults resolve to own id; remap ok; mod+b vs Cmd+Shift+B false; changes.acceptAll registered in ChatSidebar:586 | holds | raw/R15-CODE-FRONTEND-016.txt |
| R15-CODE-FRONTEND-020 | grep tests + live GET /custom-agents/tool-ids | route test present; live 200 list (add_chart_drawing, ...) | ci_pinned | raw/R15-CODE-FRONTEND-020.txt |
| R15-CODE-FRONTEND-024 | ls/grep dead modules | fuzzy.ts, indicator-presets.ts + tests gone; no refs outside dead-surface.test.ts | holds | raw/R15-CODE-FRONTEND-024.txt |
| R15-CODE-FRONTEND-028 | grep tests | research-spaces.test.ts:124 + workspace.test.ts:471 R15-CODE-FRONTEND-028 | ci_pinned | raw/R15-CODE-FRONTEND-028.txt |
| R15-CODE-FRONTEND-033 | grep alias test | host-actions.test.ts:147 'arrange_layout pattern=focus resolves a panel ALIAS' | ci_pinned | raw/R15-CODE-FRONTEND-033.txt |
| R15-CODE-FRONTEND-037 | grep test + source | workspace.test.ts:454 empty watchlist round-trips; Array.isArray(workspace.watchlist) guard | ci_pinned | raw/R15-CODE-FRONTEND-037.txt |
| R15-CODE-PLATFORM-005 | live 200 concurrent POST /quant/option/price (32 threads) vs serial refs | 0 mismatches, 0 zero prices (refs 29.1490 / 18.1748) | holds | raw/R15-CODE-PLATFORM-005.txt |
| R15-CODE-PLATFORM-014 | source + pin (rc2 used a scratch vitest probe; battery runs no vitest) | plugin-runtime.test.ts:175 'loadPlugin is idempotent, while reloadPlugin re-runs initialize with fresh secrets' | ci_pinned | raw/R15-CODE-PLATFORM-014.txt |
| R15-CODE-PLATFORM-019 | live POST /workflow/run sleep 4s + independent B->C; node timeout_seconds=2 on 6s sleep | C done at 0.03s while A done 4.03s; node-error at 2.05s 'node timed out after 2s' | holds | raw/R15-CODE-PLATFORM-019.txt |
| R15-CODE-PLATFORM-023 | metrics.ts under node on INFY.NS vs ^NSEI 1y from own sidecar vs independent Python statistics | n 246; vol 0.30686, Sharpe -0.96824, Sortino -1.32422, maxDD -0.41691, beta 0.68945 match to 1e-15 | holds | raw/R15-CODE-PLATFORM-023.txt |
| R15-CODE-PLATFORM-027 | node scripts/audit-design-tokens.mjs real tree / nonexistent root / violating fixture | clean 392 files exit 0; 'refusing to report clean' exit 1; fixture 2 violations exit 1 | holds | raw/R15-CODE-PLATFORM-027.txt |
| R15-CODE-PLATFORM-034 | in-process b13_bt.py walk-forward 10 bars 3 slices | disjoint slices; max hits per bar 1, total 10 of 10 | holds | raw/R15-CODE-PLATFORM-034.txt |
| R15-CODE-PLATFORM-038 | grep error-code consumers + run_manager detail | streaming.ts provider_402/insufficient_credit/ollama_not_running; SETTINGS_FIX_CODES; run_manager.py:391 detail=humanize(...).message | holds | raw/R15-CODE-PLATFORM-038.txt |
| R15-CODE-PLATFORM-042 | read greeks.py + live POST /quant/option/greeks vs /option/price | greeks.py delegates to price_european_bs; identical price 9.46117 / delta 0.53046 | holds | raw/R15-CODE-PLATFORM-042.txt |
| R15-CODE-PLATFORM-048 | grep tests + source | plugin-runtime.test.ts:558 "'<0.9.0' is rejected as unsupported" + :613 | ci_pinned | raw/R15-CODE-PLATFORM-048.txt |
| R15-CODE-PLATFORM-052 | grep 'Patch an existing holding' | gone (exit 1); doc reads 'Replace an existing holding's fields (not a partial merge)' | holds | raw/R15-CODE-PLATFORM-052.txt |
| R15-CODE-PLATFORM-056 | grep keychain.rs dev keystore migration tests | dev_keystore mod; migrate_with_erroring_reader_leaves_unmigrated_and_retries test | ci_pinned | raw/R15-CODE-PLATFORM-056.txt |
| R15-CODE-PLATFORM-060 | grep -rni tray src-tauri + BLUEPRINT | 0 hits in Rust, 0 in BLUEPRINT.md (docs no longer promise a tray) | holds | raw/R15-CODE-PLATFORM-060.txt |
| R15-CODE-PLATFORM-065 | live POST /workflow/run dangling edge / unregistered node type | run-start + run-error "edge e1 references unknown target node 'ghost'" / "unregistered type 'example.plugin-node'" | holds | raw/R15-CODE-PLATFORM-065.txt |
| R15-CODE-PLATFORM-069 | grep test + live /workflow/node-types | 'plugin node absent from the server list is not runnable' test; live example.* count 0 | ci_pinned | raw/R15-CODE-PLATFORM-069.txt |
| R15-CODE-PLATFORM-076 | per-agent systemPrompt byte length | copilot 4382 B (was 8751); others 2581-3900 | holds | raw/R15-CODE-PLATFORM-076.txt |
| R15-CODE-RESEARCH-003 | in-process rs3.py forced loop failure per depth + grep run_deep_research | no run_deep_research; normal/deep -> iter, ultra -> heavy, honest 'could not finish' | holds | raw/R15-CODE-RESEARCH-003.txt |
| R15-CODE-RESEARCH-007 | grep four keys in semantics.py vs types/brief.ts + pinned test | all four emitted and declared in brief.ts; test_emitted_keys_subset_of_brief_ts_mirror present | holds | raw/R15-CODE-RESEARCH-007.txt |
| R15-CODE-RESEARCH-011 | in-process annotations of semantics._*_leg | all 7 legs return tuple[dict, list]; no 'for symmetry' discard | holds | raw/R15-CODE-RESEARCH-011.txt |
| R15-CROSS-PLATFORM-004 | grep layout menu labels + MENU_PAYLOAD_TO_MODE | LAYOUT_MENU_LABELS fundamental/technical/macro/compare-desk/default; command route action:layout:* | holds | raw/R15-CROSS-PLATFORM-004.txt |
| R15-CROSS-PLATFORM-009 | grep command glyph outside keybindings.ts | zero non-test hits; guard source-guards.test.ts:50 | holds | raw/R15-CROSS-PLATFORM-009.txt |
| R15-DATA-001 | live GET /fundamentals/{DAL,CHTR,SMR,SUMAX}/income, RELIANCE.NS (IN) | DAL.BO / CHTR.BO / SMR.BO March-FY INR (DAL rev 2.07 cr); SUMAX -> SUMAX-SM.NS empty; RELIANCE.NS unchanged | holds | raw/R15-DATA-001.txt |
| R15-DATA-006 | live GET /quotes/DAL (IN) + /fundamentals/DAL field_meta | timestamp 2025-03-12, change 0.0, freshness stale; price-derived field_meta as_of 2025-03-12 | holds | raw/R15-DATA-006.txt |
| R15-DATA-010 | in-process b7_bt.py _compute_metrics | sortino 6.352097860237519 == textbook 6.352097860237523; identical-loss series -2.51 | holds | raw/R15-DATA-010.txt |
| R15-DATA-014 | live GET /fundamentals/{DAL,FUSION,JONJUA} | DAL revenue_ttm 99.7M bse 'sum of 4 filed quarters', Yahoo 27.6M not served; FUSION 17,144.2M nse; JONJUA flagged TTM gap | holds | raw/R15-DATA-014.txt |
| R15-DATA-018 | live GET /resolve zomato/ZOMATO/autocomplete/SEQUENT/VIYASH | zomato, ZOMATO, autocomplete -> ETERNAL (former_name ZOMATO); SEQUENT -> VIYASH (former_name SEQUENT) | holds | raw/R15-DATA-018.txt |
| R15-DATA-022 | live GET /disclosures/shareholding?symbol=SMR | count 1, quarter_end 2026-06-04 (IPO-dated pattern kept), HTTP 200 | holds | raw/R15-DATA-022.txt |
| R15-DATA-026 | live GET /fundamentals/DHANBANK/income?period=quarterly | periods 2026-06-30 .. 2025-03-31 | holds | raw/R15-DATA-026.txt |
| R15-DATA-031 | grep EarningsCalendarPanel tests | EarningsCalendarPanel.test.tsx:224 'R15-DATA-031: labels EPS with currency...' | ci_pinned | raw/R15-DATA-031.txt |
| R15-DATA-035 | in-process b19_set13.py 035 bhavcopy marker cases + live fetch | HTML-200 no marker; own-day marker not honoured; live 2026-09-23 5060 rows | holds | raw/R15-DATA-035.txt |
| R15-DATA-039 | live GET /sec/filings?symbol=INFY and AAPL | INFY 40 rows (6-K 16, 20-F 1, F-6...); AAPL 144, 8-K/A, SD, SCHEDULE 13G rows | holds | raw/R15-DATA-039.txt |
| R15-DATA-043 | live POST /screener/run custom [AAPL,RELIANCE.NS,MSFT,TCS.NS] sort market_cap desc | coverage 'spans INR, USD - ranked within each currency'; RELIANCE, TCS (INR) then AAPL, MSFT (USD) | holds | raw/R15-DATA-043.txt |
| R15-DATA-047 | live GET /fundamentals/ABBOTINDIA | dividend_per_share 525 flagged 'below the 656 actually paid in the trailing 12 months by 20%'; dividend_per_share_ttm 656 | holds | raw/R15-DATA-047.txt |
| R15-DATA-051 | live GET /resolve SMR, CREST | SMR board SME group M fv 10; CREST mainboard B fv 10 | holds | raw/R15-DATA-051.txt |
| R15-DATA-055 | live GET /fundamentals/AMAL.NS, RELIANCE.NS | listing_date 2026-08-17 / 1995-11-29; 52w high/low dates present; forward_pe_fiscal_year key (RELIANCE 2027-03-31); per-leg as_of differ (4/5 distinct) | holds | raw/R15-DATA-055.txt |
| R15-DATA-060 | live GET /disclosures/{shareholding,announcements,results}?symbol=SIFY, AAPL; 20-F lane SIFY/WIT region US | HTTP 200 not_applicable with note (was 502); SIFY shareholding via sec-20f 'covered' with major holders; WIT covered | holds | raw/R15-DATA-060.txt |
| R15-DATA-065 | live GET /history SPY 1mo, AAPL 1wk, TCS.NS 1mo, RELIANCE.NS 1wk (Sat 2026-10-03) | current bars freshness eod (SPY 2026-10-01, AAPL 2026-09-28 ...); none stale | holds | raw/R15-DATA-065.txt |
| R15-DATA-069 | live GET /fundamentals/AAPL/ratings/price-target-history and /individual + label grep | 971 rows over 60 firms, per-firm targets (Evercore 365->380); 60/60 individual targets non-null; 'Mean of targets revised that day' | holds | raw/R15-DATA-069.txt |
| R15-DATA-073 | live NSE holiday-master (CM) vs locale._NSE_HOLIDAYS 2026 | 20 vs 20, no difference either way; regenerate_holidays.py present | holds | raw/R15-DATA-073.txt |
| R15-DATA-077 | live GET /data-sources + marketplace grep | nse_direct/nse/bse region IN; marketplace.test.ts:121 pins the India keyless lanes | ci_pinned | raw/R15-DATA-077.txt |
| R15-DATA-082 | in-process b19_set13.py 082 stubbed ccxt ticker + live crypto /quotes | no last/close -> ProviderError; last=0 -> CorrectnessError 'non-positive price 0.0'; live BTC 84870.01 live | holds | raw/R15-DATA-082.txt |
| R15-DATA-086 | in-process b4_086.py getaddrinfo down then restored | down -> ProviderError kind network; restored -> 25 real rows | holds | raw/R15-DATA-086.txt |
| R15-DATA-090 | live POST /workspace v1,v2; truncate file; GET; save; [] on disk | GET serves .bak {"v":1}, damaged file kept as .corrupt-*; .bak parseable after next save; [] -> 404 not 500 | holds | raw/R15-DATA-090.txt |
| R15-DATA-095 | in-process p095.py existing DB + simulated next numeric field | ebitda_margin ALTERed in on the existing DB by _connect() | holds | raw/R15-DATA-095.txt |
| R15-DATA-100 | live POST /quant/bond/price (IN) + panel test grep | route currency-free (clean 1028.73); BondPricerPanel.test.tsx:73 'in region IN, prices render with rupee, not $' | ci_pinned | raw/R15-DATA-100.txt |
| R15-DATA-104 | in-process probe84.py 104 get_upcoming 120 symbols; breaker open | max concurrent fetches 8 (cap 8); breaker open -> 0 fetches | holds | raw/R15-DATA-104.txt |
| R15-DATA-108 | in-process b13_scr.py 108 repeat sector_map calls | _sector_master hits=100 misses=1; same obj | holds | raw/R15-DATA-108.txt |
| R15-DATA-112 | live POST /screener/run custom [MANIKA.NS,RELIANCE.NS,TCS.NS] market_cap desc | RELIANCE 1.58e13, TCS 7.5e12, MANIKA (null) last | holds | raw/R15-DATA-112.txt |
| R15-DATA-116 | live GET /disclosures/shareholding {AMAL,DAL,NAPEROL,JUMBO,ELCIDIN,TCS} (IN) | all 200 with patterns (104/43/103/102/101/20), quarter 2026-06-30 | holds | raw/R15-DATA-116.txt |
| R15-DOCS-006 | grep original false claims + guard | no 'ONE search surface', no 'three-place', none in PanelHost.tsx/page.tsx; remaining 9 files on the guard's shrinking allowlist | holds | raw/R15-DOCS-006.txt |
| R15-DOCS-012 | ls generators and v0.6.0 mock dirs | render_phase_6_* gone; teammate-e/teammate-sc gone (exit 2 from ls of the removed paths) | holds | raw/R15-DOCS-012.txt |
| R15-DOCS-017 | docs universe counts vs live universes | docs 503/3506/5042/5891 == live sp500 503, nse-all 3506, bse-all 5042, india-all 5891 | holds | raw/R15-DOCS-017.txt |
| R15-DOCS-021 | read CURRENT_STATE persistence table + grep stores | custom_agents.db and delegate_runs.db rows; gap note 'six of the seven' names delegate_runs.db migration | holds | raw/R15-DOCS-021.txt |
| R15-LEAD-002 | live 3 rounds GET /fundamentals/{TCS,INFY,ITC,HDFCBANK,SBIN} (IN) | round 1 cold 14.6-16.2 s; round 2 1.2-2.8 s; round 3 1.0-1.4 s (no 4-8.5 s steady state) | holds | raw/R15-LEAD-002.txt |
| R15-LEAD-006 | grep _row_value | one definition growth_check.py:93; earnings_quality.py imports it | holds | raw/R15-LEAD-006.txt |
| R15-LEAD-010 | live GET /sec/filings?symbol=AAPL&form_type=10-K then /sec/filings/{acc}?identifier=AAPL x3 | all 200: 10-K filed 2025-10-31 / 2024-11-01 / 2021-10-29, 2 sections each | holds | raw/R15-LEAD-010.txt |
| R15-LEAD-014 | in-process l014.py _repair_tool_args schema-echo forms | 0 of 8 full echoes accepted; fenced/prose None; legit news args kept | holds | raw/R15-LEAD-014.txt |
| R15-LEAD-018 | in-process probe40.py 018 nemotron fixture through ReasoningSplitter | thinking len 296, answer len 0 (echo dropped) | holds | raw/R15-LEAD-018.txt |
| R15-LEAD-022 | live GET /quotes/{BHP.AX,0700.HK,7203.T,VOD.L,SAP.DE,BRK.B} | all 200 priced in AUD/HKD/JPY/GBp/EUR; BRK.B -> BRK-B 502.65 | holds | raw/R15-LEAD-022.txt |
| R15-LEAD-027 | grep suggested:chart + test | no suggested:chart row; command-palette.test.ts:278 'no two empty-query rows share a panelId' | holds | raw/R15-LEAD-027.txt |
| R15-LEAD-032 | in-process inproc_ratio.py adr_ratio.lookup with _fetch raising OSError x3 | None None None; fetch calls 1 | holds | raw/R15-LEAD-032.txt |
| R15-LEAD-039 | live GET /earnings/{RDY,TM,SONY,AAPL}/estimates | all 200 with revenue fields, EPS null (was 502); AAPL full | holds | raw/R15-LEAD-039.txt |
| R15-LEAD-045 | in-process l045.py fetch_quotes_batch 16 symbols live Yahoo v7 | rows 16, failures {} | holds | raw/R15-LEAD-045.txt |
| R15-LEAD-051 | in-process FiledPeriods.cadence() literal case + controls | 2 quarters -> quarterly-gap (was half-yearly); 1 quarter -> quarterly-gap; half+2 quarters covering 12m -> quarterly; pure half -> half-yearly; 4 q -> quarterly | holds | raw/R15-LEAD-051.txt |
| R15-LIFECYCLE-003 | grep autosave-during-restore test | App test 'autosaves nothing during the launch restore; the first save after it carries the research space' | ci_pinned | raw/R15-LIFECYCLE-003.txt |
| R15-LIFECYCLE-007 | env -i minimal PATH: _resolve_docker_binary + _run_docker --version | resolved /usr/local/bin/docker; rc 0 'Docker version 29.4.0' | holds | raw/R15-LIFECYCLE-007.txt |
| R15-LIFECYCLE-012 | live: ollama copilot delegate run killed mid-flight (own sidecar stopped by recorded sleep pid), rebooted same data dir; GET row, resume, cancel (lock-held) | mid-flight checkpoint_json non-null (49 B, steps 1); after reboot status error "interrupted by sidecar restart"; resume 200 {resumed:true}; cancel 200 -> cancelled | holds | raw/R15-LIFECYCLE-012.txt |
| R15-LIFECYCLE-017 | grep screener enrichment guard + test | BLE001 'unexpected enrichment error' path; test_b5_screener.py:73 R15-LIFECYCLE-017 | ci_pinned | raw/R15-LIFECYCLE-017.txt |
| R15-LIFECYCLE-021 | in-process dead nse_direct session x4 NSE quotes + live /system/provider-health | 4 quotes served by nse; fallthroughs [{nse_direct, quote, count 4}]; live endpoint carries fallthroughs list | holds | raw/R15-LIFECYCLE-021.txt |
| R15-LIFECYCLE-026 | live own sidecar: 3 cycles x 8 cheap GETs per ~52 s + 2 cold BSE history; ps cputime; idle samples | 5.4% of a core under load (8.38 s / 154 s; entry ~60%); idle 3.9-5.2% (rc2 0.3%, see env notes) | holds | raw/R15-LIFECYCLE-026.txt |
| R15-LIFECYCLE-030 | in-process b23_set81.py IN boot + sweep first cycle | seed_india_store calls = 1 (want 1) | holds | raw/R15-LIFECYCLE-030.txt |
| R15-LIFECYCLE-034 | in-process p_lows.py lc34 setup() with write_settings OSError | state error, reason 'setup failed: [Errno 28] No space left on device', traceback logged | holds | raw/R15-LIFECYCLE-034.txt |
| R15-LIFECYCLE-038 | grep sidecar_healthy probe + test | sidecar_healthy sends GET /health; plain_tcp_listener_is_not_healthy test | ci_pinned | raw/R15-LIFECYCLE-038.txt |
| R15-RELEASE-007 | grep lint script + audit run + negative fixture | lint = 'eslint . && node scripts/audit-design-tokens.mjs'; clean 392 files; fixture 3 violations exit 1 | holds | raw/R15-RELEASE-007.txt |
| R15-RELEASE-011 | grep vitest config + ci-local | coverage thresholds lines 81.4 autoUpdate; ci-local runs vitest --coverage | holds | raw/R15-RELEASE-011.txt |
| R15-RESEARCH-004 | in-process cross_check with figure-led claim lines | claims intact ('40.5% revenue growth', '-0.4% ...', '67.13953 P/E'); no mangling | holds | raw/R15-RESEARCH-004.txt |
| R15-RESEARCH-009 | real _research(depth=deep) on ollama llama3.1:8b in-process (lock-held); PROFILES | brief.cost {tokens 15222, spend 0.0, steps 5, estimate true} (was zero); PROFILES deep 600k/$3, ultra 1.8M/$9 | holds | raw/R15-RESEARCH-009.txt |
| R15-RESEARCH-013 | in-process r013.py fast._filings_leg live + BSE-down simulation | JUMBO bse; AMAL/RELIANCE nse+bse; BSE down -> nse | holds | raw/R15-RESEARCH-013.txt |
| R15-RESEARCH-017 | in-process t017.py _run_loop with loops raising | neither escapes: ok False, 'the iter/heavy research loop failed', execution_loop iter/heavy | holds | raw/R15-RESEARCH-017.txt |
| R15-RESEARCH-021 | in-process p021.py entity_match | BAJFINANCE 200 DMA / 52-week high / breakout 1.0 True; KPITTECH 1.0 True | holds | raw/R15-RESEARCH-021.txt |
| R15-RESEARCH-026 | source + pin (rc2 used a vite ssr bundle; battery builds nothing) | format.ts:149 '· currency unknown'; brief-blocks.tsx:317 Market cap via formatInstrumentMoney; brief-blocks.test.ts:356 pins it | ci_pinned | raw/R15-RESEARCH-026.txt |
| R15-RESEARCH-030 | grep catalog transcript + in-process p41b.py live NSE KPITTECH/INFY | catalog entry present; KPITTECH filing 2026-08-04, INFY 2026-07-28, source NSE, text returned | holds | raw/R15-RESEARCH-030.txt |
| R15-RESEARCH-034 | in-process reflect_says_complete | 'Price action is not covered yet' False; 'COMPLETE' True; 'no gaps' True | holds | raw/R15-RESEARCH-034.txt |
| R15-RESEARCH-038 | in-process p038.py keyless backend one engine failing | after 1 failed search: 2 engine calls, breaker closed, failures 1; opens after 2nd | holds | raw/R15-RESEARCH-038.txt |
| R15-RESEARCH-042 | in-process _stamp_source_floor 0/2/3 sources | 0/2 -> structured.source_floor note 'N sources (below 3)' + md '_Cited: N sources (below 3)._'; 3 -> no marker | holds | raw/R15-RESEARCH-042.txt |
| R15-UI-004 | grep test + source | EquityOverview test 'R15-UI-004: a failed live-quote fetch shows the banner and Retry re-fetches'; QuoteFetchResult error branch | ci_pinned | raw/R15-UI-004.txt |
| R15-UI-008 | live POST /llm/keys/validate fake openrouter/gemini/xai keys | all ok:false reason invalid '<Provider> rejected this key.' | holds | raw/R15-UI-008.txt |
| R15-UI-012 | live POST /agents/nope/invoke, /agents/copilot/invoke {} + client pins | 404 "unknown agent: 'nope'"; 422 field error; streaming.test.ts:484/492 pins | ci_pinned | raw/R15-UI-012.txt |
| R15-UI-016 | node strip-types kb2.mts on candidate keybindings.ts | all 13 defaults resolve to own id; after remap Cmd+K none, Cmd+P palette.open | holds | raw/R15-UI-016.txt |
| R15-UI-020 | grep tests | workspace.test.ts:767, ChartPanel.test.tsx:298/945, chart-drawings.test.ts:68 R15-UI-020 | ci_pinned | raw/R15-UI-020.txt |
| R15-UI-025 | headless source probe only (GUI-certified at gui-round@ace7dd7) | NotesToolbar LinkPopover replaces window.prompt; lint rule bans window.prompt | needs_gui | raw/R15-UI-025.txt |
| R15-UI-029 | grep tests + live GET /macro/catalog?provider=ecb | MacroSeriesPicker.test.tsx:111 Retry; macro.test.ts:153; live 200 | ci_pinned | raw/R15-UI-029.txt |
| R15-UI-033 | grep tests + source | MarketplacePanel.test.tsx:182/199; configure() error path sets validationError | ci_pinned | raw/R15-UI-033.txt |
| R15-UI-037 | grep test | 'the cost input and column say per share (R15-UI-037)' | ci_pinned | raw/R15-UI-037.txt |
| R15-UI-045 | grep tests + source | ScreenerCriteriaBuilder.test.tsx:71/93 R15-UI-045; CriterionGroupEditor carries threshold | ci_pinned | raw/R15-UI-045.txt |
| R15-UI-050 | headless source probe only (GUI-certified at gui-round@ace7dd7) | min-h-8 row class present in source; visual check needs the rig | needs_gui | raw/R15-UI-050.txt |
| R15-UI-054 | in-process p17b.py kept_previous ack | kept_previous emitted as notice kind 'The panel kept the brief already on screen' | holds | raw/R15-UI-054.txt |
| R15-UI-058 | node kb2.mts setOverrides merge + SettingsPanel tests grep | merge w/ bogus keeps {changes.acceptAll: mod+shift+a}; SettingsPanel.test.tsx:394/403; keybindings.test.ts:85/94 | ci_pinned | raw/R15-UI-058.txt |
| R15-UI-063 | node strip-types call of src/lib/date-defaults.ts at now + literal grep | defaults today 2026-10-03 (option/bond/backtest); no date literal in quant panels | holds | raw/R15-UI-063.txt |
| R15-UI-067 | grep DataBadges tests | 'states synthetic in visible text...' and 'dates EOD in the viewer's local calendar across IST midnight (R15-UI-067)' | ci_pinned | raw/R15-UI-067.txt |
| R15-UI-072 | grep test + source | 'R15-UI-072: the trigger contains a chevron icon'; ChevronDown rendered | ci_pinned | raw/R15-UI-072.txt |
| R15-UI-076 | grep region defaults + tests | DEFAULT_REGION IN; IN_DEFAULT_SYMBOLS; workspace.test.ts:800 R15-UI-076 | ci_pinned | raw/R15-UI-076.txt |
| R15-UI-080 | grep provenance chip + test | isInternalProvenance vysted://; BriefPanel.test.tsx:353 provenance chip test | ci_pinned | raw/R15-UI-080.txt |
| R15-UI-085 | text-charcoal-600 resting-fg grep + token contrast | no resting text-charcoal-600 fg; charcoal-600 1.98:1 border/disabled only, charcoal-500 5.24:1 | holds | raw/R15-UI-085.txt |
| R15-UI-091 | live GET /indicators/suggested + /indicators/AAPL | (5m,eq) ema:9,ema:21,vwap,rsi; (1d,crypto) ema:50,ema:200,vwap:week,rsi; EMA(9)/EMA(21); 'VWAP (week)' | holds | raw/R15-UI-091.txt |

## Totals

holds 111 / regressed 0 / ci_pinned 35 / needs_gui 2 / blocked_env 0 (total 148)

## Environment notes

- No vitest/pytest suite run. ci_pinned = certified through a pinned test, which is named in the row. CODE-FRONTEND-003, CODE-PLATFORM-014 and RESEARCH-026 were holds at rc2 through scratch vitest/vite probes; the battery runs no vitest or build, so they are ci_pinned here on source plus the named pin.
- UI-025 and UI-050 were GUI-certified; only a headless source probe was run (needs_gui).
- CODE-PLATFORM-023 used the own sidecar's cached INFY/^NSEI history; numbers identical to rc2.
- LEAD-002: round-1 cold fetches 14.6-16.2 s, warm rounds 1.0-2.8 s (rc2 warm 0.4-0.6 s); no 4-8.5 s steady state, so the entry holds, but warm is slower than rc2 (network variance, not attributed).
- AGENT-022: in-process guard holds (missing cost_basis -> ok:false, ask the user). Live llama3.1:8b twice printed the portfolio_add_position call as text JSON instead of a tool call; no write and no claimed write. Filed as a low known_limitation (keyless local-model lane).
- LIFECYCLE-026: under-load CPU 5.4% (entry 60%, rc2 3.7%). Idle samples 4.6-5.2% on the long-lived sidecar and 3.9-4.6% about 1-2 min after the LIFECYCLE-012 reboot, against rc2's 0.3%. Not attributed (no py-spy; the fresh sample overlaps boot-time sweeps); worth a dedicated idle soak.
- Several first-draft probes used wrong module/route/field names and were corrected before judging (DATA-073/090/100/104, LIFECYCLE-021, LEAD-010/051, DATA-043/112, CODE-DATA-001/022, CODE-AGENT-023/031, AGENT-066/070, UI-063); raws hold the corrected run.
- Ollama calls (AGENT-022/035/039/074, CODE-AGENT-011, RESEARCH-009, LIFECYCLE-012) each held /tmp/vysted-r15-ollama.lock, one call per hold.
- LIFECYCLE-012 restarted the own sidecar (old sleep pid 18819 -> new 28129/worker 28130); shard-3.pids.json updated.

COVERAGE: 148/148 ids raw; no raw: none
