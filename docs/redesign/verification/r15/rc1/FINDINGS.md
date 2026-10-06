# RC1 Findings — merged

Merged from all 29 `docs/redesign/verification/r15/rc1/findings/*.json` files of gate round 2 (`findings/round-1/` excluded) into `FINDINGS.json` (126 findings total), sorted by kind then severity. No new judgement — every row below is copied verbatim from its source file.

| Key | Kind | Severity | Register id | Title | Source file |
|---|---|---|---|---|---|
| rc1-datapack:1 | regression | critical | R15-DATA-008 | SIFY revenue_ttm/net_income_ttm still served as INR-scale numbers under currency:"USD" (partial fix) | rc1-datapack.json |
| rc1-verifier:6 | regression | critical | R15-DATA-002 | The watchlist path still drops the picked listing's region: pickCandidate(symbol) stores a bare symbol, and SymbolEntry has no region field (code-level; GUI ... | rc1-verifier.json |
| rc1-vshard-7:8 | regression | critical | R15-DATA-002 | The picked listing's region is dropped on the watchlist path: picking 'AMAL (US)' from the watchlist autocomplete stores the bare 'AMAL', so the watchlist qu... | rc1-vshard-7.json |
| rc1-verifier:4 | regression | high | R15-AGENT-019 | The intent gate still strips portfolio write tools from everyday question-shaped delete/update asks. The literal register phrasings pass, and fresh phrasings... | rc1-verifier.json |
| rc1-verifier:5 | regression | high | R15-AGENT-093 | Schema-gate coercion is not a class fix. A nested numeric string ('185.5' in points[].price, '3' in instruments[].tenor) and '5.0' for an integer are still r... | rc1-verifier.json |
| rc1-vshard-0:1 | regression | high | R15-DATA-002 | NOT CERTIFIED: watchlist/screener/agent overview paths still re-query the bare symbol; a picked NASDAQ:AMAL shows Amal Ltd (INR) in an IN session | rc1-vshard-0.json |
| rc1-vshard-0:3 | regression | high | R15-CODE-FRONTEND-002 | NOT CERTIFIED: a chat-tab click (or '+') inside an open research space drops the research transcript, then leaving the space saves the chat tab's conversatio... | rc1-vshard-0.json |
| rc1-vshard-4:1 | regression | high | R15-RESEARCH-028 | FAST research drops web_search reason on the ok path: a degraded SearXNG still reports keyless-fallback with web_reason None, so the brief shows the 'set up ... | rc1-vshard-4.json |
| rc1-vshard-7:5 | regression | high | R15-AGENT-019 | Question-shaped portfolio write asks without a listed cue word still classify as read and lose every write tool: 'Could you drop WIPRO from my portfolio?', '... | rc1-vshard-7.json |
| rc1-vshard-7:7 | regression | high | R15-UI-090 | Freshness is still not the instrument's exchange calendar for non-IN listings: BHP.AX, 7203.T, 0700.HK, ^N225 and VOD.L are dated on the US calendar, so they... | rc1-vshard-7.json |
| rc1-vshard-8:1 | regression | high | R15-RESEARCH-007 | Blog/newsletter platforms outside the vendored PSL and the 10-host denylist still rank an ir./investors. host TIER_PRIMARY and outrank Reuters (typepad, live... | rc1-vshard-8.json |
| rc1-vshard-8:2 | regression | high | R15-AGENT-090 | _guard_ratio_claims keeps a fabricated fractional/decimal or 'a dozen'/'half' ADR ratio unchanged, even for SIFY when the tool result carries the true ratio 6 | rc1-vshard-8.json |
| rc1-datapack:2 | regression | medium | R15-DATA-058 | Sify (ADR) name-search: SIFY now included but still ranked last despite the highest score | rc1-datapack.json |
| rc1-verifier:10 | regression | medium | R15-DATA-059 | The US master still has no ISIN/CUSIP: SIFY and ONC resolve with isin null (fix_shape: 'add ISIN/CUSIP to the US master') | rc1-verifier.json |
| rc1-verifier:11 | regression | medium | R15-AGENT-053 | News symbol chips are still plain <span> elements inside the article <a>, so a click opens the article and never loads the symbol (fix_shape: 'make rendered ... | rc1-verifier.json |
| rc1-verifier:12 | regression | medium | R15-RESEARCH-015 | Independence still counts hosts, not registrable domains: www.nseindia.com and nsearchives.nseindia.com count as two domains, so one domain reached by both l... | rc1-verifier.json |
| rc1-verifier:7 | regression | medium | R15-DATA-113 | Estimate revenue is labelled by financialCurrency even where Yahoo's estimate is in the trading currency: INFY revenue_estimate_mean 491,654,926,200 is serve... | rc1-verifier.json |
| rc1-verifier:8 | regression | medium | R15-LEAD-028 | BSE scrip-code addressing still 404s on /fundamentals, the entry's own example included | rc1-verifier.json |
| rc1-verifier:9 | regression | medium | R15-DATA-064 | 30m history with an explicit range of 3mo or 1y returns [] with reason in_eod_only for RELIANCE.NS, though yfinance serves its 30m bars at the default range.... | rc1-verifier.json |
| rc1-vshard-0:2 | regression | medium | R15-RESEARCH-015 | NOT CERTIFIED: cross-check counts two hosts of ONE registrable domain as independent channels (nseindia.com + nsearchives.nseindia.com -> AGREE) | rc1-vshard-0.json |
| rc1-vshard-0:4 | regression | medium | R15-AGENT-045 | NOT CERTIFIED: compare_symbols ['COCHINSHIP','MAZAGONDOCK'] still does not compare MAZDOCK (fix_shape's own test) | rc1-vshard-0.json |
| rc1-vshard-1:3 | regression | medium | R15-UI-090 | UI-090 not certified: non-US, non-IN listings (BHP.AX, VOD.L) still read 'live' after their own exchange closes, because instrument_region defaults everythin... | rc1-vshard-1.json |
| rc1-vshard-2:1 | regression | medium | R15-DATA-064 | 30m/intraday lookback never clamped to Yahoo's 60-day cap: explicit range or node-editor default period 1y gives an empty series, and IN is labelled in_eod_only | rc1-vshard-2.json |
| rc1-vshard-2:2 | regression | medium | R15-DATA-066 | nse_direct throttle still sleeps on executor threads: a cold IN batch stalls unrelated to_thread routes about 19x | rc1-vshard-2.json |
| rc1-vshard-2:3 | regression | medium | R15-AGENT-053 | News symbol chips are still dead text inside the article link; news snapshot carries no headlines; bond/yield/option-chain panels publish nothing | rc1-vshard-2.json |
| rc1-vshard-4:2 | regression | medium | R15-DATA-061 | Yahoo throttle still mislabelled: earnings estimates return 502 provider_error, and statement routes return 200 empty with provider_health.record_success | rc1-vshard-4.json |
| rc1-vshard-4:3 | regression | medium | R15-DATA-066 | NSE throttle wait still sleeps inside the to_thread executor: a cold 20-name batch stalls cached single quotes (0.002 s -> 5.5 s, one 30 s timeout) and /hist... | rc1-vshard-4.json |
| rc1-vshard-4:4 | regression | medium | R15-DATA-055 | Research brief still labels a September-2026 listing (MPIMANIPAL.NS, listed 2026-09-17) as '52-week price change (Yahoo)' / 'trailing 52 weeks' and 'Below 52... | rc1-vshard-4.json |
| rc1-vshard-5:1 | regression | medium | R15-DATA-055 | SMR.BO (BSE SME, first_trade 2026-06-08, the entry's own DAT-S2-8 pin) returns listing_date null + fifty_two_week_change -0.068, so the overview shows a 52w ... | rc1-vshard-5.json |
| rc1-vshard-5:2 | regression | medium | R15-DATA-061 | An unknown .NS/.BO symbol at an intraday timeframe is told 'India is EOD only' (reason in_eod_only) instead of unknown symbol; history.py treats any .NS/.BO ... | rc1-vshard-5.json |
| rc1-vshard-5:3 | regression | medium | R15-LEAD-026 | A suffixed unknown symbol (QQZZFAKE.NS / .BO) at 1d returns reason null instead of unknown_symbol; _is_unknown_symbol exempts every suffixed symbol (document... | rc1-vshard-5.json |
| rc1-vshard-5:5 | regression | medium | R15-CODE-PLATFORM-013 | resetToDefaultLayout() calls setEnabledMap({}), wiping every plugin:<id> flag, so a plugin disabled in plugins.db reappears in enabledModules/enabledCommands... | rc1-vshard-5.json |
| rc1-vshard-5:6 | regression | medium | R15-CODE-PLATFORM-017 | The code-node inspector's mathjs syntax check + live preview still disagree with the canonical server evaluator (nested ternary 2 vs parse error, round(1.005... | rc1-vshard-5.json |
| rc1-vshard-6:1 | regression | medium | R15-UI-085 | A readable text label still renders in charcoal-600 (#484848): dockview's hidden-panel tab titles in an inactive group, 2.08:1 on the #101010 tab strip, unde... | rc1-vshard-6.json |
| rc1-vshard-6:2 | regression | medium | R15-DATA-071 | The registry fall-through works, but when no lane is complete the partial BSE series is served with partial=true and nothing reads the flag. ChartPanel and t... | rc1-vshard-6.json |
| rc1-vshard-7:1 | regression | medium | R15-DATA-059 | US instruments still carry no ISIN: /resolve?q=ONC and q=SIFY return isin null; the fix_shape step 'add ISIN/CUSIP to the US master' was never done (us_instr... | rc1-vshard-7.json |
| rc1-vshard-7:2 | regression | medium | R15-LEAD-028 | BSE scrip-code addressing still 404s on the fundamentals data route: /fundamentals/506597.BO and /fundamentals/532540.BO 404 while /fundamentals/AMAL.BO and ... | rc1-vshard-7.json |
| rc1-vshard-7:3 | regression | medium | R15-DATA-112 | A row with no fundamentals currency and a null market_cap still displaces a valued row: the DATA-043 round-robin top-K cut treats the missing currency as its... | rc1-vshard-7.json |
| rc1-vshard-7:4 | regression | medium | R15-DATA-113 | Foreign-reporter revenue estimate still mislabelled: INFY's INR-sized revenue_estimate_mean 491,180,745,790 is served with revenue_currency USD (Yahoo financ... | rc1-vshard-7.json |
| rc1-vshard-7:6 | regression | medium | R15-AGENT-093 | The schema gate coerces only TOP-LEVEL numeric strings: a nested numeric param sent as a string (add_chart_drawing.points[].price '185.5', yield_curve_value.... | rc1-vshard-7.json |
| rc1-vshard-7:9 | regression | medium | R15-CODE-PLATFORM-013 | Settings > Reset layout wipes the runtime-derived plugin:<id> flags (setEnabledMap({})), so a plugin disabled via the marketplace gets its panels/commands ba... | rc1-vshard-7.json |
| rc1-drive-onboarding-stranger:1 | regression | low | R15-LEAD-030 | Reclassification note (not a new finding): a fresh instance of the already-adjudicated, blocked_tier4 R15-LEAD-030 class ('local model narrates a fabricated ... | onboarding-stranger.json |
| rc1-drive-portfolio-notes:2 | regression | low | R15-UI-035 | P4/P4b delete-control harness replay needed a rewrite for a new ConfirmButton arm/confirm gate, not a regression in the fix itself | rc1-drive-portfolio-notes.json |
| rc1-vshard-1:10 | regression | low | R15-CODE-AGENT-020 | CODE-AGENT-020 still reproduces (register status open, never certified): get_provider drops base_url for gemini and groq | rc1-vshard-1.json |
| rc1-vshard-1:4 | regression | low | R15-AGENT-010 | AGENT-010 fix_shape part unfixed: yf.Search still has no explicit timeout (yfinance default 30 s) | rc1-vshard-1.json |
| rc1-vshard-1:9 | regression | low | R15-CODE-AGENT-018 | CODE-AGENT-018 still reproduces (register status open, never certified): _STAGEABLE_PLAN_ACTIONS and _READ_SAFE_PANEL_ACTIONS identical with no stated relati... | rc1-vshard-1.json |
| rc1-vshard-5:4 | regression | low | R15-DOCS-018 | CURRENT_STATE.md:337-340 says fundamentals still hit yfinance first, but provider_registry ranks openbb-mcp 10 ahead of yfinance 50 for fundamentals/statemen... | rc1-vshard-5.json |
| rc1-verifier:17 | plausible_regression | high | R15-AGENT-010 | The off-loop fix holds per shard-8, but the fix_shape clause 'pass an explicit yf.Search timeout' is unmet: yf.Search(query, max_results=5, news_count=0) has... | rc1-verifier.json |
| rc1-verifier:16 | plausible_regression | medium | R15-CODE-PLATFORM-013 | resetToDefaultLayout still calls useModulesStore.setEnabledMap({}) (workspace.ts:184), wiping the plugin:* flags the marketplace lifecycle derives. Code-leve... | rc1-verifier.json |
| rc1-drive-portfolio-notes:1 | new_defect | high |  | Portfolio quote auto-refresh has no overlap guard or request cancellation, causing an unbounded in-flight backlog once any symbol resolves slowly | rc1-drive-portfolio-notes.json |
| rc1-scenarios:1 | new_defect | high |  | price_data's silent 90-bar cap masquerades as a '52-week' window; the model states an internally-impossible 52-week-low/current-price relationship as fact | rc1-scenarios.json |
| rc1-verifier:1 | new_defect | high |  | BSE shareholding index is fetched with plain httpx and BSE answers 403, so /disclosures/shareholding returns 502 for every BSE-only name (AMAL, ELCIDIN, JUMB... | rc1-verifier.json |
| rc1-verifier:2 | new_defect | high |  | The MCP tools list_workspaces and get_workspace call GET /workspaces and /workspaces/{id}, but the router prefix is /workspace. Every call 404s and raise_for... | rc1-verifier.json |
| rc1-vshard-1:1 | new_defect | high |  | BSE shareholding-pattern index fetched with plain httpx gets 403 Access Denied live: no FII/DII split for any name, BSE-only shareholding provider_error | rc1-vshard-1.json |
| rc1-vshard-5:9 | new_defect | high | R15-RESEARCH-028 | Research query 'KPIT Technologies — latest quarterly results' is resolved to BSOFT (Birlasoft, former_name KPIT) at score 1.00 with no disambiguation althoug... | rc1-vshard-5.json |
| rc1-drive-research-briefs:2 | new_defect | medium |  | Citation-integrity net only recognises a bare '[n]' marker; a bracketed group '[2, 3]' or a prose pseudo-citation '[New findings]' ships as literal, unresolv... | rc1-drive-research-briefs.json |
| rc1-fix-r1-recheck:1 | new_defect | medium |  | Citation grammar fix covers only ',' / ';' groups and a pseudo-label NOT followed by '[': range groups '[2-4]' / '[2–4]' and '[New findings][2]' still ship a... | rc1-fix-r1-recheck.json |
| rc1-fix-r1-recheck:2 | new_defect | medium |  | Pseudo-citation rule deletes (backend) or flags as a broken citation (frontend) any letter-led bracket token, including the metric basis qualifiers the produ... | rc1-fix-r1-recheck.json |
| rc1-fix-r2-recheck:1 | new_defect | medium |  | rc1-drive-research-briefs:2 not certified at 81fbfe91: bracketed pseudo-citations outside the hard-coded prompt-label family, and groups that mix a label wit... | rc1-fix-r2-recheck.json |
| rc1-verifier:3 | new_defect | medium |  | Fix loop not closed: rc1-drive-research-briefs:2 reproduces at 4c6dfe8c. The citation-integrity net matches only a bare [n], so '[2, 3]' groups and '[New fin... | rc1-verifier.json |
| rc1-vshard-0:5 | new_defect | medium | R15-RESEARCH-003 | Deep brief cites fundamentals-only figures (P/E, market cap, EPS, dividend yield) to exchange result PDFs instead of vysted://fundamentals | rc1-vshard-0.json |
| rc1-vshard-0:6 | new_defect | medium | R15-AGENT-008 | A 3-result round on a multi-cue prompt overflows the ollama num_ctx by estimate; _fit_to_window never trims the latest round and only debug-logs | rc1-vshard-0.json |
| rc1-vshard-1:2 | new_defect | medium |  | INFY.NS earnings estimate labels an INR revenue estimate (491,180,745,790 = Rs 49,118 cr) as revenue_currency USD, so the grid renders about $491B | rc1-vshard-1.json |
| rc1-vshard-1:5 | new_defect | medium |  | Research news-lane sources drop published_at and carry a feed label as domain ('Yahoo! Finance: DIXON News'); filing-floor rows carry the date only inside th... | rc1-vshard-1.json |
| rc1-vshard-3:1 | new_defect | medium |  | MCP list_workspaces and get_workspace always fail: they call GET /workspaces (plural) but the router is mounted at /workspace, so both published MCP tools 40... | rc1-vshard-3.json |
| rc1-vshard-3:2 | new_defect | medium | R15-LIFECYCLE-023 | The agent dock (ChatSidebar) has no error boundary: a render throw in chat still unmounts the whole cockpit, portfolio panels included, even though each dock... | rc1-vshard-3.json |
| rc1-vshard-4:5 | new_defect | medium | R15-DATA-032 | INFY.NS revenue estimate is INR-sized (491,180,745,790) but labelled revenue_currency USD (from financialCurrency); Yahoo's annual totalRevenue is 20.3B USD | rc1-vshard-4.json |
| rc1-vshard-4:6 | new_defect | medium | R15-DATA-048 | Derived ROCE and ROE diverge from screener.in (KPITTECH ROCE 21.3% vs 26.3%, ROE 16.5% vs 20.9%): period-end capital, no average, no witness | rc1-vshard-4.json |
| rc1-vshard-5:7 | new_defect | medium | R15-AGENT-083 | External MCP save_workflow persists and overwrites a user's saved workflow with no confirmation, while spec.md:329/:783 call the external MCP surface read-on... | rc1-vshard-5.json |
| rc1-vshard-6:3 | new_defect | medium | R15-UI-091 | Indicator params are silently ignored except ema:N and vwap:week\\|session. rsi:7 computes RSI(14), sma:50 computes SMA(20), and ema:0/ema:abc compute EMA(20)... | rc1-vshard-6.json |
| rc1-vshard-7:10 | new_defect | medium |  | Every 10-Q opens as an empty filing viewer: sec-edgar-mcp get_filing_sections returns only {has_financials: true} for a 10-Q, and get_filing serves 200 with ... | rc1-vshard-7.json |
| rc1-vshard-7:11 | new_defect | medium |  | _parse_verdict's marker-scan fallback reads a negated reason as AGREE when the reply has no verdict word: 'Not verified - no source confirms the figure', 'I ... | rc1-vshard-7.json |
| rc1-vshard-7:12 | new_defect | medium |  | fetch_latest_fo still returns None (502) when an older, uncached day's probe fails transiently even though an older good day sits in cache, and re-probes tha... | rc1-vshard-7.json |
| rc1-vshard-8:3 | new_defect | medium | R15-LEAD-033 | The history trailer's '[failed: …]' line still rides the assistant content to the provider; only '[tool steps:' lines are stripped | rc1-vshard-8.json |
| rc1-vshard-8:6 | new_defect | medium | R15-LEAD-030 | With an ok fundamentals(MSFT) call in the turn, llama3.1:8b streams an invented 'previous answer' (MSFT P/E 27.42, market cap ₹1,23,011 cr, EV/EBITDA 14.17) ... | rc1-vshard-8.json |
| rc1-gate8:1 | new_defect | low |  | The review card and the applied label price an agent's portfolio write in the REGION currency, not the listing's: a US holding reads 'Add 10 AAPL @ ₹0 to the... | rc1-gate8.json |
| rc1-gate8:2 | new_defect | low |  | Portfolio CSV export writes Market value, P&L and P&L % as raw binary floats (805.3499999999999, 11.454545454545455) while Weight % is rounded to 2 dp | rc1-gate8.json |
| rc1-gate8:3 | new_defect | low |  | 'Buy 10 shares of AAPL at market' under AUTO: llama3.1:8b emits portfolio_add_position with an invented cost_basis 0 (the runtime accepts it though the tool ... | rc1-gate8.json |
| rc1-vshard-0:7 | new_defect | low | R15-AGENT-082 | Chat footer pairs last-round tokens with whole-turn spend | rc1-vshard-0.json |
| rc1-vshard-0:8 | new_defect | low | R15-DATA-007 | 10-Q and 8-K filing detail returns 200 with zero sections | rc1-vshard-0.json |
| rc1-vshard-0:9 | new_defect | low | R15-DATA-009 | Backtest skips a buy sized exactly to available cash (float rounding) | rc1-vshard-0.json |
| rc1-vshard-1:6 | new_defect | low |  | web_search category (news/financial) never reaches any backend: dispatch passes 'category', SearXNG reads 'categories', other backends ignore it | rc1-vshard-1.json |
| rc1-vshard-1:7 | new_defect | low |  | DAL fundamentals withhold the 52-week range but still ship 52-week high/low dates (2025-09-25, a forward-filled bar) and fifty_two_week_change 0.0 with statu... | rc1-vshard-1.json |
| rc1-vshard-1:8 | new_defect | low |  | Sibling stream consumers still surface raw FastAPI error bodies: workflow runWorkflow throws the raw text, screener stream interpolates a 422 detail array | rc1-vshard-1.json |
| rc1-vshard-2:4 | new_defect | low | R15-CODE-PLATFORM-018 | Quant workflow nodes reject the engine's generic per-node timeout_seconds (extra_forbidden) | rc1-vshard-2.json |
| rc1-vshard-2:5 | new_defect | low | R15-CODE-PLATFORM-020 | GET /workflow/saved/{id} and POST /schedules return 500 for a malformed saved row (version mismatch returns 409) | rc1-vshard-2.json |
| rc1-vshard-2:6 | new_defect | low | R15-AGENT-052 | Screener and Earnings still publish under literal bus keys that differ from their dockview ids | rc1-vshard-2.json |
| rc1-vshard-2:7 | new_defect | low | R15-DATA-017 | Generic-token-only legal-name queries still return unrelated fuzzy 'X Engineering Limited' candidates at 0.80-0.88 when the live rung finds nothing | rc1-vshard-2.json |
| rc1-vshard-2:8 | new_defect | low | R15-AGENT-049 | Register marks AGENT-049 blocked_tier4 but the candidate implements and pins the fix | rc1-vshard-2.json |
| rc1-vshard-2:9 | new_defect | low | R15-CODE-PLATFORM-022 | Stale vi.mock of @/modules/portfolio/api with functions that module does not export | rc1-vshard-2.json |
| rc1-vshard-4:10 | new_defect | low | R15-DATA-061 | Unknown macro provider returns 502 provider_error 'Retry' instead of a 4xx client error | rc1-vshard-4.json |
| rc1-vshard-4:7 | new_defect | low | R15-DATA-114 | fetch_latest_fo stops walking on an older-day transport failure: today 404, D-1 failed, D-2 cached -> returns None instead of the cached D-2 | rc1-vshard-4.json |
| rc1-vshard-4:8 | new_defect | low | R15-DATA-054 | listing_date field_meta provider is stamped 'yfinance' while the value comes from the NSE master (symbol_resolver.nse_listing_date) | rc1-vshard-4.json |
| rc1-vshard-4:9 | new_defect | low | R15-UI-027 | Keybinding recorder uses event.key: on macOS Option+1 records 'alt+¡', conflicts() misses the clash with alt+1 (agent.mode.agent), so the remap silently neve... | rc1-vshard-4.json |
| rc1-vshard-5:10 | new_defect | low | R15-RESEARCH-028 | web.detail handed to the model says 'add an Exa key / local SearXNG' while SearXNG is running (degraded) | rc1-vshard-5.json |
| rc1-vshard-5:11 | new_defect | low | R15-CODE-RESEARCH-004 | test_search_exports.py rglob('*.py') from sidecar/ also scans .venv (24,960 files) so a site-packages hit can count as the second-file caller; base.py:109 do... | rc1-vshard-5.json |
| rc1-vshard-5:12 | new_defect | low | R15-DOCS-004 | CLAUDE.md Frontend gotcha + Visual verification describe a zinc + cool-indigo palette, but tokens.css/globals.css/VYSTED_DESIGN.md at the candidate are the p... | rc1-vshard-5.json |
| rc1-vshard-5:8 | new_defect | low | R15-DATA-068 | Earnings drill-down 'As of' chip renders the client fetchedAt, not the server as_of, so a 24h-cached surprises envelope reads as current | rc1-vshard-5.json |
| rc1-vshard-6:4 | new_defect | low | R15-DATA-079 | option_chain answers a non-date expiry with the raw Python error "Invalid isoformat string: 'nearest'" and not the listed expiries or 'omit for the nearest'.... | rc1-vshard-6.json |
| rc1-vshard-7:13 | new_defect | low |  | humanize's credit rule over-matches rate limits whose body mentions billing/quota: a Groq TPM 429 ('Please try again in 5.6s ... settings/billing') and a Gem... | rc1-vshard-7.json |
| rc1-vshard-8:4 | new_defect | low | R15-CODE-DATA-023 | routers/screener.py:192 get_universe docstring still quotes the dropdown as 'S&P 500 (100 tickers)'; the live universe is 503 | rc1-vshard-8.json |
| rc1-vshard-8:5 | new_defect | low | R15-AGENT-090 | When the ratio guard fires, the part of the sentence that was already released streams, then the replacement is spliced mid-sentence ('a standard Y-Share has... | rc1-vshard-8.json |
| rc1-verifier:15 | known_limitation | low | R15-LEAD-030 | Local lane (llama3.1:8b) note: ollama-sk4-sify-v2 states '6 ordinary shares' right after saying the ratio is unavailable, and converts ₹4,651 cr to about $57... | rc1-verifier.json |
| rc1-verifier:13 | harness_gap | n/a |  | Battery coverage incomplete at the candidate: 76 fixed ids have no raw battery file, and 84 more have raw output only from before 4c6dfe8c was committed (202... | rc1-verifier.json |
| rc1-verifier:14 | harness_gap | n/a |  | Agent scenarios and data packs do not carry the candidate. All 20 OpenRouter scenario transcripts and 7 of the 13 llama transcripts date from 25 Sep, before ... | rc1-verifier.json |
| rc1-verifier:18 | concurrence | n/a | R15-CODE-PLATFORM-001 | CONCUR R15-CODE-PLATFORM-001 (removed_with_feature) | rc1-verifier.json |
| rc1-verifier:19 | concurrence | n/a | R15-UI-042 | CONCUR R15-UI-042 (removed_with_feature) | rc1-verifier.json |
| rc1-verifier:20 | concurrence | n/a | R15-UI-043 | CONCUR R15-UI-043 (removed_with_feature) | rc1-verifier.json |
| rc1-verifier:21 | concurrence | n/a | R15-AGENT-083 | CONCUR R15-AGENT-083 (not_a_defect) | rc1-verifier.json |
| rc1-verifier:22 | concurrence | n/a | R15-DATA-080 | CONCUR R15-DATA-080 (not_a_defect) | rc1-verifier.json |
| rc1-verifier:23 | concurrence | n/a | R15-UI-041 | CONCUR R15-UI-041 (not_a_defect) | rc1-verifier.json |
| rc1-verifier:24 | concurrence | n/a | R15-UI-047 | CONCUR R15-UI-047 (not_a_defect) | rc1-verifier.json |
| rc1-verifier:25 | concurrence | n/a | R15-UI-059 | CONCUR R15-UI-059 (not_a_defect) | rc1-verifier.json |
| rc1-verifier:26 | concurrence | n/a | rc1-scenarios:1 | CONCUR rc1-scenarios:1 (rejected (not a regression)) | rc1-verifier.json |
| rc1-verifier:27 | concurrence | n/a | rc1-datapack:1 | CONCUR rc1-datapack:1 (rejected (not a regression of R15-DATA-008)) | rc1-verifier.json |
| rc1-verifier:28 | concurrence | n/a | rc1-datapack:2 | CONCUR rc1-datapack:2 (rejected (not a regression of R15-DATA-058)) | rc1-verifier.json |
| rc1-verifier:29 | concurrence | n/a | set-67 ratio escape | CONCUR set-67 ratio escape (rejected (known-limitation class)) | rc1-verifier.json |
| rc1-verifier:30 | concurrence | n/a | set-28 | CONCUR set-28 (rejected (harness, environment)) | rc1-verifier.json |
| rc1-fix-r1-triage:1 | register_note | medium | R15-LEAD-037 | New instance of the value-only-grounding class (DECISIONS 4.11): llama3.1:8b labels a historical price_data bar low (ELCIDIN 2026-07-31 low 110,095) as the 5... | rc1-fix-r1-triage.json |
| rc1-fix-r1-triage:3 | register_note | low | R15-LEAD-030 | New instance of the hallucinated-tool-result-citation class (DECISIONS 4.9): llama3.1:8b states Zomato price/high/low/% figures with only get_terminal_state ... | rc1-fix-r1-triage.json |
|  | register_note | low |  | New instance of the local-model untraced-claim pattern surfaced via the AGENT-090 ratio guard, on a tool path the batch-16 certification did not exercise | rc1-battery-5.json |
| rc1-battery-3:1 | environment | medium | R15-DATA-056 | BSE shareholding SHP index blocked (403 Akamai) from this dev IP, pre-existing at base | rc1-battery-3.json |
| rc1-datapack:3 | environment | low | R15-DATA-003 | BSE shareholding index returned 403 Forbidden for every BSE-only symbol this run, not just AMAL/SMR | rc1-datapack.json |
| rc1-drive-failure-inducer:1 | environment | low |  | Shared SearXNG's DDG/Brave/Startpage engines are currently CAPTCHA'd/rate-limited (upstream, not candidate code) | rc1-drive-failure-inducer.json |
| rc1-fix-r1-triage:2 | environment | n/a |  | Battery coverage gap: set-28 (batch-7/W4-research-funnel) was run against 12 nonexistent ids; the 12 real ids in battery/INDEX.md:81 were never re-verified t... | rc1-fix-r1-triage.json |
|  | environment | n/a |  | batch-7/W4-research-funnel register/task data mismatch: 12 assigned ids do not exist | rc1-battery-5.json |

## Counts

By kind: regression=47, plausible_regression=2, new_defect=53, known_limitation=1, harness_gap=2, concurrence=13, register_note=3, environment=5

By severity: critical=3, high=16, medium=52, low=38, n/a=17
