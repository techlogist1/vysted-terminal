# DS-3 — ADRs and cross-currency figures; INR units in a brief (investor lens)

Stacks: own sidecar :52810 (binary) for SIFY/WIT/IBN at 15:00 IST, retry on :52381 (source) at 15:16 IST. Raw: `raw/investor/ds3.json`, `raw/investor/ds3-retry.json`, `raw/investor/kpit-ollama.jsonl`, and the AC-1 compare run.
Outside witness: Sify 6-K ex99.1 filed 2026-07-16 (https://www.sec.gov/Archives/edgar/data/1094324/000155485526001544/ex991_1.htm): "Revenue was INR 12,352 Million" for the quarter.

## SIFY (US ADR, INR statements)
- /fundamentals/SIFY: revenue_ttm 46,506,049,536 with financial_currency INR. P/S, BVPS and P/B are withheld with a stated USD-vs-INR basis reason (R15-DATA-008 holds). EPS -0.13 is USD per ADS. The app states no ADR ratio. Not filed: nothing wrong is shown.
- /earnings/SIFY/estimates: revenue_estimate_mean 191,700,000 labelled revenue_currency INR. That is a USD-sized figure (Sify's actual quarter is INR 12,352 M, about 64x the label). `earnings_provider._revenue_currency` (:124-155) rules INR out by its own scale check, then falls back to the country currency INR. `EpsEstimateGrid.tsx` renders it -> **investor:4** (regression of R15-DATA-113).

## IBN (ICICI Bank ADR) — 15:16 retry
- currency USD, financial_currency INR, market_cap 98.49 bn USD, revenue_ttm 2.04 trn INR. P/S, P/B and book value are withheld with the same basis reason. EPS 1.61 and P/E 17.04 sit on one USD basis. Pass.

## WIT (Wipro ADR)
- /fundamentals/WIT returned 429 "The data provider is throttled right now" at 15:00 and again at 15:16 (Yahoo throttling shared by every stack on this host). The app's message is honest. Not verified; this is environmental.

## INR units in a brief / chat (KPIT)
- KPIT FAST brief (ollama, 15:11): the fundamentals leg was rate-limited, so every derived metric is null with unit `currency`/`fraction` and none is invented. The INR market-cap unit could not be exercised in the brief.
- Same check through chat (AC-1 p1, gpt-4o-mini, 15:16): KPIT "₹13,394 cr" and Tata Elxsi "₹19,268 cr". Tata Elxsi's served market_cap is 192,680,083,456 INR (= ₹19,268 cr, price 3,092.8 × 62.3 M shares). KPIT at price 492 implies about 27.2 cr shares, which is consistent. The rupee/crore scaling is right (R15-AGENT-001 holds).

VERDICT DS-3: finding investor:4
