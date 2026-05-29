# Phase 10 Adversarial Bug Hunt — Data Layer + API Contracts + Edge Cases

Lens: sidecar routers (validation, status codes, empty/missing data, upstream failures),
`types/data.ts` <-> `sidecar/models/` sync drift, screener / macro / sec / earnings / quant
endpoints, news + portfolio data paths. Every claim cites `file:line` against the actual
source. All findings verified against code; `tsc --noEmit` passes clean (no compiler signal),
so the drifts below are runtime/contract bugs the type system cannot catch (hand-mirrored
contracts, `unknown`-erased fetch bodies, second-order data shapes).

Sidecar smoke tests / pytest were NOT run (would need the venv on PATH per MEMORY.md and would
not exercise the frontend-vs-sidecar contract anyway). Findings are static + provider-trace
based.

---

## BUG 1 — FastAPI 422 validation errors render as `[object Object]` in Portfolio + every GET panel

**Severity: medium** · **Confidence: 9/10**

**Files:**

- `src/lib/sidecar-client.ts:84-92` (`sidecarGet`)
- `src/modules/portfolio/api.ts:27-37` (`sidecarSend`)
- `sidecar/models/portfolio.py:36-39` (`PositionInput` field constraints)
- `src/modules/portfolio/PortfolioPanel.tsx:107-138` (`handleSubmit`)

**What's wrong.** Both error-parsing helpers type the error body as `{ detail?: string }` and do:

```ts
const parsed = (await response.json()) as { detail?: string };
if (parsed.detail) {
  detail = parsed.detail;
}
```

FastAPI request-validation (422) responses do NOT have a string `detail` — they return
`{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}` — an **array of objects**.
`if (parsed.detail)` is truthy for a non-empty array, so `detail` (typed `string`) is assigned
the array. The thrown `SidecarError.message` is then the array; `String(...)` of it yields
`"[object Object]"` (or comma-joined object stringifications). The user sees a garbage error
message instead of "quantity must be greater than 0".

**This is reachable on real input.** `PositionInput` enforces `quantity: Field(gt=0, le=1e12)`
and `cost_basis: Field(ge=0)` (`portfolio.py:36,39`). The frontend `handleSubmit`
(`PortfolioPanel.tsx:111`) only guards `Number.isFinite(quantity)` / `Number.isFinite(costBasis)`
— it does **not** reject `0` or negatives. So a user typing `quantity = 0`, `quantity = -5`, or
`cost_basis = -100` passes the client check, POSTs, and the sidecar returns 422. The catch block
(`PortfolioPanel.tsx:132-134`) sets `error` to the garbled `SidecarError.message`.

**Repro.** Open Portfolio panel → add a position with quantity `0` (or `-5`). Submit. The error
banner shows `[object Object]` (or similar) rather than a useful validation message.

**Fix.** In both `sidecarGet` and `sidecarSend`, normalise array-shaped `detail`:

```ts
const parsed = (await response.json()) as { detail?: unknown };
if (typeof parsed.detail === "string") {
  detail = parsed.detail;
} else if (Array.isArray(parsed.detail)) {
  detail = parsed.detail
    .map((e) =>
      e && typeof e === "object" && "msg" in e ? String((e as { msg: unknown }).msg) : String(e),
    )
    .join("; ");
}
```

Optionally also tighten the client-side guard in `handleSubmit` to reject `quantity <= 0`.

---

## BUG 2 — Screener `eq` on `currency` silently drops every row (contract accepts an unevaluatable field)

**Severity: medium** · **Confidence: 9/10**

**Files:**

- `sidecar/models/screener.py:63` (`ScreenerStringField = Literal["sector", "industry", "currency"]`)
- `sidecar/services/screener.py:208-212` (`_string_field_value`)
- `sidecar/models/fundamentals.py:11-28` (`Fundamentals` — no `currency` field)
- `types/screener.ts:76` (`ScreenerStringField = "sector" | "industry" | "currency"`)

**What's wrong.** The contract (both Python and TS) lets a `StringEqCriterion` target `currency`.
But `_string_field_value` resolves string fields purely via `getattr(fundamentals, field, None)`
(`screener.py:212`), and `Fundamentals` has **no `currency` attribute** (`fundamentals.py:11-28`
— currency lives on `Quote`, `market.py:22`). So `getattr(fundamentals, "currency", None)` is
always `None`; `_evaluate_criterion` then returns `False` for that criterion
(`screener.py:243-246`), which AND-fails the whole row. Result: a screener run filtering by
`currency == "USD"` returns **zero rows** with no error and HTTP 200 — a silent empty result.

