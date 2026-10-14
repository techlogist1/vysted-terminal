# R15 Stage C — batch-25 plan

Base: `004-r4-experience-rebuild` @ `84280221388069a471516aa920e00c5384f2b336`. D81 (trading out) is on the base;
nothing here touches any trading surface.

**Selection.** Every OPEN register entry with severity critical/high/medium: 1 critical, 5 high, 8 medium = 14
entries (the queue given to the planner). 10 of 14 are in the operator's four areas. All 14 are planned as fixes: nothing
deferred, nothing proposed as not-a-defect. Lows are not in this batch's severities, so LOWS_TRIAGE.json was not
applied. No open low shares a root cause with a selected entry. `R15-CODE-PLATFORM-045/046` share the label
`plugin-lifecycle-split` with PLATFORM-013, but their mechanism is different (plugin-bootstrap.ts bridging without
checking loadPlugin / an unguarded `moduleForPlugin`), so they stay in the low queue.

Every mechanism below was re-read in code at the base. Where the register's latest refutation note corrects the
original claim, the plan follows the corrected mechanism, not the original title. Several entries have 2
certification failures on record (DATA-002, AGENT-019, PLATFORM-013, DATA-059, LEAD-028, RESEARCH-043), and a third
failure stops them for the operator. Writers therefore implement the refutation audit's named fix at that scope and
pin it with a test on a case the fix was not written against.

## Writers at a glance

| W | model | entries | why this model |
|---|---|---|---|
| W1 | opus | R15-DATA-002 (critical), R15-CODE-PLATFORM-013 | changes the shape of workspace-persisted state (watchlist `SymbolEntry`, `enabled` map restore/reset); risk-adjacent per the routing rule |
| W2 | sonnet | R15-DATA-059, R15-AGENT-010 | fully specified, with checkable acceptance tests (symbol_resolver.py owner) |
| W3 | sonnet | R15-LEAD-028, R15-DATA-064 | fully specified (yfinance_provider.py owner) |
| W4 | sonnet | R15-DATA-116, R15-CODE-AGENT-034, R15-DATA-113 | three S/M plumbing fixes with written acceptance tests |
| W5 | opus | R15-RESEARCH-043, R15-RESEARCH-015 | RESEARCH-043 needs a class-level root-cause design (two Sonnet regex rounds failed); 015 shares the research module ownership |
| W6 | sonnet | R15-AGENT-019, R15-AGENT-093 | specified gate and arg-coercion changes; no runtime state machine is touched |
| W7 | sonnet | R15-AGENT-053 | a single-file JSX fix with a written test |

Common rules for every writer: branch `worktree-agent-batch-25-W<n>`. First run
`git reset --hard 84280221388069a471516aa920e00c5384f2b336` (worktree base hazard) and check `git log -1`. Push
every deliverable. Edit only your owned files. Run only your focused tests; never run a full suite in the
foreground. Before a Python commit, run `ruff format <files> && ruff check sidecar`. Before a TS commit, run
`pnpm exec prettier --check <files>` and `pnpm exec eslint <files>`. Each writer returns its commit shas plus
anything out of scope, listed in issues[].

---

## W1 — opus — DATA-002 + CODE-PLATFORM-013 (frontend, persisted state)

**Owned files:** `src/store/symbols.ts`, `src/modules/watchlist/WatchlistPanel.tsx`, `src/modules/watchlist/api.ts`,
`src/lib/sidecar-client.ts`, `src/components/CommandPalette.tsx`, `src/store/modules.ts`, and the tests
`src/modules/watchlist/WatchlistPanel.test.tsx`, `src/components/CommandPalette.test.tsx`,
`src/lib/workspace.test.ts`, `src/store/modules.test.ts`, `src/store/workspace.test.ts`,
`src/components/SettingsPanel.test.tsx`. `src/lib/workspace.ts` is read-only for this batch: it needs no change
(see below).

### R15-DATA-002 (critical, ui-panels/data-smallcaps/research-search) — watchlist drops the picked listing's region
- **Mechanism (rc1 gate round 2 refutation, confirmed at base).** The chart and overview legs already carry the region.
  `loadSymbolIntoChart(symbol, tf, region)` is at host-actions.ts:321, `openCompanyOverview(symbol, metric, region)`
  at :338, and CommandPalette.tsx:394 passes `c.region`. The watchlist does not. `SymbolEntry` (symbols.ts:15-18) has
  no region. `pickCandidate(symbol)` (WatchlistPanel.tsx:286-287, called at :298 and :434) drops `c.region`.
  `fetchWatchlistQuotes` (watchlist/api.ts) calls `sidecarApi.quotes(symbols)`, and that call sends no region header
  (sidecar-client.ts:338). The row click (WatchlistPanel.tsx:560/562) and the palette's watchlist item
  (CommandPalette.tsx:207) pass no region. `setEntries` (symbols.ts) strips unknown keys, so a persisted region would
  also be lost on restore. The result: in an IN session, picking "AMAL · US" tracks, quotes and opens Amal Ltd (INR).
