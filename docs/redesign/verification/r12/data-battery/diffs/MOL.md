# MOL (Meghmani Organics Limited) — data-battery diff

Fresh-context audit. App capture: `inapp/MOL.json` (NSE-direct quote + yfinance
fundamentals, as-of quote timestamp 2026-07-09T00:00 UTC, provider `nse_direct`/
`yfinance`). Reference: `reference-packs/MOL.json` (independent web pass —
screener.in primary, groww.in cross-check, company's own audited Q4 FY26 filing
PDF fetched from meghmani.com, research date 2026-07-10).

**Entity-trap note (checked first, cleared):** the reference pack flags that
"Meghmani Organics Ltd" has two ISINs in circulation — a pre-2021 entity
(ISIN INE974H01013, delisted/merged, listed on screener.in as ticker `MEGH`
"(Merged)") and the current entity (ISIN INE0CT101020, BSE 543331, CIN
L24299GJ2019PLC110321) that trades today as NSE:MOL. The app's `resolve_symbol`
calls (both name-query "Meghmani Organics" and symbol-query "MOL") bound at
confidence 1.0 to symbol MOL / "Meghmani Organics Limited" / NSE / yahoo_symbol
MOL.NS — the current, correct entity. No sign of the app having resolved to the
old/merged shell. Identity resolution is clean.

