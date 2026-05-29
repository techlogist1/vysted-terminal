# Phase 10 Adversarial Bug Hunt — State/Store Logic + Data Correctness

Lens: Zustand stores, derived values, P&L / aggregate math, formatting edge cases
(NaN / Infinity / huge numbers), watchlist / screener / portfolio computations,
persistence / restore correctness — frontend + the sidecar computations that feed them.

Method: read the actual source, cite file:line, reproduce where feasible with a
throwaway Node snippet, never speculate. Baseline confirmed green:
`vitest run src/modules/portfolio src/store/screener.test.ts src/store/orders.test.ts`
→ 27/27 pass.

LOCKED files were inspected for context only, not flagged: `types/plugin.ts`,
`sidecar/models/audit_log.py`, `kill_switch.py`, `broker_base.py`,
`tests/test_safety_end_to_end.py`.

---

## BUG-1 (HIGH) — Screener results sort floats unknown/null values to the TOP in descending order

**File:** `src/modules/screener/ScreenerResultsTable.tsx:56-76`

`compareValue` always returns `+1` when `av === null` (line 60) so nulls sort to the
*end* of an ascending sort — correct. But the descending path does **not** use a
direction-aware comparator; it sorts ascending and then `.reverse()`s the whole array
(line 74-75):

```ts
const sorted = [...result.rows].sort((a, b) => compareValue(a, b, sortKey));
return sortDirection === "asc" ? sorted : sorted.reverse();
```

Reversing flips the null-handling: nulls that correctly sank to the bottom in ascending
order rise to the **top** in descending order.

The default state is `sortKey = "market_cap"`, `sortDirection = "desc"` (lines 69-70), so
the bug manifests on the **first render** of any result set that contains an unknown
market cap. The sidecar's own screener comment notes "market_cap is unknown for many
crypto pairs" (`sidecar/services/screener.py:30-32`), and the `crypto-top50` universe is
a first-class option — so an unknown-market-cap row landing above the largest real value
is the common case, not an exotic one.

The sidecar *correctly* sorts nulls last in both interpretations
(`sidecar/services/screener.py:296-298`: `key=lambda row: (row.market_cap is None, -(row.market_cap or 0.0))`),
but the frontend's client-side re-sort discards that ordering the moment the table renders
or the user clicks a header.

**Repro (verified):**
```
rows = [BIG:1000, MID:500, UNK:null, SMALL:10]
DESC (highest first) → UNK:null  BIG:1000  MID:500  SMALL:10   ← null on top
ASC  (lowest first)  → SMALL:10  MID:500  BIG:1000  UNK:null   ← null correct
```

**Fix:** make the comparator direction-aware so nulls always sink, regardless of
direction. e.g.

```ts
const sorted = [...result.rows].sort((a, b) => {
  const cmp = compareValue(a, b, sortKey);          // nulls already -> +1
  return sortDirection === "asc" ? cmp : -cmp;
});
// then keep nulls pinned to the end in BOTH directions:
```
Cleaner: split the comparator so the null/non-null partition is computed first
(non-null always precedes null), then order the non-null group by `cmp * dir`. Do NOT
`.reverse()` the array — reverse re-orders the null partition too.

**Severity:** high — it is the screener's core job to rank, and the most prominent default
view (highest market cap) is the one that breaks.
**Confidence:** 0.95 (reproduced; default sort confirmed at lines 69-70).

---

## BUG-2 (MEDIUM) — Tradesa "Today P&L" / "7d P&L" sums a row-capped dataset, not a time-bounded one

**File:** `plugins/tradesa-v2/components/TradeHistoryPanel.tsx:65-90`
(+ `plugins/tradesa-v2/connection.ts:195`, `plugins/tradesa-v2/store.ts:153`)

`computeSummary` derives `todayPnl` / `weekPnl` by iterating `rows` and summing
`realized_pnl` for trades whose `closed_at` falls in the last 24h / 7d (lines 80-86). But
`rows` is whatever `listClosedTrades()` returned, and that call is hard-capped:

```ts
async listClosedTrades(limit = 100): Promise<TradesaTrade[]>   // connection.ts:195
```

