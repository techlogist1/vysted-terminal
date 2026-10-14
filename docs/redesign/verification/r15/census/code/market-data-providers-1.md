# CODE CRITIQUE — `market-data-providers-1` (Market Data Providers, part 1/3)

APOSD critique (Ousterhout, 2nd ed.) of the 25 files / 5,925 LOC listed for this id in
`CODE_PARTITION.json`. Run under the `aposd-critique` skill.

**Run notes.** Skill invoked and followed. **Assessment independence: degraded (sequential)** —
no sub-agent tool is available to this worker, so Assessment A (Strategic Thinker) was
completed and recorded before Assessment B (Tactical Tornado) was run; both are woven below.
Snapshot persistence skipped (census output goes to this file per `tooling/COMMON.md`, not to
`.aposd/critique/`). No `.aposd/critique/ignore.md` present. Every claim below cites
`file:line`; four are backed by executed probes (marked **PROVEN**).

---

## Tactical Tornado verdict

**Risk: HIGH, and it is concentrated in a specific shape** — not sloppiness, but *good work
done once and not propagated*. The subsystem is full of carefully-reasoned, heavily-documented
modules (`nse_provider`'s cookie dance, `bse_provider`'s XBRL scale inference,
`provider_registry`'s declaration table) sitting next to modules that quietly opted out of the
very discipline those modules established.

The most damning pattern: **`yfinance_provider._yahoo_symbol` (yfinance_provider.py:97-137)
exists solely because the naive `symbol.replace(".", "-")` rule turned `RELIANCE.NS` into
`RELIANCE-NS`, which Yahoo 502s on — its own docstring calls that "the root cause of the
all-dashes Indian Equity Overview". That exact broken line is still live, verbatim, in
`earnings_provider.py:81` and `analyst_ratings_extended.py:132`.** The fix was applied to one
call site instead of to the shared concept, so two whole panels are still dead for every Indian
symbol. **PROVEN** (probe): `'RELIANCE.NS'` → `yfinance_provider` `'RELIANCE.NS'` /
`earnings_provider` `'RELIANCE-NS'` / `analyst_ratings_extended` `'RELIANCE-NS'`.

Flags found, in severity order: information leakage (4 sites: symbol normalisation ×3,
rate-limit classification ×4, dividend-yield plausibility bound ×3, holiday table reached
privately), special-general mixture (crypto special-cased *out* of the correctness gate),
pass-through variable dropped on the floor (`range_` for crypto), repetition (`_resample`
byte-identical in three providers, `_num` in five), overexposure (`_CircuitBreaker.
seconds_remaining()` is a query that mutates), and a cluster of *fabricated* values presented
on typed contracts (`earnings_provider` median/stddev/analyst-count).

Things the Strategic Thinker read as strengths that the Tornado scan caught anyway: the
correctness gate is genuinely well-designed **but is wired to exactly one caller**
(`provider_registry`) — the screener's batch path and the crypto path both run outside it, so
the "no wrong data" guarantee has two holes the architecture's own docstring does not admit.

---

## Design principles score

**8 pass, 5 at risk, 5 violate (8/18 pass).**

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | at-risk | `yfinance_provider.py:97` fixes the India symbol rule; `earnings_provider.py:81` + `analyst_ratings_extended.py:132` keep the broken copy | The same bug is fixed once and shipped twice more; two panels dead for IN |
| 2 | Deep modules | pass | `provider_registry.py:448-529` — 8 accessors hide preference order, region routing, gate, accept/fallback over 6 providers | A router adds a data source by editing one declaration row |
| 3 | Information hiding | violate | `bse_provider.py:962` reads `locale._HOLIDAYS_BY_REGION` (private); `yahoo_batch_provider.py:430` / `yfinance_provider.py:351` / `correctness_gate.py:44` each hold their own dividend-yield bound (2.0, 2.0, 0.25) | The same field is legal on one surface and withheld on another |
| 4 | General-purpose over special-purpose | violate | `provider_registry.py:456,469` — `validate = None if asset_class == "crypto"` | The one correctness mechanism is switched off for an entire asset class by an `if` |
| 5 | Different layer, different abstraction | at-risk | `bar_loader.py:96-123` `_provider_range` encodes yfinance `period` tokens inside the backtest loader | yfinance's vocabulary leaks two layers up |
| 6 | Pull complexity downward | violate | `provider_registry.py:360,410` catch only `ProviderError`; `india_provider.py:147-153,189-203` raise bare pandas errors from the parse path while `_stock_df:104-125` carefully wraps the fetch path | A column rename upstream bypasses the fallthrough entirely → 500 instead of BSE/yfinance data |
| 7 | Better together / better apart | pass | `provider_health.py` (shared Yahoo family breaker) vs `nse_provider._CircuitBreaker` (per-path) is a correct split, justified at `provider_health.py:45-49` | One poisoned NSE path cannot down the healthy ones |
| 8 | Define errors out of existence | violate | `correctness_gate.py:99,133` — `price <= 0` / `close <= 0` is `False` for `NaN`, so NaN passes; Starlette renders with `allow_nan=False` and raises | **PROVEN**: gate accepts NaN, response 500s, and no fallback provider is tried |
| 9 | Design it twice | pass | `bse_provider.py:694-759` — per-filing XBRL scale inference with a stated decisive test, plus `_validate_shp_summary:807` as the backstop | A schema change degrades to `{}`, never to a half-corrupt split |
| 10 | Comments describe what code cannot | pass | `nse_provider.py:17-45` records live-probe observations (dates, status codes, payload shapes) unreachable from the code | The next maintainer knows `quote-equity` 403s by design |
| 11 | Comments as design tool | at-risk | `earnings_provider.py:252-256` — a comment explains a dead `if eps_stddev is None` branch left behind by a hot-patch | The comment preserves history the structure should have deleted |
| 12 | Consistent naming/conventions | violate | `_is_rate_limited` exists 4× with 2 *different* predicates: `yfinance_provider.py:47` matches `"Too Many Requests"` in the message; `growth_check.py:172` / `dividend_history.py:86` / `earnings_quality.py:222` match `"ratelimit"` in the type name | The same 429 opens the shared breaker on some paths and is invisible on others |
| 13 | Obvious code | at-risk | `nse_provider.py:208-219` — `seconds_remaining()` reads as a query but performs the half-open transition | A reader who calls it for logging silently resets the breaker |
| 14 | Avoid temporal decomposition | pass | `provider_registry.py:305-318` — routing is keyed on `(model_key, asset_class, region)`, not call order | Adding `bse` was one declaration, not a new branch in five routers |
| 15 | Avoid pass-through methods | pass | `provider_registry.py:473-492` — `get_fundamentals` adds region resolution, the gate, `accept`, `fallback_ok` | Real abstraction, not a forwarder |
| 16 | Avoid pass-through variables | violate | `provider_registry.py:122-124` — `lambda symbol, timeframe, range_=None: ccxt_provider.get_ohlcv(exchange, symbol, timeframe)` accepts `range_` and discards it | The chart's range selector is a silent no-op for every crypto pair |
| 17 | Exceptions aggregated, not scattered | at-risk | `bar_loader.py:146-150` converts a provider failure into `[]` | A backtest reports metrics over a silently-reduced basket |
| 18 | Repetition eliminated | at-risk | `_resample` is byte-identical at `india_provider.py:206`, `nse_provider.py:635`, `bse_provider.py:919`; `_num` appears 5× | A resample fix must be made three times or the lanes disagree |

---

## Overall impression

The registry, the gate and the India exchange-direct lanes are the best-designed code in this
partition — genuinely deep modules with honest degradation stories. The problem is that the
**correctness contract is enforced at exactly one seam and three large code paths run around
it**: crypto (explicitly switched off), the v7 batch screener path (never registered), and any
provider that raises something other than `ProviderError` (bypasses the fallthrough entirely).
Under those holes sits a second, quieter class of defect: **values that are invented and then
presented on a typed field** — an EPS median that is the mean, a stddev that is `(high−low)/4`,
a revenue analyst count copied from EPS, a news `published_at` set to `now()` when the feed
omitted one. For a product whose stated moat is data trust, those are not rounding errors.

Single biggest opportunity: **make the correctness gate the only door.** Every value that
reaches a router should pass through it — which means registering the v7 batch path, deleting
the crypto exemption, and catching `Exception` (not `ProviderError`) at the resolver so a
misbehaving provider falls through instead of escaping.

---

## What's working

1. **The declaration table is a real single source of truth** (`provider_registry.py:114-216`
   → `active_providers():552`). `/health` is *derived*, not hand-kept, so it cannot drift from
   what the resolver actually does. Adding `bse` cost one frozen dataclass row.
2. **`accept` / `fallback_ok` is a genuinely subtle distinction, correctly drawn**
   (`provider_registry.py:219-285, 369-440`): a *wrong* result raises and falls through; an
   *incomplete-but-correct* one is held as a fallback; an all-null shell is refused rather than
   served as a dishonest 200. That three-way split is the kind of thing most codebases collapse
   into one boolean and regret.
3. **`bse_provider.parse_shp_xbrl` (694-759) + `_validate_shp_summary` (807)** — an undeclared
   upstream schema change (0-1 fraction vs 0-100 percent) is detected by a *decisive* test
   ("a single category can never exceed 1.0 as a true fraction") with a class-level backstop,
   and `_shp_cached_summary:823` re-validates on read so a disk cache written by a buggy build
   self-heals instead of replaying the bug forever. Exemplary.

---

## Priority issues

### [P0] The correctness gate accepts `NaN` — and the response then 500s with no fallback

- **Principle**: Define errors out of existence (#8)
- **Complexity symptom**: Unknown unknowns
- **Evidence**: `correctness_gate.py:99` (`quote.price is None or quote.price <= 0`), `:133`
  (`last.close is None or last.close <= 0`). `NaN <= 0` is `False`, so NaN passes both.
  NaN reaches them from `yfinance_provider.py:285-291` and `india_provider.py:197-200`, which
  build bars with bare `float(row["Open"])` — while a NaN-safe `_num()` sits in the *same file*
  (`yfinance_provider.py:218`, `india_provider.py:240`) and is applied only to `volume`.
- **PROVEN**: `validate_series` returned a series whose last close is `nan`; `validate_quote`
  accepted `price=nan`; `starlette.responses.JSONResponse.render` uses `allow_nan=False` and
  raises `ValueError: Out of range float values are not JSON compliant: nan`.
- **Why it matters**: the failure is *worse* than no gate. Because the gate says "valid",
  `_resolve_sync` returns immediately (`provider_registry.py:359`) — the healthy next provider
  is never tried — and the request dies as a 500 at render time. A user sees a hard error on a
  symbol that BSE or yfinance could have served.
- **Fix**: in `correctness_gate`, replace the two comparisons with a finite check —
  `if price is None or not math.isfinite(price) or price <= 0` — and route every provider's
  OHLC coercion through its existing `_num()` so a NaN bar is dropped at the source.

### [P0] Values are fabricated and served on typed fields as if measured

- **Principle**: Obvious code (#13) / information hiding (#3)
- **Complexity symptom**: Unknown unknowns
- **Evidence**: `earnings_provider.py:439` `eps_estimate_median=eps_mean` and `:445`
  `revenue_estimate_median=rev_mean` (comment: "yfinance does not surface a separate median");
  `:429` and `:261` `eps_stddev = max(high - low, 0.0) / 4.0` ("assume high/low span ~= 4
  stddev"); `:448` `revenue_analyst_count=analyst_count` — the *EPS* analyst count reused for
  revenue. `news_provider.py:151-158, 161-171` return `_utcnow()` for an unparseable or absent
  publication date, and `:395` then sorts newest-first, so an undated item is displayed as the
  freshest headline.
- **Why it matters**: these fields carry no provenance marker. The panel renders a median that
  is the mean and a dispersion that is an assumption, indistinguishable from real statistics —
  directly against the stance `correctness_gate.py:1-8` and `bse_provider.py:807-820` take
  everywhere else ("missing data is honest, half-corrupt is worse than none").
- **Fix**: set the median, stddev and revenue analyst count to `None` when the upstream does
  not carry them (the models already allow `None`); if the `(high−low)/4` proxy is wanted,
  ship it on a separate `eps_estimate_stddev_proxy` field or stamp it in `field_meta`. For
  news, leave `published_at` null and sort nulls last rather than minting `now()`.

### [P1] The correctness gate has three bypasses, one of them deliberate

- **Principle**: General-purpose over special-purpose (#4) / information hiding (#3)
- **Complexity symptom**: Change amplification
- **Evidence**:
  (a) **Crypto is switched off** — `provider_registry.py:456` and `:469`:
  `validate = None if asset_class == "crypto" else …`. Meanwhile `ccxt_provider.py:52`
  `price = ticker.get("last") or ticker.get("close") or 0.0` and `:66` `price=float(price)`
  serve a **0.0 price as a real quote** when the ticker carries neither field.
  (b) **The v7 batch path is never registered** — `yahoo_batch_provider.fundamentals_from_v7`
  (`:480-508`) is called directly from `screener.py:875,1222` and `fundamentals_warm.py:180`,
  so `validate_fundamentals`' plausibility bounds never run on it, and it sets no `field_meta`
  (contrast `yfinance_provider.py:404`).
  (c) **The plausibility bound is duplicated at three values** — `yahoo_batch_provider.py:430`
  accepts a dividend yield up to `2.0`, `yfinance_provider.py:351` the same, while
  `correctness_gate.py:44,231` withholds anything above `0.25`.
- **Why it matters**: the same symbol can show a 150% dividend yield in the screener and a
  withheld dash in the equity overview, and a crypto quote can print ₹0.00 as truth. The
  architecture's own claim ("after a provider returns, the registry runs the served value
  through this gate") is false for two of three consumers.
- **Fix**: delete the crypto exemption and give `ccxt_provider._ticker_to_quote` an honest
  `raise ProviderError` when no price field is present; register the batch path as a
  `ProviderDeclaration` (or call `correctness_gate.validate_fundamentals` in
  `screener`/`fundamentals_warm` at the two mapping sites); move `_PLAUSIBLE_YIELD_FRACTION`
  into the gate as the *only* bound and drop the two local `<= 2.0` guards.

### [P1] `bse_provider` re-parses the whole-market bhavcopy once per trading day

- **Principle**: Pull complexity downward (#6)
- **Complexity symptom**: Change amplification (performance is the user-visible symptom)
- **Evidence**: `bse_provider._assemble_history:424-462` loops trading days; each iteration
  calls `_bhavcopy_for:274` → `_read_cached:296` → `parse_bhavcopy:211`, which builds a full
  pandas DataFrame of every scrip on the exchange, in order to take **one row** via
  `_match_scrip:409`. There is no per-day frame memo, no per-symbol extraction, no index.
  `_quote_from_bhavcopy:540-545` runs the same loop over 14 days for a single quote.
- **PROVEN** (probe, 5,000-row synthetic bhavcopy — a realistic BSE cash-market day):
  one `parse_bhavcopy` = **332 ms**. A warm-cache chart therefore costs ≈ **8.6 s for `1mo`**,
  ≈ **82 s for `1y`**, ≈ **412 s for `5y`** of pure CPU — and ≈ **4.6 s per quote**, per BSE
  symbol on a watchlist.
- **Why it matters**: BSE micro-caps are the stated coverage differentiator ("the B/X/XT/T/Z
  groups NSE never listed"). The lane exists and is unusable at its advertised ranges.
- **Fix**: extract per-symbol series at *write* time — when `_download_bhavcopy:301` caches a
  day, also append each scrip's row to a per-code store (one SQLite table keyed
  `(code, date)`, which `data_cache`'s DB already precedents). `_assemble_history` then becomes
  one indexed range query. As a stopgap, memoise `_bhavcopy_for` per `(day)` within a call and
  cache the parsed frame, which removes the repeated parse inside one request.

### [P1] A non-`ProviderError` from a provider bypasses the entire fallthrough

- **Principle**: Pull complexity downward (#6) / consistency (#12)
- **Complexity symptom**: Change amplification
- **Evidence**: `provider_registry.py:360` (`except ProviderError`) and `:410` (same).
  `india_provider._stock_df:104-125` carefully wraps *every* jugaad failure as `ProviderError`
  — but the parse path does not: `get_quote:147-153` (`float(last["CLOSE"])`,
  `last["DATE"]`) and `_frame_to_bars:189-203` (`float(row["OPEN"])`) raise bare `KeyError` /
  `ValueError` on any column rename or unexpected cell. `nse_provider` and `bse_provider` do
  the same at `_rows_to_bars:389` / `_assemble_history:451`.
- **Why it matters**: the registry's central promise is "a failure advances to the next
  provider". An upstream schema drift — the single most likely failure mode for a scraped
  keyless source — is precisely the case that escapes it, producing a 500 while `bse` and
  `yfinance` sit ready.
- **Fix**: catch `Exception` in `_resolve_sync`/`_resolve_async`, log it at `error` with the
  provider id, and fall through (re-raise only when no candidate remains). One change at the
  resolver is smaller than wrapping every parse site, and it is the place all callers route
  through.

---

## Secondary findings (real, lower blast radius)

- **The bundled trading calendar expires in three months, silently.**
  `locale.py:59-121` — `_NSE_HOLIDAYS` ends at `2026-12-25`, `_US_HOLIDAYS` at `2026-12-25`.
  There is no regeneration script (contrast `services/resolver_masters/`), no expiry assertion,
  and no test that fails when the table lapses. After it does, `most_recent_session:173` counts
  holidays as sessions, `is_rejectably_stale:257` over-counts lag, and the gate can reject
  genuinely fresh EOD data during a holiday cluster — falling through *every* provider to
  "unavailable". Smallest fix: a test asserting the max date is ≥ 12 months out, so CI fails
  before users do.
- **A BSE 404 is cached as a permanent empty marker.** `bse_provider._download_bhavcopy:317-319`
  writes `""` on 404 and `_bhavcopy_for:287-289` then returns `None` forever. A bhavcopy
  requested before BSE publishes it (any intraday call) poisons that trading day for the life
  of the cache — that day's close never appears. Give the empty marker a TTL, or never cache a
  404 for a day ≥ today.
- **`record_success` is missing from the five busiest yfinance paths.** It is called at
  `yfinance_provider.py:252` (quote) and `:310` (fundamentals) but **not** in `get_history:267`,
  `get_income_statement:418`, `get_balance_sheet:431`, `get_cash_flow:442`,
  `get_analyst_rating:455`. Chart history is the highest-frequency Yahoo call in the app, so
  the shared breaker (`provider_health.py:126`) can stay open for up to 900 s while Yahoo is
  demonstrably healthy, needlessly degrading the screener (`screener.py:514,973`).
- **`earnings_provider.get_upcoming` is the one uncapped, un-breakered Yahoo fan-out.**
  `:314` `asyncio.gather(*(_one(sym) for sym in universe))` with no semaphore, while `_one` →
  `_fetch_calendar_sync:147` makes 3+ Yahoo round trips per symbol (`calendar`,
  `earnings_dates`, `info`, `earnings_estimate`), and it never consults
  `provider_health.is_open`. Every sibling caps at 8 (`bar_loader.py:157`,
  `yahoo_batch_provider.py:67`). A 50-symbol watchlist is ~150+ concurrent hits — enough to
  open the circuit and degrade the screener as a side effect.
- **Four divergent `_is_rate_limited` implementations.** `yfinance_provider.py:38-50` matches
  `"Too Many Requests"` in the *message*; `growth_check.py:160-175`, `dividend_history.py:74-87`
  and `earnings_quality.py:210-223` match `"ratelimit"` in the *type name*. Neither predicate is
  a superset of the other, so the same upstream 429 is reported to the shared breaker on some
  paths and swallowed as a generic failure on others. One `provider_health.is_rate_limit(exc)`
  helper, imported by all four.
- **`data_cache` is unbounded and never evicted.** `data_cache.py:107` documents that a stale
  row "is NOT auto-evicted"; `invalidate:152`, `clear:168` and `size:174` have **zero
  production callers** (grep over `services/` + `routers/` returns tests only), while
  `routers/earnings.py`, `routers/disclosures.py` and `routers/fundamentals.py` write one row
  per symbol per endpoint forever. The file grows monotonically on a local-first desktop app.
  Add a `DELETE FROM cache WHERE updated_at < ?` sweep on the stale read, or a size cap.
- **A cold-cache BSE range request silently downgrades to ≤ 8 bars.**
  `bse_provider.py:87` `_MAX_COLD_DOWNLOADS = 8` and `:437-444`. A `1y` request on a cold cache
  returns 8 daily bars in an `OHLCVSeries` carrying no partial-coverage marker, so the chart
  renders 8 points as if that were the year. The series model needs a `coverage`/`partial`
  signal, or the provider should raise so a richer lane is tried.
- **`bar_loader` turns a provider failure into an empty basket.** `bar_loader.py:146-150`
  catches `ProviderError` and returns `[]`; `load_bars:175` concatenates. The backtest engine
  then computes and reports metrics over a silently-reduced universe with no surfaced
  degradation. Return the per-symbol failures alongside the bars so the result can be labelled.
- **`active_providers()` ignores region.** `provider_registry.py:552-570` ranks over all
  declarations without applying `serves_region`, so `/health` reports
  `nse_direct (nse, bse, yfinance fallback)` for `quote` even in a US session — the one
  observable that is supposed to be *derived* and therefore trustworthy.

---

## Persona walkthrough

**Tactical Tornado.** Asked to make the Indian earnings panel work, the Tornado opens
`earnings_provider.py:81`, sees `_normalise_symbol` already exists, and adds a special case
next to it — a third spelling of a rule that already has two. Asked to make the BSE chart
faster, it adds an LRU in front of `_bhavcopy_for:274` rather than noticing that
`parse_bhavcopy:211` is building a 5,000-row frame to fetch one row, so the 332 ms stays and
only the second identical request gets cheaper. Asked for a stddev, it writes
`(high - low) / 4.0` at `earnings_provider.py:261` with a comment justifying the assumption —
and the comment is exactly what lets it ship, because it reads as rigour. Asked why crypto
quotes show ₹0.00, it adds `if price == 0: return None` at `ccxt_provider.py:52` instead of
asking why the one correctness gate is disabled for crypto at `provider_registry.py:456`.

**Strategic Thinker.** Would make the resolver the *only* door: catch `Exception` at
`provider_registry.py:360,410` so any provider misbehaviour becomes a fallthrough; delete the
`asset_class == "crypto"` exemption at `:456,469`; and register
`yahoo_batch_provider` as a `ProviderDeclaration` so the screener inherits the gate for free
instead of duplicating its bounds at `yahoo_batch_provider.py:430`. Would then collapse the
three symbol-normalisation rules into the one that is already correct
(`yfinance_provider._yahoo_symbol:97`) and export it, deleting
`earnings_provider.py:79-81` and `analyst_ratings_extended.py:130-132` — the same diff that
fixes both dead panels. Would lift `_resample` and `_num` out of the three India providers into
one `services/eod_common.py`, and would replace `bse_provider`'s per-day whole-market parse with
a per-scrip table written at download time, turning `_assemble_history` into a range query.

---

## Minor observations

- `hardware_fit.py` (397 LOC, local-LLM device gating) has nothing to do with market data
  providers; it is misfiled in this partition and inflates the LOC count that drove the
  "needs a second split" note in `CODE_PARTITION.json`.
- `nse_provider._CircuitBreaker.seconds_remaining():208-219` mutates `_opened_at`/`_blocks`
  on read; and if `_holder.ensure():251` keeps raising (a persistently blocked warm-up), the
  `ProviderError` escapes `_get_json`'s loop before `breaker.record_block():339` runs, so that
  path's circuit never opens and every request pays two warm-up attempts indefinitely.
- `ccxt_provider._sync_exchange:46-48` constructs a fresh `ccxt.Exchange` per call, so
  `fetch_ticker`'s implicit `load_markets()` re-downloads the exchange's full market list on
  every quote. One module-level instance per exchange would remove a multi-MB fetch per quote.
- `provider_registry._resolve_sync:365` / `:439` rely on `assert last_exc is not None`;
  assertions are stripped under `python -O`, which would turn the invariant into an
  `UnboundLocalError`. Raise explicitly.
- `data_cache.db_path():94` also asserts. Same note.
- `bar_loader._provider_range:96-123` maps a date window onto yfinance period tokens inside the
  backtest layer — a provider vocabulary two layers above the provider.

---

## Questions to consider

- If the correctness gate is the product's central promise, why is it reachable only through
  `provider_registry`? What would it cost to make *every* value-producing path a
  `ProviderDeclaration`, including the v7 batch and the crypto lane?
- `OHLCVSeries` carries `symbol`/`timeframe`/`provider` but no coverage or completeness field.
  Would adding one define out of existence both the "8 bars for a 1y request" problem and the
  bar_loader "silently reduced basket" problem?
- Three providers each own a byte-identical `_resample` and a near-identical `_num`. Is the
  India EOD lane actually three modules, or one module with three fetch strategies?
