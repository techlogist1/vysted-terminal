# DS-6 — symbol forms across lanes (investor lens)

Stack: own sidecar :52810, region IN, 15:09-15:11 IST (as_of 09:39-09:41Z). Raw: `raw/investor/ds6.json`. Routes per symbol: /history (1d, 1mo), /quotes/{s}, /earnings/{s}/history, /news?symbols=, /fundamentals/{s}/ratings, plus one batch /quotes.

| symbol | history | quote | earnings | news | ratings |
|---|---|---|---|---|---|
| ^NSEI | 21 bars, yfinance | 22421.95 INR | empty (index) | 10, tagged ^NSEI | empty (index) |
| BHP.AX | 23 bars | 61.21 AUD | empty | 10 on BHP | hold, 17 analysts |
| 0700.HK | 22 bars | 421.20 HKD | 4 periods | 10 on Tencent | buy, 44 analysts |
| 7203.T | 20 bars | 2856.5 JPY | 4 periods | 10 on Toyota | buy |
| VOD.L | 23 bars | 126.80 GBp | empty | 10 on Vodafone | buy |
| RELIANCE.NS | 26 bars nse_direct | 1167.70 INR | latest 2026-06-30 | 2 | buy, 26 analysts, target 1676.85 |
| RELIANCE.BO | 26 bars bse | 1166.00 INR | latest 2025-12-31 | 2 | buy, 36 analysts, target 1716.65 |
| HDFCBANK | 26 bars nse_direct | 721.20 INR | HDFCBANK.NS, latest 2026-06-30 | 2 | buy |

- R15-LEAD-011 (caret index) and R15-LEAD-022 (foreign dot suffixes) hold: every form is served with the right currency, GBp kept as pence.
- R15-DATA-029 holds: earnings and ratings resolve the Indian forms (bare HDFCBANK -> HDFCBANK.NS, not a US namesake).
- R15-DATA-030 (blocked_tier4): news now tags suffixed and bare Indian symbols (2 items each), so nothing new to attach.
- New: RELIANCE.BO earnings history stops at Dec 2025 while RELIANCE.NS has Mar and Jun 2026, and the two listings show different analyst counts and targets for one company -> investor:7.
- BTC-USD under IN: 404 "check the symbol" (BTC-USD.NS), by design (see DS-5).

VERDICT DS-6: finding investor:7