- **Fix.**
  1. `SymbolEntry` gains `region?: string`.
  2. `addSymbol(symbol, assetClass, region?)` de-duplicates on symbol+region.
  3. `removeSymbol(symbol, region?)` removes the matching entry. With no region given it removes every entry for that
     symbol, so the agent host action keeps its meaning.
  4. `setEntries` keeps `region` only when it is a non-empty string among the sidecar regions (`US`, `IN`, `GLOBAL`).
     The persisted blob is the trust boundary. Older blobs have no region, stay session-region, and are not rewritten.
  5. `pickCandidate(c)` takes the candidate and stores `{symbol, assetClass:'equity', region: c.region}`. A typed
     draft add stays region-less, so it follows the session.
  6. `sidecarApi.quotes(symbols, assetClass, region?)` sends `regionHeader(region)`, the same way `quote` and
     `history` already do.
  7. `fetchWatchlistQuotes` groups equity entries by region: one `/quotes` call per region (none for region-less
     entries), with quotes keyed by `region|SYMBOL`.
  8. The table `rowKey` and the selected-row compare use symbol+region.
  9. The row click passes `row.entry.region` to both host actions. CommandPalette.tsx:207 passes
     `item.symbolEntry.region`.
  10. Workspace persistence needs no workspace.ts edit. The watchlist slice serialises `entries` as they are
     (workspace.ts:360-366), and `setEntries` now keeps the field.
- **Tests (acceptance from the register note).**
  - `WatchlistPanel.test.tsx`: with settings region IN and autocomplete returning `[AMAL/NSE/IN, AMAL/US/US]`, picking
    the US option leaves `{symbol:'AMAL', region:'US'}` in the store. The next poll's `/quotes` request for AMAL
    carries `X-Vysted-Region: US`, asserted on the mocked fetch headers. A row click calls
    `openCompanyOverview('AMAL', undefined, 'US')`. The fresh case the fix was not written against: after both
    listings are picked, AMAL/IN and AMAL/US are two rows, each quoted under its own header.
  - `src/lib/workspace.test.ts`: a serialise, then deserialise, round trip keeps `region: 'US'`. An older blob
    entry without a region restores region-less. A blob region of `'XX'` is dropped.
  - `CommandPalette.test.tsx`: the palette's watchlist item for a `region:'US'` entry calls
    `loadSymbolIntoChart('AMAL', undefined, 'US')`.
- **Out of scope (issues[] if noticed):** the original fix_shape's "chooser for two confidence-1.0 cross-region
  candidates". The latest two audits scope the defect to propagating the pick, and autocomplete already lists both
  listings.

### R15-CODE-PLATFORM-013 (medium, ui-panels) — a bulk enabled-map write overwrites lifecycle-owned `plugin:*` flags
- **Mechanism (round 2 refutation, confirmed).** modules.ts:76 is `setEnabledMap: (enabled) => set({ enabled })`,
  so every caller replaces the whole map, `plugin:*` keys included. Two callers reach it. `resetToDefaultLayout`
  (store/workspace.ts:184) calls `setEnabledMap({})`, and the Settings import (SettingsPanel.tsx:2071-2079) writes
  imported `plugin:*` values through it. After either one, a plugin the runtime and plugins.db report as active has
  its panels and commands hidden (or a disabled one comes back). The Settings Modules toggle itself is already routed
  through the marketplace (SettingsPanel.tsx:1946-1947). Workspace restore already merges by hand (workspace.ts:311-314).
- **Fix (single owner, in the shared setter).**
  `setEnabledMap: (enabled) => set((s) => ({ enabled: { ...nonPlugin(enabled), ...plugin(s.enabled) } }))`, using a
  two-line inline filter in modules.ts (no import from lib/workspace.ts, which would be circular).
  From then on, `plugin:*` flags change only through `setModuleEnabled`, which the lifecycle owner calls. Leave
  workspace.ts:311-314 as it is: it is now redundant but harmless, and removing it is a refactor outside the entry.
  Add a one-line comment on the `setEnabledMap` doc saying that `plugin:*` keys are owned by the plugin lifecycle.
- **Tests.**
  - `src/store/workspace.test.ts` "resetToDefaultLayout keeps lifecycle-owned plugin:* flags (R15-CODE-PLATFORM-013)":
    seed `setEnabledMap({news:false})` plus `setModuleEnabled('plugin:vysted-example', false)`. After
    `resetToDefaultLayout`, `enabled` equals `{'plugin:vysted-example': false}`.
  - `SettingsPanel.test.tsx`: importing `enabledModules {'plugin:vysted-example': true}` while the live flag is false
    leaves it false, and a non-plugin module in the same import is applied.
  - `modules.test.ts`: `setEnabledMap({'plugin:x': true, chart:false})` over a live `plugin:x=false` gives
    `{'plugin:x': false, chart:false}`. This is the fresh case: the setter is called directly, not through either
    reported caller.

---

