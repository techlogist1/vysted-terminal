# SBIN data-battery diff — app vs reference pack

Both packs are as-of the same trading day (NSE close, 2026-07-09) — no as-of gap to
account for. App fundamentals come from `yfinance` (provider-labeled throughout); the
reference pack is a hand-researched pull from screener.in (standalone + consolidated
pages), dhan.co/NSE/BSE aggregators, and SBI's own Q4FY26 filing/press coverage.

Fresh-context auditor note up front: the app's `fundamentals` block (P/E, EPS, book
value, ROE) tracks the reference's **consolidated** screener figures closely, while the
reference's own MRQ growth series is **standalone** (banks report standalone quarterly
by regulatory requirement; consolidated is only half-yearly/annual — see reference
`valuation_and_earnings.pe_ttm.note`). That consolidated/standalone split explains most
of the "watch" rows below. The two "mismatch" rows (revenue/earnings growth MRQ YoY) do
**not** fit that pattern — they don't reconcile against either the reference's standalone
series or the app's own deep-research citation of the same quarter, which is why they're
flagged as bug candidates rather than basis differences.

| # | Metric | App value | Reference value | Δ | Verdict | Basis note |
|---|---|---|---|---|---|---|
| 1 | Entity identity | SBIN · State Bank of India · NSE · SBIN.NS (confidence 1.0) | SBIN · State Bank of India · NSE (BSE 500112) · ISIN INE062A01020 | — | **ok** | Same entity, correct exchange/symbol/ISIN-implied identity. No "Ltd" suffix issue (SBI is a statutory corporation, not a Companies-Act entity) — app doesn't misname it. |
| 2 | Price (close, 2026-07-09) | ₹1,022.10 (NSE, `nse_direct`, EOD) | NSE ₹1,022.10 / BSE ₹1,021.65 / screener display ₹1,022 | ₹0.00 vs NSE | **ok** | Exact match on the NSE line, which is what the app quotes. |
| 3 | Change / change % on day | +₹5.20 / +0.5114% | prev close ₹1,016.90 → +₹5.20 / +0.5114% (derived) | 0.00 | **ok** | Exact match — good cross-check that the price feed and prior-close arithmetic are sound. |
| 4 | Market cap | ₹9,43,461.39 Cr (₹9,434,613,940,224) | screener.in ₹9,42,396 Cr; dhan.co aggregator ₹9,38,661.50 Cr | +0.11% vs screener; +0.51% vs dhan | **ok** | Within ±2% as-of tolerance; consistent with the ~0.4–0.5% spread the reference pack itself documents between its two sources (share-count/timestamp lag). |
| 5 | P/E (trailing) | 11.2183 (yfinance; = price/eps = 1022.10/91.11, internally consistent) | standalone 11.8; consolidated 11.3; standalone-computed-TTM 11.70 | −0.72% vs consolidated; −4.9% vs standalone; −4.1% vs computed | **watch** | App's P/E tracks the **consolidated** basis almost exactly, not the standalone basis India's banks actually report quarterly. Real, named basis split — not a bug. |
| 6 | EPS (TTM) | 91.11 | standalone computed (sum of last 4 std. quarters) 87.41; consolidated FY26 full-year 90.24 | +0.96% vs consolidated; +4.2% vs standalone | **watch** | Same consolidated-vs-standalone split as P/E; app is consolidated-leaning. |
| 7 | Book value / share | 645.819 | standalone 590; consolidated 646 | **−0.03%** vs consolidated; +9.46% vs standalone | **watch** | Confirms the consolidated basis explicitly — reference states consolidated book value differs from standalone because it includes SBI Life/Cards/MF/General Insurance. App value is essentially an exact match to consolidated. |
| 8 | 52-week high | ₹1,234.70 | ₹1,234.70 (screener rounds to ₹1,235) | ₹0.00 | **ok** | Exact match. |
| 9 | 52-week low | ₹786.55 | ₹786.55 | ₹0.00 | **ok** | Exact match. |
| 10 | Drawdown from 52w high | 17.2188% (`(high−price)/high`) | 17.22% (`(1022.10−1234.70)/1234.70`) | 0.001pp | **ok** | Same formula, same inputs, same answer. |
| 11 | 52-week price change | +25.854% (Yahoo trailing calc) | +30.29% (dhan.co aggregator snapshot) | −4.44pp (~15% relative) | **watch** | Real gap, but the 52w high/low/price/mcap all reconcile exactly across sources — this is a vendor-methodology difference in how "trailing 52-week return" is windowed/dated, which the reference pack itself doesn't resolve to a single number either. Not a red flag on data integrity. |
| 12 | Dividend per share (TTM) | 17.35 (`fundamentals.dividend_per_share`) | 17.35 (FY25-26 final dividend; prior year's ₹15.90 correctly excluded as outside the trailing-12-month window) | ₹0.00 | **ok** | Exact match. *Footnote: the top-level `fundamentals.dividend_per_share_ttm` field is `null` while the identical nested `research_normal`/`research_deep` copies show 17.35 — an internal app inconsistency, not a mismatch vs. the reference, since the correct value is present in `dividend_per_share`.* |
| 13 | Dividend yield | 1.71% (`fundamentals.dividend_yield`); 1.6975% (derived recompute) | 1.70% (screener; recomputed 17.35/1022.10 = 1.698%) | ≤0.02pp | **ok** | All cluster tightly at ~1.70%. |
| 14 | No specials/other dividends | none disclosed | none within TTM window (prior FY24-25 final of ₹15.90 explicitly excluded as outside window) | — | **ok** | Agrees — nothing omitted or over-counted. |
| 15 | Latest-quarter net profit (Q4 FY26) | ₹19,684 Cr, ~+6% YoY (app's own deep-research brief, citing NSE/BSE filings) | ₹19,684 Cr, +5.58% YoY (standalone) | ₹0 Cr | **ok** | Exact match on the absolute figure; the growth number is a rounded restatement (+6% vs +5.58%), immaterial. |
| 16 | Latest-quarter revenue (Q4 FY26) | ₹1,40,412 Cr, −2.4% YoY ("Total income", app's deep-research brief) | ₹1,23,098 Cr, +3.00% YoY ("Sales" = interest income, standalone) | +14.06% (₹17,314 Cr), growth sign flips too | **watch** | Named, real basis difference: app cites "Total income" (interest + other/treasury/fee income), reference explicitly uses screener's "Sales" line (interest income only) for its MRQ growth series. Different revenue definition, not a bug — but worth the app disclosing which income line it's citing. |
| 17 | **Revenue growth (MRQ YoY) — headline `fundamentals` field** | **+7.1%** (`growth_basis: "mrq_yoy"`) | standalone Sales MRQ YoY: **+3.00%** | +4.1pp (**+137% relative**) | **mismatch** | Same claimed basis (quarterly YoY) as the reference's own calc, but the value doesn't reconcile against *either* the reference's standalone Sales growth (+3.00%) *or* the app's own deep-research "Total income" growth for the same quarter (−2.4%). No disclosed basis explains +7.1% under any income definition — bug candidate, likely a stale/mis-aligned yfinance quarterly comparison for an Indian bank. |
| 18 | **Earnings growth (MRQ YoY) — headline `fundamentals` field** | **−3.1%** (`growth_basis: "mrq_yoy"`) | standalone MRQ YoY: **+5.58%** | −8.68pp, **sign flip** | **mismatch** | Most severe finding. Same claimed basis, opposite direction from the reference. Worse: the app's *own* deep-research pass (same collection run, same JSON) independently reports net profit ₹19,684 Cr / **+~6% YoY** for the identical quarter — directly contradicting its own headline `earnings_growth` figure. Internal self-contradiction plus external mismatch = strong bug candidate in the yfinance ingestion/labeling path for this ticker, not a basis difference. |
| 19 | ROE | 15.48% (yfinance `roe`) | standalone screener 16.2%; consolidated screener 15.4% ("ROE – Last Year"); company-reported FY26 18.57% | +0.52% vs consolidated; −4.4% vs standalone; −16.6% vs company-reported | **watch** | App's figure lines up almost exactly with the **consolidated** screener ROE, consistent with the P/E/EPS/book-value pattern above. Reference itself couldn't reconcile the three figures (differing denominators), so this is basis-explained, not a bug. |
| 20 | Currency | INR (`quote.currency`, `fundamentals.currency`) | INR throughout (₹ figures) | — | **ok** | Match. |
| 21 | Net income (TTM) | ₹83,298.78 Cr | FY26 standalone net profit ₹80,032 Cr (≈ TTM, since Q1 FY27 hasn't reported yet — both app and reference note this) | +4.08% | **ok** | Within ±5% tolerance; gap direction is consistent with the consolidated-vs-standalone pattern (subsidiary profit contribution), same story as book value/P/E/EPS/ROE. |
| 22 | Revenue (TTM) | ₹3,76,678.44 Cr | *not provided* — reference only has Q4FY26 standalone quarterly Sales, no FY-total revenue figure to check against | — | **ok** (unverifiable) | No reference figure exists to compare. Internally consistent: net_income_ttm / revenue_ttm = 22.11%, exactly matching the reported `profit_margin` (0.22114) — no internal red flag, just outside what the reference pack captured. |
| 23 | Promoter / insider holding | 57.00% (`held_percent_insiders`) | 55.52% (Mar-2026 shareholding pattern, Government of India) | +1.48pp (+2.7%) | **ok** | Within tolerance; small snapshot-date drift (app's collection vs Mar-2026 pattern date) is a plausible explanation. |
| 24 | ROA | 1.109% (yfinance `roa`) | 1.12% (company-reported FY26, cited in app's own deep-research brief too) | −0.011pp | **ok** | Effectively exact — good corroborating signal that not everything from yfinance is off, only the two flagged growth fields. |

## Verdict summary

- **24 figures compared** (all populated in at least one pack; no fabrications found).
- **ok: 14** — identity, price, day change, market cap, both 52-week bounds, drawdown,
  dividend per share, dividend yield, no-specials check, latest-quarter net profit,
  currency, net income TTM, revenue TTM (unverifiable but uncontradicted), promoter
  holding, ROA.
- **watch: 8** — P/E, EPS, book value, 52-week change, latest-quarter revenue, ROE all
  trace to one real, consistently-named split: **the app's `fundamentals` block is
  built on a CONSOLIDATED basis while the reference's MRQ series is STANDALONE** (the
  regulator-mandated quarterly basis for Indian banks) — plus one vendor-methodology gap
  on 52-week price change and one revenue-definition gap (Total income vs Sales) on the
  latest-quarter revenue citation. None of these are bugs; they're basis/vendor
  differences the app should ideally surface in its UI (e.g. label the fundamentals
  panel "consolidated" where it materially diverges from standalone).
- **mismatch: 2, both severe** — the headline `fundamentals.revenue_growth` (+7.1%) and
  `fundamentals.earnings_growth` (−3.1%) fields, both self-labeled `growth_basis:
  "mrq_yoy"`. Neither reconciles against the reference's standalone MRQ series, and
  **earnings_growth flips sign** relative to every other data point in this file
  (reference standalone +5.58%, and the app's own deep-research citation of ~+6% YoY net
  profit for the identical quarter). This is the actionable finding: the yfinance-sourced
  MRQ growth pair for SBIN looks stale or quarter-misaligned and should be investigated
  in the sidecar's fundamentals ingestion — it directly contradicts the app's own
  research module output for the same collection run.
- **fabrications: 0** — every app figure traces to an attributed provider (`nse_direct`,
  `yfinance`, or web-sourced filings/media in the research brief); nothing is asserted
  without support, even where the yfinance-sourced figures are apparently wrong.