The code even documents the gap in the docstring (`screener.py:209-211`: "currency is on the
quote — but the screener doesn't currently fetch ... only fundamentals-side string fields are
first-class today") but ships the field in the public contract anyway. The criteria-builder UI
will offer `currency` as a selectable `eq` field (it mirrors `ScreenerStringField`).

**Repro.** `POST /screener/run` with `{universe:"sp500", criteria:[{field:"currency", operator:"eq", value:"USD"}], limit:200}` → `200 OK`, `rows: []`, `result_count: 0` even though every S&P 500 name is USD.

**Fix.** Either (a) wire `currency` through `_string_field_value` from the `Quote` (the row
already carries `quote` in `_evaluate_criterion` via `apply_criteria`), or (b) drop `currency`
from `ScreenerStringField` in both `screener.py:63` and `screener.ts:76` until it's supported.
Given the brief says the contract pair must stay in sync, (a) is the honest fix — pass `quote`
into `_string_field_value` and special-case `currency` like the numeric `price`/`volume` trio.

---

## BUG 3 — `EarningsSurpriseChart` crashes on duplicate `reported_date` (no timestamp dedup)

**Severity: medium** · **Confidence: 7/10**

**Files:**

- `src/modules/earnings/EarningsSurpriseChart.tsx:33-35` (`toChartTime`)
- `src/modules/earnings/EarningsSurpriseChart.tsx:84-94` (`setData`)
- contrast: `src/modules/macro/MacroChart.tsx:69-76` (the correct pattern — dedupes)

**What's wrong.** `reported_date` is a date (`models/earnings.py:59` `reported_date: date`;
`types/earnings.ts:57` ISO date string). `toChartTime` floors to second resolution from a
date-only string → midnight UTC → an identical timestamp for any two surprises sharing a
reported date. The map at `EarningsSurpriseChart.tsx:89-93` sorts ascending but does **not**
dedupe equal timestamps before `series.setData(data)`. lightweight-charts asserts strictly
ascending unique time and throws (`Assertion failed: data must be asc ordered by time`) on a
duplicate, which surfaces as a panel render crash.

