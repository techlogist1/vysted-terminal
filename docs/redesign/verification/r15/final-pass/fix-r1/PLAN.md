# Final fix round 1: plan

Planner: claude-opus-5-5 (effort medium), label final-fix-r1-plan, 2026-10-03 18:34 IST. Base: d38b5d1a2487bd52fe8a7e741a3a5266e3206611 (the candidate).

## Scope rule for this round

The operator's burst-window request wins over the computed task where they conflict. It says: "criticals and highs closed in one round, mediums and lows filed for 0.9.1". TRIAGE.md applies the same bar: "Mediums ... filed for 0.9.1 unless writers have room".

So this round does three things:

1. It plans all 8 critical and high entries (R15-FINAL-001 to R15-FINAL-008).
2. It plans a medium or low only where it fits beside that work: the same files, small and fully specified. That is 18 more entries.
3. Every other medium is listed as **0.9.1 (operator bar)** in the return value's `deferred`, and every other low is in `lows_unplanned`.

Nothing in this round is a Tier-4 deferral, and no DECISIONS item was drafted:

- No entry needs a Tier-1 file. `src-tauri/src/lib.rs` (FINAL-038) is not Tier-1, and neither is `sec_edgar_mcp.rs` (LEAD-124).
- No entry is an R4 instance.
- No entry reaches R7. R15-AGENT-027 and R15-RESEARCH-022 are at 2 failures each, so one more not_certified would stop either of them. Both are medium, and I left both for a deliberate 0.9.1 attempt rather than a squeezed one.

**Probe.** I did not boot a sidecar on :52882. Every planned mechanism was confirmed from code at the sha (path:line below), and final-triage's live re-runs (raw/final-triage/rr.out) stand. LEAD-060 was re-run in-process against final-cand/sidecar/.venv:

- `_parse_verdict('_UNVERIFIED_ - no source confirms ...')` returns `agree`.
- The plain form returns `unverified`.

## Writer W1 `portfolio-host` (opus)

Opus because the round touches several risk-adjacent things:

- workspace persistence: the Holding blob gains a field;
- the proposed-changes gate surface: `portfolio_add_position` and `write_note` are both staged writes;
- the agent's tool-result truth: get_portfolio.

The work also needs a server-side concurrency call on /quotes.

Files, all owned by W1:

- `src/store/portfolios.ts`
- `src/modules/portfolio/api.ts`
- `src/modules/portfolio/PortfolioPanel.tsx`
- portfolio tests
- `src/modules/chat/context-provider.ts` (+ its test)
- `src/lib/host-actions.ts` (+ test)
- `src/lib/layout-templates.ts` (+ test)
- `src/modules/sec/SecFilingsPanel.tsx`
- `sidecar/routers/quotes.py` (+ test)
- `src/lib/workspace.ts`, only if the restore path needs it