## W2 — sonnet — DATA-059 + AGENT-010 (symbol_resolver.py owner)

**Owned files:** `sidecar/services/symbol_resolver.py`, `sidecar/services/agent_tools/resolve_symbol.py`
(the comment only), `sidecar/tests/test_symbol_resolver.py`, `sidecar/tests/test_resolve_symbol_tool.py`.

### R15-AGENT-010 (high, agent-chat/data-smallcaps) — the live `yf.Search` has no timeout
- **Mechanism.** Both agent handlers already `asyncio.to_thread` the resolver (resolve_symbol.py:55,
  fundamentals.py:131). What remains is symbol_resolver.py:1574, `yf.Search(query, max_results=5, news_count=0)`,
  which inherits yfinance 1.3.0's `timeout=30` (search.py:34). A hung Yahoo therefore holds a worker thread, and the
  caller, for 30 s on every concurrent miss.
- **Fix.** Add a module constant `_LIVE_SEARCH_TIMEOUT_SECONDS = 5.0` next to `_LIVE_FAILURE_COOLDOWN_SECONDS` and
  pass `timeout=_LIVE_SEARCH_TIMEOUT_SECONDS`. Live misses measure 0.4 to 2.2 s. The existing except already arms
  the 60 s cooldown. Update the "up to 30 s" comment at resolve_symbol.py:52-53.
- **Test.** `test_symbol_resolver.py::test_live_lookup_passes_an_explicit_short_search_timeout`: monkeypatch
  `yfinance.Search` with a kwargs-recording class (`quotes=[]`), clear `_live_cache` and `_live_cooldown_until`, call
  `_live_lookup('zzqx nonexistent co', 'IN')`, and assert `kwargs['timeout'] <= 10`.

### R15-DATA-059 (medium, research-search) — US instruments carry no ISIN
- **Mechanism (round 2 refutation, confirmed).** The former-name half is fixed at base: `_enrich_instrument`
  (:1378-1393) joins `_former_names()['us']`. The ISIN half is open. `us_instruments.json` rows are
  `[ticker, name]` only (10,365 rows, and no generator in-repo), and `_enrich_instrument` returns before any ISIN for
  a non-NSE/BSE row. So `resolve('SIFY'|'ONC'|'AAPL').best.isin` is always null.
- **Fix (Tier-3, recorded here).** A lazy, bounded, validated ISIN lookup, applied ONLY to a US `best`, never to
  every candidate. Nothing is bundled: the lookup is the user's own runtime fetch, so no CUSIP-derived data is
  redistributed in the AGPL repo, which is why this is not a master column.
  1. New `_us_isin(symbol) -> str | None`. It GETs the keyless endpoint that yfinance's own `Ticker.isin` uses:
     `https://markets.businessinsider.com/ajax/SearchController_Suggest?max_results=25&query=<SYMBOL>`. Use `httpx`
     with `timeout=3.0`. Do NOT use `yf.Ticker.isin`: it makes an extra quote call first, has no timeout control,
     and its fuzzy `'"|'` fallback can return another company's ISIN.
  2. Parse only an EXACT keyword token `"<SYMBOL>|<ISIN>|`, and take the first one. The live response (probed at
     planning) lists `SIFY|US82655M2061|` first and the retired `SIFY|US82655M1071|` second, and
     `ONC|US07725L1026|`.
  3. Accept the value only when it matches `^[A-Z]{2}[A-Z0-9]{9}\d$`, the ISIN check digit passes (letters to
     numbers, then Luhn), and the prefix is not `IN`. The `IN` rule means an Indian ISIN can never land on a US
     namesake (the R13 TCI guard).
  4. Cache hits and definite misses per symbol for the process, in a small dict under the existing
     `_live_cache_lock`. A transport failure is not cached and opens its own 60 s cooldown.
  5. In `resolve()`, after `_enrich_resolution`: if `best` exists, `best.exchange == 'US'` and `best.isin is None`,
     replace `best` (and the identical candidate row) with the looked-up ISIN. All four callers of `resolve()` are
     already on worker threads.
  6. Add a `ponytail:` comment noting that the lookup is a scrape of a public suggest endpoint, capped at one call
     per new US symbol per process, and that a licensed identifier feed is the upgrade.
- **Tests (`test_symbol_resolver.py`, with the fetch monkeypatched to return the captured suggest text).**
  - `resolve('SIFY','US').best.isin == 'US82655M2061'`: the first exact token, not the retired one.
  - The ONC case `== 'US07725L1026'`.
  - A response with no exact token (only `SIFYX|…`) leaves None.
  - An `INE…` value is rejected, and so is a bad check digit.
  - A transport exception leaves None, and the next call inside the cooldown makes no fetch.
  - The existing TCI guard stays green, and TCI (US) keeps `bse_code` None.
  - The fresh case: `resolve('AAPL','US').best.isin == 'US0378331005'` from a captured AAPL response.
  - Live: `curl :<port>/resolve?q=SIFY` gives isin `US82655M2061`.

---

