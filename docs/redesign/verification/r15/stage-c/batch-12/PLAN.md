# R15 Stage C: Batch 12 Plan (RC1 round-2 fix batch: 2 critical, 8 high, 13 medium; 22 to fix, 1 deferred)

- **Base:** branch `004-r4-experience-rebuild` at `bc3e64fe3ac1615740ecb7bfa1c016be3fbd371e` (the commits after the batch-11 merge are docs-only). D81 is merged: nothing here re-adds trading, orders, brokers or a paper account.
- **Author:** the batch planner (Opus). I opened the code each row names at this base. Mechanisms follow each entry's `rc1 refutation audit @6741387b` note (the corrected root cause and its acceptance test), or, for the ten batch-12 mined entries, the adjudicated mechanism. Line numbers are at base.
- **Queue:** 2 critical, 8 high, 13 medium open (lows are not in this batch). All 23 are either selected (22) or deferred with a reason (1). None is proposed not-a-defect: every entry reproduced from the code at base.
- **Lead note vs pacing cap:** the lead note sketches 11 sets (a)-(k); the role spec caps a batch at 8 writer sets. I merged by file ownership: (g) docs goes with (b) screener (the docs entries describe the screener and registry); (h) Settings, (i) the design audit and (k) LEAD-010 share W8 (the audit's 2 SecFilingsPanel hits and LEAD-010's SEC surface would otherwise split `SecFilingsPanel.tsx`); (j) AGENT-090 goes to W5 because its fix is the shared first-party preamble in `agent_runtime.py`; `errors.py` (AGENT-027) left (e) for its own Sonnet set because it needs no root-causing.
- **Routing:** Sonnet is the default. Opus only for W1 (resolver identity: ISIN source feasibility still unknown, three venue lanes) and W5 (agent runtime state machine plus the proposed-changes gate, §6.5-adjacent).
- **Every writer brief cites its entry's refutation-audit note verbatim** (the `note` field in `docs/redesign/verification/vysted-r15-register.json`). Writers implement to that acceptance test and commit it as the pin. Where a class shows up twice, the writer adds one test on a case the fix was not written against (named below).

## 0. The 23 entries

| id | sev | disposition | writer |
|---|---|---|---|
| R15-DATA-002 | critical | fix (chart leg) | W7 |
| R15-RESEARCH-002 | critical | fix | W4 |
| R15-AGENT-019 | high | fix | W5 |
| R15-DATA-043 | high | fix | W2 |
| R15-LEAD-010 | high | verify cold, then fix what is wrong | W8 |
| R15-RESEARCH-007 | high | fix | W4 |
| R15-UI-090 | high | fix | W7 |
| R15-AGENT-090 | high | fix | W5 |
| R15-AGENT-092 | high | fix | W5 |
| R15-AGENT-093 | high | fix | W5 |
| R15-AGENT-027 | medium | fix | W6 |
| R15-CODE-PLATFORM-013 | medium | fix | W8 |
| R15-DATA-059 | medium | fix (regression) | W1 |
| R15-DATA-068 | medium | fix | W3 |
| R15-DOCS-017 | medium | fix | W2 |
| R15-DOCS-018 | medium | fix | W2 |
| R15-LEAD-028 | medium | fix | W1 |
| R15-RELEASE-007 | medium | fix | W8 |
| R15-DATA-112 | medium | fix | W2 |
| R15-DATA-113 | medium | fix | W3 |
| R15-DATA-114 | medium | fix | W6 |
| R15-CODE-AGENT-033 | medium | **deferred** (see §9) | - |
| R15-DATA-115 | medium | fix | W1 |

---

## W1 (opus): resolver and venue identity

Why Opus: DATA-059's ISIN half needs a keyless US ISIN source judged before any code (none is bundled), and the three entries span three venue lanes plus the correctness gate.