| Metric | App (inapp/MOL.json) | Reference (reference-packs/MOL.json) | Δ | Verdict | Basis note |
|---|---|---|---|---|---|
| Entity identity (name/symbol/exch) | "Meghmani Organics Limited", MOL, NSE, MOL.NS, confidence 1.0, no disambiguation | Confirmed current entity: MOL / BSE 543331 / ISIN INE0CT101020 / CIN L24299GJ2019PLC110321 (explicitly distinguished from the old merged "MEGH" entity) | none | **ok** | App doesn't surface ISIN/CIN/BSE-code fields (absent, not wrong) but symbol/name/exchange all agree with the confirmed-current entity. |
| Price (latest close) | ₹46.39 (`quote.price`, NSE close, 2026-07-09, `nse_direct`, freshness=eod) | ₹46.40 (screener.in) / ₹46.39 (groww.in), as-of 2026-07-09 | ₹0.00–0.01 (~0.02%) | **ok** | Same as-of date, sub-paisa spread, well inside ±2% tolerance. |
| Market cap | ₹1,179.76 Cr (`market_cap` 11,797,636,096 ÷ 1e7) | Screener.in ₹1,178 Cr / groww.in ₹1,171 Cr (pack midpoint ₹1,175 Cr) | +0.15% (vs screener) / +0.75% (vs groww) | **ok** | Both within ±2% price/mcap tolerance; shares outstanding match exactly (25.43 Cr both sides). |
| P/E (TTM) | 41.053 | 41.0 (screener) / 40.75 (groww) | +0.13% / +0.75% | **ok** | Within ±5% ratio tolerance; consistent with price/EPS = 46.4/1.13 = 41.06 on both sides. |
| EPS (TTM) | ₹1.13 | ₹1.13 (consolidated FY26 full year = TTM, since Q1 FY27 not yet reported) | 0.00 | **ok** | Exact match; reference confirms TTM = FY26 diluted EPS from the audited consolidated filing. |
| 52-week high | ₹106.30 | ₹106.30 (groww) / ₹106 rounded (screener) | 0.00 | **ok** | Exact match to the more precise source. |
| 52-week low | ₹36.50 | ₹36.50 (groww) / ₹36.4 rounded (screener) | 0.00 | **ok** | Exact match to the more precise source. |
| Drawdown from 52w high | 56.36% below high (`derived.drawdown_from_high` = 0.56359) | −56.35% ((46.40−106.30)/106.30) | 0.01pp | **ok** | Same formula, same inputs, rounding-level agreement. |
| 52-week price change | −54.10% (`fifty_two_week_change`, Yahoo-sourced) | **Unresolved/disputed** — one aggregator cluster: −42.18%; a separate tickertape-linked cluster: −49.3%/−49.51%; reference explicitly declines to assert a single value | ~5–12pp vs the disputed clusters | **watch** | Different basis across ALL sources here, not just app-vs-reference: Yahoo's trailing-52-week return calc (fixed 365-day lookback from the quote date) vs whatever anchor dates the web aggregators used (reference itself couldn't reconcile a ~7–17pt spread between its own two source clusters). App's figure is internally consistent with its own 52w-high/low (a ~₹101 price a year ago is plausible given the ₹106.3 high occurred earlier in the window per the brief's price-action narrative), but sits outside even the reference's disputed band — worth a follow-up historical-price lookup, not asserted as a bug given the basis ambiguity is universal to this metric. |
| Dividend per share (TTM) | `null` (`dividend_per_share`, `dividend_per_share_ttm`) | ₹0.00 effective TTM payout (last actual dividend was FY2023 final, ₹1.40/share, ex-date 2023-06-20 — outside the TTM window; confirmed via trendlyne.com + indmoney.com corporate-action history) | null vs 0.00 | **watch** | yfinance's null-for-no-current-dividend convention vs reference's explicit 0.00 — same underlying fact (no dividend paid in TTM), different null-vs-zero representation. Not a wrong value, but a UI ambiguity: null could read as "no data" rather than "confirmed zero." |
| Dividend yield | `null` (`dividend_yield`) | 0.00% (screener.in and groww.in both show 0.00%) | null vs 0.00% | **watch** | Same yfinance null-vs-zero convention as DPS above. Reference also separately investigated and discarded an unverified freepressjournal/univest claim of a ₹1.20/share "recommended" dividend (contradicted by the primary filing and by trendlyne's corporate-action history) — app's null is not fabricating that discarded claim, which is correct, but the true confirmed value (0.00%) is trivially available and the app doesn't surface it as a distinct zero. |
| Latest quarter revenue (absolute, MRQ) | **Not exposed** — app fundamentals schema only carries `revenue_ttm` (₹2,173.96 Cr, matches reference FY26 full-year consolidated revenue of ₹2,173.96 Cr exactly), no discrete Q4 FY26 line item | ₹474.34 Cr (Q4 FY26, Jan–Mar 2026, consolidated) — cross-verified to the rupee against the company's own audited filing PDF | absent vs ₹474.34 Cr | **watch** | Granularity gap, not a wrong value: the app's yfinance-backed fundamentals surfaces only TTM aggregates, never a discrete latest-quarter revenue figure, while this is trivially available from screener.in (and the primary filing). Absence here is honest (no field to be wrong), but it's a real coverage gap against a figure the reference obtained easily. |
| Latest quarter net profit (absolute, MRQ) | **Not exposed** — only `net_income_ttm` (₹28.74 Cr, matches reference FY26 full-year consolidated net profit of ₹28.74 Cr exactly) | ₹8.03 Cr (Q4 FY26, consolidated, owners' share) — cross-verified to the rupee against the primary filing | absent vs ₹8.03 Cr | **watch** | Same granularity gap as revenue above — TTM-only schema, no discrete MRQ net profit field. |
| Revenue growth (MRQ YoY) | −14.3% (`revenue_growth` −0.143, `growth_basis: "mrq_yoy"`) | −14.30% ((474.34−553.46)/553.46, Q4 FY26 vs Q4 FY25 consolidated) | 0.00pp | **ok** | Exact match — app's disclosed `mrq_yoy` basis correctly compared against reference's quarterly (not annual) YoY figure. |
| Earnings growth (MRQ YoY) | −59.0% (`earnings_growth` −0.59, `growth_basis: "mrq_yoy"`) | −59.48% ((8.03−19.82)/19.82, Q4 FY26 vs Q4 FY25 consolidated) | +0.48pp (~0.8% relative) | **ok** | Within ±5% tolerance; same quarterly-YoY basis on both sides. |
| ROE | 1.878% (`roe` 0.01878) | 1.88% (screener) / 1.86% (groww, recomputed 1.86% from primary filing) | −0.002pp to +0.018pp | **ok** | Same consolidated-FY basis; sub-basis-point agreement. |
| Book value per share | ₹61.551 | ₹60.70 (screener) / ₹60.74 (groww) / ₹60.75 (independently recomputed from primary filing equity) | +0.80 to +0.85 (~1.3–1.4% relative) | **ok** | Within ±5% ratio tolerance; both consolidated basis, shares outstanding match exactly so the small gap is most likely a minor equity-base/rounding difference between providers. |
| Currency | INR (`fundamentals.currency`, `quote.currency`) | INR (all figures quoted in Rs/Cr, face value in INR) | none | **ok** | Match. |

## Verdict summary

- **13 ok**, **5 watch**, **0 mismatch**, **0 fabrication**.
- No same-basis, materially-different-value conflicts were found — nothing here rises to a bug candidate.
- The five "watch" items cluster into two real but explainable gaps, not bugs:
  1. **52-week price change** (−54.10% app vs a disputed −42%..−50% band in the reference) — a basis/anchor-date ambiguity that the reference itself could not resolve across its own sources, not unique to the app.
  2. **Dividend fields returning `null` instead of an explicit `0`** (DPS, DPS-TTM, yield) — yfinance's convention for "no current dividend," which reads correctly (no false dividend asserted, and it correctly avoids echoing a discarded/unreliable web claim of a ₹1.20 recommended dividend) but obscures the confirmed-zero fact that the reference established with two independent sources.
  3. **No discrete latest-quarter (MRQ) revenue/net-profit fields** — the app's fundamentals only carry TTM aggregates (which independently match the reference's FY26 full-year consolidated figures to the rupee: revenue ₹2,173.96 Cr, net profit ₹28.74 Cr), while the reference easily sourced the Q4 FY26 standalone quarter figures (₹474.34 Cr / ₹8.03 Cr) from screener.in and the primary filing. This is a genuine coverage gap worth closing, not a wrong value.
- Everything else (identity, price, market cap, P/E, EPS, both 52-week bounds, drawdown, both MRQ growth rates, ROE, book value, currency) agrees with the independent reference within tolerance, including several exact-to-the-rupee/percent matches (EPS, 52w high/low, revenue growth MRQ YoY, TTM revenue, TTM net profit).
