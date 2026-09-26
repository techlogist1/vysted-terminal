# R15 Stage C — batch-26 fresh-context verdicts

Verifier: Opus (fresh context). Target: `worktree-agent-batch-26-int@2e1950fe`. The main sidecar was booted from that
worktree's source on 127.0.0.1:52310, using a copy of the vysted-iso data dir (session region IN). MCP subprocesses ran
on :52153/:52154. The local model was llama3.1:8b via ollama.

**Verdict: approve.** The chain is green. Two entries certify, and nothing certified is a regression. DATA-002 is not
certified, but its delivered legs improve the product and are safe to merge.

## Chain (re-run by the verifier on 2e1950fe)
- `pnpm typecheck && vitest run`: 153 files, 1849 tests passed.
- Full sidecar `pytest`: 3645 passed, 1 skipped.
- Focused pytest (resolver, earnings provider/router/tools, research_iter, resolve_symbol tool): 143 passed. Focused vitest (watchlist, CommandPalette, command-palette store, host-actions, workspace, earnings): 238 passed.
- The integrator's `ci-local-2.log` is green end to end, and `smoke.log` reports "all sidecars booted cleanly".
- `2e1950fe` removes a `test_research_iter` assertion. That is legitimate: it pinned the grouped-marker grammar that
  3a674e7c reverted, the entry is operator-stopped (RESEARCH-043), and the bare `[n]` remap assertion stays.

## R15-LEAD-039: CERTIFIED
- Original repro, live on :52310: `/earnings/RDY/estimates`, `/TM/estimates` and `/SONY/estimates` each return **200**
  (they were 502). The EPS triple is `null`, and the revenue triple is set (e.g. RDY rev mean 84.51B INR, TM 13.35T JPY).
- Fresh case the fix was not written against: **HMC** returns 200, with the EPS triple null and revenue 5.84T JPY.
  WIT/IBN/NVO/AAPL still carry real EPS values (NVO 5.0045/5.33/4.68).
- Nothing invented: a direct `yf.Ticker('TM'/'HMC').calendar` has `Earnings Average/High/Low = None` upstream.
- Cache path: a second RDY call is 200 (0.004 s). `EpsEstimateGrid` null-glyph rendering is covered by vitest (passes).
- "No upcoming earnings event" stays a 502, as the plan intends. BABA hits it in an IN session because it binds to
  BABA.BO. Under `X-Vysted-Region: US`, BABA returns 200 with a full EPS triple.

## R15-AGENT-010: CERTIFIED
- Original live bar (`refaudit2-newhigh/a010.py hang`, a never-answering HTTPS_PROXY, cold process, this worktree):
  `'zzqx vericheck unfound co': 6.15s status=unresolved max_gap_ms=21` (the base was 31.07 s). The 6.15 s includes the
  cold masters load.
- Fresh case (warm masters, new query): `'plorvex quantum nidhi works': 5.99s max_gap_ms=21`. A masters hit (`infosys`)
  is 0.35 s. The event loop never stalls (max gap 21 ms).
- Saturation (`a010-sat.py`, 12 concurrent misses): an unrelated `to_thread` waited 15.05 s (the base was 36.89 s).
  I split this with an instrumented copy:
  - Each `_live_lookup` is now bounded at **5.34-5.69 s** under the hang (it was 30+ s).
  - The same scenario with `yf.Search` stubbed to return instantly still waits **9.39 s**. That is the cold
    resolver-masters load under 12-way contention, which exists without Yahoo and is outside this entry (see Issues).
  - The live leg's contribution is therefore about 5 s, against 30 s at the base. The literal "<= 7 s" bar assumed a
    smaller cold-load baseline than this machine measures.
- The title claim ("up to 30 s on a yf.Search miss") no longer holds, and the fix_shape (to_thread plus an explicit
  bound) is delivered.

## R15-DATA-002: NOT CERTIFIED
Delivered and verified live, with the fresh case **SMR** (SMR Jewels BSE vs NuScale US) run through the real frontend
modules (vitest) against :52310:
- `fetchWatchlistQuotes([{SMR,US},{SMR}])` in an IN session returns `8.42 USD` and `94 INR`: each listing is quoted
  under its own region.
- Agent add by name: "NuScale Power" next to a region-less SMR adds `{SMR, region:'US'}`. Repeating it gives "already
  on", and undo removes only the US listing. "SMR Jewels" next to a region-less SMR gives "already on".
- The palette lists `symbol:SMR` and `symbol:SMR:US` ("equity · US") as two items.
- Autocomplete, the chooser, offers both listings for AMAL and for SMR. The overview legs for SMR under US return
  NuScale Power, Industrials, USD.

Unfixed class site: **the agent add after the agent has already resolved the listing.** `add_to_watchlist` has no
region field (`catalog.py:1368-1377`, `parseHostAction` in `host-actions.ts:1005-1011`). `addResolvedEquity`
re-resolves whatever string it is given, under the session region.
- llama3.1:8b on :52310, IN session, prompt: "Resolve the company name 'Amalgamated Financial' to its ticker using
  the resolve_symbol tool, then add it to my watchlist."
  - `tool_use resolve_symbol {"query":"Amalgamated Financial"}` returns AMAL/US.
  - `tool_use add_to_watchlist {"symbol":"AMAL"}` is staged.
  - The model then says: "I've added Amalgamated Financial (AMAL) to your watchlist."
- Applying that proposal through the real frontend path against :52310 (`applyIntentAsync`, IN, empty watchlist) adds
  `{AMAL, region:'IN'}`, and the row quotes **674.4 INR** (Amal Ltd). SMR the same way adds `{SMR, IN}` at **94 INR**
  (SMR Jewels).
- So the wrong company is written while the agent claims the right one. The plan (fix step 11) put this agent-add
  class site in scope, and the title's "binds silently to the session region" still holds on it.
- A fix would carry the resolved listing's region on `add_to_watchlist`, as an optional `region` in the catalog
  schema and `parseHostAction`, stored as-is.

Not a regression: every changed leg behaves at least as well as the base, and the user-pick flows are fixed.

## Issues noticed (outside the entries, not in the diff)
1. Cold resolver-masters load saturates the default `to_thread` pool. With 12 concurrent first resolves, an unrelated
   `to_thread` waits about 9.4 s even when `yf.Search` answers instantly (`b26v/sat-timed.py stub`).
2. For TM, `/earnings/TM/estimates` returns `estimate_analyst_count: 1` with a null EPS triple. The count comes from
   `earnings_estimate`, which has avg 2.735 from 1 analyst, while the triple comes from the calendar (None). The two
   fields read inconsistently. `earnings_estimate` could fill the triple, but that is not in this entry's scope.
3. The `a010` scratch processes linger at interpreter exit for up to about 60 s. The abandoned yf-search pool workers
   hang on the dead proxy, which the ponytail comment in the code already names. In the long-lived sidecar this only
   holds 4 workers.