Owned files: `sidecar/services/symbol_resolver.py`, `sidecar/services/correctness_gate.py`, `sidecar/services/nse_provider.py`, `sidecar/services/india_provider.py`, `sidecar/services/resolver_masters/us_instruments.json` and its generator (only if ISINs land), tests `sidecar/tests/test_symbol_resolver.py`, `test_correctness_gate.py` (or `test_provider_registry_region.py`), `test_nse_provider.py`, `test_india_provider.py`.

**R15-DATA-059** (regression_confirmed). Mechanism: `symbol_resolver.py:1377` `if inst.exchange not in ("NSE","BSE"): return inst` returns before the former-name fallback (:1406-1411); that fallback only echoes a `former_name` the name scan (:1064-1100) stamped. So a US ticker resolve (`ONC`, `SIFY`) never joins `_former_names()["us"]` (:469), which does hold `ONC -> ['BeiGene, Ltd.']` and `SIFY -> ['SIFY LTD','SATYAM INFOWAY LTD']`. Fix: for a non-Indian instrument, return it with `former_name = inst.former_name or <most recent entry of _former_names()["us"][bare]>`; keep every Indian identity field at `None` (the R13 TCI guard stays). ISIN: `us_instruments.json` rows are `[ticker, name]`. Add ISINs only from a keyless, licence-compatible bulk source joined exactly (not fuzzily). If none exists, leave `isin` null (honest) and report could-not with the evidence. Test: `resolve('ONC','US').best.former_name == 'BeiGene, Ltd.'`, `resolve('SIFY','US').best.former_name == 'SIFY LTD'`; the TCI guard test stays green; the ISIN asserts only if ISINs landed.

**R15-LEAD-028.** Mechanism (batch-11 verifier): the resolver half works (`bse_symbol_for_code('506597') -> 'AMAL'`, `bse_provider._require_bse` canonicalises), but `correctness_gate.symbols_match` (`_match_key`, :118-131) compares `506597` with the returned `AMAL`, so `validate_quote` (:155-158) and `validate_series` (:193-196) reject the BSE result as a symbol mismatch. The registry then falls through to yfinance, which has no data (404 / empty bars). Fix: in `symbols_match`, canonicalise a bare 5-6-digit BSE scrip-code request through `symbol_resolver.bse_symbol_for_code` before comparing. One place, so every validator gets it. Check the import direction for cycles. Test (registry-level, through the gate): a fake bse lane answering `AMAL` for `506597.BO` is accepted by `provider_registry.get_quote` and by history; a code whose canonical ticker differs from the returned symbol is still rejected.

**R15-DATA-115.** Mechanism: `nse_provider._require_nse` (:361-369) and `india_provider._require_nse` (:128-137) strip the suffix with `locale.strip_exchange_suffix` and accept `AMAL.BO`, because `AMAL` is also an NSE symbol. So `nse_direct` (rank 15) serves NSE's 28 bars for an explicit `.BO` request before `bse` (rank 25) is tried. This is one class across two gates: both NSE lanes ignore an explicit BSE suffix. Fix: both `_require_nse` raise `ProviderError(kind="not_found")` for a `.BO`-suffixed symbol. Tests: `nse_provider` and `india_provider` each reject `AMAL.BO` without a network call. Class pin on a case the fix was not written against: `/history/RELIANCE.BO` via the registry is served by `bse` (or yfinance), never by `nse_direct`/`nse`.

## W2 (sonnet): screener ordering + CURRENT_STATE doc drift

Owned files: `sidecar/services/screener.py`, `docs/CURRENT_STATE.md`, tests `sidecar/tests/test_screener.py`, new `sidecar/tests/test_current_state_doc.py`.

**R15-DATA-043.** Mechanism: `screener.py:423-429` sorts currency-grouped (`INR` before `USD`); `:815` `rows = matched[:limit]` cuts that order, so a mixed-currency top-K keeps only the alphabetically-first currency; `:845-847` compute `served_currencies` over the page, so the "ranked within each currency" note vanishes exactly when the cut hides a currency. Fix: compute the currency span over `matched`, and cut per currency: take each currency group's top rows round-robin by rank until `limit`, then serve them in the grouped order. Test: the note's acceptance (custom AAPL/RELIANCE.NS/MSFT/TCS.NS, market_cap desc, limit=2 -> coverage contains "ranked within each currency" and the page has a USD row).