| id | mechanism (at d38b5d1a) | fix | pinning test |
|---|---|---|---|
| R15-FINAL-001 (critical) | `Holding` (portfolios.ts:23-30) has no listing. `fetchPositionQuote` (api.ts:32-41) calls `sidecarApi.quote(symbol, assetClass)` with no region, so the global `X-Vysted-Region` rebinds a bare ticker to another listing when the session region changes. | Add `region?: string` to Holding/HoldingInput. Stamp it at add time with the session region, on the form path and on the agent `portfolio_add_position` path (host-actions.ts:1398). On restore, stamp a missing region with the session region once. Quote each holding with its own region. The client already supports per-call region: sidecar-client.ts:393-413, used the same way as watchlist/api.ts:36-55. The CSV export uses the same priced rows. | vitest: INFY 20 @ 1500 added under IN; switch the region to US. The /quotes request for INFY still carries `X-Vysted-Region: IN`, and the row and the CSV show the IN quote. Fresh case: TCS (also an NYSE-less IN name) added under US stays US. An old blob with no region restores stamped. |
| R15-FINAL-006 (high) | api.ts:46-63 fans out one GET per holding. The 30 s default (sidecar-client.ts:264, R15-LIFECYCLE-027) aborts each GET client-side. `quoteFetchInFlightRef` (PortfolioPanel.tsx:197-257) releases on the abort while the server keeps working, so every 5 s tick re-sends all 100. Server side, routers/quotes.py:70-100 gathers one worker thread per symbol with no bound. | Refresh through the batch `sidecarApi.quotes` route, grouped by (region, assetClass) as the watchlist does. Give that call an explicit `timeoutMs` sized for a cold batch. After a timeout, back off instead of re-sending every 5 s. Bound the batch route's concurrency (a semaphore) so a 100-symbol batch cannot starve a single `/quotes/{symbol}`. | vitest with a stub fetch that never resolves for 100 holdings: exactly one /quotes request is in flight across 3+ ticks. pytest: a 100-symbol batch with a slow stub provider leaves a concurrent single quote answering within its own latency. Live (certifier): own sidecar, 100 cold NSE names mounted in the jsdom harness; `curl /quotes/RELIANCE.NS` answers < 5 s while mounted. |
| R15-FINAL-007 (high) | context-provider.ts:161-166 `fallbackCurrency` returns `regionConfig(session region).currency` for any equity. portfolioFromStore (:225) uses it for every holding, so AAPL is served as INR. | Derive the currency from the holding's own listing: `.NS`/`.BO` give INR, and a crypto pair gives its quote side. Otherwise use `null`, so the tool says the currency is unknown. Never use the session region (a holding's stored region is not its currency: AAPL added under IN is still USD). The TerminalHolding currency becomes nullable if it is not already. Apply the same to extractHoldings. | vitest: region IN, panel closed, holdings RELIANCE.NS + AAPL. RELIANCE.NS is INR; AAPL is not INR (null or USD). Fresh case: BTC/USDT is USDT. |
| R15-FINAL-017 (medium, same files) | api.ts:32-41 maps a 404 not_found to `{error}`, :52-58 counts it in `failed`, and PortfolioPanel.tsx:223 shows the transport banner with Retry. | With the batch route, a symbol missing from a successful batch is a row-level "no quote for this symbol": no banner, and it is not retried every tick. Only a failed request raises the banner. | vitest: ZZZZNOTREAL beside 4 resolved rows. No transport banner, the row says no quote, and no per-tick re-request for it. |
| R15-FINAL-033 (low, same file) | portfolios.ts:113 tests `raw.costBasis === ''` untrimmed, then `Number('   ') === 0`. :100 accepts `Number('0x10') === 16`. | Trim before the empty check, and accept only a plain decimal pattern for quantity and cost. | vitest through the form: cost `'   '` is refused, qty `'0x10'` is refused, and `'1e3'` follows the decimal rule. |
| R15-FINAL-016 (medium, same file) | host-actions.ts:1651-1660 returns `done('Arranged …')` unconditionally. applyCustomLayout (layout-templates.ts:279-289) early-returns on an empty plan, and planCustom drops unknown tokens. parseCustomPanels (host-actions.ts:406) yields [] for a string. | Make applyCustomLayout return what it placed. On an empty plan, `fail(...)` naming the unresolved tokens. On a partial plan, note the dropped ones. parseCustomPanels accepts a comma string. | vitest with the two probe inputs: `panels:['sec_filings_list']` fails and names the token; `panels:'chart, sec-filings'` arranges both or names the miss. |
| R15-FINAL-030 (low, same file) | host-actions.ts:764-768 `noteScope` only uppercases, so 'Cochin Shipyard' lands under 'COCHIN SHIPYARD'. | Resolve a non-ticker scope through /resolve at staging, the way add_to_watchlist does. If nothing resolves, keep the literal and say so in the label. | vitest: scope 'Cochin Shipyard' with /resolve stubbed to COCHINSHIP gives `noteFor('COCHINSHIP')` the text. Fresh case: a ticker scope is unchanged. |
| R15-LEAD-077 (medium, same file) | SecFilingsPanel.tsx:164-175 publishes `identifier` but no `symbol`, and the context provider reads `symbol`. | Publish `symbol` (the active identifier) alongside it. | vitest: focused SEC panel on MSFT; the snapshot's focused symbol is MSFT. |

## Writer W2 `data-fundamentals` (opus)

Opus because FINAL-005 needs a live probe and a design call: does NSE serve SME integrated XBRL under `index=sme` (nse_provider.py:375-380)? And because these are money-relevant figures.

Files, all owned by W2:

- `sidecar/services/correctness_gate.py`
- `sidecar/services/provider_registry.py`
- `sidecar/services/exchange_financials.py`
- `sidecar/services/earnings_provider.py`
- `sidecar/routers/earnings.py`
- `sidecar/routers/fundamentals.py`
- `sidecar/models/` and `types/data.ts` (the hand mirror, same commit)
- `src/modules/equity-overview/EquityOverviewPanel.tsx`
- their tests

