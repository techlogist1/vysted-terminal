# R15 Stage C — batch-26 plan

Base: `004-r4-experience-rebuild` @ `fb1eb556c001608b16c2c370983ad2cee1aae6f6`. D81 (trading out) is on the base.
Nothing here touches a trading surface.

**Selection.** These are the OPEN register entries with severity critical, high or medium, excluding
`R15-RESEARCH-043` and `R15-DATA-059`, which are stopped under the three-failure rule (DECISIONS §4.14/§4.13). That
leaves three entries: `R15-DATA-002` (critical), `R15-AGENT-010` (high) and `R15-LEAD-039` (medium). All three are in
the operator's named areas, and all three are planned as fixes. Nothing is deferred and nothing is proposed as
not-a-defect. Lows are not in this batch's severities, so LOWS_TRIAGE.json does not apply. No open low shares a root
cause with a selected entry. The closest are `R15-UI-076` (the default watchlist ignores the IN region, a wrong-default
seed, not a dropped pick) and `R15-DATA-105` (freshness badge). Both stay in the low queue.

**Failure counts.** DATA-002 stays at two (DECISIONS §5.12: batch-25 did not deliver it, and non-delivery is not a
certification failure). AGENT-010 is at two after batch-25. A third failure stops either entry for the operator, so
each writer implements the named mechanism at full class scope and pins it on a case the fix was not written against.

## Writers at a glance

| W | model | entries | why this model |
|---|---|---|---|
| W1 | opus | R15-DATA-002 (critical) | changes workspace-persisted state (watchlist `SymbolEntry`) and the agent's watchlist write + undo in `host-actions.ts` (risk-adjacent: persistence and the agent write gate) |
| W2 | sonnet | R15-AGENT-010, R15-LEAD-039 | both have a known mechanism, a written fix and a checkable acceptance test (sidecar, plus the `types/earnings.ts` mirror) |

Common rules: branch `worktree-agent-batch-26-W<n>`. First run
`git reset --hard fb1eb556c001608b16c2c370983ad2cee1aae6f6` (worktree base hazard) and check `git log -1`. Push every
deliverable. Edit only your owned files. Run only your focused tests, and never run a full suite in the foreground.
Anything over about 120 s runs detached and is polled. Before a Python commit, run
`ruff format <files> && ruff format --check sidecar && ruff check sidecar`. Before a TS commit, run
`pnpm exec prettier --check <files>`, `pnpm exec eslint <files>` and `pnpm typecheck`. Return your commit shas, plus
anything out of scope, in issues[].

---

## W1 — opus — R15-DATA-002 (frontend; persisted state + agent write/undo)

**Owned files:** `src/store/symbols.ts`, `src/modules/watchlist/WatchlistPanel.tsx`, `src/modules/watchlist/api.ts`,
`src/lib/sidecar-client.ts`, `src/store/command-palette.ts`, `src/components/CommandPalette.tsx`,
`src/lib/host-actions.ts`. Tests: `src/modules/watchlist/WatchlistPanel.test.tsx`, `src/lib/workspace.test.ts`,
`src/components/CommandPalette.test.tsx`, `src/store/command-palette.test.ts`, `src/lib/host-actions.test.ts`.
`src/lib/workspace.ts` needs no edit: the watchlist slice serialises `entries` as they are (:360-368), and `setEntries`
is the restore path.

**Start from the batch-25 WIP.** Run `git cherry-pick b91ddef3` from `worktree-agent-batch-25-W1-data002-wip`. It
applies cleanly on the base: none of its six files changed since its parent `ef102fa5`, which is an ancestor of the
base. Read the diff before building on it. It already delivers fix steps 1-9 below except the palette leg (step 10) and
the agent leg (step 11). Reword its commit message: drop "NOT for merge as-is".