**R15-DATA-112.** Mechanism: `_currency_sort_key(None)` (:358-360) returns `''`, which sorts ahead of every currency code, so a row with no fundamentals currency (MANIKA.NS) forms a leading group. Fix: the sort key puts a missing currency last, `(currency is missing, currency, value is None, signed value)`, for both sort directions. This is the same missing-values-last rule as the value leg. Test: the repro (MANIKA/RELIANCE/TCS desc -> MANIKA last) plus asc.

**R15-DOCS-017.** Mechanism: `CURRENT_STATE.md` §3.3 screener bullet (:358-365) never names `nse-all`/`bse-all`/`india-all`. Its sp500 clause (506 symbols, "R15-LEAD-013 open") went stale when batch 11 regenerated the pack (503 symbols, snapshot 2026-09-24). Fix: rewrite the bullet from `sp500.json` and `screener_universe_india.py`. Test: `test_current_state_doc.py` asserts §3.3 contains `f"{len(sp500['symbols'])} symbols"` and `snapshot_date`, lacks "R15-LEAD-013 open", and names every `ScreenerUniverseId` literal except `custom` in backticks.

**R15-DOCS-018.** Mechanism: §3.3 (~318-335) omits the IN chain from `provider_registry.py:161-219` (nse_direct 15, nse/jugaad 20, bse 25, region IN, ahead of yfinance 50) and calls yfinance "the no-key default for equities". Fix: list the IN chain with ranks and qualify yfinance's default role by region. Test (same file): every `ProviderDeclaration` whose region contains `IN` has its id in §3.3, and the yfinance bullet mentions the region qualification.

## W3 (sonnet): as-of on the ratings consensus + estimate revenue currency

Owned files: `sidecar/routers/fundamentals.py`, `sidecar/models/fundamentals.py`, `types/data.ts`, `src/modules/equity-overview/EquityOverviewPanel.tsx`, `sidecar/services/earnings_provider.py`, `sidecar/models/earnings.py`, `types/earnings.ts`, `src/modules/earnings/EpsEstimateGrid.tsx`, tests `sidecar/tests/test_analyst_extended_router.py` (or a fundamentals-router test), `test_earnings_provider.py`, co-located frontend tests if a render assertion is added.

**R15-DATA-068.** Mechanism: `fundamentals.py:251` `rating, _ = await _cached(...)` discards the cache write time for the base `GET /fundamentals/{symbol}/ratings` (6 h `_TTL_RATINGS`). `AnalystRating` (`models/fundamentals.py:231`) and `types/data.ts:356` have no `as_of`, so the Equity Overview consensus (`EquityOverviewPanel.tsx:1139`) shows a possibly 6 h-old figure with no timestamp. Fix: add `as_of: datetime | None = None` to the model and mirror it (`as_of?: string | null`) in the same commit. The route stamps the `_cached` fetched_at. Render an as-of next to the consensus, following the AnalystRatingsPanel precedent. Test: the note's acceptance (non-null ISO `as_of`; a second GET within TTL returns the same `as_of`).

**R15-DATA-113.** Mechanism: `earnings_provider.py:168/199/288/405/505` stamp every money field with `info['currency']` (the trading currency). Yahoo gives statement-size revenue estimates and actuals in `financialCurrency`, so WIT's INR-sized `revenue_estimate_mean` is labelled USD. Fix: carry a separate `revenue_currency` (`financialCurrency`, falling back to `currency`) on every model with revenue fields: estimates detail, the history rows (:424-425) and surprises (:459-461). This is the same class on three shapes; `yfinance_provider.py:400-410` is the precedent. Mirror it in `types/earnings.ts` and label per field in `EpsEstimateGrid.tsx`. Tests: WIT-shaped payload (currency USD, financialCurrency INR) -> estimates `currency=='USD'`, `revenue_currency=='INR'`. Class pin on a case not written against: the history-row revenue for the same payload carries INR.