| id | mechanism | fix | pinning test |
|---|---|---|---|
| R15-FINAL-003 (high) | `overlay_filed_periods` (correctness_gate.py:678-801) replaces `eps` and `net_income_ttm` but never recomputes `pe_ratio`. The earlier EPS/PE flag (:397-430) reasons from the un-overlaid provider net income and leaves `field_meta.pe_ratio` with a third implied P/E. | When the overlay serves `eps`, recompute `pe_ratio = ratio_price / served eps` for eps > 0. Stamp it `derived` with basis "price / exchange-filed TTM EPS" and replace the stale pe/eps flag meta. If the served EPS is ≤ 0, withhold `pe_ratio` with a reason. | pytest: a SUNRAJDI-shaped fixture (provider eps 0.08, pe 155.5, filed TTM eps 0.23, ratio_price 12.44) gives pe ≈ 54.1, basis stated, and no 141.1 reason. Fresh case: a different overlaid name with filed EPS above the provider's. |
| R15-FINAL-005 (high) | Yahoo serves nothing for `-SM.NS` (raw/investor/yf-sme.txt). `get_fundamentals` (provider_registry.py:546-565) raises not_found, so the user gets 404 'check the symbol'. Statements return an empty 200 with no reason. exchange_financials already strips `-SM` (:370-375). | When every provider is not_found for an Indian listing, build Fundamentals from `exchange_financials.get_filed_periods` through the existing `overlay_filed_periods` (revenue/NI/EPS TTM), with price from the quote lane and P/E derived. Otherwise return a typed not-covered reason ("no provider covers NSE Emerge/SME fundamentals"), not 'check the symbol'. Empty statement lanes carry the same typed reason (model + types/data.ts), and EquityOverviewPanel shows that reason. **First step: a live probe of `get_filed_periods('YASHOPTICS.NS')` saved to evidence.** If NSE has no SME XBRL, the fix is the typed reason alone, and the commit says so. | pytest with stubs: YASHOPTICS (providers not_found, filed periods present) gives a 200 with revenue/NI/EPS from NSE, basis stated. SUMAX with no filings gives the typed not-covered reason. income/balance give an empty list with the reason. vitest: EO renders the reason. |
| R15-FINAL-009 (medium, same file) | The AMAL NSE fundamentals pass Yahoo's missing marketCap/sharesOutstanding through. The app's own BSE-derived master share count (market_cap_witness.py:1-40, `_lookup`) is used only as a research witness. | In `apply_witnesses`: when `market_cap` is None for an Indian listing with a master share count for the same company, fill `shares_outstanding` and `market_cap = ratio_price × master shares`, stamped `derived` with that basis. Never override a served value. | pytest: AMAL.NS fixture with null mcap and a master count of 12,362,662 gives a derived mcap with the basis stated. A name with a served mcap is untouched. |
| R15-FINAL-024 (low, same file) | `reconcile_ownership` (correctness_gate.py:528-529) flags on `zero_mismatch` but always writes 'beyond 3pp'. | Skip the zero-mismatch flag when the absolute gap is within the band (0.00 vs 0.03 is not a disagreement). Otherwise state the actual rule. | pytest: 0.00 vs 0.03 is not flagged; 0.00 vs 12.0 is flagged with a true reason. |
| R15-FINAL-010 (medium) | earnings_provider.py:124-155: the scale check rules out `financialCurrency`, then it falls back to country India → INR even when INR is the ruled-out currency (SIFY). | When the scale check has ruled out `financialCurrency`, and the country fallback would return that same currency, return None. The estimate grid then shows no currency label rather than a wrong one. | pytest: a SIFY fixture (USD-sized 191.7M, total revenue INR 46.5bn, country India) is not INR. WIT and INFY rows stay green. |
| R15-LEAD-071 (medium, same file) | earnings_provider.py `_fetch_history_sync` swallows the `earnings_history` exception (a Yahoo 429 included) as None. routers/earnings.py:78-90 caches the empty result for 24 h. | Re-raise a rate-limit as ProviderError so `_cached` does not store it. Do not cache an empty history that came from an exception. | pytest: a stub that raises YFRateLimitError gives a typed error and no cache row; the next call refetches. |

## Writer W3 `resolver-research-docs` (sonnet)

Sonnet. The mechanisms are pinned to lines and the fixes are deterministic. The docs are mechanical.

