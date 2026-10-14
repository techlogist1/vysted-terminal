# RUBYMILLS — data-battery diff (R12)

Fresh-context audit. App pack: `inapp/RUBYMILLS.json` (collected 2026-07-10 00:45–00:50 IST,
i.e. covering the 2026-07-09 NSE/BSE close). Reference pack: `reference-packs/RUBYMILLS.json`
(generated 2026-07-10, independent web research, as-of 2026-07-09). Same as-of date on both
sides, so the ±2% price/mcap tolerance applies without an as-of-date discount.

App sections used: top-level `quote` + `fundamentals` (yfinance/BSE), `research_normal.structured`
(NSE-direct price, yfinance fundamentals, `derived`), `research_normal.publish_brief_events[1]`
(FAST narrative brief), `research_deep.publish_brief_events[0]` (deep narrative brief, 22 sources).

## Diff table

| # | Metric | App | Reference | Δ | Verdict | Basis note |
|---|---|---|---|---|---|---|
| 1 | Entity identity | "The Ruby Mills Limited", NSE `RUBYMILLS`, BSE candidate `RUBYMILLS.BO`; ISIN corroborated via cited upstox URL `.../INE301D01026/` | Legal name "The Ruby Mills Limited", ISIN `INE301D01026`, NSE `RUBYMILLS`, BSE scrip `503169` | none | **ok** | Full agreement on name/symbol/ISIN/dual-listing. |
| 2 | Sector / industry classification | "Consumer Cyclical" / "Textile Manufacturing" (yfinance taxonomy) | "Textiles (composite mill – yarn/fabric/interlining/apparel) **+ Real Estate** (Mumbai commercial property)" | qualitative | **watch** | Different classification basis: Yahoo's single-category GICS-style tag vs. a qualitative description. Yahoo's tag isn't wrong but drops the real-estate segment the reference flags as material to the business. |
| 3 | Last price (NSE feed, `research_normal.structured.price`) | ₹365.55 (nse_direct, as of 2026-07-09, +4.998%) | ₹365.55 cross-check (upstox/tickertape/trendlyne, as of 2026-07-09 15:28–31 IST) | 0.00% | **ok** | Exact match to the cross-checked (non-screener) figure. |
| 4 | Last price (BSE feed, top-level `quote`) | ₹366.85 (bse, +4.99%) | ₹366.00 (screener.in, rounded) | +0.23% | **ok** | Within tolerance; screener itself flags its own value as a whole-rupee rounding vs the paise-precision 365.55 seen elsewhere — consistent with the app's small BSE/NSE cross-exchange spread. |
| 5 | Market capitalization | ₹12,223,991,808 (≈ ₹1,222.40 Cr) | ₹1,218 Cr (screener) / ₹1,222.40 Cr (tickertape) / ₹1,146.16 Cr (upstox, reference itself flags as outlier) | ≈0.00% vs tickertape; +0.36% vs screener | **ok** | Matches tickertape's figure almost to the rupee. Correctly on the non-outlier side of the reference's own flagged 3-way split. |
| 6 | P/E (TTM) | 28.076× | 28.0× (screener consol./standalone) / 28.07× (tickertape) / 26.30× (upstox, reference flags as stale) | +0.02% vs tickertape | **ok** | Matches the non-stale cross-check almost exactly. |
| 7 | EPS (TTM) | ₹13.02 | ₹13.03 (screener consol./standalone, tickertape, upstox all agree) | −0.08% | **ok** | Trivial rounding-level gap. |
| 8 | 52-week high | ₹365.55 | ₹367.00 (screener, rounded) / ₹365.55 (tickertape/upstox/trendlyne — trendlyne explicitly flags "New 52W High today") | 0.00% vs the cross-checked figure | **ok** | App matches the more precise, multiply-corroborated value; screener's 367 is its own internal rounding artifact per the reference's own note. |
| 9 | 52-week low | ₹169.02 | ₹169.02 (all sources agree) | 0.00% | **ok** | Exact match. |
| 10 | Drawdown from 52w high | 0.0% (`(52w high − price) / 52w high`) | 0.0% (primary basis: close = high = 365.55, stock made a fresh ATH same day) | 0.00% | **ok** | Exact match on the reference's primary (non-screener-rounding) basis. |
| 11 | 52-week price change | +42.13% (Yahoo `fifty_two_week_change` field, label explicitly says "(Yahoo)") | +47.0% (screener, "Stock Price CAGR 1yr") / +47.22% (tickertape/upstox aggregation) | −4.9 pp (≈ −10.4% relative) | **watch** | Real gap, but different calculation basis: Yahoo's raw trailing-52-week price-change field vs. screener's separately-labelled "CAGR 1yr" metric — these two providers plausibly anchor to different exact trading days 52 weeks back, and this name had an extreme run (169 low → fresh ATH with a same-day +5% pop), so the exact anchor date matters a lot. Not a same-basis conflict; flagged for tracking, not a bug. |
| 12 | Dividend yield | 0.5% (yfinance raw field) / 0.4787% (app's own `derived` recomputation, dividend/price) | 0.48% (screener) / 0.52% (stockanalysis) / 0.73% (upstox, reference flags as outlier/stale-price artifact) | ≈0.00% vs screener | **ok** | App's own derived figure matches screener almost exactly. |
| 13 | Dividend per share, TTM paid | ₹1.75 | ₹1.75 (only dividend that crossed the TTM-paid window — Sep 2025 final, ex-date 2025-09-04) | 0.00% | **ok** | Exact match. |
| 14 | Dividend per share TTM — internal consistency check | `null` in top-level `fundamentals` (quote panel) vs. `1.75` in both `research_normal.structured.fundamentals` and `research_deep.structured.fundamentals`, all three pulls seconds apart from the same yfinance provider | ₹1.75 | n/a (app self-conflict) | **watch** | Not a reference conflict — the correct value (1.75) is present and matches in 2 of 3 same-run fetches. Flagging as an internal null-coalescing inconsistency in the quote-panel code path, not a data-accuracy bug against source. |
| 15 | Dividend declared, not yet paid (FY25-26 final) | ₹2.50/share, board recommendation 28 May 2026, ex/record date "not available in this run" (deep-research narrative, citing an NSE/BSE filing title) | ₹2.50/share, board approval 2026-05-28, "no record/ex/pay date surfaced by any source" (marketscreener.com) | 0.00% | **ok** | Precise match, including both sides independently failing to find the ex-date. |
| 16 | Special dividends in TTM window | None reported | "None identified... a consistent single-payment-per-year pattern, no interims/specials" | — | **ok** | Absence matches absence. |
| 17 | Latest-quarter revenue | Deep-research narrative surfaces **Q3 FY26** (quarter ended 31 Dec 2025): Revenue from Operations ₹79.995 Cr (7,999.51 lakh), citing a filed source; explicitly states Q4 FY26 (Mar 2026) "revenue and PAT figures were not retrievable from the provided evidence." Structured schema has no quarterly-revenue field at all (only `revenue_ttm`). | Q4 FY26 (quarter ended 31 Mar 2026): revenue ₹123 Cr (123.38 Cr precise) | different quarter entirely | **watch** | Real, disclosed basis gap: the app's deep pass found the Q4 FY26 filing *exists* (cited by title) but could not extract line-item figures from it, so it honestly fell back one quarter and labelled the fallback explicitly. Not a fabrication — the gap is stated, not papered over. Still one full quarter stale vs. what screener.in has readily. |
| 18 | Latest-quarter net profit | Q3 FY26 PAT ₹7.26 Cr (726.23 lakh), same caveat as above | Q4 FY26 net profit ₹11 Cr (11.07 Cr precise) | different quarter entirely | **watch** | Same basis gap as row 17. |
| 19 | Latest-quarter filing status (FAST/normal narrative claim) | "No standalone quarterly-results filing has hit the exchanges yet in this brief's data window... suggesting Q1 FY27 results are imminent but not yet declared." | Q4 FY26 (Mar 2026) results were filed and reported **28 May 2026** — over 6 weeks before this data was collected — per marketscreener.com and business-standard.com; board recommended the FY25-26 final dividend the same day. | factually wrong | **mismatch** | This is a genuine bug, not an as-of gap: the app's own MRQ-YoY growth figures (row 20/21, `growth_basis: "mrq_yoy"`) are only computable *because* the Q4 FY26 print exists, and the app's own deep-research pass (row 17/18) separately found and cited that exact filing. The FAST brief's claim directly contradicts the rest of the same app's output for the same symbol in the same run — likely because the `corporate_announcements` tool call backing the FAST brief has a lookback window too short to reach the 28-May filing. A user reading only the quick brief is told results are still pending when they've been out for 6+ weeks. |
| 20 | Revenue growth, MRQ YoY | +53.6% (`revenue_growth: 0.536`, `growth_basis: "mrq_yoy"`) | +51.28% precise (Q4FY26 ₹123.38 Cr vs Q4FY25 ₹81.56 Cr) / +50.0% rounded | +2.3 pp (≈ +4.5% relative vs. precise) | **ok** | Inside the ±5% ratio tolerance, but close to the edge — worth a re-check next cycle. |
| 21 | Earnings growth, MRQ YoY | −31.1% (`earnings_growth: -0.311`) | −30.86% precise (Q4FY26 ₹11.07 Cr vs Q4FY25 ₹16.01 Cr) / −31.25% rounded | −0.24 pp (≈ 0.8% relative vs. precise) | **ok** | Tight match. |
| 22 | ROE | 6.645% | 6.65% (standalone) / 6.46% (consolidated) | +0.008 pp vs standalone | **ok** | Matches the standalone figure almost exactly; the standalone/consolidated spread is already called out as non-conflicting by the reference itself. |
| 23 | Book value per share | ₹201.449 | ₹202 (consolidated and standalone agree) | −0.27% | **ok** | Trivial gap. |
| 24 | Currency | INR | INR (implicit throughout, all ₹-denominated) | — | **ok** | Match. |
| 25 | Promoter holding (bonus cross-check, deep narrative) | 74.9% ("no shares encumbered in FY26") | 74.91% (quarter ended Mar 2026; 74.91% prior quarter too) | −0.01 pp | **ok** | Near-exact match; good corroboration that the deep-research pass is pulling real, current shareholding data. |

## Verdict summary

- **19 ok**, **5 watch**, **1 mismatch**, **0 fabrications** (25 figures compared).
- Core valuation/price/ratio figures (price, market cap, P/E, EPS, 52w high/low, drawdown,
  dividend yield/amount, ROE, book value, MRQ growth rates) all land inside tolerance against
  the independently-sourced reference pack. No fabricated numbers found anywhere in the app
  output — every figure traces to either a live provider field (yfinance/NSE/BSE) or a cited
  source in the deep-research pass.
- The one real **mismatch** is a narrative/logic bug, not a numeric one: the FAST-mode research
  brief asserts no quarterly results have been filed, which is factually wrong and is
  self-contradicted by the same app's `growth_basis: mrq_yoy` figures and by its own deep-research
  pass in the same collection run. Root cause is almost certainly a short lookback window on the
  `corporate_announcements` tool call feeding the FAST brief.
- Two **watch** items (rows 17–18, latest-quarter revenue/profit) reflect an honestly-disclosed
  one-quarter-stale fallback (Q3 FY26 instead of Q4 FY26) in the deep-research brief — the app
  found the Q4 filing but couldn't extract its figures, said so explicitly, and did not paper
  over the gap. This should be closed (extraction from the actual Q4 FY26 filing, or a
  structured `latest_quarter` field sourced the way screener.in gets it) but it is not a
  fabrication.
- The 52-week price-change watch item (row 11, Yahoo field vs. screener's CAGR label, ~10%
  relative gap) is plausibly explained by different anchor-date methodology on a stock that just
  made a fresh ATH off a deep 52-week low — worth keeping an eye on but not evidence of a bug.
- One internal (app-vs-app, not app-vs-reference) inconsistency worth engineering attention:
  `dividend_per_share_ttm` returns `null` from the top-level quote/fundamentals endpoint but
  `1.75` from both research-mode fundamentals pulls, seconds apart, same provider.