## W3 — sonnet — LEAD-028 + DATA-064 (yfinance_provider.py owner)

**Owned files:** `sidecar/services/yfinance_provider.py`, `sidecar/tests/test_yfinance_provider.py`,
`sidecar/tests/test_history.py`, `sidecar/tests/test_provider_registry_region.py`, `sidecar/tests/test_price_data.py`.
W3 does not edit `symbol_resolver.py` (W2 owns it). It only calls the existing `symbol_resolver.bse_symbol_for_code`.

### R15-LEAD-028 (medium, data-smallcaps) — scrip-code `.BO` symbols reach Yahoo unchanged
- **Mechanism (round 2 refutation, confirmed).** In `_yahoo_symbol` (yfinance_provider.py:224-225), a symbol that
  ends in `.BO` is returned as it is. `506597.BO` goes to Yahoo, which has no such symbol. Scrip-code
  canonicalisation exists only in the BSE lane (`bse_provider._require_bse`), and the fundamentals, statements,
  ratings and earnings routes never reach that lane. The correctness gate already accepts the canonical ticker for a
  code-addressed request (correctness_gate.py:136-142).
- **Fix.** In `_yahoo_symbol`: if `s.endswith('.BO')` and `s[:-3].isdigit()`, map the bare code through
  `symbol_resolver.bse_symbol_for_code`. On a hit, return `f'{ticker}.BO'`. With no mapping, pass the symbol
  through. Every yfinance-served route goes through this one function.
- **Tests.** `test_yfinance_provider.py`:
  - `_yahoo_symbol('506597.BO') == 'AMAL.BO'`
  - `_yahoo_symbol('544774.BO') == 'SMR.BO'`
  - the fresh case: `532540.BO` maps to `TCS.BO`, or whatever the bundled master maps 532540 to (assert against
    `bse_symbol_for_code`)
  - an unknown code passes through
  - `^BSESN` and `RELIANCE.BO` are unchanged

  `test_provider_registry_region.py`: with a fake yfinance, `get_fundamentals('506597.BO', region='IN')` returns
  Amal's fundamentals.

### R15-DATA-064 (medium, ui-panels) — sub-hour history requested past Yahoo's intraday window
- **Mechanism (round 2 refutation, confirmed).** The `30m` default is already `1mo` (:130). But `get_history` (:522)
  does `period = range_ or default_period`, so an explicit range goes to Yahoo unclamped: `/history?range=3mo|1y`
  at 30m, and the agent's `price_data` default of 6mo. Yahoo answers with an empty frame, and the history router's
  `_empty_series_reason` then blames the exchange (`in_eod_only`) for an IN listing.
- **Fix.** Clamp inside `get_history`, the shared function, before `ticker.history`:
  - sub-hour intervals (2m-30m): at most 60 days; `1m`: at most 7 days
  - `1h`: at most 730 days
  - convert Yahoo period strings (`Nd`, `Nmo`, `Ny`, `ytd`, `max`) to days for the compare
  - use a period string Yahoo accepts for the cap (for example `60d`, `5d`, `2y`), verified live once

  When the clamp shortens the requested range, return `partial=True` and set `coverage_start` on the series to the
  first bar's date, falling back to today minus the cap. These fields already exist (models/market.py:70-71), so
  there is no model change. Leave the router alone: once the clamp is in, `in_eod_only` fires only where no intraday
  data exists.
- **Tests.**
  - `test_yfinance_provider.py`: `get_history('AAPL','30m','1y')` calls `ticker.history` with a period of at most
    60 days, and the series has `partial=True`. `get_history('AAPL','30m','1mo')` is not clamped and
    `partial=False`. The fresh case: `1m` with `range='1mo'` is clamped to 7 days or less.
  - `test_history.py`: with a fake provider, `/history/RELIANCE.NS?timeframe=30m&range=3mo` returns bars and
    `reason` None.
  - `test_price_data.py`: `_price_data({'symbol':'AAPL','timeframe':'30m'})` returns `ok: True` on a fake.
  - Live: `curl ':<port>/history/RELIANCE.NS?timeframe=30m&range=1y'` returns bars > 0 and `reason` null.

---

## W4 — sonnet — DATA-116 + CODE-AGENT-034 + DATA-113 (sidecar plumbing + one wire mirror)

**Owned files:** `sidecar/services/bse_provider.py`, `sidecar/tests/test_bse_provider.py`,
`sidecar/tests/test_corporate_disclosures.py`, `sidecar/services/mcp_server.py`, `sidecar/tests/test_mcp_server.py`,
`sidecar/services/earnings_provider.py`, `sidecar/models/earnings.py`, `types/earnings.ts`,
`src/modules/earnings/EpsEstimateGrid.tsx`, `sidecar/tests/test_earnings_provider.py`,
`src/modules/earnings/EpsEstimateGrid.test.tsx` (new).