## W4 (sonnet): research verdict parse + source authority

Owned files: `sidecar/services/research/verify.py`, `sidecar/services/research/deep.py`, `sidecar/services/research/finance.py`, tests `sidecar/tests/test_research_verify.py`, `test_research_finance.py` (plus the deep reflect test file if the reflect pin lands there).

**R15-RESEARCH-002.** Mechanism: `verify.py:134-140`. When the first word is not a verdict word, the fallback scans `_AGREE_MARKERS` over the whole line before looking for a standalone UNVERIFIED/DISAGREE. `deep.leading_token` (:348-361) strips only `*:-#>`, so a `Verdict:` label, `[ ]` brackets or `1.` numbering hide the verdict. Fix: (1) `leading_token` skips a leading `Label:` word, bracket and list numbering, which fixes both callers, verify and `_reflect_says_complete`; (2) in `_parse_verdict`, before the marker scan, look for an uppercase standalone verdict word in the first line with priority UNVERIFIED > DISAGREE > AGREE. Test: the note's `test_parse_verdict_reads_a_labelled_verdict_word` table. Class pin on a case not written against: `_reflect_says_complete('[GAPS] revenue covered but margins are not')` is False and `'1. COMPLETE - all dimensions covered'` is True.

**R15-RESEARCH-007.** Mechanism: `finance.py:146`. `_looks_like_ir` accepts `investors.`/`ir.` as a host prefix even when that label IS the registrable domain (`investors.com` after the `www.` strip), and `_IR_PLATFORM_DENYLIST` (:79-89) lacks github.io/wixsite.com/netlify.app/hubpages.com and matches blogspot only on `.com`. Fix: require the IR label to be a subdomain (the host has at least 3 labels), extend the denylist with the free-hosting platforms (github.io, gitlab.io, wixsite.com, netlify.app, vercel.app, pages.dev, hubpages.com, weebly.com, tumblr.com), and match `blogspot.<any tld>`. Test: the note's `test_ir_host_prefix_never_promotes_news_or_platform_hosts` plus its four controls. Class pin on a case not written against: `ir.blogspot.co.uk` and `investors.pages.dev` are not PRIMARY.

## W5 (opus): agent runtime (intent gate, delegate halt, arg coercion, grounding rule)

Why Opus: this is the runtime state machine and the proposed-changes gate (§6.5-adjacent). The intent-gate change widens which write tools reach the model, so it must keep every data write staged for review. Never weaken a §6.5 safeguard.

Owned files: `sidecar/services/planner.py`, `sidecar/services/agent_runtime.py`, `sidecar/services/run_manager.py`, `sidecar/agents/copilot.json` (only if needed), tests `sidecar/tests/test_b3_runtime_intent_gate.py`, `test_run_manager.py`, `test_b3_runtime_tool_args.py`, and the agent-runtime test that owns the preamble.

**R15-AGENT-019.** Mechanism: `planner.py:76-108` `_EDIT_SIGNALS` has no log/record/hold cue, and `:120` `\?\s*$` makes a trailing `?` a positive read cue. So `agent_runtime.py:1666` (`read_only = inferred_intent == 'read' and bool(intent.signals)`) strips every data write at :1669-1688 for "Can you log 10 TCS at 3400 in my portfolio?". Any edit cue already beats read (`classify_intent` :207-216). Fix the class, not the two words: add `log`/`record` cues and a holding-shaped cue (a quantity, a word, then `at <price>`, e.g. "10 TCS at 3400"). Test: the note's parametrized `_agent_tool_ids` test. Controls: "what is P/E?" and "How is my portfolio doing?" still strip. Class pin on a case not written against: "Could you enter 5 HDFCBANK at 1600 into my portfolio?" keeps `portfolio_add_position`.