The panel never overrides the default, so the time-window aggregates are computed over the
**100 most-recent closed trades only**. For an active perp bot, 100 closed trades can span
much less than a day — so a label that says "7d P&L" can silently reflect only the last few
hours of trades, understating (or overstating sign-wise) the real windowed P&L. The number
is presented as an authoritative summary card with no "capped" indicator.

**Repro:** bot with >100 closed trades in the last 24h → "Today P&L" sums only the newest
100; the 101st-and-older trades inside the same day are dropped from the total.

**Fix:** either (a) fetch with a limit derived from the window (and page if needed), or
(b) compute the windowed sums server-side in `/tradesa-v2/cost-today`-style endpoint where
the full table is queryable, or (c) at minimum surface "(last 100 closed)" in the card so
the number isn't read as a true time-window total. The bot's table is the authority — the
wrapper should not present a row-capped slice as a time aggregate.

**Severity:** medium — read-only display, but a P&L figure shown as a definitive window
total that is actually truncated is a genuine data-correctness defect.
**Confidence:** 0.85 (limit + call path confirmed; impact depends on the bot's trade
cadence, which the wrapper cannot bound).

---

## BUG-3 (MEDIUM) — Portfolio P&L% shows "+0.00%" for a real gain on a zero-cost-basis position

**File:** `src/modules/portfolio/metrics.ts:60-61`

`cost_basis` of `0` is explicitly allowed and documented as valid ("zero-cost (e.g. vested
shares) is valid" — `sidecar/models/portfolio.py:37-39`). When `costValue === 0` the
per-position percentage is forced to `0`:

```ts
const pnlPercent =
  pnl !== null && costValue !== 0 ? (pnl / costValue) * 100 : pnl !== null ? 0 : null;
```

So a vested-share lot with cost basis 0 and a $1,500 market value displays as
`+$1.5K (+0.00%)` (verified) — a non-zero, in-fact-infinite-percent gain rendered as a
flat 0%. The dollar P&L is correct; the percentage is silently wrong and reads as "no
movement". The same `costValue === 0` guard would also mask a loss on a zero-basis short
were shorts reachable (they are not — see Note A).

**Fix:** distinguish "0% because no P&L" from "undefined % because no basis". Return `null`
for `pnlPercent` when `costValue === 0 && pnl !== 0` and render it as "—" (or "n/a") rather
than "0.00%". The portfolio formatter pipeline already degrades `null`/non-finite to "—"
(`PortfolioPanel.tsx:334`).

**Severity:** medium — quietly misreports the headline metric for a legitimate, common
position type (vested equity / RSUs with zero acquisition cost).
**Confidence:** 0.8 (reproduced; the "render 0 not NaN" choice is partly deliberate per the
F-GUI-1 test, but conflating no-basis with no-gain is still a correctness regression).

---

## BUG-4 (LOW-MEDIUM) — Watchlist / Equity Overview re-implement formatters WITHOUT the NaN/Infinity guards the shared module was built to provide

**Files:**
- `src/modules/watchlist/WatchlistPanel.tsx:16-26` (`formatPrice`, `formatPercent`)
- `src/modules/equity-overview/EquityOverviewPanel.tsx:13-42` + `:251-255`

`src/lib/format.ts` exists precisely to "degrade non-finite inputs (NaN / ±Infinity, which
division-by-near-zero can produce) to an em-dash" (header comment, lines 1-10). These two
panels do **not** use it — they ship local formatters that only guard `null`, not
`Number.isFinite`:

- Watchlist `formatPercent(value)` → `${sign}${value.toFixed(2)}%` with no finite check
  (line 25). `formatPrice` likewise (line 17-20).
- Equity Overview renders `quote.change_percent.toFixed(2)` **inline with no guard at all**
  (line 255), plus local `formatNumber` / `formatLargeNumber` / `formatPercent` that only
  test `value === null` (lines 13-42).

A non-finite quote therefore renders literally as `NaN%` / `Infinity` in those panels.
The path is real though uncommon: `sidecar/services/yfinance_provider.py:83-91` does
`price = float(fast.last_price)`; for a halted/delisted symbol yfinance can hand back a
`nan` last price (and/or `nan` previous_close). The `if prev else 0.0` guard at line 91
only catches `prev == 0` — a **NaN** `prev` is truthy in Python, so `change/prev` stays
`NaN` and flows to the wire. The watchlist/equity panels then print it verbatim.