- **Mechanism (confirmed at base).** The chart and overview legs already carry a picked listing's region:
  `CommandPalette.tsx:394` calls `loadSymbolIntoChart(c.symbol, undefined, c.region)`. Three legs drop it.
  1. **The watchlist.** `SymbolEntry` (`symbols.ts:15-18`) has no region. `pickCandidate(c.symbol)`
     (`WatchlistPanel.tsx:286/298/434`) drops `c.region`. `fetchWatchlistQuotes` calls `sidecarApi.quotes` with no
     region header (`sidecar-client.ts:338`). The row click (`WatchlistPanel.tsx:560/562`) passes no region.
     `setEntries` strips unknown keys, so a persisted region would also be lost on restore.
  2. **The palette's watchlist item.** `command-palette.ts:57` types `symbolEntry` as `{symbol, assetClass}`, and
     `:318` builds the id `symbol:${entry.symbol}`, so two listings of one ticker collide as one cmdk value.
     `CommandPalette.tsx:207` then calls `loadSymbolIntoChart(item.symbolEntry.symbol)` with no region.
  3. **The agent's watchlist add (same class, second site).** `addResolvedEquity` (`host-actions.ts:2054-2081`)
     receives `reply.resolved` from `/resolve`, which carries `region` (`symbol_resolver.instrument_payload`, :314).
     Its `ResolveReply` type (:2042) drops the region, and it calls `addSymbol(symbol, "equity")`. Its idempotence
     checks (:1732, :2033, :2076) compare the bare symbol. So in an IN session with Amal Ltd (region-less AMAL)
     tracked, "add Amalgamated Financial" resolves to AMAL/US and answers "AMAL is already on your watchlist" about
     the wrong company. The undo of `watchlist-added` (:1972) calls `removeSymbol(symbol)`, which removes every listing
     of the symbol.
- **Fix.** Steps 1-9 are the WIP; confirm each one.
  1. `SymbolEntry.region?: string`. `entryKey(entry)` is `region|SYMBOL`.
  2. `addSymbol(symbol, assetClass, region?)` de-duplicates on `entryKey`.
  3. `removeSymbol(symbol, region?)`: `undefined` removes every listing of the symbol, `null` removes the region-less
     entry, and a string removes that listing.
  4. `setEntries` keeps `region` only when it is one of `REGIONS` (`US`/`IN`/`GLOBAL`), because the persisted blob is
     the trust boundary. An older blob with no region restores region-less, which follows the session.
  5. `pickCandidate(c)` stores `c.region`. A typed draft add stays region-less.
  6. `sidecarApi.quotes(symbols, assetClass, region?)` sends `regionHeader(region)`.
  7. `fetchWatchlistQuotes` makes one `/quotes` call per region group and joins rows on `entryKey`.
  8. The row key, the selection and the remove button use the listing, not the symbol.
  9. The row click passes `row.entry.region` to `openCompanyOverview`. It also passes it to `loadSymbolIntoChart` for
     the crypto branch; crypto has no region, so `undefined` is correct there.
  10. **Palette.** `PaletteItem.symbolEntry` becomes `SymbolEntry` (import the type). The id stays `symbol:SPY` for a
      region-less entry, which the existing `command-palette.test.ts:246` asserts. A regioned entry gets
      `symbol:AMAL:US`. The description shows the region (`equity · US`). `CommandPalette.tsx:207` passes
      `item.symbolEntry.region` as the third argument.
  11. **Agent add/undo.** `ResolveReply.resolved` gains `region: string`. `addResolvedEquity` stores
      `reply.resolved.region`. Its idempotence check is on the listing: an entry with the same symbol whose
      `region ?? <current settings region>` equals the resolved region. The `watchlist-added` preImage gains
      `region?: string`, and its undo removes only that listing (`removeSymbol(symbol, region ?? null)`). The
      pre-check at :2033 must not short-circuit to "already on" for a different-region listing, so apply the same
      listing predicate there or drop the symbol-only pre-check in favour of the resolved one.
      `remove_from_watchlist` removes the found entry's listing only (`removeSymbol(symbol, entry.region ?? null)`), so
      the single-entry `watchlist-removed` undo stays an exact inverse. Its restore guard compares `entryKey`. The
      sync crypto add (:1741) is unchanged: crypto has no region.