**R15-AGENT-092.** Mechanism: `run_manager.py:293-302` appends host actions from every yielded `tool_use`. `agent_runtime` yields the `tool_use` before the round's budget-halt check, and `:302` only sets `halted` on `HALT_NOTICE_TOOL`, without dropping that round's entries. `delegate-runs.ts` then enqueues them as proposed changes. Fix: collect host actions per round and discard the pending round's entries when `HALT_NOTICE_TOOL` arrives. Do not touch `delegate-runs.ts`; dispatched actions are unaffected. Test: `test_run_manager.py::test_a_halted_rounds_host_actions_are_not_proposed` (valid write_note + done(100k tokens), `RunBudget(max_tokens=1000)` -> status error, `row.host_actions == []`).

**R15-AGENT-093.** Mechanism: the schema gate (`agent_runtime.py:~848-866`) already coerces a JSON-string array/object to its declared container type, but not a numeric/boolean string, so `"5"` for an `integer` param fails `Draft7Validator`. Fix: extend the same coercion loop so a string that parses exactly as the declared `integer`/`number`/`boolean` type is converted before validation. Non-numeric strings stay invalid. Test (in `test_b3_runtime_tool_args.py`): `option_chain` `max_strikes: "10"` passes as int 10; `"ten"` still yields the invalid-args sentinel. Class pin on another tool the fix was not written against: `screener_run` `limit: "25"`.

**R15-AGENT-090.** Mechanism: no tool result carries an ADR ratio. The copilot prompt says "never invent … fetch it", but nothing tells any agent what to do when no tool CAN return the fact, so models attribute a made-up ratio to "fundamentals data". Fix: add one rule to the shared `TERMINAL_CAPABILITIES_PREAMBLE` (every first-party agent, so the whole class): a fact no tool result this turn contains is stated as unavailable and never attributed to a tool or source. Also add a real deterministic guard if one fits this scope; if not, record the ceiling with a `ponytail:` note. Test: the loaded spec of every first-party agent carries the rule, plus a scripted-provider test if a deterministic guard lands.

## W6 (sonnet): error copy markers + option-chain negative probe

Owned files: `sidecar/services/errors.py`, `sidecar/services/option_chain.py`, tests `sidecar/tests/test_errors.py`, `test_option_chain.py`.

**R15-AGENT-027.** Mechanism: the `errors.py` `_BODY_RULES` marker lists are too narrow. The context_overflow markers (:288) miss Gemini's "input token count … exceeds the maximum number of tokens allowed". The model_not_found markers (:272) miss Groq's "has been decommissioned" / `model_decommissioned`. The credit rule (:263-264) matches only {400,429}, so xAI's 403 "doesn't have any credits" falls to auth (:411-417). The class heuristic (:454-460) gives Ollama's ReadTimeout network copy. Fix: extend those three marker rows and the credit status set to include 403, and give the Ollama branch (provider `ollama`, timeout/connect class) "Ollama is not responding/running" copy. Test: the note's parametrized `test_provider_bodies_get_a_workable_next_step`; every existing row stays green.

**R15-DATA-114.** Mechanism: `option_chain.fetch_latest_fo` (:125-151). A `failed` probe of today returns `None` (:146-147) before the walk reaches an older cached day, and today's 404 is never cached, so every request re-probes NSE. Fix: after a failed or missing today-probe, keep walking back CACHE-ONLY (no more network calls) and serve the newest cached day. Cache today's negative probe under a short-TTL key so repeated requests within the window do not re-probe. Tests: yesterday cached and today's `_fetch_fo_day` `failed` -> returns yesterday; two calls with today's 404 hit `_fetch_fo_day` for today once.

## W7 (sonnet): instrument region on the chart + Indian index calendar

Owned files: `sidecar/services/locale.py`, `src/components/CommandPalette.tsx`, `src/lib/host-actions.ts`, `src/store/chart-command.ts`, `src/lib/sidecar-client.ts`, `src/modules/chart/ChartPanel.tsx`, tests `sidecar/tests/test_quotes.py`, `test_locale.py`, `src/components/CommandPalette.test.tsx`, `src/store/chart-command.test.ts`.