**Fix:** route all three panels through `src/lib/format.ts` (`formatMoney`,
`formatPercent`, `formatCompactNumber`) — they already em-dash non-finite and abbreviate
huge magnitudes. As defense-in-depth, also guard the sidecar: in
`yfinance_provider.get_quote`, treat a non-finite `price`/`prev` as a provider miss
(raise `ProviderError` or null the derived fields) instead of emitting `NaN`.

**Severity:** low-medium — visible "NaN%" in a Bloomberg-style terminal undermines trust,
but the trigger (a NaN-priced symbol) is intermittent.
**Confidence:** 0.7 (formatter gap is certain; the NaN-reaching-the-wire path is plausible
and matches the documented reason format.ts exists, but is data-source dependent).

---

## BUG-5 (LOW) — `restoreLastSessionOrDefault` / `deserializeWorkspace` can leave the modules `enabled` map mutated when layout restore throws

**File:** `src/lib/workspace.ts:75-90` (+ `:158-177`)

`deserializeWorkspace` mutates the live stores in sequence:

```ts
useModulesStore.getState().setEnabledMap(workspace.enabledModules);  // 1. applied first
api.fromJSON(workspace.layout);                                       // 2. can throw
useWorkspaceStore.getState().setName(workspace.name);
```

`api.fromJSON(workspace.layout)` will throw on a malformed / truncated layout (corrupt
autosave blob, partial write). `restoreLastSessionOrDefault` wraps the whole thing in
try/catch and falls back to `applyDefaultLayout` (lines 162-176) — but by then step 1 has
**already** overwritten the modules `enabled` map with the corrupt workspace's value. The
default-layout fallback re-lays-out panels but does not reset the enabled map, so the app
boots with a default cockpit layered over a possibly-wrong enabled-module set.

There is no validation that `workspace.enabledModules` / `workspace.layout` are even the
expected shapes before they are applied (the type is cast from `response.json()` at
lines 144 / 165 with no runtime check, and `SerializedWorkspace` has an open index
signature).

**Fix:** validate the payload (or wrap each store mutation) and apply atomically — snapshot
the enabled map before `fromJSON`, restore it if `fromJSON` throws; or validate
`workspace.layout` / `workspace.enabledModules` shape up front and bail to default before
touching any store. The autosave write path is best-effort and explicitly swallows errors
(`autosaveLayout` lines 201-203), which makes a partially-written blob a realistic input.

**Severity:** low — requires a corrupt autosave blob; observable as wrong panels enabled
after a crash-during-save → relaunch.
**Confidence:** 0.65 (ordering bug is real; reaching it needs a corrupt persisted blob).

---

## BUG-6 (LOW) — `or`-chained numeric fallbacks discard a legitimate `0` in analyst/earnings target resolution

**File:** `sidecar/services/analyst_ratings_extended.py:289, 315, 368-372`

Several numeric fallbacks use Python `or`, which treats `0.0` as falsy and skips it:

```ts
target_to = _num(row.get("Target")) or _num(row.get("Price Target"))     # :289
snapshot_target = _num(snapshot.get("mean") or snapshot.get("current"))  # :315
target_to = (_num(...PriceTarget) or _num(...Target) or _num(...Price Target))  # :368-372
```

If the first source legitimately resolves to `0.0`, the `or` falls through to the next
source (or to `None`). A `0` price target is economically nonsensical, so the blast radius
is small — but the pattern is a latent correctness trap and would matter for any field where
`0` is a real value. `_num` already returns `None` for missing/NaN, so the `or` is doing
double duty it shouldn't.

**Fix:** prefer explicit `x if x is not None else y` chaining (or a small
`first_non_none(...)` helper) instead of `or` for numeric fallbacks. Same idiom appears safe
elsewhere only because the fields can't legitimately be 0.

**Severity:** low — current fields can't be 0; flagged as a pattern risk.
**Confidence:** 0.6.

---

## BUG-7 (LOW) — MacroChart de-dups equal-time observations by keeping the FIRST, ignoring later revisions

**File:** `src/modules/macro/MacroChart.tsx:60-78`

