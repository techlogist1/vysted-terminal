# APOSD critique — subsystem `fundamentals-profile`

**Subsystem:** Fundamentals & Profile Contract (field_meta)
**Partition entry:** `docs/redesign/verification/r15/census/CODE_PARTITION.json` → `fundamentals-profile` (9 files, 2689 LOC, 5 test files)
**Reviewer model:** `claude-opus-5[1m]`
**Skill:** `aposd-critique` loaded and followed (two personas, 18 principles, file:line evidence).
**Assessment independence:** degraded (sequential — Strategic Thinker pass completed before Tactical Tornado scan; no sub-agents dispatched, per the run's parallelism budget).
**Snapshot persistence:** SKIPPED — this run is read-only on the repo except its own output files, so `.aposd/critique/` was not written. No trend line available.

Owning files read in full: `sidecar/models/fundamentals.py`, `sidecar/routers/fundamentals.py`,
`sidecar/services/agent_tools/fundamentals.py`, `sidecar/services/fundamentals_seed.py`,
`sidecar/services/fundamentals_store.py`, `sidecar/services/fundamentals_warm.py`,
`sidecar/services/screener_universes/__init__.py`,
`sidecar/services/screener_universes/regenerate_fundamentals_seed.py`, `types/data.ts` (Fundamentals section).
Boundary files opened to settle claims: `sidecar/app.py:312`, `sidecar/services/errors.py:27`,
`sidecar/services/yfinance_provider.py:53-65,320-342`, `sidecar/models/screener.py:58-97`,
`sidecar/models/market.py:14-29`, `sidecar/services/data_cache.py:74-160`, and the five test files.

---

## Tactical Tornado verdict

**Risk: medium-low on the store, medium-high on the seams.**

This is not tornado code. `fundamentals_store.py` is one of the better-reasoned files in the
repo: the soundness contract on `prefilter` (`fundamentals_store.py:21-24`) is stated, then
actually held by `_criterion_fails_sql` returning `None` for anything it cannot soundly
translate (`fundamentals_store.py:671,676,688`); the per-tier authority rules
(`upsert_v7` clears its tier, `upsert_info` clears only `.info`-only fields —
`fundamentals_store.py:327-332,397-402`) are exactly the kind of decision a tornado never makes.
The comments carry a *reason*, usually a past incident, not a restatement of the code.

The damage is concentrated where this subsystem meets its neighbours, and it has one shape:
**truth that is declared in several places and enforced in none.** Six instances, all proven:

| # | Red flag | Location | Proof |
|---|---|---|---|
| 1 | Information leakage (most damning) | `fundamentals_store.py:67-95` ↔ `regenerate_fundamentals_seed.py:33-61` ↔ `models/screener.py:58-93` | three hand-kept copies of the same 27-field column vocabulary; drift in the third raises `sqlite3.OperationalError: no such column` inside `prefilter` |
| 2 | Information leakage | `fundamentals_store.py:176-182` vs `:67-95,121-152` | `_migrate` hardcodes 3 columns and does not derive from `_NUMERIC_FIELDS`; proven `OperationalError: table fundamentals has no column named ebitda_margin` on the next field added |
| 3 | Information destruction + repetition | `agent_tools/fundamentals.py:67-68` then `:44-51` | `ProviderError.kind` is thrown away, then re-derived by substring; proven `kind="not_found"` → `reason="provider_error"` |
| 4 | Inconsistency (same policy, two answers) | `routers/fundamentals.py:104-115` vs `app.py:312-315` | proven `GET /fundamentals/X` → 429, `GET /fundamentals/X/income` → 502 on the identical throttle |
| 5 | Repetition | `routers/fundamentals.py:206-222, 225-241, 244-260` | three verbatim copies of get-cache / validate / fetch / set, each with an `except ProviderError → 502` the global handler already performs |
| 6 | Temporal decomposition / duplicated work | `fundamentals_warm.py:418-424` and `:203-208` | the boot seed is scheduled twice on an IN boot, concurrently, by two unrelated code paths |

The most damning single pattern is **#2**, because it is silent, it is dormant, and it fires on
*users*, not on CI: `cargo test`/`pytest` build a fresh DB every time, so the migration gap is
invisible until an existing install upgrades and every `upsert_v7` starts raising.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | **pass** | `fundamentals_store.py:327-332` — the v7-authority comment names the live bug the old tactical behaviour caused ("a vanished value … served as fresh forever") and the code was rewritten, not patched | Design debt is being paid down, not accrued. |
| 2 | Deep modules | **pass** | `fundamentals_store.prefilter` (`:704-753`) — 50 lines of caller-facing interface hides tier TTLs, SQL translation, chunking, soundness and lock discipline behind `prefilter(symbols, criteria, quote_ttl=…) -> list[str]` | High benefit/interface ratio; the screener never learns the schema. |
| 3 | Information hiding | **violate** | `fundamentals_store.py:67-95` vs `regenerate_fundamentals_seed.py:33-61` vs `models/screener.py:58-93`; `_migrate` `:176-182` | The column vocabulary is public knowledge in three modules and the migration in a fourth. Change amplification: one new ratio = four edits, three of which fail silently. |
| 4 | General-purpose deeper than special-purpose | **at-risk** | `fundamentals_store.row_to_pair:529-558` builds only `_NUMERIC_FIELDS`, so `revenue_ttm`/`net_income_ttm`/`free_cash_flow`/`dividend_per_share`/`field_meta` are always `None` on the store path | A `Fundamentals` from the store is a different animal from a `Fundamentals` from a provider, but the type says they are the same. |
| 5 | Different layer, different abstraction | **violate** | `agent_tools/fundamentals.py:67-68` collapses a structured `ProviderError(kind=…)` into a string, and `:44-51` parses the string back | The agent layer re-implements, badly, a classification the provider layer already made. |
| 6 | Pull complexity downward | **violate** | `routers/fundamentals.py:104-115` keeps the `kind`→HTTP-status map in ONE route while `app.py:312-315` owns the translation for every other route in the app | Every future route must remember to re-do the mapping; eight routes in this file already forgot. |
| 7 | Better together or better apart | **at-risk** | `fundamentals_store.freshness:799-813` reports 3 tiers; `services/screener.py:625,666,806` independently computes a 4th (`seed_as_of`) | Two implementations of "the honest-coverage block"; the store's own is the incomplete one. |
| 8 | Define errors out of existence | **violate** | `models/fundamentals.py:39` `status: str` (any string validates) vs `types/data.ts:179` `status: "ok" \| "withheld" \| "unavailable"`; `:128` `field_meta: dict[str, FieldMeta] \| None` | The subsystem's core invariant ("per-field provenance on every value") is *optional* in the type, so absence is legal and exactly one producer honours it. |
| 9 | Design it twice | **pass** | `fundamentals_store.py:59-63` + `info_priority:756-793` — the failed-fetch rotation is visibly a second design after the first wedged the crawler | The alternative (never-attempted-first only) is documented as rejected with its failure mode. |
| 10 | Comments describe what code cannot | **pass** | `fundamentals_store.py:406-424` (`upsert_eod_batch` "Deliberately NEVER stamps `v7_updated_at`"), `agent_tools/fundamentals.py:351-355` | Comments carry *why*, anchored to incidents; a reader can reconstruct the reasoning. |
| 11 | Interface comments precede implementation | **pass** | `models/fundamentals.py:19-44` (`FieldMeta`), `:46-57` (units are documented per field group) | A consumer can use the contract without reading the provider. |
| 12 | Choosing names | **at-risk** | `fundamentals_store.py:286` maps `row["seed_as_of"]` → column `seed_updated_at`; `_NUMERIC_FIELDS` means "screener-relevant numerics", not "all numeric fields of `Fundamentals`" | Two names for one concept across a 5-file boundary; `_NUMERIC_FIELDS` misleads on first read. |
| 13 | Modifying existing code keeps the design clean | **at-risk** | `routers/fundamentals.py:206-260` — Phase-6 ratings routes were appended as three copies rather than folded into the existing surface | Each later cache change is a 3× edit with no test that they stay identical. |
| 14 | Consistency | **violate** | `routers/fundamentals.py:73` wraps `symbol_resolver.resolve` in `asyncio.to_thread`; `agent_tools/fundamentals.py:119` calls the identical function directly on the loop. `:74` guards it with `try/except`; `:119` does not | Same call, two blocking behaviours and two failure contracts, inside one subsystem. |
| 15 | Code should be obvious | **at-risk** | `fundamentals_store.py:596` `if field not in v7_set and field not in ("price","change_percent_1d","volume")` re-spells the keys of `_QUOTE_FIELD_COLUMNS` (`:635-639`) as a literal | A reader cannot tell the two lists must agree; adding a quote field breaks `query()` silently. |
| 16 | Heed the red flags as they appear | **at-risk** | `fundamentals_warm.py:366` `await asyncio.gather(*(_one(s) for s in batch))` with no `return_exceptions=True`, while `upsert_info` at `:362` sits *outside* the per-symbol `try` | One store write failure aborts the cycle's accounting and orphans the siblings' results. |
| 17 | Designing for performance | **at-risk** | `fundamentals_warm.py:418-424` + `:203-208` — two full `india-all` universe builds + seed-pack loads at every IN boot; `_connect()` (`:164-169`) re-runs `executescript(_SCHEMA)` + `PRAGMA table_info` on every single call | Boot does double work; every store call pays a schema round-trip (mitigated only because the hot paths batch). |
| 18 | Complexity is incremental — resist it every time | **pass** | `fundamentals_seed.py:40-50` — the loader's failure ladder degrades to `{}` with a *named* reason per exception class, rather than a bare `except Exception` | The seed lane cannot take the app down, and the reason is logged at the right level. |

**Summary: 6 pass, 7 at risk, 5 violate (6/18 pass).**

---

## Overall impression

The store is well built and the reasoning behind it is recoverable from the code — that is rare
and worth protecting. The problem is not inside any one file; it is that **this subsystem's
defining promise — per-field provenance on every fundamentals value — is enforced by
convention rather than by structure, at every one of its five boundaries.** `field_meta` is
optional and has exactly one producer. `status` is a free string on the Python side and a closed
union on the TypeScript side. `growth_basis` asserts `"mrq_yoy"` by default on payloads whose
growth numbers came from a months-old seed pack. The column vocabulary that decides what the
store can even *hold* is typed out three times by hand.

The single biggest complexity reduction: **make the contract's invariants structural.** One
declaration of the column vocabulary that the schema, the migration, the exporter and the
screener's field Literal all derive from; `Literal[...]` on `FieldMeta.status`; and the
`ProviderError.kind` → HTTP-status map living once, in `app.py:312`. That is roughly 60 lines of
deletion and four `Literal`/derivation changes, and it closes five of the fifteen findings below.

---

## What's working

1. **Soundness is enforced, not asserted.** `prefilter`'s contract ("pruning may only widen")
   is held by `_criterion_fails_sql` returning `None` (`fundamentals_store.py:671,676,688`) and
   by `_fresh_sql` (`:691-701`) requiring the value's own tier stamp. The 2025 fix at `:694-696`
   — "hardcoding the full-market TTL here let a curated screen prune on a quote up to 10 minutes
   old" — shows the invariant being actively defended. *Reduces unknown unknowns:* a screener
   author cannot accidentally make the prune phase lie.
2. **Per-tier write authority is the right abstraction.** `upsert_v7` clears its whole tier
   (`:331-332`), `upsert_info` clears only `_INFO_ONLY_NUMERIC_FIELDS` and writes v7 fields
   only when non-`None` (`:397-402`), and `upsert_eod_batch` deliberately refuses to stamp
   `v7_updated_at` (`:421-424`). Three writers, one column set, zero ambiguity about who owns
   what. *Reduces change amplification:* a new lane picks a tier and inherits the rules.
3. **The crawler's failure rotation is a genuinely second design.** `info_priority`
   (`:756-793`) plus `mark_info_failure` (`:465-470`) plus the throttle carve-out at
   `agent_tools`-adjacent `fundamentals_warm.py:351-355` ("a throttle is NOT absence") together
   solve the wedge without starving coverage. *Reduces cognitive load:* the priority rule is one
   sort key, stated in the docstring, matching the code exactly.

---

## Priority issues

### [P0] The contract's central invariant is optional, and one of six producers honours it

- **Principle:** Define errors out of existence (#8); Information hiding (#3)
- **Complexity symptom:** Unknown unknowns
- **Evidence:** `models/fundamentals.py:128` — `field_meta: dict[str, FieldMeta] | None = None`.
  The only populating producer in the tree is `services/yfinance_provider.py:188`
  (`_served_field_meta`). `fundamentals_store.row_to_pair:531-539` constructs `Fundamentals`
  with no `field_meta`; proven at runtime: `field_meta=None`. `openbb_mcp_provider.py:385`,
  `bse_provider.py`, and the bhavcopy lane likewise emit none.
- **Why it matters:** The subsystem exists to make "where did this number come from and when"
  answerable per field. Because absence is legal, a consumer cannot distinguish *"this provider
  does not do provenance"* from *"this field has no provenance"* — and the India screener, which
  serves the entire full-market universe through the store path, is in the first bucket for every
  value it renders. `types/data.ts:151-155` promises the same optionality to the frontend, so no
  TypeScript check will ever force the gap closed.
- **Fix:** Make `field_meta` non-optional on `Fundamentals` with a producer-side default that
  marks every populated field `status="ok"` carrying `provider` + the row's serving stamp, and
  have `row_to_pair` derive it from the row's `seed_updated_at`/`v7_updated_at`/`info_updated_at`
  columns (the data is already in the row — `fundamentals_store.py:141-146`). Providers that
  cannot do better emit `status="unavailable"` rather than an absent map.

### [P0] `_migrate` does not derive from the schema — the next numeric field breaks every existing install

- **Principle:** Information hiding (#3) / Information leakage
- **Complexity symptom:** Change amplification + unknown unknowns
- **Evidence:** `fundamentals_store.py:121-152` builds `_SCHEMA` from `_NUMERIC_FIELDS`
  (`:67-95`), but `_migrate:176-182` iterates a hardcoded 3-tuple
  `(("info_failed_at","REAL"),("seed_updated_at","REAL"),("eod_updated_at","REAL"))`.
  `CREATE TABLE IF NOT EXISTS` is a no-op on an existing table (`:173-174` says so).
- **Failure scenario (proven):** append `"ebitda_margin"` to `_NUMERIC_FIELDS` and
  `_V7_NUMERIC_FIELDS`, open an existing `fundamentals_cache.db` →
  `_connect()` does **not** add the column, and `upsert_v7` raises
  `sqlite3.OperationalError: table fundamentals has no column named ebitda_margin`. Fresh DBs
  (every test, every CI run) get the column from `_SCHEMA` and pass, so nothing catches it.
- **Why it matters:** This fires on upgrade, on users, after CI is green. `upsert_v7_batch`
  (`:359-364`) has no per-row error handling, so the whole India sweep dies on the first write.
- **Fix:** Replace the hardcoded tuple with a derivation from one declaration — parse the
  expected column set from the same list that builds `_SCHEMA`
  (`{*_NUMERIC_FIELDS, *_NON_NUMERIC_COLUMNS}`) and `ALTER TABLE ADD COLUMN` for every name
  `PRAGMA table_info` does not report. Add one test that opens a DB created from a trimmed
  `_NUMERIC_FIELDS` and asserts the column appears after `_connect()`.

### [P1] The throttle/not-found classification dies at four of nine routes

- **Principle:** Pull complexity downward (#6); Consistency (#14)
- **Complexity symptom:** Change amplification
- **Evidence:** `routers/fundamentals.py:104-115` maps `ProviderError.kind` → 429 / 404 / 502
  inline in `get_fundamentals`. `app.py:312-315` maps **every** `ProviderError` to a flat 502,
  ignoring `kind`. `/income:180`, `/balance:186`, `/cashflow:192`, `/ratings:198` have no
  handling and fall to the global one — even though `yfinance_provider.py:424,437,448,463` raise
  those failures through `_provider_error` (`:53-65`), which *does* set `kind="rate_limited"`.
- **Failure scenario (proven with `TestClient`):** with the registry raising
  `ProviderError(..., kind="rate_limited")`, `GET /fundamentals/RELIANCE.NS` → **429**,
  `GET /fundamentals/RELIANCE.NS/income` → **502**, `/balance` → **502**, `/ratings` → **502**.
- **Why it matters:** This is exactly the D53 scenario the repo already fought — a Yahoo-throttled
  Indian IP. The equity-overview panel opens all five endpoints; one tells the client to back off
  and four tell it the provider is permanently broken, so it retries into the throttle and shows
  "provider error" where the truth is "throttled". And per the CLAUDE.md CORS gotcha, the user
  sees it as a CORS failure.
- **Fix:** Move the `kind`→status map into `app.py:312-315` (`rate_limited`→429,
  `not_found`→404, else 502) and **delete** `routers/fundamentals.py:104-115` and the three
  redundant `except ProviderError → 502` blocks at `:219-220,238-239,257-258`. Net deletion;
  every route in the app gets the honest status.

### [P1] The agent tool destroys `ProviderError.kind`, then guesses it back from the message

- **Principle:** Different layer, different abstraction (#5); Define errors out of existence (#8)
- **Complexity symptom:** Cognitive load + silently wrong output
- **Evidence:** `agent_tools/fundamentals.py:67-68` — `except ProviderError as exc: return
  _FetchResult(None, f"provider error: {exc}")` (the `kind` attribute is discarded).
  `_classify_reason:44-51` then substring-matches `_RATE_LIMIT_MARKERS`/`_NOT_FOUND_MARKERS`
  (`:33-41`) to rebuild it.
- **Failure scenario (proven):** `yfinance_provider.py:334-337` raises
  `ProviderError("Yahoo has no company record for 'KSE.NS'", kind="not_found")`. None of
  `("not found","no data","no such","unknown symbol","delisted","404")` appears in that string,
  so `_classify_reason` returns `"provider_error"`. Same for `:339-342`
  ("returned a non-company (fund-id) record"). The R13 vocabulary's stated purpose
  (`:24-31`) is inverted: the model is told "OUR feed's gap — the data may well exist" when the
  truth is "this instrument does not exist", and it will narrate the wrong cause.
- **Why it matters:** `test_rate_limited_failure_is_classified`
  (`tests/test_fundamentals_tool.py:90-101`) constructs `ProviderError("429 too many requests")`
  with **no `kind=`** — the test only ever exercises the substring path, so the real
  classification is untested and the suite stays green.
- **Fix:** Carry the kind: give `_FetchResult` a `kind: str | None` field set from `exc.kind` at
  `:67`, and make `_classify_reason` a pure fallback for the un-kinded case only. Retarget the
  test to the real raise sites.

### [P2] Three hand-kept copies of the column vocabulary, with `prefilter` as the blast radius

- **Principle:** Information hiding (#3) / Information leakage
- **Complexity symptom:** Change amplification
- **Evidence:** `fundamentals_store.py:67-95` (27 names, builds the SQL schema),
  `regenerate_fundamentals_seed.py:33-61` (the same 27 names, decides what the *shipped seed
  pack* contains), `models/screener.py:58-93` (26 of them + the 3 quote fields, the criterion
  Literal). Verified identical today; nothing asserts it. `_criterion_fails_sql:669-687` uses
  `col = criterion.field` **verbatim** as a SQL identifier for string/set criteria, with no
  allow-list.
- **Failure scenario (proven):** add a field to `ScreenerNumericField` without adding the column
  → `prefilter` raises `sqlite3.OperationalError: no such column: ebitda_margin` inside
  `_work` (`:740-749`), uncaught, mid-screen. Add a field to the store without adding it to the
  exporter → the bundled seed pack silently under-exports and every fresh install screens on a
  NULL column, with no error anywhere.
- **Fix:** One declaration. Export `_NUMERIC_FIELDS` from `fundamentals_store` and derive
  `ScreenerNumericField` and the exporter's list from it (`Literal[*_NUMERIC_FIELDS, "price",
  "change_percent_1d", "volume"]` works on 3.13); add an assertion in `_criterion_fails_sql`
  that `col` is in the known column set before it reaches SQL.

---

## Remaining findings (P2/P3)

- **[P2] Double boot seed.** `fundamentals_warm.py:416-424` schedules `_boot_seed()` *and*
  `_sweep_loop:203-208` runs `seed_india_store()` on its first IN cycle behind a local `seeded`
  flag. Nothing coordinates them, so an IN boot builds the 5k-symbol `india-all` row list and
  loads the gzip seed pack **twice**, concurrently, both contending `fundamentals_store._lock`.
  Idempotent (NULL-fill only) so not wrong data — just double boot cost and a reader who cannot
  tell which path is authoritative. *Fix:* delete the `seeded` flag from `_sweep_loop`; the
  start-up path already owns the seed.
- **[P2] The boot-seed task is untrackable, and the leak test cannot see it.**
  `fundamentals_warm.py:424` `loop.create_task(_boot_seed())` discards the handle, so
  `stop_warm_fundamentals:433-444` (which cancels `_sweep_task`/`_crawl_task`/`_bhavcopy_task`)
  cannot cancel it — a shutdown mid-seed leaks it, and asyncio may GC the task while it runs.
  `tests/test_fundamentals_warm.py:288-289` asserts "no leaked tasks" but its own comment says
  "Region defaults to US in tests" — the `get_region() == "IN"` branch that creates the task is
  never entered, so the one test that would catch this is structurally blind to it. *Fix:* store
  it as `_seed_task` and include it in the cancel list; add `monkeypatch` of the region to the
  leak test.
- **[P2] `gather` without `return_exceptions`, and the store write outside the guard.**
  `fundamentals_warm.py:362` `await fundamentals_store.upsert_info(symbol, rich)` sits *outside*
  the per-symbol `try` (`:344-361`), and `:366` gathers with no `return_exceptions=True`. One
  sqlite failure aborts the gather, discards the `fetched` count, and leaves siblings' exceptions
  unretrieved. *Fix:* `return_exceptions=True` plus move the upsert inside the try.
- **[P2] `row_to_pair` turns "unknown" into asserted values.**
  `fundamentals_store.py:550-553` — `change=row.get("quote_change") or 0.0`,
  `change_percent=… or 0.0`, `currency=row.get("quote_currency") or "USD"`. Proven: a row with
  `quote_price=100.0` and NULL change/currency yields `change=0.0, change_percent=0.0,
  currency='USD'`. A genuinely unknown day-change renders as a confident "unchanged" in the
  screener table (`services/screener.py:748` is the consumer), and the USD fallback ignores the
  row's own `currency` column (which the seed pack populates with `"INR"` —
  `fundamentals_store.py:272`) on an India-first terminal. *Fix:* fall back to the row's
  `currency` column before the literal, and leave change/percent unset rather than 0.0 (widen
  `Quote.change` to `float | None`, or omit the quote when the change is unknown).
- **[P2] `growth_basis` asserts a provenance nobody checked.** `models/fundamentals.py:102`
  defaults `growth_basis = "mrq_yoy"` on *every* `Fundamentals`, and `:97-101` says "every
  surface rendering the growth fields must disclose this basis". Proven: `row_to_pair` produces
  `growth_basis='mrq_yoy'` on a payload whose `revenue_growth` may have come from the bundled
  seed pack via `seed_fundamentals:259-302`. The disclosure is therefore a default, not a fact.
  *Fix:* default to `None` and have each producer set it explicitly; the yfinance provider is
  the only one that can honestly claim `mrq_yoy`.
- **[P2] `FieldMeta.status` is a closed union in TypeScript and a free string in Python.**
  `models/fundamentals.py:39` `status: str` vs `types/data.ts:179`
  `status: "ok" | "withheld" | "unavailable"`. A typo or a new status passes Pydantic validation,
  ships over the wire, and lands in a frontend `switch` that TypeScript believes is exhaustive.
  The three legal values are enumerated in the docstring (`:23-33`) — a comment holding an
  invariant the type could hold. *Fix:* `status: Literal["ok","withheld","unavailable"]`.
- **[P2] The seed tier is invisible to the store's own freshness block.**
  `fundamentals_store.freshness:799-813` reports `quotes_as_of`/`valuation_as_of`/`deep_as_of`
  and never `seed_updated_at` (`:145`), so a fresh install serving entirely seeded values gets an
  **empty** honest-coverage block from the module that owns honest coverage.
  `services/screener.py:625,666,806` compensates by computing `seed_as_of` itself — two
  implementations of one concept, and only the caller's is complete. *Fix:* add the seed tier to
  `freshness()` and delete the screener's duplicate.
- **[P2] The throttle-prone routes are the uncached ones, and the cached ones are unbounded.**
  `/income:180`, `/balance:186`, `/cashflow:192`, `/ratings:198` call the provider on every
  request with no cache, while `/ratings/history`, `/ratings/price-target-history` and
  `/ratings/individual` cache at 6 h (`:211,230,249`). The caching three write into
  `data_cache`, which never evicts (`services/data_cache.py:106` — "the row is NOT
  auto-evicted") and has no size bound, so `data_cache.db` grows monotonically with every symbol
  ever viewed. Also: `data_cache` executes SQLite **synchronously on the event loop**
  (`data_cache.py:113-118,144-151`), where `fundamentals_store` carefully offloads every query
  via `asyncio.to_thread`. *Fix:* cache the four uncached statement/ratings routes on the same
  6 h TTL (it is the cheapest throttle relief available), and add a row-count ceiling with
  oldest-`updated_at` eviction to `data_cache.set`.
- **[P3] `_canonicalize` blocks the event loop and can raise from a "never raises" path.**
  `agent_tools/fundamentals.py:119` calls `symbol_resolver.resolve(symbol, region=region)`
  directly inside an async tool, unguarded — while `routers/fundamentals.py:73-75` wraps the
  identical call in `asyncio.to_thread` *and* `try/except`, with the comment "a resolver failure
  must not break /fundamentals". The tool's own `_fetch_once:61` promises "error captured (never
  raised)"; a resolver exception escapes `_fundamentals` entirely. *Fix:* mirror the router —
  `await asyncio.to_thread(...)` inside a `try`.
- **[P3] `query()` re-spells `_QUOTE_FIELD_COLUMNS`' keys as a literal.**
  `fundamentals_store.py:596` `field not in ("price","change_percent_1d","volume")` duplicates
  the keys of the map at `:635-639`. A fourth quote-derived field would be added to the map and
  silently mis-gated in `query()`. *Fix:* `field not in _QUOTE_FIELD_COLUMNS`.
- **[P3] The warm loops reach into another module's privates.** `fundamentals_warm.py:188`
  (`screener._WARM_THROTTLE_RATIO`), `:229` and `:239` (`screener._warm_sleep_seconds`). The
  intent ("never duplicated", `:13-14`) is right; the mechanism makes the backoff policy a public
  contract spelled with a leading underscore, and the five function-local `from services import
  screener` imports (`:165,194`) exist only to dodge a circular import the layering created.
  *Fix:* promote the two names to a public `screener_backoff` seam.

---

## Persona walkthrough

**Tactical Tornado — what they would do next in this code.** They would open
`routers/fundamentals.py:244-260`, copy the block one more time for a fourth ratings endpoint,
and add a fifth `except ProviderError → 502`. They would add `"ebitda_margin"` to
`_NUMERIC_FIELDS` (`fundamentals_store.py:95`), see the tests pass on a fresh DB, ship it, and
field the `OperationalError: table fundamentals has no column named ebitda_margin` reports a
week later. Hitting the `_classify_reason` gap at `agent_tools/fundamentals.py:44-51` they would
append `"no company record"` to `_NOT_FOUND_MARKERS` (`:41`) — closing that one string, leaving
the next raise site to fail the same way. And they would fix the `/income` 502 by pasting
`routers/fundamentals.py:104-115` into `get_income_statement`, making the map's fourth copy.
Each of those is the smallest edit that makes the symptom go away, and each widens the exact
leak the subsystem is already bleeding from.

**Strategic Thinker — the redesign.** They would treat the column vocabulary as one owned
declaration: `_NUMERIC_FIELDS` stays in `fundamentals_store.py:67-95` and becomes the source
`_SCHEMA`, `_migrate`, `regenerate_fundamentals_seed._NUMERIC_FIELDS` and
`models/screener.ScreenerNumericField` all derive from — so a new ratio is one edit and the
migration follows for free. They would delete `routers/fundamentals.py:104-115` and the three
`except ProviderError` blocks outright, pushing the `kind`→status map into `app.py:312-315`
where the translation already lives (the deepest version of this module is the one with *less*
error code in it, not more). They would make `FieldMeta.status` a `Literal`, make `field_meta`
non-optional with a `row_to_pair`-derived default built from the tier stamps the row already
carries (`fundamentals_store.py:141-146`), and default `growth_basis` to `None` — turning three
comment-held invariants into type-held ones. Then they would carry `ProviderError.kind` through
`_FetchResult` instead of stringifying it, and `_classify_reason` shrinks to the un-kinded
fallback it should always have been.

---

## Questions to consider

- `field_meta` is optional so that a provider without provenance can still return a
  `Fundamentals`. What breaks if it is required and those providers must say
  `status="unavailable"` per field? Is "we don't know" not exactly the thing this contract exists
  to express?
- `row_to_pair` returns a `Fundamentals` that can never carry `revenue_ttm`, `field_meta`, or an
  honest `growth_basis`. Should the store return `Fundamentals` at all — or a narrower
  `StoredFundamentals` whose type says what it can and cannot know?
- `app.py:312` already owns "any provider failure → an HTTP response". If that one function read
  `exc.kind`, how many of the ~40 routes in this sidecar would immediately start answering 429
  correctly — and how much per-route error code could then be deleted?

---

## Run notes

- Target: `fundamentals-profile` (partition id). 9 owning files, all read in full.
- Ignore list `.aposd/critique/ignore.md`: not present.
- Assessment independence: **degraded (sequential)** — no sub-agents dispatched.
- Snapshot persistence: **skipped** (read-only run; `.aposd/critique/` not written). No trend.
- Claims verified by execution, not inspection: the migration gap, the `prefilter` unknown-column
  raise, the `row_to_pair` coercions, the 429-vs-502 route asymmetry, and the `kind` →
  `provider_error` misclassification. Scratchpad scripts under the session scratchpad; no repo
  files other than the two outputs were created or modified. No process was started or stopped
  beyond two short-lived `python` invocations; the operator's live app was not contacted.