**R15-UI-090.** Mechanism: `locale.py:176-178` `instrument_region` returns IN only for an nse_direct/nse/bse provider or a `.NS`/`.BO` suffix. Indian indices served by yfinance (`^NSEI`, `^BSESN`, `^NSEBANK`) are dated against the US calendar and read `eod` during NSE hours. Fix: recognise Indian caret indices (the `^NSE`/`^BSE`/`^CNX` families and `^INDIAVIX`) as IN in `instrument_region`. Do not add calendars: locale knows only US/IN, so `.AX` stays out of scope; report it in issues. Test: the note's acceptance (`/quotes/%5ENSEI` and `%5EBSESN` are `live` under both IN and US at `_NSE_HOURS`; `instrument_region('^NSEI','yfinance') == 'IN'`). Class pin: `^CNXIT` -> IN.

**R15-DATA-002.** Mechanism: the per-listing pick reaches the Equity Overview (`openCompanyOverview` carries region), but not the chart. `CommandPalette.tsx:391` and `:207` call `loadSymbolIntoChart(c.symbol)` and drop exchange/region; `host-actions.ts:318` and `chart-command.ts:39` take no region; `sidecar-client.ts:341` `history()` sends no `regionHeader()`. Fix: thread an optional `region` through `loadSymbolIntoChart` -> `loadSymbol` -> the command -> `ChartPanel` state -> `sidecarApi.history(…, region)` and any other per-instrument call the chart makes for that symbol. Derive the region from the picked candidate's exchange (NSE/BSE -> IN, a US exchange -> US), as `openCompanyOverview` callers already do. Tests: the note's acceptance (`CommandPalette.test.tsx`: in an IN session, "AMAL US" -> `/history/AMAL` carries `X-Vysted-Region: US`, "AMAL NSE" -> `IN`; `chart-command.test.ts`: `loadSymbol('AMAL', undefined, 'US')` stores region `US`).

## W8 (sonnet): design-token gate, Settings plugin toggle, SEC filing lookup (LEAD-010 verify-first)

Owned files: `package.json`, `src/components/OnboardingFlow.tsx`, `src/modules/chat/ProposedChangesReview.tsx`, `src/modules/sec/SecFilingsPanel.tsx`, `src/components/SettingsPanel.tsx` (+ `SettingsPanel.test.tsx`), `sidecar/services/sec_filings_provider.py`, `sidecar/routers/sec_filings.py`, `sidecar/services/agent_tools/catalog.py` (the `sec_filing_content.form_type` description only), `sidecar/services/agent_tools/sec_tools.py` (only if forwarding is missing), tests `sidecar/tests/test_sec_filings_provider.py`, `test_sec_tools.py`, `test_sec_filings_router.py`.

**R15-RELEASE-007.** Mechanism: `node scripts/audit-design-tokens.mjs` exits 1 at base with 4 hits: OnboardingFlow.tsx:533 `px-1.5`, ProposedChangesReview.tsx:106 `py-1.5`, SecFilingsPanel.tsx:212 `max-h-56`, :226 `py-1.5`. `package.json` `lint` is `eslint .`, so the audit gates nothing (CODE-PLATFORM-027, the Windows path walk, is already fixed). Fix: move the 4 classes onto the R9 grid, then set `lint` to `eslint . && node scripts/audit-design-tokens.mjs`, which chains it into ci-local and the lint workflow with no workflow edit. Pin: the lint wiring itself, since `pnpm lint` exits 0 and the audit prints clean. Add no scratch fixture test.