This is a real-data hazard: a company can report two fiscal periods on close dates, providers
occasionally emit dup rows (the `MacroChart` author explicitly guarded against "some providers
emit dup rows" at `MacroChart.tsx:69` — the earnings author did not), and yfinance's
`get_history` can yield multiple entries that collapse to the same date after the `date` coercion.

**Repro.** Feed `EarningsSurpriseChart` two `EarningsSurprise` entries with the same
`reported_date` → lightweight-charts throws inside the `useEffect` and the surprise chart fails
to render.

**Fix.** Dedupe by `time` after sorting, mirroring `MacroChart.tsx:69-76` (keep last-write or
first-write per timestamp). The same `toChartTime` second-flooring + no-dedup pattern should be
audited in the other panels that share the helper name (`PriceTargetTimeline.tsx:32`,
`BacktestResultView.tsx:44`).

---

## BUG 4 — News symbol tagging breaks for crypto-pair / non-word-char symbols (`\b` boundary)

**Severity: low** · **Confidence: 7/10**

**Files:**

- `sidecar/routers/news.py:51-63` (`_tag_symbols`)
- `src/store/symbols.ts:24-25` (watchlist stores `BTC/USDT`, `ETH/USDT`)
- `src/store/symbols.ts:66-69` (`toNewsSymbol` collapses pairs to base before sending)

**What's wrong.** `_tag_symbols` matches with `re.search(rf"\b{re.escape(symbol)}\b", haystack)`.
`\b` is a word/non-word boundary; it only works for tokens that begin and end with word
characters. The frontend's `toNewsSymbol` (`symbols.ts:66`) collapses `BTC/USDT` → `BTC` before
calling `/news`, so the common path is safe. BUT:

- The endpoint is public and the contract accepts arbitrary `symbols`. Any caller (agent tool,
  MCP client, plugin) that passes a raw pair like `BTC/USDT` or a dotted symbol like `BRK.B`
  gets broken matching: `\bBRK.B\b` — the `.` is regex-escaped to `\.` so it's literal, but the
  trailing `\b` after `B` works; the leading is fine — actually `BRK.B` matches. The genuine
  break is `BTC/USDT`: `\bBTC/USDT\b` — the trailing `\b` requires a word char (`T`) adjacent to
  a non-word char or string end, which holds, but the **leading** `\b` before `B` is fine too.
  The concrete failure is a symbol that _starts or ends_ with a non-word char (e.g. `.NS` suffix
  on Indian tickers `RELIANCE.NS` works, but a leading-dot or pure-symbol token does not).
- More robustly broken: single-letter or all-symbol tickers and the default-watchlist `BTC`/`ETH`
  matching inside larger words is _correctly_ prevented by `\b`, which is the intent — so the
  default path is fine. The exposure is the contract accepting pair/suffixed forms it then
  silently fails to tag.

**Repro.** `GET /news?symbols=BTC/USDT` → items mentioning "BTC/USDT" in the headline are not
tagged (and, because `requested` is non-empty, ALL items are then dropped by the
`if requested and not tagged: continue` filter at `news.py:106-107` → empty feed).

**Net effect.** A caller passing a slash-pair gets an **empty news feed** (200, `[]`), not an
error. Low severity because the bundled frontend pre-normalises, but it's a latent contract trap
for plugins/agents and the MCP surface.

**Fix.** Normalise symbols before matching (strip to base asset, upper-case) OR match on a
token-set built from `re.findall(r"[A-Z0-9.]+", haystack.upper())` membership rather than a
per-symbol `\b` regex.

---

## BUG 5 — `/macro/{series_id}` returns two different shapes at one URL (latent contract hazard)

**Severity: low** · **Confidence: 8/10**

**Files:**

- `sidecar/routers/macro.py:70-104` (`get_macro_series`, return type `MacroSeriesExtended | MacroSeries`, NO `response_model`)
- `src/store/macro.ts:82-84` (always casts the response to `MacroSeriesExtended`)

**What's wrong.** The route has no `response_model` and returns a union. When `provider` is one
of the four v0.6.0 providers it returns `MacroSeriesExtended` (with `frequency`,
`seasonal_adjustment`, `last_updated`, `source_url`, `notes`). Otherwise it falls back to the
legacy `MacroSeries` (`macro.py:101-102`) which has **none** of those fields. The frontend store
unconditionally does `sidecarGet<MacroSeriesExtended>("/macro/{id}", { provider })`
(`macro.ts:82`) — TypeScript trusts the cast, so a legacy-shaped payload would leave
`frequency`/`seasonal_adjustment`/etc. `undefined` at runtime while the type claims they exist.

The bundled frontend always passes a valid `MacroProvider` (`macro.ts:30` keys by provider), so
in practice it always hits the extended path — which is why this is low severity, not medium.
But the union-at-one-URL is a real hazard: any agent tool / MCP caller hitting
`/macro/DGS10` with no `provider` (or `provider=fred` via the legacy literal but routed to the
legacy branch) gets a `MacroSeries` that the TS contract has no representation for, and the
Macro panel would render `undefined` metadata fields (no crash — optional chaining — but blank
"Frequency / Seasonal adjustment" rows).

**Fix.** Split into two routes (`/macro/{id}` extended-only, legacy under a versioned path) or
always normalise the legacy `MacroSeries` up to `MacroSeriesExtended` (nulling the new fields)
so one URL = one shape. Add an explicit `response_model` so FastAPI documents and enforces it.

---

## BUG 6 — News `limit` is not enforced at the provider layer; only post-truncated (minor coverage/perf)

**Severity: low** · **Confidence: 8/10**

**Files:**

- `sidecar/routers/news.py:78-118` (`get_news` — `limit` validated `ge=1, le=200`)
- `sidecar/services/news_provider.py:271-319` (`fetch_news` ignores `limit` except for NewsAPI pageSize)
- `src/modules/news/api.ts:21-26` + `src/modules/news/NewsFeedPanel.tsx:172` (frontend never passes `limit`)

**What's wrong.** `fetch_news` only applies `limit` to NewsAPI's `pageSize`
(`news_provider.py:179`). RSS sources return **all** entries; `fetch_news` returns the full
de-duplicated, sorted list (`news_provider.py:318-319`). The router then sentiment-scores
**every** collected item (`news.py:101-116` — a VADER call per item) and only truncates with
`scored[:limit]` at the very end (`news.py:118`). So `limit` does not bound the work done — on a
busy feed day every fetched item is scored and (when filtering by symbol) regex-matched before
the slice. Functionally correct, but `limit` does not mean what a caller expects (it's a tail
slice, not a fetch bound), and the per-item VADER scoring is unbounded.

Separately, the frontend `NewsFeedPanel` calls `fetchNews(newsSymbols)` with no `limit`
(`NewsFeedPanel.tsx:172`), so it always uses the `api.ts` default of 50 — fine, but means the
panel can never request more/fewer without a code change.

**Fix.** Apply `[:limit]` (or pass `limit` into the score loop with an early break) before the
scoring loop in `news.py`, after the newest-first sort, so scoring is bounded. Low severity —
correctness holds, it's a perf/semantics nit.

---

## BUG 7 — `relativeTime` shows future-dated news as "now" (clock-skew / fallback-to-now masking)

**Severity: low** · **Confidence: 6/10**

**Files:**

- `src/modules/news/NewsFeedPanel.tsx:18-37` (`relativeTime`, `Math.max(0, ...)`)
- `sidecar/services/news_provider.py:99-119` (`_parse_struct_time` / `_parse_iso` fall back to `_utcnow()`)

**What's wrong.** Two interacting behaviours:

1. When an RSS/NewsAPI item has an unparseable or missing date, the provider falls back to "now"
   (`news_provider.py:106, 119, 152`). Those items then sort to the **top** of the feed
   (`fetch_news` sorts by `published_at` desc, `news_provider.py:318`) and render as "now" — a
   stale/dateless item masquerades as the freshest. Real feeds routinely have malformed dates.
2. A genuinely future-dated item (provider clock skew, embargoed timestamp) is clamped by
   `Math.max(0, ...)` (`NewsFeedPanel.tsx:23`) to "now" rather than flagged.

Not a crash; it's a correctness/trust issue for a finance news feed where recency ordering is the
whole point. A dateless item from a low-quality feed can pin itself to the top of the watchlist
news indefinitely.

**Fix.** Have the provider leave `published_at` null-able (it's currently non-null in the model)
or carry a `date_estimated` flag, and have the panel de-prioritise / label estimated timestamps
rather than treating fallback-now as real recency.

---

## Non-bugs verified (so the next session doesn't re-chase them)

- **Quant `validate_domain()` IS called.** It looked like dead code in `routers/quant.py`
  (router never calls it), but each service module calls `req.validate_domain()` first:
  `services/quant/options.py:259`, `greeks.py:29`, `bonds.py:40`, `yield_curve.py:62`. The
  `ValueError` → 400 mapping in the router (`quant.py:41-42` etc.) is wired correctly.
- **Earnings required-float contract is defended.** `EarningsEstimateDetail.eps_estimate_high/low`
  are required floats; the provider raises `ProviderError` (→ 502) when the upstream is missing
  them (`earnings_provider.py:419-420`) rather than letting Pydantic 500. Good.
- **Screener NaN/Inf rejection works** (`models/screener.py:17-21, 76-99`) and `limit` is clamped
  both at the model (`le=1000`) and runtime (`screener.py:368-369`).
- **SEC param-validation-before-availability order is correct** (`sec_filings.py:99-107`): 400
  for missing cik/symbol precedes the 501 availability gate — fixed in Phase 9 S3, still holds.
- **Macro 502-not-501 unification holds** (`macro.py:95-104`) — FRED-no-key is a 502, matching
  the global `ProviderError` handler (`app.py:180-183`).
- **`MacroChart` correctly sorts + dedupes timestamps** (`MacroChart.tsx:68-76`) — this is the
  reference pattern BUG 3's earnings chart is missing.
- **`XBRL`-precision-as-string contract is intact** (`types/sec.ts` + `models/sec.py` type
  XBRL values + insider `shares`/`price_per_share`/`transaction_value` as `str`).

## Dead contract (note, not a bug)

- **`FinancialFacts` / `XbrlFact` are defined but never exposed or consumed.** Present in
  `sidecar/models/sec.py:72-96` and `types/sec.ts:84-102`, but `routers/sec_filings.py` has no
  financials endpoint and `grep` finds zero frontend consumers. Either an unfinished surface or
  should be removed to keep the locked-mirror contract honest. Low priority.