### R15-DATA-116 (high, data-smallcaps/ui-panels) — the SHP quarter index goes over plain httpx and gets 403
- **Mechanism (confirmed).** `_fetch_shp_index` (bse_provider.py:861-877) GETs `_SHP_INDEX_URL` (:744,
  api.bseindia.com) through `_http_get` (:175, plain httpx), and BSE answers 403. `_api_json` (:1189, curl_cffi
  `impersonate="chrome"`) is the lane every other api.bseindia.com call uses. The unit stubs monkeypatch `_http_get`
  for the index URL, which hides the problem.
- **Fix.** `_fetch_shp_index(code)` returns `_table(_api_json('SHPQNewFormat/w', {'scripcode': code}), 'Table',
  'SHPQNewFormat/w')`. `ProviderError` semantics are kept (messages become `bse SHPQNewFormat/w: …`). The only
  message-text dependency, test_ownership_check.py:93, raises its own text, so it is unaffected. The per-quarter
  XBRL download (www.bseindia.com) stays on `_http_get`. Drop `_SHP_INDEX_URL` once it is unused.
- **Tests.** Move the SHP stubs: the index is served through a monkeypatched `_api_json`, and the XBRL through
  `_http_get`. Change `_shp_http_stub` in test_bse_provider.py:618 and the stub in test_corporate_disclosures.py:872.
  The new pin `test_shp_index_rides_the_impersonated_lane`: `_http_get` raises AssertionError for any
  `SHPQNewFormat` URL, `_api_json` returns the fixture index, and `get_shareholding` returns rows.
  Live: `/disclosures/shareholding?symbol=AMAL` returns 200 on the writer's own sidecar.

### R15-CODE-AGENT-034 (high) — the MCP workspace tools hit `/workspaces` and return a bare list
- **Mechanism (confirmed).** At mcp_server.py:252-265, `list_workspaces` GETs `/workspaces` and `get_workspace` GETs
  `/workspaces/{id}`. The router prefix is `/workspace` (routers/workspace.py:21), so both calls 404. `GET /workspace`
  returns a bare `list[str]`, and `list_workspaces` skips the `_get_list` wrap (:113).
- **Fix.** `list_workspaces` becomes `return await _get_list("/workspace", "workspaces")`. `get_workspace` GETs
  `f"/workspace/{quote(workspace_id, safe='')}"`. It maps an `httpx.HTTPError` (including a raised status) to
  `{"ok": False, "error": f"GET … failed: {exc}"}` the way `_get_list` does. Correct both docstrings. The REST
  contract does not change.
- **Tests (test_mcp_server.py).** New `test_workspace_tools_reach_the_workspace_router`: with the bound-app client and
  a scratch `VYSTED_DATA_DIR`, POST `/workspace {'name':'t-ws','workspace':{'version':1}}`. Then:
  - `call_tool('list_workspaces',{})` returns a dict, with `'t-ws'` in `['workspaces']`
  - `get_workspace('t-ws') == {'version':1}`
  - `get_workspace('missing')` gives `ok False` with `'404'` in the error
  - the fresh case: a name with a space round-trips through the quoted path

  Add `('list_workspaces', '/workspace')` to the parametrisation of `test_list_tool_reports_a_failing_route_as_not_ok`.

### R15-DATA-113 (medium, data-smallcaps) — the revenue-estimate currency trusts `financialCurrency`
- **Mechanism (round 2 refutation, confirmed live at planning).** `_revenue_currency` (earnings_provider.py:101-108)
  returns `financialCurrency`, falling back to `currency` and then `'USD'`. For INFY and INFY.NS, Yahoo's
  `financialCurrency` is USD and `totalRevenue` is 2.03e10, but `Revenue Average` is 4.92e11. That figure is
  INR-sized, so the estimate is labelled USD. Live probe: WIT gives INR / 9.50e11 vs 2.45e11, TSM gives TWD /
  4.44e12 vs 1.45e12, and AAPL gives USD / 4.67e11 vs 1.14e11. Each of those three is in band, and INFY is 97x
  out of band.
- **Fix.** `_revenue_currency(payload, sample_estimate)` does a scale check. It annualises the quarterly estimate
  (x4) and compares it with `info['totalRevenue']`, which is already on the info dict and is in `financialCurrency`
  by construction, so there is no extra Yahoo call. Add `total_revenue` and `country` to both fetch payloads.
  - Within 0.3x to 3x of totalRevenue, label `financialCurrency`.
  - Otherwise, label the issuer's home currency from a small country-to-currency map (India INR, Taiwan TWD,
    United States USD, plus the few markets the app covers). Add a `ponytail:` note on the map's ceiling.
  - If neither answer is determinable, `revenue_currency = None`. Never guess a label.

  The estimate detail passes the estimate mean. `get_history` passes the newest row's `revenueEstimate`.
  `get_surprises` inherits it.

  **Wire mirror, in the same commit:**
  - `revenue_currency: str | None` in models/earnings.py:84/114/167, with the default kept.
  - `revenue_currency?: string | null` in types/earnings.ts:85/115/163.
  - EpsEstimateGrid.tsx:65 falls back to `currency` only when the field is `undefined`, which means an older cached
    payload. On `null` it formats the revenue number with no currency code.
