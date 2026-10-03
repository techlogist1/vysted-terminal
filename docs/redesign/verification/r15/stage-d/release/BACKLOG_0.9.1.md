# 0.9.1 backlog (draft at `4da7fc91`)

## 1. What this is

The filed open mediums and lows at 0.9.0, the Tier-4 bucket, the awaiting-manual-check entries, and the two features that left the 0.9.0 release line (BL-03, BL-18). Register state: `docs/redesign/verification/vysted-r15-register.json` at `4da7fc91` (745 entries). Open: 31 medium, 58 low (<<OPEN_COUNTS>>). The final adversarial pass may add mediums and lows: <<FINAL_PASS_SUMMARY>>.

R15-LEAD-116 (high) is status **fixed** at `4da7fc91` (certified at `d3509715`), so it is not a 0.9.1 item.

## 2. Open mediums and lows at 0.9.0 - first 0.9.1 batch

| ID | Severity | Title | Fix shape |
| --- | --- | --- | --- |
| R15-AGENT-027 | medium | humanize() classifies by HTTP status alone, so users get a next step that cannot work: OpenAI no-credit 429 and free-model shared-pool 429 say 'wait a minute', invalid Gemini/xAI... | A data table keyed (provider?, status, body-substring) -> (code, message, action) with rows for 429+credit/quota, 429+:free/shared_pool, 400+api key invalid -> auth, 400+not a valid model -> model_not_found, 400/413 context ->... |
| R15-CODE-PLATFORM-072 | medium | Data-source description is hand-maintained in marketplace.ts, disconnected from provider_registry and the plugin contract, and has already drifted (yfinance entry lists 3 keys vs... | Make provider_registry the one source: expose its declarations (serves, region, asset classes, plus a new optional credentials field) over a GET route and derive the data-provider marketplace rows from it, deleting the hand-written... |
| R15-LEAD-060 | medium | Verifier verdict text wrapped in underscore emphasis (_UNVERIFIED_ / __UNVERIFIED__) parses as AGREE | to be planned |
| R15-LEAD-061 | medium | strip_model_bibliography misses common bibliography heading variants, so a model-written source list survives beside the verified one | to be planned |
| R15-LEAD-062 | medium | A Gemini free-tier per-minute 429 (RESOURCE_EXHAUSTED ... retry in Ns) is shown as "out of credit or quota. Add credit or check your plan" | to be planned |
| R15-LEAD-063 | medium | historyForSend drops the oldest turns once the thread passes 60k chars with no notice to the user or the model | to be planned |
| R15-LEAD-064 | medium | 20-F ownership lane returns not_applicable with 0 holders for ADRs whose 20-F has a holders table (IBN, HDB) | to be planned |
| R15-LEAD-065 | medium | FAST research web-only branch (no instrument resolves) awaits _web_round without a time box; only the resolved branch uses asyncio.wait_for | to be planned |
| R15-LEAD-066 | medium | write_screener_filters with only the documented OR/nested group tree is rejected: schema requires criteria | to be planned |
| R15-LEAD-067 | medium | Macro search failure renders as an empty "No matching series": the store catches every error and stores []; keyless FRED search is a 502 with an actionable message | to be planned |
| R15-LEAD-068 | medium | Settings privacy copy over-promises: "Nothing leaves this machine except calls you make to providers you configure" while keyless lanes (Yahoo, NSE/BSE, DDG) call out without... | to be planned |
| R15-LEAD-069 | medium | Screener formula validate accepts a boolean operand in a comparison ("roe > (pe_ratio < 15)", "(pe_ratio > 3) > 0.5") and coerces it | to be planned |
| R15-LEAD-070 | medium | Analyst ratings swallow a Yahoo rate-limit into an empty 200 list that reads as no coverage | to be planned |
| R15-LEAD-071 | medium | A Yahoo rate-limit on earnings history is swallowed as an empty history and cached for 24 h | to be planned |
| R15-LEAD-072 | medium | Heavy/ULTRA brief stopped by its spend ceiling publishes note=None, and the cross-check keeps spending after the breach | to be planned |
| R15-LEAD-073 | medium | The latest round's tool results are never elided by _fit_to_window, so a multi-result round leaves the answer below the 1/8 reserve | to be planned |
| R15-LEAD-074 | medium | Scheduled and MCP-run workflows run with no event sink: action.notify_desktop reports notified:true but nothing is shown | to be planned |
| R15-LEAD-075 | medium | Editing a custom agent silently clears its default_model on save (customSpecToSummary sets defaultModel: null) | to be planned |
| R15-LEAD-076 | medium | A partially throttled screen shows "No rows matched - loosen a threshold / Reset filters" although most symbols were never evaluated | to be planned |
| R15-LEAD-077 | medium | A focused SEC Filings panel publishes identifier, not symbol, so the agent context names the wrong symbol | to be planned |
| R15-LEAD-078 | medium | Flaky test_research_fast::test_fast_web_round_runs_alongside_a_time_boxed_fan_out: an unstubbed earnings-quality leg makes it timing-dependent | to be planned |
| R15-LEAD-079 | medium | ReasoningSplitter releases a held reasoning echo in full when an answer follows it (provisional, shard evidence only) | to be planned |
| R15-LEAD-080 | medium | Agent/MCP compute_greeks and price_option return QuantLib-unit vega/theta/rho unlabelled; the model restated them as per-unit values | to be planned |
| R15-LEAD-081 | medium | sp500 screen serves S&P 500 member PTC as PTC India Limited (INR) from a fundamentals row written before the LEAD-044 fix; no migration purges it | to be planned |
| R15-LEAD-082 | medium | Screener top-K round-robin gives currency-less rows their own group slot, so a null-market-cap row displaces a real one | to be planned |
| R15-LEAD-083 | medium | Earnings drill-down As-of chip shows the client fetch clock and ignores the envelope server as_of | to be planned |
| R15-LEAD-122 | medium | Screener 'Export CSV' writes the file but shows no saved path, toast or error (the result of downloadCsv is discarded) | Reuse the Watchlist/Portfolio 'Saved <path>' / 'Export failed' status strip in the screener results table. |
| R15-LEAD-124 | medium | sec-edgar-mcp is killed while still extracting on a cold or busy launch (~91 s) and /sec routes return 501 for the whole session | Size the MCP bind budget to the cold-extraction worst case (keep the smoke-test budget in lockstep) or move to --onedir (CLAUDE.md Deferred). |
| R15-LIFECYCLE-024 | medium | No persistent store records a schema version (user_version 0 on all 8 SQLite DBs; no top-level workspace blob version) and nothing backs up the data dir before a new build touches... | One shared sidecar helper migrate(conn, steps) keyed on PRAGMA user_version used by all 8 stores (audit_log's append-only triggers untouched); |
| R15-RESEARCH-022 | medium | A 200-status CAPTCHA/block page from a keyless engine is recorded as a healthy empty answer and resets that engine's circuit breaker, so a blocking engine is never benched and an... | Move _filter_results above record_success; |
| R15-UI-084 | medium | The agent surface cannot take the full cockpit: the dock width is hard-capped at 1200 px and there is no maximize mode (FR-001 requires 'dominant column or full cockpit') | Add a 'maximized' state to the agent-dock store (a command plus a double-click on the handle) that renders the dock at 100% width and hides PanelHost, and restore the previous width on un-maximize. |
| R15-AGENT-065 | low | Two documented-deferred copilot/customizability builds remain unbuilt: the 3-pane agent roster panel with hard persona hand-off, and the data-source connector hub (Plugin Manager... | Keep deferred; ensure BLUEPRINT.md carries the same Deferred caveat as CURRENT_STATE.md. |
| R15-AGENT-085 | low | Plain chat answers carry no citation object and no unverified-claim check: the citation and [unverified] machinery exists only on research briefs and the Equity Overview narrative | Attach the turn's tool-call provenance (tool id + provider + as-of) as a sources footer on each chat message, reusing the brief's source chip renderer; |
| R15-AGENT-086 | low | A Delegate run can never be paused for a question: pause_run has no caller (no ask_user tool, no pause route), so the answer route serves a state no run can reach | Add an internal-only ask_user capability (catalog.py) whose handler calls pause_run with the question and ends the round; |
| R15-CODE-DATA-018 | low | Resolution.needs_disambiguation and the DISAMBIGUATION_THRESHOLD re-export are dead second-decision surfaces kept alive only by tests | Delete both; switch the four test call sites to resolution_policy.decide(...).outcome. |
| R15-CODE-FRONTEND-031 | low | Under AUTO the transcript narrates 'Applied:' before the async apply resolves, so a failed apply stays recorded as applied in the chat step line | enqueue returns {id, outcome: Promise<'pending'\|'applied'\|'failed'>}; |
| R15-CODE-PLATFORM-045 | low | Boot path bridges a plugin's panels and commands without checking that loadPlugin succeeded, so an errored plugin still contributes UI | const snap = await runtime.loadPlugin(plugin); |
| R15-CODE-PLATFORM-046 | low | moduleForPlugin re-implements capability negotiation without the runtime's try/catch, so a throwing getPanels()/getCommands() rejects bootstrapPlugins() mid-loop | Source panels/commands from runtime.collectPanels()/collectCommands() filtered by plugin id (or export callIfFlagged); |
| R15-DATA-098 | low | The yield curve emits a duplicated first point and extrapolates past the last instrument without saying so when step_days floors to 1 | Build the grid in float over max tenor and clamp; |
| R15-LEAD-025 | low | The fundamentals warmer hits openbb-mcp hard at boot with no observed throttling on the default (non-IN) universe warm path | Not root-caused yet -- the verifier note is one line with no reproduction detail. |
| R15-LEAD-041 | low | Earnings estimate detail's analyst count and its EPS triple are read from different upstream fields and disagree: TM shows estimate_analyst_count 1 while the EPS triple is null | Fill the EPS triple from earnings_estimate when the calendar's Earnings Average/High/Low is missing but earnings_estimate has a value, or null the analyst count alongside a null EPS triple so the two fields never disagree. |
| R15-LEAD-042 | low | The proposed-change review card and its applied label price a US lot in the session region's currency, not the listing's: {MSFT, 4, 480 USD} under an IN session reads 'Add 4 MSFT... | Have formatPrice (and describeIntent's callers) take the position's own currency (already resolved for the ledger write) instead of the session region, so the review-card and applied-label text always matches the value's real currency. |
| R15-LEAD-047 | low | A derived EPS (e.g. MSFT) is stamped field_meta status 'ok' with no reason text distinguishing it from a directly-served EPS | Attach a reason/label (e.g. 'derived from net_income_ttm/shares_outstanding') to field_meta.eps when eps is computed rather than provider-served, matching the labelling convention already used for withheld/overlaid fields. |
| R15-LEAD-052 | low | An ALL-CAPS headline still over-matches a 3-character common-word ticker in the non-IN relevance gate | Require an anchored common-word ticker match to sit in an otherwise-mixed-case headline (or add a second anchor signal, e.g. |
| R15-LEAD-053 | low | Direct GET /quotes/TATAMOTORS.NS and .BO still 404 with no rename hint to TMPV, even though /resolve already lists TMPV first for the same query | When a direct /quotes/{symbol} lookup 404s, consult the same former-name index /resolve uses before giving up; |
| R15-LEAD-054 | low | sp500.json carries ECHO and VMRK, two symbols absent from the current US resolver master, the same stale-universe-seed class R15-LEAD-049 fixed for nifty50 | Run the same fresh-master audit R15-LEAD-049's verifier used against sp500.json specifically, and update or drop ECHO and VMRK (or point them at their current symbols if renamed, not delisted). |
| R15-LEAD-055 | low | R15-AGENT-053's own regression test (NewsFeedPanel 'publishes the top headline...') flakes under full vitest-suite load: a context-bus publish is asserted synchronously right... | Move the context-bus payload assertion inside its own `waitFor` (or the same one guarding the DOM text) so it retries until the effect has flushed, instead of asserting synchronously right after an unrelated wait resolves. |
| R15-LEAD-056 | low | DOW's (and NICE's) own stripped company-name alias is the common word itself, so the DATA-030 stoplist's anchored-ticker rule never applies and 'Dow Jones falls 300 points' still... | Run the stoplist/anchored-mention check against the name alias too when the stripped name equals (or reduces to) a COMMON_WORD_TICKERS entry, not only against the ticker alias; |
| R15-LEAD-057 | low | Name-alias derivation leaves master-name registry artefacts in place ('amazon com', 'keycorp /new/'), so plain-prose company mentions never tag | Strip trailing registry/domain artefacts (a lone 'com' token from '.com', bracketed or slash-delimited listing-class suffixes like '/NEW/', '/OLD/') when deriving the name alias, in addition to the existing corporate-suffix strip; |
| R15-LEAD-058 | low | GM and GS (2-letter tickers with no brand token) never pass the non-IN relevance gate on a bare mention | Extend the short-token entity signal to 2-letter tickers directly (drop or lower the len(symbol) >= 3 floor for the plain ticker-token check, keeping the existing common-word/anchoring gate for stoplisted tickers), so a bare 'GM beats... |
| R15-LEAD-084 | low | NSE holiday table ends 2026-12-25; 2027-01-26 (Republic Day) is treated as an IN trading day (D-B9-4 covers the test horizon, not the data) | to be planned |
| R15-LEAD-085 | low | Suffixed unknown symbols (QQZZFAKE.NS, XYZNOTATICKER.BO) still return 200, 0 bars, reason null | to be planned |
| R15-LEAD-086 | low | The sibling [failed: ...] trailer still rides verbatim assistant history to the provider (_without_step_trailers strips only [tool steps:]) | to be planned |
| R15-LEAD-087 | low | Ratio guard still replaces a correct ADS-ratio sentence dated 26-Jun-2026 / Jun-26-2026 with "not available" | to be planned |
| R15-LEAD-088 | low | Resolver suggestions for MAZAGONDOCK / RELIANCEIND variants | to be planned |
| R15-LEAD-089 | low | Import toast says "Imported settings." for {settings:{fontSize}} when nothing applied | to be planned |
| R15-LEAD-090 | low | Cross-check extract still slow before the wall timeout (verdict leg boxed) | to be planned |
| R15-LEAD-091 | low | Type-first JSON tool-call text can leak into the visible answer | to be planned |
| R15-LEAD-092 | low | _row_value has a twin implementation that can drift | to be planned |
| R15-LEAD-093 | low | One doc line still says "the 18" host actions while the others and the catalog say 19 | to be planned |
| R15-LEAD-094 | low | sidecar/agents/copilot.json system prompt example reply "Built you a brief on NVDA - it's at the top of the cockpit" teaches an applied-tense claim that conflicts with review mode... | to be planned |
| R15-LEAD-095 | low | Bond pricer display currency fixed at mount; region switch while open keeps USD | to be planned |
| R15-LEAD-096 | low | leading_token reads a negated COMPLETE sentence as complete | to be planned |
| R15-LEAD-097 | low | A scrip with one trade inside 52 weeks keeps a forward-fill-derived provider 52w low unflagged when it is within the 10% tolerance | to be planned |
| R15-LEAD-098 | low | The announcements cache key includes limit and the raw symbol form, so callers that differ in limit or .NS suffix refetch the full history | to be planned |
| R15-LEAD-099 | low | save_screen overwrites the user's live screener draft without disclosing it; Undo does not restore the draft | to be planned |
| R15-LEAD-100 | low | _us_isin caches a definite ISIN miss for the life of the process | to be planned |
| R15-LEAD-101 | low | CONTRIBUTING.md says 'Python 3.13+' but the build requires exactly 3.13 | to be planned |
| R15-LEAD-102 | low | Ollama adapter catch-all humanizes internal exceptions as an Ollama error | to be planned |
| R15-LEAD-103 | low | Onboarding local-model recommendation collapses any sidecar failure to 'Couldn't reach the local engine' | to be planned |
| R15-LEAD-104 | low | Perplexity/Sonar ResearchSource builders drop published_at | to be planned |
| R15-LEAD-105 | low | OpenRouter chat URL literal in research lanes | to be planned |
| R15-LEAD-106 | low | SEC company search is a raw substring match | to be planned |
| R15-LEAD-107 | low | add_chart_drawing: a non-empty bogus panelId bypasses the open-chart fallback | to be planned |
| R15-LEAD-108 | low | BLUEPRINT says 12 AI agents; 13 first-party agents ship | to be planned |
| R15-LEAD-109 | low | /earnings/{sym}/estimates maps a yfinance 429 to 502 provider_error 'unexpected response', while /fundamentals/{sym}/ratings maps the same throttle to 429 rate_limited | to be planned |
| R15-LEAD-110 | low | A listed 1994 JPM 10-K opens as 502 'unexpected response' (sec-edgar-mcp get_filing_sections NoneType) instead of degrading to the raw filing text | to be planned |
| R15-LEAD-111 | low | clearSearch does not bump searchGeneration; late 501 paints error under emptied SEC search field | to be planned |
| R15-LEAD-112 | low | 200 F&O bhavcopy with truncated PK zip raises BadZipFile out of fetch_latest_fo, no walk-back | to be planned |
| R15-LEAD-113 | low | Stale 'client-side mathjs' comments in node-registry.ts:185-190 and code-node-run.ts header | to be planned |
| R15-LEAD-114 | low | nse_bhavcopy.py:36-40 docstring says the NSE master is '~2,675 symbols' and that SME (SM/ST) rows are 'outside the master'; the master is now 3506 rows including 571 SM | to be planned |
| R15-LEAD-115 | low | The quarterly-gap TTM reason always says 'a quarter of the trailing year' is unfiled, which understates the gap for fresh listings with only one or two quarters ever filed | to be planned |
| R15-LEAD-117 | low | FOCUS&exchange=BSE answers venue_not_covered with a note claiming FOCUS is not listed on BSE (BSE 543312 exists, a different company) | Note wording: 'BSE FOCUS (543312) is a different company; |
| R15-LEAD-118 | low | Shareholding percentages differ by symbol spelling for the same scrip/quarter/filing (e.g. FOCUS vs FOCUS.BO vs 543312) | Key the shareholding cache and the XBRL parse budget by the resolved scrip identity, not the normalized query spelling, so every spelling of the same scrip converges on the same parse state. |
| R15-LEAD-119 | low | The vitest coverage ratchet never gets committed: thresholds read lines 0 while measured coverage is about 81.4 | Either commit the auto-updated threshold as a CI step (fail the job if the diff is uncommitted) or stop auto-updating and hand-ratchet the floor on each release. |
| R15-LEAD-120 | low | Bare 2-letter ticker absent from the company name (KO / Coca-Cola) still fails the non-IN relevance gate; _entity_signals credits a ticker mention only for len(symbol)>=3 | Extend ticker-mention credit to 2-letter tickers under the same anchoring rule R15-LEAD-050 applied to 3+ char tickers (case/punctuation-anchored bare mention passes); |
| R15-LEAD-121 | low | llama3.1:8b prints USD portfolio holdings with the rupee sign although each holding carries currency:'USD' (IN default region) | Have the agent runtime or a post-process step render each holding's currency using its own currency field (symbol lookup keyed by holding.currency) rather than relying on the model to pick the right symbol; |
| R15-LIFECYCLE-040 | low | The Tauri-Rust MCP spawn (the Windows deadlock fix) has never been exercised inside a launched packaged app; CI builds the bundle and smoke-tests the raw binaries, but no packaged... | Run one packaged-app cold boot on each platform (launch the built bundle, check /openbb-mcp/status and /sec/status bind) and record it in DECISIONS.md; |
| R15-UI-068 | low | DataTable, 'the ONE table primitive', has no loading/empty slot and its sort headers are not keyboard-operable, so panels hand-roll skeleton tables and four surfaces still... | Add loading?:{rows} and empty?:ReactNode rendered through the same colgroup; |

## 3. Sidecar and boot

- **R15-LEAD-124** (medium, open): sec-edgar-mcp is killed while still extracting on a cold or busy launch (~91 s) and /sec routes return 501 for the whole session Fix shape: Size the MCP bind budget to the cold-extraction worst case (keep the smoke-test budget in lockstep) or move to --onedir (CLAUDE.md Deferred). Note: Split out of the R15-LEAD-123 root cause. 0.9.1 unless the final pass closes it.

## 4. Tier-4 bucket - waiting on the operator (35)

Each entry with the `DECISIONS_FOR_OPERATOR.md` section that covers it (nearest preceding heading that names the id).

| ID | Severity | Title | Where it is decided |
| --- | --- | --- | --- |
| R15-DATA-002 | critical | A bare ticker that exists in both the US and Indian masters binds silently to the session region, and every data panel re-queries the bare symbol, so... | DECISIONS 4.15 |
| R15-AGENT-017 | high | The shipped default chat model (DeepSeek V4 Flash via OpenRouter) returns content_filter with zero tool calls on ordinary portfolio-write asks, so... | DECISIONS 4.2 |
| R15-AGENT-019 | high | The intent gate classifies 'write a note', the composer's own /screener expansion, 'save' asks and everyday portfolio phrasings ('Delete TCS from my... | DECISIONS 4.16 |
| R15-AGENT-090 | high | Agent fabricates SIFY's ADR ratio with a fake 'fundamentals data' citation (true ratio is 1 ADS = 6 ordinary shares; the model states 1:1, later... | DECISIONS 4.17 |
| R15-DATA-030 | high | News symbol tagging matches the raw request string: every exchange-suffixed or company-named Indian ticker (RELIANCE.NS, HDFCBANK, SBIN) tags nothing... | DECISIONS 4.21 |
| R15-LEAD-030 | high | After an errored or uncalled tool, llama3.1:8b narrates a fabricated 'tool returned' citation for a financial figure no tool result carries | DECISIONS 4.9 |
| R15-RELEASE-001 | high | Every desktop bundle ships unsigned on macOS and Windows: a downloaded .dmg is refused by Gatekeeper as 'damaged' and the NSIS installer is flagged... | DECISIONS 2.8 |
| R15-RELEASE-002 | high | No GitHub release pipeline: pushing a v* tag produces no Release and no downloadable asset, so the public repo (tags v0.6.0..v0.8.0) has zero... | DECISIONS 2.9 |
| R15-RELEASE-003 | high | Auto-updater is dead end-to-end: registered and configured but never invoked, not permitted by the capability, and no update artifact is ever... | DECISIONS 2.10 |
| R15-RELEASE-004 | high | CI has never run on the product branch: 654 commits (R4-R15) bypass GitHub Actions and the newest cross-OS signal (main, 2026-05-30) is a red lint run | DECISIONS 2.11 |
| R15-RESEARCH-007 | high | Any URL with '/investor' in its path or an 'ir.' host is ranked PRIMARY (exchange/regulator grade), so a Medium or WordPress post outranks Reuters,... | DECISIONS 4.18 |
| R15-UI-090 | high | Quote freshness is stamped against the USER's locale calendar, not the instrument's exchange, so a closed US quote reads 'live' during Indian market... | DECISIONS 4.20 |
| R15-AGENT-049 | medium | Native web search has no per-run cap off Anthropic and per-search billing is never metered, so a $10/1k-search lane is invisible to the spend ceiling... | DECISIONS 4.3 |
| R15-AGENT-064 | medium | There is no way to add a user-chosen MCP server: only openbb-mcp and sec-edgar-mcp are wired, with no config surface, route or UI | DECISIONS 2.12 |
| R15-CODE-FRONTEND-013 | medium | Kill switch and append-only audit log gate only broker adapters: the surviving agent data-write gate (portfolio, notes, screens, layouts, region) has... | DECISIONS 3.3 |
| R15-CODE-PLATFORM-010 | medium | write_text_atomic / write_bytes_atomic accept any absolute path from the webview with no confinement, and CSP is null, so any webview script can... | DECISIONS 2.13 |
| R15-CODE-PLATFORM-015 | medium | Plugin data contribution is declaration-only: getDataSources() output only feeds a count in the Plugin Manager subtitle, VystedPlugin.subscribe has... | DECISIONS 2.14 |
| R15-CODE-PLATFORM-071 | medium | First-party panels bypass the plugin model: every core panel is a static-import VystedModule the user cannot install or remove, skipping manifests... | DECISIONS 2.15 |
| R15-CODE-PLATFORM-073 | medium | The design-token off-scale audit (PDD section 16's 'gate for one system') runs in neither ci-local nor any CI workflow, and covers only part of... | DECISIONS 2.16 |
| R15-CROSS-PLATFORM-001 | medium | Windows/Linux CI has never built or tested branch 004 (655 commits since the 2026-05-31 merge-base): the 3-OS workflows only trigger on push:main /... | DECISIONS 2.17 |
| R15-DATA-059 | medium | Former company names never resolve and non-Indian identity stays empty: 'BeiGene' does not find ONC, 'Toss the Coin Private Limited' finds nothing,... | DECISIONS 4.13 |
| R15-DATA-061 | medium | Data-route failures are misclassified and leak raw library text: ProviderError.kind is dropped by the app handler (a throttle is 429 on one route,... | DECISIONS 4.19 |
| R15-DOCS-002 | medium | COMMERCIAL_LICENSE.md and LICENSING.md give commercial@vysted.com as the only commercial contact, but vysted.com has no MX or A record, so a would-be... | DECISIONS 2.18 |
| R15-DOCS-003 | medium | BLUEPRINT §2 Locked Decisions and CLAUDE.md (project DNA) name Next.js 16 App Router static export as the frontend stack; the repo has no Next.js and... | DECISIONS 2.19 |
| R15-DOCS-015 | medium | Plugin docs describe a plugin system that no longer exists: PLUGIN_DEVELOPMENT.md and CLAUDE.md tell authors to ship panels via a sibling panels.ts +... | DECISIONS 2.20 |
| R15-LEAD-035 | medium | Told explicitly 'without calling any tool', llama3.1:8b stages a portfolio_update_position write anyway | DECISIONS 4.10 |
| R15-LEAD-037 | medium | The fabrication guard grounds a stated figure by VALUE only, so an older bar buried in the same price_data payload counts as grounded for the... | DECISIONS 4.11 |
| R15-LEAD-038 | medium | When an explicit no-tool instruction correctly empties the tool surface, llama3.1:8b still narrates a false completed portfolio write with no tool... | DECISIONS 4.12 |
| R15-RESEARCH-043 | medium | Research brief citation-integrity net matches only a bare [n]; grouped markers [2, 3] and prose pseudo-citations [New findings] ship unresolved as... | DECISIONS 4.14 |
| R15-UI-044 | medium | A keychain read failure during first-launch TOS hydrate is a silent dead end: the TOS dialog never renders and first-run onboarding is suppressed... | DECISIONS 2.21 |
| R15-UI-088 | medium | In-webview drag gestures (dockview tab reorder, node-editor palette-to-canvas) have no automated coverage and have been carried as NEEDS-MANUAL-CHECK... | DECISIONS 4.4 |
| R15-CODE-PLATFORM-063 | low | scripts/*.py (12 files incl. r15 tooling and scripts/rig) sit outside every ruff gate in CI and ci-local | DECISIONS 4.5 |
| R15-DOCS-008 | low | BLUEPRINT §2/§3.1 still say the OpenBB data layer is 'wrapped as a runtime sidecar'; it is now the out-of-process openbb-mcp subprocess | DECISIONS 4.6 |
| R15-DOCS-011 | low | CONTRIBUTING.md asks for a CLA but no CLA gate exists in CI and the process is not finalized, contrary to BLUEPRINT §4/§6.1 | DECISIONS 4.7 |
| R15-RELEASE-012 | low | CI never caches the three PyInstaller sidecar binaries, so every push pays ~9 cold sidecar builds (3 workflows x 3 OSes, ~20-25 min each workflow) | DECISIONS 4.8 |

The four local-model entries (R15-LEAD-030, -035, -037, -038) are the signed-off known limitation, not a 0.9.1 item unless reopened.

## 5. Awaiting manual check - needs_gui (5)

| ID | Severity | Awaiting manual check |
| --- | --- | --- |
| R15-CODE-AGENT-001 | high | The whole sidecar (including the unauthenticated /mcp surface with 36 tools, invoke_agent among them) answers any browser Origin with access-control-allow-origin: * and... |
| R15-LIFECYCLE-001 | high | Every launch freezes the app's main event loop for the whole MCP bind window (about 25 s warm, 34 s+ cold, up to 90 s), and the data sidecar is not even spawned until... |
| R15-LIFECYCLE-008 | high | No diagnostics exist and a shipped build persists no log at all: every Rust, sidecar and MCP line goes to process stdout (no console at all on a Windows release build),... |
| R15-UI-022 | medium | Chart drawing tools cannot place what the user clicks: anchors snap to the bar close, clicks past the last bar commit invisible drawings, Text always reads 'label', and... |
| R15-DOCS-024 | low | MCP_INTEGRATION.md's Claude Desktop (mcp-remote) setup has never been demonstrated end to end, and its claim that tools appear in Claude Desktop's slash picker as... |

## 6. Features

### BL-03 — Reasons about you (first 0.9.1 feature)

Moved off the 0.9.0 release line by scope change 3 (§6.2). Branch:
`origin/feature/bl-03-reasons-about-you`, carrying
`docs/redesign/features/bl-03/{README,SPEC,CRITIC,PANEL_VERDICT}.md`.

BL-03 makes every answer about a held name start from the user's own
position: when the owner asks about a stock they hold, the sidecar preamble
adds a short, grounded line stating the position (quantity, average cost,
weight in the marked book, unrealised P&L) pulled from the user's own
hand-kept portfolio, with zero extra tool calls; the research brief for a
held name gets a matching "Your position" metric card on the renderer. No
broker, no order, no portfolio write, and no new agent tool or MCP
projection — the feature only reads holdings the user already keeps by hand.
Panel verdict: rank-1 survivor, `4/5/4.5` value, `5/5/5.0` feasibility, S-M
size, 2-3 day effort, not killed, closing census finding
`WLD-agent-native-ux-1` (high).

### BL-18 — Brief diff, ask again and see what changed (post-launch)

Post-launch per the operator decisions of 26 Sep. Spec:
`docs/redesign/verification/r15/invent/specs/BL-18.SPEC.md` (+ `.CRITIC.md`).

BL-18 adds a "Changed since &lt;date&gt;" strip to the top of a research
brief on a symbol the user has seen before, leading with what can only change
when the company files (new exchange announcements or filings, moved filing
facts such as promoter holding or EPS, new/resolved cross-source conflicts)
while collapsing market-moving values (price, market cap, P/E) into one
"Market moved (N)" line. It is computed entirely on the renderer from a
per-symbol brief fingerprint recorded on publish, at zero extra tokens and no
network call.