Points are sorted by time only (line 68), then de-duped by dropping any point whose time
equals the previous kept point's time (lines 70-76). When a provider emits the same date
twice (e.g. an original print and a later revision — common for macro series like GDP/CPI),
the **first** encountered survives. Because the sort is stable and keyed on time only, "first
encountered" is the original array order, not necessarily the revised value — so the chart
can plot the stale original instead of the revision.

**Fix:** when collapsing equal-time points, keep the last (or the one with the newer
`last_updated` / revision marker if the model carries one). Macro data is revision-heavy;
"first wins" is the wrong default.

**Severity:** low — affects only series with duplicate-date revisions; cosmetic-to-mild data
skew on a single point.
**Confidence:** 0.6.

---

## Things that look wrong but are NOT bugs (verified clean)

- **`src/store/orders.ts:175`** — confirm body posts `{ humanConfirmed, confirmNote }`
  (camelCase) while the inline comment (lines 154-157) says `human_confirmed` /
  `confirm_note`. The **comment is stale**: the router model accepts camelCase
  (`sidecar/tests/test_brokers_router.py:130,158` posts `humanConfirmed` and the route
  unpacks `payload.human_confirmed` via a Pydantic alias). Not a bug.
- **`sidecar/services/quant/_common.py:44-64`** — `build_bsm_process` passes
  `(spot, q_handle, r_handle, vol)` to `BlackScholesMertonProcess`, which is the correct
  `(spot, dividendTS, riskFreeTS, volTS)` order; `greeks.py:32-38` calls it with
  `(spot, risk_free_rate, dividend_yield, ...)` and the params map correctly inside. No
  rate/dividend swap.
- **`sidecar/services/earnings_provider.py:372`** — `entry.eps_actual - estimate` cannot
  hit `None - float`: `EarningsHistoryEntry.eps_actual` is non-nullable
  (`models/earnings.py:131`) and `get_history` drops rows where it is missing
  (`earnings_provider.py:344-345`). `_surprise_pct` guards divide-by-zero
  (`:128-132`). Clean.
- **`buildPortfolioSummary` weight / concentration math** (`metrics.ts:78-84`) — divides
  by `totalMarketValue` with a `!== 0` guard and `Math.max` over `weight ?? 0`. Note A:
  short positions (negative qty → negative market value, which would distort
  `totalMarketValue` and `concentration`) are **unreachable** from the UI: `PositionInput`
  enforces `quantity > 0` (`models/portfolio.py:36`), so the panel path can only create
  longs. Safe today; would need re-examination if shorts ever ship.
- **`totalPnlPercent` denominator** (`metrics.ts:74`) — correctly denominator-matched to
  resolved positions and guarded against div-by-zero (returns 0, verified by
  `metrics.test.ts:41-48`). This is the F-GUI-1 fix and it holds.
- **Frozen-empty selector pattern** — `chart-sync.ts`, `panel-context.ts`,
  `macro.ts`, `store.ts` (tradesa), `agents.ts` all correctly return module-level frozen
  empty references to defeat the `useSyncExternalStore` infinite-loop precedent. Verified
  clean across the board.
- **`backtest.ts` SSE run-id promotion** (`:153-298`) — temp→real id promotion and
  `event.result.trades` overwrite are coherent; the `resolvedRunId` closure tracks the
  active slot correctly across run-start.

---

## Summary table

| # | Severity | File | One-liner |
|---|----------|------|-----------|
| 1 | HIGH | ScreenerResultsTable.tsx:74-75 | desc sort `.reverse()` floats null market caps to the top |
| 2 | MEDIUM | TradeHistoryPanel.tsx:65-90 | "Today/7d P&L" sums a 100-row cap, not the time window |
| 3 | MEDIUM | portfolio/metrics.ts:60-61 | zero-cost-basis gain renders "+0.00%" |
| 4 | LOW-MED | WatchlistPanel.tsx:16-26 / EquityOverviewPanel.tsx:13-42,251-255 | local formatters skip NaN/Infinity guards |
| 5 | LOW | lib/workspace.ts:75-90 | corrupt-layout restore leaves enabled-map mutated |
| 6 | LOW | analyst_ratings_extended.py:289,315,368-372 | `or`-chained numeric fallbacks drop a legit 0 |
| 7 | LOW | macro/MacroChart.tsx:60-78 | equal-time de-dup keeps stale original over revision |