- **Tests.**
  - `test_earnings_provider.py`: a fake INFY.NS payload (currency INR, financial_currency USD, country India,
    total_revenue 2.03e10, Revenue Average 4.9165e11) gives `revenue_currency == 'INR'`.
  - The INFY ADR (currency USD, same payload) gives `'INR'`.
  - The WIT, TSM and AAPL fakes give INR, TWD and USD.
  - The fresh case: an out-of-band estimate with an unmapped country gives `None`.
  - The same helper on the history path gives `'INR'` for INFY.
  - `EpsEstimateGrid.test.tsx`: `revenue_currency: null` renders no currency code on the revenue rows, and
    `undefined` falls back to `currency`.

---

## W5 — opus — RESEARCH-043 + RESEARCH-015 (research module owner)

**Owned files:** `sidecar/services/research/citecheck.py`, `sidecar/services/research/verify.py`,
`sidecar/services/research/finance.py`, `sidecar/services/research/deep.py`, `src/lib/brief-ingest.ts`, and the tests
`sidecar/tests/test_research_citecheck.py`, `sidecar/tests/test_research_verify.py`,
`sidecar/tests/test_research_deep.py`, `sidecar/tests/test_research_finance.py`, `src/lib/brief-ingest.test.ts`.
Do NOT edit `src/modules/research/brief-blocks.tsx` or `BriefPanel.tsx`. Both render from
`sanitizeCitationMarkers` output (brief-blocks.tsx:1075, BriefPanel.tsx:643), so a normalised `[2][3]` chips with
no renderer change.

**Why opus.** RESEARCH-043 has 2 failed fix rounds, both Sonnet regex patches (fix-r1 and fix-r2 on
`worktree-agent-rc1-4c6dfe8-fix-int@81fbfe91`, never merged). A third failure stops it for the operator.

### R15-RESEARCH-043 (medium, research-search) — the citation net only knows a bare `[n]`
- **Mechanism (confirmed).** The backend `MARKER_RE = r"\[(\d{1,3})\](?!\()"` (citecheck.py:39) drives
  `strip_invalid_markers`, `_claim_sentences` and `soften_sentence`. The frontend mirrors it in `CITE_MARKER_RE`
  (brief-ingest.ts:396), which drives `sanitizeCitationMarkers` and `countBrokenCitations`. Any bracket the grammar
  rejects is neither resolved nor flagged, so it ships verbatim.
  - The fix-r2 recheck (`docs/redesign/verification/r15/rc1/fix-r2/RECHECK.md` row rc1-drive-research-briefs:2;
    corpus in `fix-r2/recheck/gr2/live-published-scan.txt`, `fresh-backend-probe.txt`, `fresh-frontend-probe.txt`)
    showed the CLASS is "bracketed citation-position tokens that do not resolve to the rail". It is not one
    spelling family. Examples: `[2, 3]`, `[New findings]`, `[NSE filing, August 2026]`,
    `[NSE filing, August 2026; 2][3]` (the real `[2]` never chips), `[Structured: {'ok': True, …}]`, `[Structured]`,
    `[Web evidence; 2]`, `[Source 2]`, `[Sources 2, 3]`, `[exchange disclosures]`.
  - Must survive byte-identical: `[basis: …]`, `[NSE: BDL]`, `[sic]`, `[the Company]`, markdown links `[t](u)`,
    reference definitions, and the `[?]` broken marker.
  - The `Structured (tool): …` label (deep.py:987-994) is one generator of the leak: the model cites the label of a
    prompt block it was shown.
- **Fix (a class-level grammar, ONE spec implemented on both sides of the wire).**
  1. **Bracket group.** A `[…]` that is not a link, not a reference definition, and not `[?]`/`[n]`. Split its content
     on `,` and `;`.
  2. **Citation tokens:**
     - a bare integer
     - an integer range with `-` or `–`: expand it, bounded to the source count
     - `Source(s) <int-list>`
  3. **Group with at least one citation token.** It is a citation. Emit `[a][b]…` for each in-range index, in order
     and de-duplicated, and drop the label tokens. An out-of-range index is stripped by the backend and becomes
     `[?]` in the frontend. The frontend counts it as broken.
  4. **Group with no citation token, at CITATION POSITION.** Citation position means the bracket is followed,
     optionally after spaces, by clause-end punctuation, end of line or another bracket group, and it closes a
     clause of prose. Unless it matches the small editorial/identifier allow-list (`sic`, `emphasis added`,
     `EXCHANGE: TICKER`, `basis: …`), it is an unresolved pseudo-citation. The backend strips it and counts it in the
     citation-check step. The frontend replaces it with `[?]` and counts it in `countBrokenCitations`, which feeds
     the BriefPanel banner.
  5. **Label bracket mid-sentence** (`said [the Company] would`) is prose and stays untouched.
  6. **Generation side (root of the leak).** In deep.py:985-995, relabel the structured prompt block so it is not a
     bracketable source label, and state in the same prompt that only `[n]` rail markers are citations.

  Keep ONE fixture of cases, both the must-fix and the must-survive lists above, as a table in each language's test.
  They must be byte-identical inputs with identical expected outputs, so parity is pinned. Before coding, read the
  failed branch's approach (`git show 81fbfe91 --stat`) and do not repeat an enumerated-spelling design. The writer
  owns the final rule: if the citation-position definition needs adjusting against the gr2 corpus, adjust it and
  record why in the commit.
