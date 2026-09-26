# R15 Stage C — batch-27 plan

Base: `004-r4-experience-rebuild` @ `e4b9554d0c18047a2417accbb454155f8718f6be`. D81 (trading out) is on the base.
Nothing here touches a trading surface.

**Selection.** The register has two OPEN entries at critical/high/medium once `R15-RESEARCH-043`, `R15-DATA-059` and
`R15-DATA-002` are excluded: `R15-DATA-117` (high, data-smallcaps) and `R15-LEAD-040` (medium, agent-chat +
data-smallcaps). Both are planned as fixes. Nothing is deferred and nothing is proposed as not-a-defect. Lows are not
in this batch's severities, so LOWS_TRIAGE.json does not apply. Both entries are new, so each has zero certification
failures. The pacing cap allows one writer set, and the two entries touch disjoint sidecar files, so they share W1.

## Writers at a glance

| W | model | entries | why this model |
|---|---|---|---|
| W1 | sonnet | R15-DATA-117, R15-LEAD-040 | The planner has already root-caused both from live probes, which are below. Each entry has a written fix and a deterministic acceptance test. Neither is safety-adjacent, persisted-state or an agent state machine. |

Common rules: branch `worktree-agent-batch-27-W1`. First run
`git reset --hard e4b9554d0c18047a2417accbb454155f8718f6be` (the worktree base hazard) and check `git log -1`. Push
every deliverable. Edit only the owned files. Run only the focused tests, and never run a full suite in the
foreground. Anything over about 120 s runs detached and is polled. Before each Python commit, run
`ruff format <files> && ruff format --check sidecar && ruff check sidecar`. Return your commit shas, plus anything
out of scope, in issues[]. There are no frontend or `types/data.ts` changes: `Fundamentals` gains no field, and the
panel already renders a `withheld` field_meta reason, as it does for P/S today.

---

## W1 — sonnet

**Owned files:** `sidecar/services/yfinance_provider.py`, `sidecar/services/yahoo_batch_provider.py`,
`sidecar/services/symbol_resolver.py`, `sidecar/routers/resolve.py`, `sidecar/routers/fundamentals.py`,
`sidecar/services/agent_tools/fundamentals.py`, `sidecar/services/agent_tools/resolve_symbol.py`.
Tests: `sidecar/tests/test_yfinance_provider.py`, `sidecar/tests/test_yahoo_batch_provider.py`,
`sidecar/tests/test_symbol_resolver.py`.

### R15-DATA-117 (high): ADR price-to-book served ok on a mixed currency basis

**Mechanism (confirmed live, 27 Sep, `.info` probe).** `get_fundamentals` withholds only the ratios in
`_MIXED_BASIS_RATIOS` (`yfinance_provider.py:420`: price_to_sales and ev_to_ebitda) when
`financialCurrency != currency`. The comment above it says Yahoo's `bookValue` is per share in the trading currency.
The probe disproves that. Yahoo's `bookValue` on a mixed-basis listing is sometimes a correct trading-currency
figure and sometimes nonsense, and nothing in the payload tells the two apart:

| symbol | ccy / fin ccy | served P/B | truth |
|---|---|---|---|
| TSM | USD / TWD | 92.17 (bookValue 4.889) | 2330.TW P/B 9.98, book 248.05 TWD ≈ $39.1/ADR |
| HDB | USD / INR | 9.32 (bookValue 2.468) | HDFCBANK.NS P/B 1.87, ≈ $12.33/ADR |
| RDY | USD / INR | 15.06 | DRREDDY.NS P/B 2.61 |
| ASML / SAP / TM | USD / EUR·JPY | 1499 / 66 / 15.5 | nonsense |
| WIT, BABA, SONY, UL, INFY.NS, HCLTECH.NS | mixed | plausible | not verifiable without FX |

`trailingPE`, `forwardPE` and `pegRatio` are consistent on every ADR probed (TSM 33.55 vs 28.98 home = the ADR
premium; HDB 16.09 vs 16.08), because Yahoo's EPS is per ADR in the trading currency. They stay served. The same class
also has two other paths. The first is `_derive_fundamentals`: when Yahoo has no `trailingEps`, the code derives
`eps = net_income_ttm / shares_outstanding`, where the net income is in the statement currency. `pe_ratio = price / eps`
then mixes the two bases. The second is `yahoo_batch_provider.fundamentals_from_v7` (the screener and warm store path).
It maps `priceToBook`/`bookValue` with no mixed-basis check at all, and never sets `financial_currency`.
`correctness_gate.reconcile_book_value` skipping foreign reporters is then moot, because a withheld field is `None`.

**Fix (Tier-3 decision, recorded here).** Keep D-B2-3's policy (no FX conversion), so a figure whose basis cannot be
verified is withheld and never converted:
1. Add `price_to_book` and `book_value` to `_MIXED_BASIS_RATIOS`. Rewrite that comment to state the probe finding.
   Make the reason truthful for every member: the figure divides or states a `{currency}` listing value against
   `{financial_currency}` statements, its basis cannot be verified without FX, so it is withheld. Keep both currency
   codes in the text.
2. In `_withhold_mixed_basis_ratios`, stamp `provider=fund.provider` instead of the module `PROVIDER`, so the v7 path
   is labelled correctly.
3. In `_derive_fundamentals`, derive `eps` only when `fund.financial_currency is None`. The P/E fallback then cannot
   run on a statement-currency EPS. Yahoo's own `trailingEps` is still used.
