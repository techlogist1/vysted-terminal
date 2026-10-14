# Battery shard 1 (final-battery-1) vs d38b5d1a

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-002 | in-process _dispatch_tool_with_progress, aclose at 0.05s | tool finished=False right after aclose and still False 0.6s later (task cancelled) | holds |
| R15-AGENT-006 | pin check (Gemini 3 key unavailable, D35) | dcbe7ba ancestor of d38b5d1a; sidecar/tests/test_gemini_multiround.py:131 pins thought-signature round trip; gemini.py:84 carries it | ci_pinned |
| R15-AGENT-010 | in-process resolve_symbol tool with event-loop tick probe | infosys 0.35s bound max_gap 56ms; unfound names 0.99s/0.72s unresolved, max loop gap 21ms (no stall) | holds |
| R15-AGENT-014 | pin check (frontend bootstrapPlugins) | c81d879 ancestor; src/lib/plugin-agents.test.ts:28 "registers an agent plugin's agents as custom agents" | ci_pinned |
| R15-AGENT-020 | in-process catalog + runtime read of notes | read_notes capability present in the default grant; runtime reads __notes__ | holds |
| R15-AGENT-024 | in-process _normalise_tool_args with stringified criteria | stringified criteria array parsed to a list | holds |
| R15-AGENT-029 | pin check (frontend streaming.ts) | dcbe7ba ancestor; src/modules/chat/streaming.test.ts:314 "One terminal callback per stream call" | ci_pinned |
| R15-AGENT-033 | live ASK-autonomy invoke, llama3.1:8b, BDL chart + RSI | both set_chart calls staged; notice "Staged for your review, not applied yet: set_chart_symbol BDL; set_chart_indicators BDL"; model says "I've proposed changes" | holds |
| R15-AGENT-037 | live delegate run, llama3.1:8b, budget max_tokens=1000 | status error "token ceiling 1000 reached (6457 used)", steps 1, activity [], no second request metered | holds |
| R15-AGENT-041 | pin check (frontend undo) | e81c9e7 ancestor; src/lib/host-actions.test.ts:1884 holding-delete undo and :1910 note-replace undo | ci_pinned |
| R15-AGENT-045 | in-process compare_symbols (COCHINSHIP+MAZAGONDOCK, then company names) | MAZAGONDOCK -> "unresolved name"; "Cochin Shipyard" resolved to COCHINSHIP.NS with a note | holds |
| R15-AGENT-050 | in-process persona system block build | persona block carries cache_control plus the second breakpoint | holds |
| R15-AGENT-054 | in-process _normalise_tool_args indicators enum | bollinger_bands rejected with the enum list; rsi+sma passes | holds |
| R15-AGENT-058 | in-process market_overview with news feed down | ok:true, headlines [] with headlines_error "news feed unavailable: all news sources failed" | holds |
| R15-AGENT-062 | in-process price_data RELIANCE 6mo/1y (AAPL Yahoo-throttled) | 6mo bars_returned 90 of bars_available 128, 1y 90 of 257, window_start stated | holds |
| R15-AGENT-068 | in-process earnings_upcoming days="seven" | tool's own error "days must be in [1, 60]", not a raw ValueError | holds |
| R15-AGENT-072 | curl /agents | tools (specialty 3-55) published separately from effective_tools (55) | holds |
| R15-AGENT-076 | pin check | d2da4535 ancestor; sidecar/tests/test_llm_ollama.py:242 test_tools_construction_error_logs_and_emits_notice; ollama.py:45 logger, :197 warning, :206 notice | ci_pinned |
| R15-AGENT-080 | pin check (frontend AUTO gate) | c81d879 ancestor; AUTO_APPLIED_KINDS in types/proposed-change.ts pinned by src/store/proposed-change-kinds.test.ts | ci_pinned |
| R15-AGENT-087 | grep of the named docs | agent-mode.ts docblock reads two-mode + autonomy; FR-003/SC-029 have no alt+1-4; one residual "Ask/Edit/Build/Delegate" in spec.md:1112 Key Entities (outside the fixed sections) | holds |
| R15-AGENT-092 | live delegate run, write_note, budget max_tokens=1000, plus default-budget control | halted run host_actions []; control done with host_actions [write_note] | holds |
| R15-AGENT-096 | pin check (frontend applyFilters) | c682ab81 ancestor; src/lib/host-actions.test.ts:1487 flat group supersedes flat criteria | ci_pinned |
| R15-CODE-AGENT-005 | in-process scrub_adapter_options | allowlist only; research_depth/depth/unknown keys dropped; used by routers/llm.py and agent_runtime | holds |
| R15-CODE-AGENT-009 | in-process ast line count | invoke_agent 101 lines (certified 95); _dispatch_round 193 | holds |
| R15-CODE-AGENT-013 | in-process catalog projections | internal 56, selectable 56, default_grant 55, mcp 31; alias macro->macro_series resolves | holds |
| R15-CODE-AGENT-017 | in-process temp custom_agents.db with an unparseable tools_json row | list_agents -> [custom:good], bad row skipped with a warning (no raise) | holds |
| R15-CODE-AGENT-021 | pin check + route grep | d2da4535 ancestor; sidecar/tests/test_llm_router.py test_no_llm_route_echoes_the_key present | ci_pinned |
| R15-CODE-AGENT-025 | in-process McpClient.call_tool with stub session | returns structuredContent {"x":1} alongside isError/content | holds |
| R15-CODE-AGENT-029 | grep _ensure_schema in services | 0 hits in sidecar/services; idempotency tests present | holds |
| R15-CODE-AGENT-033 | pin check | 17301f54 ancestor; sidecar/tests/test_agent_runtime.py:3345 and test_runtime_phases.py:209 pin the tool outcome in the stream; live tool_result frames seen in AGENT-033 run | ci_pinned |
| R15-CODE-DATA-003 | in-process resolve_symbol tool vs routers.resolve, rename lane warm | GUJGASLTD/MMYT/EMAMILTD first-candidate dicts identical incl. rename block | holds |
| R15-CODE-DATA-007 | pin check | d2da4535 ancestor; test_lane_keyerror_degrades_to_partial_merge + test_shareholding_lane_keyerror_falls_through_to_next_lane present; except Exception at corporate_disclosures.py:611 | ci_pinned |
| R15-CODE-DATA-011 | pin check | d2da4535 ancestor; sidecar/tests/test_router_cached_helper.py test_corrupt_cache_entry_refetches_for_all_rating_routes | ci_pinned |
| R15-CODE-DATA-015 | pin check (frontend) | d2da4535 ancestor; EarningsCalendarPanel.test.tsx "skeleton and loaded colgroups share widths" | ci_pinned |
| R15-CODE-DATA-020 | pin check + live bad formula | d2da4535 ancestor; test_internal_error_is_500_formula_error_is_400 present; live bad formula -> 422 with parse reason | ci_pinned |
| R15-CODE-FRONTEND-001 | pin check (frontend) | 806a90c ancestor; src/lib/workspace.test.ts:664 "loading a named workspace never rolls back portfolios or notes" | ci_pinned |
| R15-CODE-FRONTEND-005 | pin check (frontend) | 806a90c ancestor; workspace.test.ts:127/:177 drawings + keybindings round trip, page.tsx store subscriptions | ci_pinned |
| R15-CODE-FRONTEND-009 | pin check (frontend) | 5e14731 ancestor; host-actions.test.ts:1416 save_screen saves the agent's recipe | ci_pinned |
| R15-CODE-FRONTEND-014 | pin check (frontend) | c81d879 ancestor; host-actions.test.ts:1341 write_note honours catalog args | ci_pinned |
| R15-CODE-FRONTEND-018 | pin check (frontend) | 806a90c ancestor; savedScreens serialized in src/lib/workspace.ts, workspace.test.ts covers it | ci_pinned |
| R15-CODE-FRONTEND-022 | pin check (frontend) | d2da4535 ancestor; CommandPalette.test.tsx "agent row selection uses agentSummary.id" | ci_pinned |
| R15-CODE-FRONTEND-026 | pin check (frontend) | d2da4535 ancestor; src/store/workflow.test.ts "append a, take, append b -> b still pending" | ci_pinned |
| R15-CODE-FRONTEND-030 | pin check (frontend) | d2da4535 ancestor; src/store/settings.test.ts R15-CODE-FRONTEND-030 case | ci_pinned |
| R15-CODE-FRONTEND-035 | pin check (frontend) | d2da4535 ancestor; host-actions.test.ts write_note append equals appendSymbolNote | ci_pinned |
| R15-CODE-PLATFORM-003 | live POST /workflow/run: bad agent id, no-key agent, api_key in node config | node-error "unknown agent: no-such-agent" and "No Anthropic API key is set", run-error; api_key in config -> 422 | holds |
| R15-CODE-PLATFORM-012 | pin check (frontend) | f407107 ancestor; PluginManagerPanel.test.tsx:118 and plugin-runtime.test.ts:620 | ci_pinned |
| R15-CODE-PLATFORM-017 | in-process evaluate_code + live workflow transform.code | 2^3^2=512, -2^2=-4, round(2.5)=3, ternary 4; workflow node outputs match; x/0 node-error | holds |
| R15-CODE-PLATFORM-021 | curl workspace verbs | POST 405, PUT/DELETE 404, GET [] | holds |
| R15-CODE-PLATFORM-025 | grep docs/BLUEPRINT.md | 249: multi-window "v1.0 roadmap, deferred"; 322: pop-out v1.0 roadmap | holds |
| R15-CODE-PLATFORM-029 | live POST /backtest/run | final equity 99996, totalReturn -4e-05, one lot of 40 | holds |
| R15-CODE-PLATFORM-036 | pin check | d2da4535 ancestor; sidecar/tests/test_backtest_lows.py test_each_rule_compiled_once | ci_pinned |
| R15-CODE-PLATFORM-040 | file check | sidecar/services/quant/monte_carlo.py absent | holds |
| R15-CODE-PLATFORM-044 | in-process inspect | LLMProvider.stream_chat is a plain def, not a coroutine function | holds |
| R15-CODE-PLATFORM-050 | pin check (frontend) | d2da4535 ancestor; metrics.test.ts rows carry the real holding id | ci_pinned |
| R15-CODE-PLATFORM-054 | pin check (Rust) | d2da4535 ancestor; src-tauri/src/lib.rs:891 fn write_atomic_round_trip_leaves_no_tmp | ci_pinned |
| R15-CODE-PLATFORM-058 | code read (untestable per VERIFY) | get_app_data_dir and keychain file_path both call crate::app_data_dir, the one policy fn | holds |
| R15-CODE-PLATFORM-062 | pin check | d2da4535 ancestor; scripts/smoke-test-sidecars.test.mjs _httpGetOk case | ci_pinned |
| R15-CODE-PLATFORM-067 | pin check | d2da4535 ancestor; test_workflow_builtin_nodes.py test_zero_input_not_replaced_by_config_and_unknown_provider_errors | ci_pinned |
| R15-CODE-PLATFORM-074 | pin check (Rust) | d2da4535 ancestor; src-tauri/src/lib.rs:941 fn clear_mcp_endpoint_file_removes_existing | ci_pinned |
| R15-CODE-RESEARCH-001 | in-process deep_research clamp + schema | clamp max(300, profile.wall_seconds); schema "30-360"; deep 180, heavy 360 | holds |
| R15-CODE-RESEARCH-005 | pin check | d2da4535 ancestor; test_research_module_boundary.py test_no_research_module_imports_a_private_name_across_modules | ci_pinned |
| R15-CODE-RESEARCH-009 | pin check | d2da4535 ancestor; test_ddg_backend.py test_one_search_with_lite_fallback_takes_one_pacing_slot | ci_pinned |
| R15-CROSS-PLATFORM-002 | grep fixture reads in the four test files | every read_text carries encoding="utf-8"; 0 bare read_text() | holds |
| R15-CROSS-PLATFORM-007 | pin check (Windows-only condition) | d2da4535 ancestor; test_workspace.py test_replace_retries_permission_error_then_succeeds; retry loop at workspace_store.py:167 | ci_pinned |
| R15-CROSS-PLATFORM-011 | pin check (Linux-only condition) | d2da4535 ancestor; onboarding.test.ts "rejecting keychain keeps seen:true once markSeen ran" | ci_pinned |
| R15-DATA-004 | curl /fundamentals DHANBANK | insiders 50.16% flagged against NSE promoter group 0.00% | holds |
| R15-DATA-008 | curl /fundamentals SIFY | currency USD, financial_currency INR; P/S and EV/EBITDA withheld with basis reason | holds |
| R15-DATA-012 | in-process resolve with injected NSDL rename | BSE NSDL resolves with rename None; ZOMATO->ETERNAL still renames | holds |
| R15-DATA-016 | curl /fundamentals + /history DAL | 52w high/low withheld "no trades in 52 weeks (last trade 2025-03-12)"; 1y 0 bars | holds |
| R15-DATA-020 | curl /disclosures/announcements HDFCBANK | 50 rows NSE 39 + BSE 11; cross-exchange pairs collapse, ~1-2 residual same-day pairs (as certified) | holds |
| R15-DATA-024 | curl /disclosures/deals KOPRAN/ADANIENT/RELIANCE | KOPRAN 125 bulk; ADANIENT 77 bulk+block; RELIANCE 359 across BSE/NSE block/bulk/sast | holds |
| R15-DATA-028 | in-process earnings_upcoming, IN region | 15 .NS events (TCS.NS, DMART.NS...), 0 US megacaps | holds |
| R15-DATA-033 | in-process correctness gate with NaN/inf | NaN and inf quote and NaN last close -> CorrectnessError; 190.0 accepted | holds |
| R15-DATA-037 | curl /history BTC/USDT 1mo/1y/5y, ETH 1h | 30 / 365 / 1826 daily bars; ETH 1h 720 bars | holds |
| R15-DATA-041 | in-process compare_symbols RELIANCE.NS + RENTOMOJO.NS | best/worst null, note "windows not comparable: RENTOMOJO has 11 bars since 2026-09-17" | holds |
| R15-DATA-045 | in-process fetch_page via httpbin 302 -> loopback canary | "blocked redirect to a non-public or non-http(s) URL", canary hits []; example.com control ok | holds |
| R15-DATA-049 | curl /fundamentals VIYASH/ICON/ELCIDIN | never-payers TTM 0.0 "no dividends paid (trailing 12m)"; ELCIDIN TTM 25 | holds |
| R15-DATA-053 | curl /quotes ICON.BO, ICONIKSPEV.BO | volume 2400 / 7934 with OHLC + prev_close | holds |
| R15-DATA-057 | curl /resolve DHANBANK | DHANBANK first at 0.792; DHAN-RE absent | holds |
| R15-DATA-063 | curl /indicators + /history ZZZNOTREAL | 200 empty indicators; history reason unknown_symbol | holds |
| R15-DATA-067 | curl /earnings/upcoming US + AAPL estimates | fiscal_period null on all 10 events and on AAPL estimates | holds |
| R15-DATA-071 | curl /history KARNAVATI.BO, TRADEWELL.BO | served by bse, 255 and 143 bars, partial False | holds |
| R15-DATA-075 | in-process _fetch_pdf_page on a real BSE attachment with AttachLive forced to 404 | fetch falls to AttachHis twin and returns PDF text (HDFCBANK filing); live AttachLive itself answers 200 today | holds |
| R15-DATA-079 | curl /quant/option/chain/NIFTY | nse-fo-bhavcopy as_of 2026-10-01, 232 contracts, 203 with OI | holds |
| R15-DATA-084 | in-process get_macro_series with the register stub | observations [(2021-01-04, 0.0), (2021-01-05, 0.07)] | holds |
| R15-DATA-088 | pin check (frontend) | 5e14731 ancestor; src/store/portfolios.test.ts:49 holding validation, host-actions.test.ts:1271 negative cost | ci_pinned |
| R15-DATA-093 | live POST /screener/run custom bare IN tickers | 5 of 5 evaluated as .NS rows, live basis | holds |
| R15-DATA-097 | in-process _live_lookup with stub Search + 301s time travel | empty result cached (1 call for 2 lookups), re-queried after +301s (TTL 300) | holds |
| R15-DATA-102 | pin check | d2da4535 ancestor; three named growth-basis tests present | ci_pinned |
| R15-DATA-106 | pin check + grep (refresh writes the candidate masters) | d2da4535 ancestor; test_enrichment_writes_canonical_seven_keys; script writes industry_raw | ci_pinned |
| R15-DATA-110 | live POST /screener/run sp500 | evaluated 498 of 503 in 0.1s from snapshot basis, 5 skipped | holds |
| R15-DATA-114 | curl repeated x3 | 200 in 0.03s each | holds |
| R15-DOCS-004 | read PRODUCT_DESIGN_DECISIONS.md head | opens with "SUPERSEDED (R15-DOCS-004)" banner naming the reversed sections | holds |
| R15-DOCS-009 | grep BLUEPRINT for LangGraph | 0 LangGraph mentions; :90 "hand-rolled loop" | holds |
| R15-DOCS-014 | grep first-token latency docs | CURRENT_STATE.md:741 records the BYOK first-token latency status | holds |
| R15-DOCS-019 | grep stale CURRENT_STATE phrases | 0 hits for "Likely broken" / "Stale/out of sync" / "A real, unfixed inconsistency" | holds |
| R15-DOCS-023 | grep README + CURRENT_STATE | README "is being specified" 0 hits; P1_P3 report link annotated as removed | holds |
| R15-LEAD-004 | curl /fundamentals NDTV/JONJUA/TCS.NS/DHANBANK | unfiled-quarter reason, no half-yearly text on quarterly filers; TCS.NS/DHANBANK ok | holds |
| R15-LEAD-008 | in-process native_search_available | xai grok-4 -> False; xai in neither native-search set | holds |
| R15-LEAD-012 | grep build scripts + venv | build-python.mjs WANT="3.13" verified; candidate venv Python 3.13.13 | holds |
| R15-LEAD-016 | curl /earnings/{sym}/history | RELIANCE.NS period_end 2026-06-30 reported 2026-07-17; MSFT 06-30 reported 07-29 | holds |
| R15-LEAD-020 | pin check | d2da4535 ancestor; test_exchange_financials_negcache.py; shorter failure TTL at exchange_financials.py:352 | ci_pinned |
| R15-LEAD-024 | curl /macro WEO USA/IND | 2025+ rows is_projection True, <=2024 False | holds |
| R15-LEAD-029 | read _nse_lookup docstring | no hardcoded "~5,156" (0 hits) | holds |
| R15-LEAD-034 | in-process symbols_match | -SM infix accepted; negative case False | holds |
| R15-LEAD-043 | curl /agents/copilot/invoke no key (openai, groq) + bad key | "No OpenAI/Groq API key is set - add it in Settings." code auth; bad key "rejected - check it in Settings" | holds |
| R15-LEAD-049 | curl /resolve TATAMOTORS + /quotes TMPV.NS | TATAMOTORS -> TMPV with rename; TMPV.NS 200; nifty50 has TMPV not TATAMOTORS | holds |
| R15-LEAD-116 | curl /disclosures FOCUS.BO | serves BSE 543312 feed (23 BSE rows) | holds |
| R15-LIFECYCLE-005 | own 2nd sidecar :52867 with openbb-mcp port pointed at closed :52868 | /openbb-mcp/status available:false with lastError; /fundamentals/MAZDOCK and KPITTECH 200 via yfinance | holds |
| R15-LIFECYCLE-010 | pin check (Rust spawn + frontend) | 68bb7aa4 ancestor; src/lib/sidecar-client.test.ts:12 spawn failure named at once | ci_pinned |
| R15-LIFECYCLE-014 | in-process _discover_specs on a copy with a bad agent + missing dir | degraded lists zz-b1-bad.json schema violation; missing dir -> degraded entry; /health agents_degraded present | holds |
| R15-LIFECYCLE-019 | in-process rename refresh, first NSE request ConnectTimeout, fresh data dir | retried after 60s backoff, lane available, GUJGASLTD -> GUJENERGY | holds |
| R15-LIFECYCLE-023 | pin check (frontend error boundary) | 68bb7aa4 ancestor; src/components/PanelHost.test.tsx:108 | ci_pinned |
| R15-LIFECYCLE-028 | pin check (frontend) | d2da4535 ancestor; workspace.test.ts:1452 pagehide flushes pending autosave | ci_pinned |
| R15-LIFECYCLE-032 | pin check | d2da4535 ancestor; test_fundamentals_warm.py test_one_upsert_failure_counts_the_others; gather return_exceptions=True at :382 | ci_pinned |
| R15-LIFECYCLE-036 | in-process _load_master with garbled JSON | logs error and returns the fallback; except tuple includes ValueError | holds |
| R15-RELEASE-005 | node isStale on a scratch fixture (seed.json.gz newer/older than binary) + grep | isStale true when the .json.gz is newer, false after the binary is touched; no extension allow-list | holds |
| R15-RELEASE-009 | pin check (Rust) | d2da4535 ancestor; src-tauri/src/lib.rs:1119 fn smoke_bind_budget_matches_supervisor | ci_pinned |
| R15-RESEARCH-002 | in-process _parse_verdict | UNVERIFIED forms parse unverified; AGREE/DISAGREE correct | holds |
| R15-RESEARCH-006 | pin check | c81d879 ancestor; sidecar/tests/test_research_verify.py:546 claim loop bounded by the round wall | ci_pinned |
| R15-RESEARCH-011 | pin check | c81d879 ancestor; test_ownership_check.py:137 and test_correctness_gate.py:417 | ci_pinned |
| R15-RESEARCH-015 | in-process _row_domains / registrable_domain | www.nseindia.com + nsearchives.nseindia.com -> {nseindia.com} (one source); distinct hosts stay 2 | holds |
| R15-RESEARCH-019 | in-process visit_for_research on 403 / SSRF / png | reasons "HTTP 403", "blocked non-public...", "unsupported content type: image/png" returned | holds |
| R15-RESEARCH-024 | in-process web_search _dispatch with a SearXNG-shaped row (keyless engines throttled live) | row carries domain business-standard.com and published_at | holds |
| R15-RESEARCH-028 | curl /search/searxng/status | degraded with engines-blocked reason while the container runs | holds |
| R15-RESEARCH-032 | pin check (frontend) | 68bb7aa4 ancestor; SettingsPanel.test.tsx:715 | ci_pinned |
| R15-RESEARCH-036 | pin check | d2da4535 ancestor; test_research_semantics.py test_prompt_keys_cover_every_derived_metric | ci_pinned |
| R15-RESEARCH-040 | pin check (frontend) | d2da4535 ancestor; DepthControl.test.tsx "Tier B + ULTRA renders an estimate before dispatch" | ci_pinned |
| R15-UI-002 | pin check (frontend) | c81d879 ancestor; CommandPalette.test.tsx:217 ticker pick commands the chart-command channel | ci_pinned |
| R15-UI-006 | live POST /screener/run india-all 0<P/E<40 sort pe asc | matched_count 3059 of 4235 evaluated, ascending from P/E 0.0005 | holds |
| R15-UI-010 | live POST /backtest/run window 0/-5/""/1e6 | 422 "window must be between 5 and 200" / "must be an integer" | holds |
| R15-UI-014 | pin check (frontend) | 68bb7aa4 ancestor; sidecar-client.test.ts:214, streaming.test.ts:463 | ci_pinned |
| R15-UI-018 | pin check (frontend) | f407107 ancestor; ConfirmButton.test.tsx:6, ScreenerPanel.test.tsx:410 | ci_pinned |
| R15-UI-023 | pin check (frontend) | e81c9e7 ancestor; ChartPanel.test.tsx:432 and :453 | ci_pinned |
| R15-UI-027 | pin check (frontend) | f407107 ancestor; SettingsPanel.test.tsx:237 Cmd+K records mod+k | ci_pinned |
| R15-UI-031 | pin check (frontend) | e81c9e7 ancestor; EquityOverviewPanel.test.tsx:368 | ci_pinned |
| R15-UI-035 | pin check (frontend) | e81c9e7 ancestor; PortfolioPanel.test.tsx:430 | ci_pinned |
| R15-UI-039 | curl /resolve/autocomplete GUJGASLTD, ZOMATO | GUJENERGY with rename, ISIN, BSE code; ZOMATO -> ETERNAL | holds |
| R15-UI-048 | pin check (frontend) | f407107 ancestor; ChartPanel.test.tsx:287, settings.test.ts:164 | ci_pinned |
| R15-UI-052 | grep shipped onboarding copy | 0 hits for "runs right now" / "Nothing leaves this computer"; OnboardingBanner.test.tsx:57 pins it | holds |
| R15-UI-056 | pin check (frontend) | 1574ed8 ancestor; src/store/screener.test.ts:337 | ci_pinned |
| R15-UI-061 | pin check (frontend) | d2da4535 ancestor; BacktestResultView.test.tsx present | ci_pinned |
| R15-UI-065 | pin check (frontend) | d2da4535 ancestor; open-panel-literals.test.ts | ci_pinned |
| R15-UI-070 | pin check (frontend) | d2da4535 ancestor; WorkspaceDialog.test.tsx export/import case | ci_pinned |
| R15-UI-074 | pin check (frontend) | d2da4535 ancestor; brief-layout.test.tsx max-w-prose case | ci_pinned |
| R15-UI-078 | pin check (frontend) | d2da4535 ancestor; portfolios.test.ts validateHolding case | ci_pinned |
| R15-UI-082 | live POST /workspace Devanagari + 260-byte name | Devanagari saved 200; long name 400 with byte-cap detail (no 500) | holds |
| R15-UI-087 | pin check (frontend) | 4097dac ancestor; SettingsPanel.test.tsx:289 provider fallback order | ci_pinned |
| R15-UI-093 | pin check + live autocomplete | d2da4535 ancestor; mentions.test.ts quoted-candidate case; live autocomplete serves AAPL | ci_pinned |

Counts: holds 86, regressed 0, ci_pinned 63, needs_gui 0, blocked_env 0.

COVERAGE: 149/149 ids raw; no raw: none