- **Tests.**
  - `test_research_citecheck.py` and `brief-ingest.test.ts`: the shared table (every corpus token above, with
    expected backend and frontend outputs).
  - Fresh cases the rule was not written against, held back from the table while designing:
    - `[Annual report, FY25; 4]` becomes `[4]`
    - `[Company filings]` at sentence end is flagged
    - `[Reuters]` at sentence end is flagged
    - `[CEO]` mid-sentence survives
    - `[3–5]` with 4 sources becomes `[3][4]` plus a broken marker
  - `ensure_citation_integrity` on a brief carrying `[2, 3]` audits the claim against sources 2 and 3
    (`_claim_sentences` sees both).
  - Live bar: one DEEP brief on the writer's own sidecar (a keyless or local lane is fine). Scan every bracket in the
    published markdown: zero unresolved label brackets at citation position.

### R15-RESEARCH-015 (medium, research-search) — independence counts hosts, not registrable domains
- **Mechanism (round 2 refutation, confirmed).** `_row_domains` (verify.py:170-177) uses `finance.domain_of`, which
  strips only `www.`. Independence (verify.py:341) and `distinct_lanes` (:344) therefore count `www.nseindia.com`
  and `nsearchives.nseindia.com` as two independent sources. The same class appears a second time in
  `deep.distinct_web_domains` (deep.py:262-269), which feeds ULTRA's `coverage_floor_met` independence floor.
- **Fix (the class, one helper).** finance.py already carries a vendored-PSL `_registrable_domain`
  (finance.py:201-211). Rename it to public `registrable_domain` (update `_looks_like_ir` and test_research_finance.py
  references), and use `finance.registrable_domain(finance.domain_of(url))` in both `verify._row_domains` and
  `deep.distinct_web_domains`. Leave `domain_of` unchanged, because the tier table keys on hosts.
- **Tests.**
  - `test_research_verify.py::test_two_hosts_of_one_registrable_domain_are_not_independent`: a SearXNG
    `['https://www.nseindia.com/q']` plus a native citation `https://nsearchives.nseindia.com/x.pdf` with
    min_domains=2 gives verdict `unverified`, corroborated False, no verdict prompts, and no "corroborated across
    channels" text. `_row_domains` over the two URLs is `{'nseindia.com'}`. The blog.example/other.example control
    stays agree/corroborated.
  - The class pin on a case the fix was not written against, in `test_research_deep.py`: web sources
    `ir.infosys.com` plus `www.infosys.com` give `distinct_web_domains == {'infosys.com'}`, and
    `coverage_floor_met(..., min_web_domains=2)` is False. A `.co.in` pair (`a.example.co.in`, `b.example.co.in`)
    counts as one.

---

## W6 — sonnet — AGENT-019 + AGENT-093 (agent gate and arg coercion)

**Owned files:** `sidecar/services/planner.py`, `sidecar/services/agent_runtime.py` (only `_normalise_tool_args` and
its helpers), `sidecar/tests/test_b3_runtime_intent_gate.py`, `sidecar/tests/test_b3_runtime_tool_args.py`.
Do not touch `_NO_TOOL_CUE` (R15-LEAD-035, stopped under the three-failure rule in batch-24) or
`_resolve_tool_surface`.