Files, all owned by W3:

- `sidecar/services/symbol_resolver.py`
- `sidecar/services/research/relevance.py`
- `sidecar/services/research/verify.py`
- `sidecar/services/news_provider.py`
- their tests
- `docs/SIDECAR_API.md`
- `docs/redesign/R12_HAND_TESTING_GUIDE.md`
- `docs/RELEASE_RUNBOOK.md`
- `docs/MCP_INTEGRATION.md`

| id | mechanism | fix | pinning test |
|---|---|---|---|
| R15-FINAL-002 (high) | `_bse_row_is_same_company` (symbol_resolver.py:1493-1511) uses `SequenceMatcher` over the whole name key ≥ 0.75. 'globesecuretechnologies' vs 'globalspacetechnologies' scores 0.826 because the generic suffix dominates. | Compare names after dropping generic trailing words (technologies, industries/inds, enterprises, solutions, services, ltd...). Re-measure the bound over the bundled masters, so every genuine dual listing still passes and GSTL/FOCUS/ZEAL/SEL fail. Update the constant's comment with the new measurement. Measured locally: globesecure/globalspace 0.45, focuslighting/focusbusinesssolution 0.53, zealglobalservices/zealaqua 0.38. | pytest: GSTL NSE row takes no isin/bse_code (not INE632W01016/540654), and /disclosures for GSTL names no Globalspace. FOCUS still refused; a true dual listing (Black Rose, D.B.Corp) still joined; one fresh pair from the masters. |
| R15-FINAL-011 (medium, same file) | `autocomplete` (symbol_resolver.py:1672-1680) skips every BSE row whose bare ticker is in the NSE master. A `.BO` query is matched on the stripped ticker. | Skip a BSE row only when `_bse_row_is_same_company` says it is the NSE company. Rank the BSE row first for a `.BO` query. | pytest: 'Zeal Aqua' offers BSE ZEAL; ZEAL.BO puts BSE Zeal Aqua first; SEL.BO offers Sanathnagar; RELIANCE gives one row. |
| R15-FINAL-004 (high) | `_entity_signals` (relevance.py:651-711) grants `distinctive` to any ≥4-char symbol token and to brand tokens bounded in the lowercased title. The `COMMON_WORD_TICKERS` gate (:746, FOCUS listed at :502) runs only on the non-IN short path. | A symbol or brand token that is a `COMMON_WORD_TICKERS` word counts only when `anchored_ticker` holds on the original-case title, or when all distinctive name tokens match. Apply this to IN and non-IN targets alike. Pass the original title in. | pytest: for FOCUS (Focus Lighting and Fixtures), 'Focus on flying, not selfies' and 'European shares focus on inflation data' score < keep; 'Focus Lighting Q1 results' is kept. Fresh case: another common-word IN ticker from the set. RELIANCE/ROUTE/SAKSOFT unchanged. |
| R15-FINAL-027 (low, same files as 004) | news_provider passes feed titles through with no `html.unescape` (0 hits for unescape). | `html.unescape` titles and summaries once, at normalisation. | pytest: 'F&amp;O Talk' becomes 'F&O Talk'. |
| R15-LEAD-060 (medium) | verify.py:130 `_parse_verdict`: `\b` is defeated by `_`, so `_UNVERIFIED_` reads as agree (re-run at the sha). | Strip markdown emphasis (`_`, `*`, `` ` ``) around the leading token before matching. | pytest: `_UNVERIFIED_`, `__UNVERIFIED__` and `*UNVERIFIED*` are unverified; `_AGREE_` is agree. |
| R15-FINAL-021 (medium) | SIDECAR_API.md:16 says the sidecar allows all origins; macro is documented as 501 (:31, :88); 'Stub routers' (:125-136); 20 of 111 routes documented. | Regenerate the route table from the candidate's `/openapi.json` (the shared :52800 is read-only GET). Correct the origin guard (app.py ALLOWED_ORIGINS), macro and stub sections. | A check script over openapi.json and the doc: 0 undocumented routes. |
| R15-FINAL-022 (medium) | R12_HAND_TESTING_GUIDE.md:7-37 walks order placement, a brokers plugin and a paper portfolio (removed by D81). | Retire the guide: replace its body with a pointer to the release docs lane's cold hand-testing guide. No order wording survives. | Grep: 0 order/broker/paper hits in the file. |
| R15-FINAL-023 (medium) | RELEASE_RUNBOOK.md:14-15 and :70-84 merge the superseded worktree-agent-r15-version-0.9.0 branch. | Drop step 1 and that section, and state that the five sources read 0.9.0 at the candidate (06879089). | Doc review. |
| R15-FINAL-037 (low, same file) | RELEASE_RUNBOOK.md:252-262's "verbatim" ci-local block differs from package.json. | Copy it from package.json. | diff = 0. |
| R15-FINAL-035 (low) | MCP_INTEGRATION.md names 25 tools; the live surface lists 39. | Regenerate the list from tools/list on :52800 (read-only), and fix the :207 sample. | 0 live tools missing. |

## Writer W4 `lifecycle-stores` (opus)

Opus because this is data-dir persistence: quarantining a user store, and the pre-upgrade backup.

Files, all owned by W4:

- `sidecar/services/schema_version.py`
- `sidecar/services/data_cache.py`
- `sidecar/services/agents_store.py`
- `sidecar/services/runs_store.py`
- `sidecar/services/plugins_store.py`
- `sidecar/services/portfolio_db.py`
- `sidecar/services/workflow_store.py`
- `sidecar/services/fundamentals_store.py`
- `sidecar/services/workspace_store.py`
- `sidecar/app.py`
- `sidecar/main.py`
- their tests

| id | mechanism | fix | pinning test |
|---|---|---|---|
| R15-FINAL-008 (high) | data_cache._connect (data_cache.py:102-106) runs `PRAGMA journal_mode=WAL` with no DatabaseError handling, from `app._lifespan` ensure_build, so startup fails on every launch. agents_store:70, runs_store:190, plugins_store:83, portfolio_db:47, workflow_store:68 and fundamentals_store:194 are the same, so every route of that store 500s. | One shared helper beside `schema_version.migrate`. It opens the database, and on `sqlite3.DatabaseError` whose message is 'file is not a database' or 'malformed' (never 'locked') it renames the file and its -wal/-shm to `.corrupt-<ts>`, logs it and recreates the database. All seven stores use it. The cache is silent; a user store logs a one-line warning naming the quarantined file. | pytest: a corrupt header per store (data_cache at boot through the lifespan, custom_agents, delegate_runs, plugins, portfolio, workflows, fundamentals_cache). The store opens empty, the `.corrupt-*` file is kept byte-identical, and a 'database is locked' error is NOT quarantined. Fresh case: a truncated (malformed) database rather than a bad header. |
| R15-LIFECYCLE-024 (medium, same file; 1 prior failure) | The remaining failing case (rc1 round-5 l024.out.txt case a): a data dir from a pre-meta released build has no `meta` row and no legacy cache. `ensure_build` (data_cache.py:127-142) clears the cache and takes no backup. | When there is no build row and no legacy build, and the data dir already holds user stores or workspaces, back up the data dir as `backups/unversioned-<date>` before stamping the build. | pytest: a data dir with portfolio.db and a workspace but no meta table gets a backup on the first boot and none on the second. Case b stays green. |
| R15-FINAL-031 (low, same family) | `delete_workspace` (workspace_store.py:224-229) unlinks only the main file, so a later corrupt-file recovery reads the stale `.bak`. | Unlink the `.bak` with it. | pytest: PUT twice, DELETE, PUT C, corrupt it, GET does not return the deleted content. |
| R15-FINAL-028 (low, boot path) | When uvicorn returns on EADDRINUSE (main.py:140), interpreter finalisation aborts because the stdin watchdog daemon thread holds the stdin lock (exit 134). | After `uvicorn.run` returns, flush the logs and `os._exit(1)` when the server did not start, or `os._exit(0)` otherwise. The watchdog already uses `os._exit` (:61-74). | pytest subprocess: a second instance on a taken port exits non-zero and not 134 (no SIGABRT). |

## Merge order

All four sets are file-disjoint. No two writers share a test file, `types/data.ts` or `sidecar/models/` (W2 only).

1. W4 lifecycle-stores: boot path first, so every later chain boots on it.
2. W2 data-fundamentals.
3. W3 resolver-research-docs.
4. W1 portfolio-host: the largest frontend diff, rebased last.

One green `pnpm ci-local` and one smoke test then run at the integrated head before certification.

## Not planned (see the return value)

- **deferred** holds the mediums filed for 0.9.1 under the operator bar, with no room beside the critical/high sets. It holds no Tier-4 item.
- **lows_unplanned** holds the lows outside any set's files.