- **Tests (acceptance).**
  - `WatchlistPanel.test.tsx` (the WIP's tests; re-run them). With settings region IN and autocomplete returning
    `[AMAL/NSE/IN, AMAL/US/US]`, picking the US option leaves `{symbol:'AMAL', region:'US'}` in the store. The next
    poll's `/quotes` for AMAL carries `X-Vysted-Region: US` (asserted on the mocked fetch headers). A row click calls
    `openCompanyOverview('AMAL', undefined, 'US')`. The fresh case: after both listings are picked, there are two rows,
    each quoted under its own header.
  - `workspace.test.ts` (WIP): a serialise/deserialise round trip keeps `region:'US'`. An older blob entry restores
    region-less. A blob region `'XX'` is dropped.
  - `CommandPalette.test.tsx` (NEW): the palette's watchlist item for an `{AMAL, region:'US'}` entry calls
    `loadSymbolIntoChart('AMAL', undefined, 'US')`. With `{AMAL,IN}` and `{AMAL,US}` both tracked, the palette lists two
    distinct symbol items (no id collision).
  - `host-actions.test.ts` (NEW, the class case the WIP was not written against): settings region IN, a region-less
    `AMAL` tracked, `/resolve` mocked to `resolved:{symbol:'AMAL', region:'US', ...}`. Then
    `applyHostActionAsync('add_to_watchlist', {symbol:'Amalgamated Financial', asset_class:'equity'})` adds
    `{AMAL, region:'US'}` (the store has two AMAL entries) and does not answer "already on". Undoing that apply removes
    only the US listing, and the region-less AMAL survives. The existing `/TSLA is already on/` idempotence case
    (:1441) still passes.
- **Live bar for the verifier.** In an IN session, pick "AMAL · US" in the watchlist. The row shows Amalgamated in USD
  (~47.58); `curl -H 'X-Vysted-Region: US' :<port>/quotes?symbols=AMAL` gives USD against INR 674.4 under IN. The row
  click opens Amalgamated.
- **Out of scope (issues[] if noticed):** the original fix_shape's cross-region chooser (autocomplete already lists both
  listings; the last two audits scope the defect to propagating the pick). The agent context snapshot
  (`chat/context-provider.ts:389`) and the add/remove preview text (`host-actions.ts:1297-1310`) read symbols only.
  They carry no wrong-entity data write, so they are not in this entry.

---

## W2 — sonnet — R15-AGENT-010 + R15-LEAD-039 (sidecar + the earnings type mirror)

**Owned files:** `sidecar/services/symbol_resolver.py`, `sidecar/tests/test_symbol_resolver.py`,
`sidecar/services/earnings_provider.py`, `sidecar/models/earnings.py`, `types/earnings.ts`,
`sidecar/tests/test_earnings_provider.py`, `sidecar/tests/test_earnings_router.py`,
`src/modules/earnings/EpsEstimateGrid.test.tsx`.

### R15-AGENT-010 (high, agent-chat/data-smallcaps): the live yf.Search leg is not wall-clock bounded
- **Mechanism (batch-25 verdict, confirmed in yfinance 1.3.0 at `sidecar/.venv/.../yfinance/data.py`).** The event
  loop no longer stalls, because both agent tools already use `asyncio.to_thread` (`agent_tools/resolve_symbol.py:55`,
  `fundamentals.py:131`). The remaining defect is the caller's wait. `_live_lookup` passes `timeout=5.0` to
  `yf.Search` (`symbol_resolver.py:1686`), but yfinance's `_make_request` (:444) calls `_get_cookie_and_crumb()` with
  no timeout. `_get_crumb_basic` then calls `_get_cookie_basic()` with no timeout, and the csrf path's
  `_get_crumb_csrf()` does the same, so each leg keeps the hard-coded 30 s. A cold process with a hung upstream waits
  30-31 s per miss (measured 31.07 s), and a to_thread worker is held that long (a010-sat saturation). No yfinance
  argument reaches those legs, so the bound has to be a wall-clock deadline in our code.
- **Fix (in `_live_lookup` only).** Run the Search on a small module-level executor and wait on it with a deadline:
  `_LIVE_SEARCH_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="yf-search")`. Submit a function that
  builds `yf.Search(..., timeout=_LIVE_SEARCH_TIMEOUT_SECONDS)` and returns `.quotes`, then call
  `future.result(timeout=_LIVE_SEARCH_TIMEOUT_SECONDS)`. On `TimeoutError`, call `future.cancel()` (this drops a
  still-queued submit) and fall into the existing `except` (it arms the 60 s cooldown and returns `[]`). Keep the
  `timeout=` kwarg: `test_live_lookup_passes_an_explicit_short_search_timeout` pins it and it bounds the main request.
  Add a `# ponytail:` comment that names the ceiling: an abandoned hung search keeps its pool worker until yfinance's
  own 30 s gives up, and at most 4 are held at once. Update the constant's comment (:134-137) so it states the deadline
  covers the cookie/crumb leg. No change to `agent_tools/resolve_symbol.py`: its "capped at 5 s" comment becomes true.
- **Tests (acceptance), in `sidecar/tests/test_symbol_resolver.py`.**
  1. `test_live_lookup_is_wall_clock_bounded_when_search_hangs`: monkeypatch `_LIVE_SEARCH_TIMEOUT_SECONDS` to 0.2 and
     `yfinance.Search` to a stub whose `__init__` blocks on a `threading.Event` (set it in a `finally` so the worker
     exits). `_live_lookup('zzqx hung co','IN')` returns `[]` in < 1.0 s, and `_live_cooldown_until` is armed.
  2. The class case the fix was not written against: 8 threads, each calling `_live_lookup` with a distinct query
     against the same hung stub, all return `[]` within 0.2 + 1.0 s total. This proves queued submits time out and are
     cancelled rather than serialising behind the hung worker.