**R15-CODE-PLATFORM-013.** Mechanism: `SettingsPanel.tsx:1938-1941`. The Modules switch calls `useModulesStore.setModuleEnabled` for bridged `plugin:<id>` modules, bypassing the lifecycle owner (`useMarketplaceStore.enable/disable`, `marketplace.ts:152/166`). `workspace.ts:309-313` drops `plugin:*` flags, so the "off" is silently undone on relaunch. Fix: route a `plugin:` module's toggle through `useMarketplaceStore.getState().enable/disable(pluginId)`. Grep for any other `setModuleEnabled('plugin:…')` caller and route it the same way. Test: the note's `SettingsPanel.test.tsx` acceptance (clicking "Vysted Example Plugin enabled" invokes marketplace `disable('vysted-example')`, and `enabled['plugin:vysted-example']` is never false while the runtime reports it active).

**R15-LEAD-010 (verify-first).** First re-run the repro cold on your own sidecar (free port, started detached, polled). Then change only what is actually wrong. Mechanism per the note: `catalog.py:741-746` calls `form_type` optional and "speeds up the lookup". Unhinted, `get_filing` (`sec_filings_provider.py:579`, :618-632) searches only 40 then 100 rows of any form. `get_filing_sections` (:650-662) and the `/sections` route (`routers/sec_filings.py:124-131`) take no `form_type`. Fix: (1) after the unfiltered windows miss, try the form-filtered lists of the periodic forms (10-K, 10-Q, 20-F) at the 40-row window only; this is a bounded cost, marked with a `ponytail:` comment naming the ceiling. (2) Accept and forward `form_type` in `get_filing_sections`, the `/sections` route and the panel's sections call if it has the form. (3) Reword the catalog description to say it is needed for older filings. Tests: the note's acceptance (the recorder test in `test_sec_filings_provider.py`, `test_sec_tools.py` `_sec_filing_content` ok, and a router test that `/sections` forwards `form_type`).

---

## Coordination and mirrors

- `types/data.ts` <-> `sidecar/models/fundamentals.py` and `types/earnings.ts` <-> `sidecar/models/earnings.py`: W3 changes each pair in the same commit. No other writer touches either pair.
- W7 needs no sidecar change for DATA-002: the sidecar already honours a per-call `X-Vysted-Region`, and `sidecarGet` lets per-call headers win.
- W1's `.BO` gate change does not move registry ranks, so W2's DOCS-018 chain (ranks and regions from `provider_registry.py`) stays true. W2 reads ranks from the code, not from W1.
- W5 must not change `delegate-runs.ts`, the proposed-changes gate or `catalog.is_read_only`. AGENT-019 only widens which writes reach the model; they still stage for review.
- W8's `catalog.py` edit is one description string. `test_mcp_catalog_parity.py` and `test_capability_catalog.py` must stay green; no roster or count change.
- No writer edits CLAUDE.md, `tauri.conf.json`, `.github/`, LICENSE*, `types/plugin.ts` or `r15-fanout.js`.

## Integrator run order

Sidecar/services sets first, then router/frontend sets:

1. W1 (resolver, gate, NSE lanes)
2. W4 (research)
3. W6 (errors, option chain)
4. W5 (agent runtime)
5. W2 (screener + docs; the doc test reads `provider_registry.py`, unchanged by W1)
6. W3 (router/models/types + frontend)
7. W8 (SEC sidecar + router, then package.json lint + frontend)
8. W7 (locale + frontend chart path)

After all merges: `pnpm lint` (now includes the design audit), `pnpm typecheck`, the focused pytest/vitest files each writer names, then `pnpm ci-local` detached.

## 9. Deferred

- **R15-CODE-AGENT-033** (grader blind to tool errors): the agent SSE stream carries no tool-result event (`models/llm.py` event kinds: delta, tool_use, research_step, agent_plan, thinking, heartbeat, done, error), so `vy.py` cannot record an ok/error for the grader. The fix needs a new stream event emitted from `agent_runtime.py`, which W5 owns this batch, and a frontend check that unknown kinds are ignored. That file cannot be shared, so the fix moves to batch 13 (`agent_runtime.py` emit + `models/llm.py` + `scripts/agent_eval/grader.py`).