4. In `fundamentals_from_v7`, set `financial_currency=yfinance_provider._financial_currency(row)`, and call
   `yfinance_provider._withhold_mixed_basis_ratios(fundamentals)` when it is set, before `validate_fundamentals`.
   There is no import cycle: `correctness_gate` already imports `yfinance_provider`, and `yfinance_provider` imports
   neither.

Put a `ponytail:` comment on the dict: withholding also drops the P/B values that are correct (WIT, INFY.NS). The
upgrade path is an FX-witness reconcile (market_cap vs statement equity × FX) that re-serves the ones that agree.

**Tests.** Add one parametrised test in `test_yfinance_provider.py` using the probe's `info` numbers. For TSM (TWD),
HDB (INR) and ASML (EUR, a case the fix was not written against): `price_to_book` and `book_value` are `None`, and
their field_meta is `withheld` with both currency codes in the reason. `pe_ratio` stays served `ok` (33.55 for TSM).
For AAPL (USD/USD): `price_to_book` is 46.34 and `book_value` is 7.36, both `ok` and unchanged. Fix the existing
`test_adr_statement_sizes_carry_financial_currency_and_mixed_ratios_withheld`. It asserts SIFY P/B `ok` on the
disproved premise, so assert it withheld instead. Log why in the commit body with the TSM/HDB truth numbers. Add a
derived-EPS pin: a TWD reporter with no `trailingEps` and net income / shares present has `eps` and `pe_ratio` not
derived. In `test_yahoo_batch_provider.py`, a TSM-shaped v7 row (`currency` USD, `financialCurrency` TWD,
`priceToBook` 92.17, `bookValue` 4.889) gives both fields withheld, with `provider == "yahoo-v7-batch"`. The
existing `test_fundamentals_from_v7_maps_valuation_and_units` row, which has no `financialCurrency`, must pass
unchanged.

### R15-LEAD-040 (medium): resolver work starves the shared to_thread pool

**Mechanism (corrected from the entry).** The title blames the cold masters load. Profiling (27 Sep) shows that load
is cheap: a cold `resolve` spends about 0.05 s on the loaders. Twelve concurrent cold resolves do call
`_load_master('nse_instruments.json')` 17 times (an `lru_cache` stampede), but that is a minor cost. The real cost is
`resolve` itself. Its `_scan_names` fuzzy scan is CPU-bound, at 0.25–0.9 s per query. For a US best it also makes a
blocking `_us_isin_http_get` network call (0.8 s measured). All five call sites run it on the SHARED default executor:
`asyncio.to_thread(symbol_resolver.resolve|autocomplete, ...)` in `routers/resolve.py:63` and `:116`,
`routers/fundamentals.py:103`, `agent_tools/fundamentals.py:131` and `agent_tools/resolve_symbol.py:55`. That
executor has min(32, cpu+4) workers, which is 12 on this Mac. Twelve concurrent resolves fill every worker, and an
unrelated `to_thread` queues behind them. A warm-on-boot load would not fix this.

**Fix.** In `symbol_resolver.py`, add `_RESOLVE_POOL = ThreadPoolExecutor(max_workers=4,
thread_name_prefix="resolver")`, following the `_LIVE_SEARCH_POOL` and `services/quant/pool.py` precedent. Add
`async def resolve_async(query, region)` and `async def autocomplete_async(query, region, limit)`, which call
`loop.run_in_executor(_RESOLVE_POOL, resolve, ...)`. Look `resolve`/`autocomplete` up as module globals at call
time, so the existing `monkeypatch.setattr(symbol_resolver, "resolve", ...)` tests still intercept. Switch all five
call sites to the async helpers. Add a `ponytail:` note on the pool size. Leave the `lru_cache` stampede alone: at
most 4 concurrent loads remain, at 0.05 s each.

**Tests (`test_symbol_resolver.py`).** (a) Behaviour. Patch `symbol_resolver.resolve` with a function that blocks
on a `threading.Event`. Start N = `min(32, (os.cpu_count() or 1) + 4)` concurrent `resolve_async` calls, which is
the default pool's size, so the unfixed routing fills it. While they are blocked,
`await asyncio.wait_for(asyncio.to_thread(lambda: 1), 2)` must return 1. Then set the event in a `finally` and
assert that all N resolves return. (b) Class pin on the call sites, including `autocomplete`, which the entry never
named. Run an AST/grep audit over `sidecar/routers` and `sidecar/services`: no `asyncio.to_thread(...)` whose
first argument is a `symbol_resolver` attribute. Also run the existing `test_resolve_router.py`,
`test_resolve_symbol_tool.py`, `test_fundamentals_tool.py` and `test_b7_exchange_financials.py`. They must pass
unchanged.

---

## Integrator run order

1. Merge `origin/worktree-agent-batch-27-W1` onto 004 (there is one set, so there are no conflicts).
2. Run the focused tests, detached and polled: `test_yfinance_provider.py test_yahoo_batch_provider.py
   test_symbol_resolver.py test_resolve_router.py test_resolve_symbol_tool.py test_fundamentals_tool.py
   test_b7_exchange_financials.py test_adr_ratio.py test_company_narrative.py test_research_semantics.py
   test_screener_batch.py test_correctness_gate*.py`, then run the full pytest detached.
3. Run `ruff format --check sidecar && ruff check sidecar`.
4. Verifier notes: a live `/fundamentals/TSM` and `/fundamentals/HDB` should show P/B and book value withheld, with
   AAPL unchanged. Cached rows in `fundamentals_store` (v7 tier TTL 6 h) can still show the old P/B until they
   expire. Use a fresh data dir or wait out the TTL. That behaviour is not a failure of the fix.