### R15-AGENT-019 (high, agent-chat/ui-panels) — a request phrased as a question classifies as read
- **Mechanism (round 2 refutation, confirmed).** `_READ_SIGNALS` has the pattern `r"\?\s*$"` (planner.py:127), so any
  trailing `?` counts as a read cue. That includes a request addressed to the agent ("Could you drop WIPRO from my
  portfolio?"). With no listed edit verb, the turn classifies read with signals, and agent_runtime's
  `read_only = inferred_intent == 'read' and bool(intent.signals)` strips every data write. Two rounds of adding
  verbs did not close it.
- **Fix.** In `classify_intent`, the bare trailing-`?` cue does not count when the text is a request to the agent
  (`\b(can|could|would|will) you\b` or `\bplease\b`). With no read signal, the turn keeps the full tool set, and data
  writes still stage for review (D-B3-3). Real read words still strip. This replaces a third round of verb-adding.
- **Tests (test_b3_runtime_intent_gate.py, via `_agent_tool_ids`).**
  - Parametrised, the needed write stays in tool_ids for: 'Could you drop WIPRO from my portfolio?', 'Can you bump
    my INFY quantity to 30?', 'Would you scrap my ITC position?', 'Can you trim INFY to 5 shares?', 'Could you get
    rid of my HDFC Bank holding?'.
  - A strip test: 'Can you explain what a P/E ratio is?', 'Is RELIANCE up today?' and 'How is my portfolio doing?'
    stay disjoint from `_DATA_WRITES`.
  - The fresh case uses a verb no cue table lists, so it passes only through the request rule: 'Could you ditch my
    ITC shares?' keeps `portfolio_delete_position`. ('note' is already an edit cue, so it cannot serve as the pin.)

### R15-AGENT-093 (high, agent-chat) — coercion only works at the top level
- **Mechanism (round 2 refutation, confirmed).** `_normalise_tool_args` (agent_runtime.py:908-960) coerces only
  `args.items()` against top-level `properties`. It never descends into `items` or nested `properties`, and
  `type(parsed) in _JSON_STRING_TYPES[expected]` refuses `'5.0'` for an integer.
- **Fix.** Replace the loop with a small recursive `_coerce(value, schema)`. It applies the existing rule at every
  depth: an exact JSON literal, the `parse_constant` guard, and a type check. It descends into `properties` for
  dicts and `items` for lists, including after a stringified array or object is parsed. For `integer`, a parsed
  float with `.is_integer()` becomes `int`. Validation afterwards is unchanged, and 'ten' and 'NaN' stay invalid.
- **Tests (test_b3_runtime_tool_args.py).** `test_nested_numeric_string_is_coerced`:
  - add_chart_drawing `points [{'price':'185.5'}]` gives 185.5
  - the stringified `'[{"price": "185.5"}]'` gives a list with 185.5
  - option_chain `max_strikes '5.0'` gives int 5
  - nested `'ten'` gives the sentinel
  - the existing `test_a_non_numeric_integer_string_stays_invalid` stays green

  The fresh case: pick one other catalog tool with a nested numeric `items` schema, check which one at base, and
  coerce its nested string.

---

## W7 — sonnet — AGENT-053 (news symbol chips)

**Owned files:** `src/modules/news/NewsFeedPanel.tsx`, `src/modules/news/NewsFeedPanel.test.tsx`.

### R15-AGENT-053 (medium, ui-panels/agent-chat) — news symbol chips are inert spans inside the article link
- **Mechanism (round 2 refutation, confirmed).** The context-bus half was certified in batch-10. What remains: the
  chips at NewsFeedPanel.tsx:138-148 are `<span>`s inside the article `<a>` (:118-150), so they are dead. A button
  cannot live inside the anchor, because interactive nesting is invalid.
- **Fix.** Close the `<a>` after the title and meta row. Render the symbol row as a sibling inside `<motion.li>`, where
  each symbol is `<button type="button" aria-label={`Load ${symbol} in chart`} onClick={() =>
  loadSymbolIntoChart(symbol)}>` with the chip styling and a visible focus ring. `loadSymbolIntoChart` comes from
  `@/lib/host-actions`, as earnings and analyst-ratings already use it. Keep the hover and focus `onFocus(item.id)`
  behaviour on the anchor.
- **Test (NewsFeedPanel.test.tsx).** `vi.mock('@/lib/host-actions')` with a spy, and render
  `newsItem({symbols:['NVDA']})`. Then `getByRole('button',{name:/NVDA/})` exists, its `closest('a')` is null, and a
  click calls the spy with 'NVDA'. The fresh case: a two-symbol item gives two buttons, and clicking the second
  loads only that symbol.

---

## Coordination and mirrors
- **Wire mirror.** DATA-113 changes `sidecar/models/earnings.py` and `types/earnings.ts` together in ONE W4 commit.
  No other writer changes a model/type pair.
- **DATA-002 needs no sidecar change.** `_RegionMiddleware` already honours a per-call `X-Vysted-Region` on
  `/quotes`. The persisted watchlist gains an optional `region`, and older blobs restore unchanged.
- **Shared-function callers.** W3 reads `symbol_resolver.bse_symbol_for_code` (unchanged), and W2 owns
  symbol_resolver.py. W2's `resolve()` ISIN step changes no signature, and W3 does not call `resolve()`.
- **RESEARCH-043.** The backend and frontend grammars live in ONE writer (W5), with one shared case table.
  The renderers (`brief-blocks.tsx`, `BriefPanel.tsx`) are untouched because they consume sanitised markdown.
- **Planner vs runtime.** W6 owns both planner.py and agent_runtime.py. Nobody else edits them this batch.

## Integrator run order
All sets are file-disjoint, so merge order is only for bisectability. Merge the sidecar-only sets first:
W4 → W3 → W2 → W6 → W5 (sidecar + brief-ingest). Then the frontend sets: W7 → W1. After each merge, run that
writer's focused tests. After the last merge, run `pnpm ci-local` once, detached and polled, then
`node scripts/smoke-test-sidecars.mjs`. W2's ISIN lookup and W4's SHP lane need network for their live bars only.
Their unit tests are offline.

## Deferred / not a defect
None. All 14 open critical/high/medium entries are planned.
