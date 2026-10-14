# Regression battery shard 2 of 4 (final pass, candidate d38b5d1a2487bd52fe8a7e741a3a5266e3206611)

Lane battery:2, claude-opus-5-5 effort high. 149 'fixed' register ids (sorted, position p%4==2, list in shard-2.ids). One own sidecar :52862 booted from final-cand (scratch data dir final-data-final-battery-2, MCP ports 52801/52802 read-only); in-process probes use final-cand sidecar/.venv; LLM probes ran under the /tmp/vysted-r15-ollama.lock mkdir lock, one call per hold. Raw output per id in raw/<id>.txt (command, output, EXIT). No vitest/pytest suite run; ci_pinned rows name the pinning test. Reference = rc2 battery rows (rc1/round-6-rc2/battery).

Counts: holds 110, regressed 0, ci_pinned 37, needs_gui 1, blocked_env 1.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-003 | in-process scripted provider, one tool_use/round, invoke_agent | 7 rounds, 6 yielded ids, final 'I stopped after 6 tool rounds'; capped write_note under AUTO never yielded | holds |
| R15-AGENT-007 | scripts/agent_eval grader in candidate venv | 16 scenarios; grade(good)=[]; input {} -> 'price_data called without required [symbol]'; pass_hat_k 0.5 | holds |
| R15-AGENT-011 | grep backtest/runs + real _run_custom_backtest(SPY) -> _auto_open_backtest_event | backtest.ts:313 caller; ok runId; synthetic open_panel{panel:backtest,run_id} id auto-backtest-t1; failed run -> None | holds |
| R15-AGENT-015 | in-process agent_invoke with prompt_template, invoke_agent stubbed | prompt received 'Typed prompt about CTX'; node-registry.ts:471 key prompt_template | holds |
| R15-AGENT-021 | injection text in web_search/news results via invoke_agent; price_data control | web_search+news fenced, UNTRUSTED header first, injection inside guard; price_data unfenced | holds |
| R15-AGENT-025 | hanging provider, heartbeat 0.01s / idle 0.05s | 4 heartbeats then LLMErrorEvent provider_idle then done; _PLANNER_TIMEOUT_SECONDS = 20.0 | holds |
| R15-AGENT-030 | error_frame on four register exceptions; real ConnectError humanize | all four -> internal 'The terminal hit an internal error.' with type in detail; ConnectError -> network | holds |
| R15-AGENT-034 | live POST /agents/copilot/runs budget {} + invalid budgets (ollama, lock held) | stored 120000/1.0/600/12; max_steps 0, spend -1, wall 0 -> 422 gt 0 | holds |
| R15-AGENT-038 | in-process one-shot max_steps=1 (inproc_runs.py) | done 'completed (step ceiling 1 reached (1 taken) on the final round)', answer kept | holds |
| R15-AGENT-042 | static: pinned tests | host-actions.test.ts:1291, PortfolioPanel.test.tsx:162 | ci_pinned |
| R15-AGENT-046 | live vy.py copilot 'Research NVDA briefly.' ollama llama3.1:8b (lock held) | research id call_2dcc6cf0...; publish_brief id call_2dcc6cf0...__autobrief; no empty ids | holds |
| R15-AGENT-051 | in-process _render_terminal_preamble, two charts INFY focused + equity-overview focus | 'Focused chart: INFY (1d, ema:9)' + 'they mean INFY'; equity-overview case prints 'Chart: SPY' + 'Focused panel: equity-overview' | holds |
| R15-AGENT-055 | catalog arrange_layout description + template test grep | description no dual-chart/heatmap promise; layout-templates.test.ts:75 planLayout cases | ci_pinned |
| R15-AGENT-059 | fastmcp list_agents/list_workflows/list_runs vs local 500 stub :58862 | each {ok:False, error:"GET ... failed: Server error '500 ...'"}, not empty lists | holds |
| R15-AGENT-063 | in-process build_aliases/enrich + live GET /news?symbols=BTC/USDT,ETH/USDT | BTC/USDT aliases [BTC/USDT,BTC,bitcoin]; 'Bitcoin options expiry looms' -> BTC/USDT negative; Ethereal/SOLID not tagged; live 2 tagged+scored items | holds |
| R15-AGENT-069 | provider_registry.get_quote patched so BADCO raises AttributeError | compare_symbols rows [GOODCO ok, BADCO error] + 'fewer than two symbols resolved'; market_overview 3 rows, BADCO error row | holds |
| R15-AGENT-073 | in-process model resolution (anthropic override no model; unknown provider) | -> claude-opus-4-8 (registry default); unknown provider -> ValueError | holds |
| R15-AGENT-077 | one-shot with configured base_url fake proxy | request landed at proxy POST /v1/chat/completions with proxy key, not api.openai.com | holds |
| R15-AGENT-081 | static: EquityOverviewPanel highlightMetric + test | EquityOverviewPanel.tsx:864,867 reads highlightMetric; test :573 | ci_pinned |
| R15-AGENT-088 | static: pinned test | slash-commands.test.ts:79 | ci_pinned |
| R15-AGENT-093 | in-process arg coercion sweep | '10'->10, '5'->5, '100'->100; 'abc' rejected; only non-coerce is dummy-enum macro_search (same as rc2) | holds |
| R15-CODE-AGENT-002 | MCP call_tool raising 5 transport errors | each ProviderError and session dropped True | holds |
| R15-CODE-AGENT-006 | curl /llm models vs model_registry.json | live 8 = registry 8, 0 diffs; model-selection.ts:14 imports registry | holds |
| R15-CODE-AGENT-010 | live cancel/resume/start/answer on done run b6070ada; unknown run | 409 x4 'run ... is done; it cannot become ...', row unchanged; unknown -> 404 | holds |
| R15-CODE-AGENT-014 | in-process handler error spelling | 'unexpected error: kaboom' / 'provider error: upstream 503'; 'news fetch failed' prefix 0 | holds |
| R15-CODE-AGENT-018 | stageable derived from PLAN_ACTIONS and HOST_ACTION_TOOLS | False; read-safe set keeps open_company_overview | holds |
| R15-CODE-AGENT-022 | curl /mcp/status + handshake + LATEST | all 2025-11-25 | holds |
| R15-CODE-AGENT-026 | static: ToolKind members + parity test | 3 members, no mcp_endpoint; test_mcp_catalog_parity.py:176 | holds |
| R15-CODE-AGENT-030 | static: no-op handler count | 0 no-op handlers x4 | holds |
| R15-CODE-AGENT-034 | TestClient save + list_workspaces/get_workspace MCP tools | list ['refaudit3-ws']; get returns doc; missing -> ok:false 404, is_error False | holds |
| R15-CODE-DATA-004 | curl screener default universe by region | IN->nifty50, US->sp500, none->nifty50 | holds |
| R15-CODE-DATA-008 | in-process provider fall-through on ValueError/TypeError | sync and async both -> 'good' | holds |
| R15-CODE-DATA-012 | TestClient corrupt cache row /earnings/NVDA/surprises + upcoming; grep | refetched once then cached; calls [surprises, upcoming]; 4 _cached( uses, 0 data_cache. | holds |
| R15-CODE-DATA-016 | static: format.ts single definitions | single definitions; no analysts key | ci_pinned |
| R15-CODE-DATA-021 | static grep windowed_ts | count 0 | holds |
| R15-CODE-FRONTEND-002 | static: pinned tests | agent-spaces.test.ts:57, research-spaces.test.ts:223, workspace.test.ts:606 | ci_pinned |
| R15-CODE-FRONTEND-006 | static: NodeEditorPanel runWorkflow + test | NodeEditorPanel.tsx:413; test :341 | ci_pinned |
| R15-CODE-FRONTEND-010 | static: pinned test | host-actions.test.ts:1458 | ci_pinned |
| R15-CODE-FRONTEND-015 | static: shared focusedSymbolFromBus + test | ChatSidebar.test.tsx:600 | ci_pinned |
| R15-CODE-FRONTEND-019 | chmod 555 my scratch workspaces dir, POST /workspace, restore | 507 'Could not write the workspace: Permission denied'; 200 after restore; workspace.ts:1159 'Autosave failed'; test :1444 | holds |
| R15-CODE-FRONTEND-023 | static: pinned test | ChartPanel.test.tsx:1172 | ci_pinned |
| R15-CODE-FRONTEND-027 | static: pinned tests | agents.test.ts:16; sidecar-client.test.ts:319 | ci_pinned |
| R15-CODE-FRONTEND-032 | static: pinned tests | ChatSidebar.test.tsx:747,762; rejectAllChanges :609,678 | ci_pinned |
| R15-CODE-FRONTEND-036 | static: RAIL_PANELS single source + parity test | layout-templates.ts:411; test :633 | ci_pinned |
| R15-CODE-PLATFORM-004 | POST /workflow/run logic.branch falsy strings | false/no/0/off -> false_path, downstream skipped; 'true' runs both | holds |
| R15-CODE-PLATFORM-013 | scratch vitest (symlinked final-cand src, jsdom localhost:5173): serializeWorkspace + setEnabledMap | persists {chart:true} only; restore keeps plugin:vysted-lenses true; pin workspace.test.ts:525 | holds |
| R15-CODE-PLATFORM-018 | workflow quant.price_option binomial 20k + 100k while polling /health | 20k 0.73s; 100k 10.0s, /health 5-6 ms x5 during run, all 200 | holds |
| R15-CODE-PLATFORM-022 | static: client exports grep | only test mock and comment; no production importer | holds |
| R15-CODE-PLATFORM-026 | static: runner lines over SIDECAR_SPECS | runners 14/16/15 lines; one targetTriple at sidecar-specs.mjs:195 | holds |
| R15-CODE-PLATFORM-030 | in-process run_backtest buy 10 then sell -100 | totalReturn -2e-05, trades [(buy,10,-2.0)], final equity 99998 | holds |
| R15-CODE-PLATFORM-037 | static: pinned test | streaming.test.ts:314 | ci_pinned |
| R15-CODE-PLATFORM-041 | curl option price steps 2 vs 3 | 2 -> 400 'between 3 and 100000'; 3 -> 200; panel uses MIN_BINOMIAL_STEPS | holds |
| R15-CODE-PLATFORM-047 | static: pinned test | plugin-runtime.test.ts:401 | ci_pinned |
| R15-CODE-PLATFORM-051 | static grep pnlTone | only :86-87, used :622 | holds |
| R15-CODE-PLATFORM-055 | static: write_atomic + Rust test | one write_atomic lib.rs:570; test write_atomic_text_and_bytes :877 | ci_pinned |
| R15-CODE-PLATFORM-059 | static grep take() | lib.rs:780, openbb_mcp.rs:190, sec_edgar_mcp.rs:185; no if-let form | holds |
| R15-CODE-PLATFORM-064 | static: script removed | script absent; 0 tracked files; README notes deletion | holds |
| R15-CODE-PLATFORM-068 | create_app() node registry | 24 types == register_all() | holds |
| R15-CODE-PLATFORM-075 | curl POST runs resumeFrom / mode resume-from | 422 extra_forbidden; 400 'unsupported run mode' | holds |
| R15-CODE-RESEARCH-002 | in-process parallel legs RELIANCE | hits [async,sync,async]; keys derived/fundamentals/price; price ok | holds |
| R15-CODE-RESEARCH-006 | in-process PANEL_MIN_ANGLES single source | no own copy in deep_research or iter; both use depth.PANEL_MIN_ANGLES | holds |
| R15-CODE-RESEARCH-010 | Brave/Mojeek MRO + 429 through each | both inherit _HtmlSerpBackend, same search; 429 -> rate_limited; 96/91 vs 141 lines | holds |
| R15-CROSS-PLATFORM-003 | in-process forced-Windows hardware_fit + real mac | _detect_windows GlobalMemoryStatusEx branch; real path pinned test_hardware_fit.py:146 | ci_pinned |
| R15-CROSS-PLATFORM-008 | static grep | only lib.rs:361 doc comment | holds |
| R15-CROSS-PLATFORM-012 | in-process data_cache with --cache-dir | db under cache dir, data dir empty; fallback True; lib.rs:278,399,407 | holds |
| R15-DATA-005 | curl fundamentals VERTEX/JUMBO/JNPR | P/B flagged | holds |
| R15-DATA-009 | in-process backtest metrics N=1/2/4 | 200 points; sharpe == date-sampled 0.4852/1.1897/1.1375 | holds |
| R15-DATA-013 | curl fundamentals DAL/SMR/JNPR/DHOOTTRANS | DAL eps 2.05 bse pe flagged; SMR flagged; JNPR ok; DHOOTTRANS 21.22 | holds |
| R15-DATA-017 | curl shareholding x15 + SUMAX quote | all 200 covered; promoters 85.94/69.67/82.78/63.66/56.05 | holds |
| R15-DATA-021 | curl patterns split_as_of | 20 patterns, no mismatched split_as_of | holds |
| R15-DATA-025 | curl corporate actions JONJUA/ELCIDIN/AMAL | bonus 7:24 and 5:40; ELCIDIN Rs25 NSE+BSE; AMAL dividend 2026-07-31 | holds |
| R15-DATA-029 | resolver + curl /earnings estimates + BDL news | RELIANCE.NS stays; INFY -> INFY.NS INR 19.636; BDL Flanigan hits 0 | holds |
| R15-DATA-034 | in-process dividend yield bound | 1.5 and 0.9 withheld (25% bound); 0.03 kept; no 2.0 bound | holds |
| R15-DATA-038 | curl SEC sections + insider | Business 10000 + Risk Factors 10000; insider 16 rows Apple and NVIDIA | holds |
| R15-DATA-042 | static: pinned test | PortfolioPanel.test.tsx:592 | ci_pinned |
| R15-DATA-046 | curl /macro worldbank IN/US vs api.worldbank.org | IN 2025=7.56666 == IND; US is USA | holds |
| R15-DATA-050 | curl events endpoints | all 200, 10/10/10/4 events | holds |
| R15-DATA-054 | curl results basis | consolidated / consolidated / unavailable 'no NSE/BSE filing states a basis' | holds |
| R15-DATA-058 | curl resolver SIFY | candidates end with SIFY US; bare SIFY -> US | holds |
| R15-DATA-064 | curl history + indicators | 273/273/260 bars; indicators 200 | holds |
| R15-DATA-068 | curl envelopes as_of | every envelope has as_of | holds |
| R15-DATA-072 | grep record_success + in-process trip (3x record_rate_limited) then stubbed get_history | 9 record_success sites; open True after trip; bars 3; open False after success | holds |
| R15-DATA-076 | curl DAL/FUSION ratios | DAL 0.452 bse; FUSION 0.0546 nse, Yahoo 128.1% not served | holds |
| R15-DATA-081 | curl crypto BTC/ETH | BTC 84695.99, ETH 200; ETH 365 bars ccxt:binance | holds |
| R15-DATA-085 | curl macro label | 'GDP (current US$) — IND' | holds |
| R15-DATA-089 | static: dead sync helpers grep + pin | no syncPositionToSidecar/sidecarPositionId/portfolioUrl; host-actions.test.ts:1210 | ci_pinned |
| R15-DATA-094 | curl /news/sources/status bogus newsapi key + log grep | unauthorized; header rss=ok;newsapi=unauthorized; key in body 0, in log 0 | holds |
| R15-DATA-099 | in-process FRED frequency map | BW->other, SA->other, W->weekly, Q->quarterly | holds |
| R15-DATA-103 | in-process quote row without change cols | change None/change_percent None; currency INR from row else USD | holds |
| R15-DATA-107 | in-process BSE lookup | MAZDOCK scrip 543237 ISIN INE249Z01020 group A; _BseRow | holds |
| R15-DATA-111 | canary_check drift sim + LIVE canary ddg/brave/mojeek | sim {ok:False,'parser drift'}, breaker 1; live ddg unreachable, brave 429, mojeek challenge, each reported honestly | holds |
| R15-DATA-115 | curl .BO / .NS history | .BO bse 255 bars; .NS nse_direct 33 bars | holds |
| R15-DOCS-005 | static: plugin count in BLUEPRINT | 20 registered; BLUEPRINT :238 '20 shipped'; ~38 count 0 | holds |
| R15-DOCS-010 | static: no amber + tests | no amber; NotesToolbar.test.tsx:117/128 | holds |
| R15-DOCS-016 | static: host action count vs catalog | doc 19 == 19 non-read-only host_action; AUTO_APPLIED_KINDS types/proposed-change.ts:38 | holds |
| R15-DOCS-020 | static: CURRENT_STATE hook name | :577 useDesktopNotificationBridge; page.tsx:55 | holds |
| R15-LEAD-001 | static pins + built binaries + /mcp/status | mcp==1.27.1 httpx==0.28.1 fastmcp==3.3.1; 3 binaries built; ready, toolCount 39 | holds |
| R15-LEAD-005 | curl quote timestamp vs Yahoo | 2026-10-02T20:00:01Z == Yahoo | holds |
| R15-LEAD-009 | curl INFY.NS vs INFY estimates | INR eps 19.636 vs USD 0.205; buy vs hold | holds |
| R15-LEAD-013 | in-process sp500 pack vs live Wikipedia | 503, snapshot 2026-09-24; 0 delisted; BXP/NVR/UDR present; live-not-in-pack 0 | holds |
| R15-LEAD-017 | curl patterns uniqueness | 49 patterns, 49 unique, 2026-08-20 once | holds |
| R15-LEAD-021 | static: StatusChrome error copy + test | StatusChrome.tsx:239 'Sidecar error — ${sidecarError}'; test :250-257 | ci_pinned |
| R15-LEAD-026 | curl history unknown symbol | ZZQXNOTASYM 200, bars 0, reason unknown_symbol | holds |
| R15-LEAD-031 | in-process LeakHold partial marker | shown '' held whole fragment 'Sure. {"name": "fundamentals", "arg' | holds |
| R15-LEAD-036 | in-process fenced-output strip | prose + 'returned no data' note; fence markers 0; no figure leak | holds |
| R15-LEAD-044 | curl screener sp500 IN/US, nifty50 US | sp500 503 USD rows both regions; nifty50 US 50 INR rows | holds |
| R15-LEAD-050 | in-process row_relevant GE + IT/ON/ALL controls | GE rows True; IT/ON/ALL False; mismatches 0 | holds |
| R15-LIFECYCLE-002 | static: pinned tests | workspace.test.ts:1063,1146 | ci_pinned |
| R15-LIFECYCLE-006 | live vy.py researcher openrouter nemotron free + o3-deep-research header | error step 'no longer available on OpenRouter; pick another in Settings > Research.' x5; answer not blank | holds |
| R15-LIFECYCLE-011 | static: terminated listener + test | app.ts:93; app.test.ts:28 | ci_pinned |
| R15-LIFECYCLE-015 | in-process runs store order + restart + 39 runs | newest-first True; get(oldest) found after restart and after 39 runs | holds |
| R15-LIFECYCLE-020 | count 'screener warm' in my sidecar log since boot | 0 lines (incl. after first /screener/run at log:568); start_warm_precompute only arms | holds |
| R15-LIFECYCLE-025 | sqlite legacy tool ids + GET/PUT | GET shows them; PUT 200 maps macro->macro_series; resolve_tool_ids same | holds |
| R15-LIFECYCLE-029 | static: pinned test | PanelHost.test.tsx:248; pluginsReady :124,194 | ci_pinned |
| R15-LIFECYCLE-033 | curl provider-health trip/reset routes | trip and reset 404; GET 200 yahoo open:false | holds |
| R15-LIFECYCLE-037 | static: clear + Rust test | lib.rs:394,440,789; test :941 | ci_pinned |
| R15-RELEASE-006 | static: staleness spec | no literal blocks; spec.stale :213,251; assertAllFresh ok | holds |
| R15-RELEASE-010 | curl both domains + BLUEPRINT | curl exit 6 both; BLUEPRINT 'planned, not yet resolved' | holds |
| R15-RESEARCH-003 | in-process iter loop marker + primary filing | marker 1 -> round-1 url, match True; primary in sources True | holds |
| R15-RESEARCH-008 | in-process _web_search keyless (live) + curl engines + rotation replica at production 6 s deadline | live: no rows, 'DuckDuckGo unreachable; Brave/Mojeek rate-limiting' in 11-18 s (< 25 s cap, no timeout); replica: hang ddg -> keyless:brave in 6.0 s; live rows not provable | blocked_env |
| R15-RESEARCH-012 | in-process results-filing floor KAYNES/CGPOWER/JONJUA | results filings lead floor rows for all three | holds |
| R15-RESEARCH-016 | in-process JONJUA floor -> ResearchBrief sources | floor rows 5; 7 sources incl. 5 BSE filings + vysted://price | holds |
| R15-RESEARCH-020 | in-process result limit | results 3 citations 3 | holds |
| R15-RESEARCH-025 | curl screener formula boolean arithmetic | three boolean-in-arithmetic forms rejected; and-formula ok | holds |
| R15-RESEARCH-029 | strip_model_bibliography on r3-ultra-kaynes markdown | 19 [n] literals -> 0; removed 9; no Merged Sources/References | holds |
| R15-RESEARCH-033 | in-process heavy research explorer crash | error step 'explorer angle 2 ... failed: RuntimeError: explorer boom' emitted; 2 angles synthesized | holds |
| R15-RESEARCH-037 | priority_note on unranked list | 'primary record ...: [2]; tier-1 press: [3]' | holds |
| R15-RESEARCH-041 | static: pinned test | host-actions.test.ts:589 | ci_pinned |
| R15-UI-003 | curl custom agent tool-ids + POST/PUT/DELETE | 56 == catalog 56; POST 201, PUT 200 keeps tools+openrouter, DELETE 204 | holds |
| R15-UI-007 | static: pinned test | ScreenerPresets.test.tsx:33 | ci_pinned |
| R15-UI-011 | static: AbortController + tests | BacktestPanel.test.tsx:261,499 | ci_pinned |
| R15-UI-015 | curl /macro/DGS10 fred keyless + test | 'FRED needs a free API key'; use-sidecar-retry.test.ts:26 | ci_pinned |
| R15-UI-019 | static: pinned tests | OnboardingBanner.test.tsx:44,65 | ci_pinned |
| R15-UI-024 | static: TaskList registration + tests | NotesPanel :33,130; NotesToolbar tests :84,95 | ci_pinned |
| R15-UI-028 | static: pinned tests | units.test.ts, OptionPricerPanel.test.tsx:70 | ci_pinned |
| R15-UI-032 | curl resolver names | Apple->AAPL first; Nvidia->NVDA; junk->0 | holds |
| R15-UI-036 | static: pinned test | PortfolioPanel.test.tsx:213 | ci_pinned |
| R15-UI-040 | static tests + GET /runs | delegate-runs.test.ts:209,243; GET /runs 200 | ci_pinned |
| R15-UI-049 | static: promoteKeyedProvider + test | llm-providers.ts:92, KeyEntryDialog.tsx:89 | ci_pinned |
| R15-UI-053 | curl 10 IMF catalog ids | 10/10 200 with observations | holds |
| R15-UI-057 | curl key probe x10 bogus keys | all 'invalid <Provider> rejected this key.'; KeyEntryDialog.tsx:68 trim() | holds |
| R15-UI-062 | static: backtestDateDefaults + test | no literal; test :156 | ci_pinned |
| R15-UI-066 | static: EmptyState role + test | EmptyState.test.tsx:55; role={isError :56 | ci_pinned |
| R15-UI-071 | static: jsx-a11y + vitest-axe config | label-has-associated-control enforced; SettingsPanel axe test (axe half ci_pinned) | holds |
| R15-UI-075 | static: globals.css font features | :114-117 tnum/zero/calt 0 | holds |
| R15-UI-079 | static: FORMULA_TRIGGER + tests | csv.ts:13; csv.test.ts:31,42 | ci_pinned |
| R15-UI-083 | static: BriefPanel save gating + gui-round evidence | Save md/pdf/png gated on bodySettled; certified in gui-round DRIVE/VERIFY (no rc2 row) | needs_gui |
| R15-UI-089 | curl /news/sources/status bogus vs none + newsapi.org direct; grep | bogus -> unauthorized (direct 401); none -> absent; probeNewsApiKeyOrThrow src/store/marketplace.ts:39,219 | holds |
| R15-UI-094 | _build_messages + _parse_output + render grep | parser fills summary/business/storyline/bull/bear/risks; EquityOverviewPanel.tsx:413-420 blocks | holds |

Side observation (not a regression; filed medium for 0.9.1 in findings/battery-2.json): same minute, the product's Brave engine (impersonated_fetch) gets HTTP 429 while a plain-UA curl from the same host gets a 20-result Brave page (raw/R15-RESEARCH-008.txt addendum), so keyless web search returns zero rows on this network.

COVERAGE: 149/149 ids raw; no raw: none
