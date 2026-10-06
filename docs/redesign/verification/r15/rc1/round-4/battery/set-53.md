# set-53 — batch-11/W6-options-chain (rc1-battery-16, candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-079 | `GET /quant/option/chain/NIFTY`, `/RELIANCE`, `/AAPL` (region US), `/TRADEWELL.NS` on own sidecar :52356 | NIFTY: provider nse-fo-bhavcopy, as_of 2026-09-25, freshness eod, expiry 2026-09-29, 276 contracts, 244 with OI (batch-11 cert: 276 contracts, 238 with OI, one trading-day earlier — the day-to-day OI count differs with the date, mechanism identical); RELIANCE: 90 contracts (exact match to cert); AAPL: yfinance provider with `implied_volatility` populated per contract (exact match); TRADEWELL.NS: 404 `"TRADEWELL.NS has no listed options (not_found)"` (exact match) | holds |

No regressions in this set.