- **Live bar for the verifier.** The scratch hang race `refaudit2-newhigh/a010.py hang 'zzqx vericheck unfound co'`
  (a local never-answering HTTPS_PROXY, cold process) finishes in <= 6 s with max_gap_ms < 50, not 31.07 s.
  `a010-sat.py`'s unrelated `to_thread` waits <= 7 s, not 36.89 s.

### R15-LEAD-039 (medium, data-smallcaps): estimate detail 502s on a partial calendar
- **Mechanism (confirmed).** `earnings_provider.get_estimate_detail` (:551-555) raises
  `ProviderError("incomplete estimate fields")` when any of Earnings Average/High/Low is missing, and the router
  answers 502. The revenue triple a few lines below is already nullable. `EarningsEstimateDetail` (models :102-105)
  types the EPS triple as a required `float`, and `types/earnings.ts:101-104` mirrors it as `number`.
- **Fix.** Delete the raise. The EPS triple becomes `float | None = None` in `sidecar/models/earnings.py` and
  `number | null` in `types/earnings.ts`. Change both in ONE commit (mirror rule). Each field is independently
  nullable, the same shape as the revenue triple. `EpsEstimateGrid.tsx` already takes `number | null` in `eps()`, so it
  renders the null glyph per row and needs no change. The agent tool `earnings_estimates` dumps the model as it is.
  "No upcoming earnings event" (:543) stays an error: that is an absent event, not partial data.
  - **Planner ruling on "a stated reason".** No new reason field. The fix_shape asks for the revenue precedent's
    shape, and the revenue triple carries its nulls with no reason field. A per-field null is the stated absence, and
    the grid renders it as the shared null glyph. Adding a field would change the wire contract for no reader.
- **Tests (acceptance).**
  1. `test_earnings_provider.py`: a fake calendar with an Earnings Date and Revenue Average/High/Low but no Earnings
     Average/High/Low returns a detail with the EPS triple `None`, the revenue triple set, and no raise.
  2. The case not written against: Earnings Average present with High/Low missing keeps the mean and nulls
     high/low.
  3. `test_earnings_router.py`: `/earnings/<SYM>/estimates` over that partial provider answers 200, not 502, and a
     second call served from the cache validates too.
  4. `EpsEstimateGrid.test.tsx`: an estimate with a null EPS triple and a set revenue mean renders the EPS rows as the
     null glyph and the revenue mean formatted.
- **Live bar for the verifier.** `GET /earnings/RDY/estimates`, `/TM/estimates` and `/SONY/estimates` answer 200. A
  fresh foreign name the fix was not written against does too. Upstream-null fields are null, never invented.

---

## Coordination notes

- **File ownership is disjoint.** W1 owns only frontend files. W2 owns the sidecar files, plus `types/earnings.ts` and
  `EpsEstimateGrid.test.tsx`. W1 touches no earnings file, and W2 touches no watchlist, palette or host-actions file.
- **Wire mirror.** LEAD-039 changes `sidecar/models/earnings.py` and `types/earnings.ts` together in ONE W2 commit.
  DATA-002 needs no sidecar change: `_RegionMiddleware` already honours a per-call `X-Vysted-Region` on `/quotes`, and
  `/resolve` already returns `resolved.region`.
- **Persisted state.** The watchlist slice of `SerializedWorkspace` gains an optional per-entry `region`. Older blobs
  restore unchanged (region-less follows the session), so no migration is needed.
- **Tier check.** No Tier-1 file is touched (`types/plugin.ts`, CI, `tauri.conf.json`, licensing, `CLAUDE.md`). No §6.5
  surface is involved. The host-actions change keeps the agent write on the proposed-changes gate. It only changes
  which listing is written and what the undo removes.

## Integrator run order

1. Merge W2 first (sidecar + mirror). Run its focused tests: `pytest sidecar/tests/test_symbol_resolver.py
   sidecar/tests/test_earnings_provider.py sidecar/tests/test_earnings_router.py sidecar/tests/test_earnings_tools.py`
   (detached), then `vitest run src/modules/earnings`.
2. Merge W1. Run `vitest run src/modules/watchlist src/components/CommandPalette.test.tsx
   src/store/command-palette.test.ts src/lib/host-actions.test.ts src/lib/workspace.test.ts`, plus `pnpm typecheck`.
3. Run `pnpm ci-local` once, detached and polled, then `node scripts/smoke-test-sidecars.mjs`.

## Deferred / not a defect

None. All three selected entries are planned.
