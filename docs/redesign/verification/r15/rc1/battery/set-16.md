# batch-5/W2-resolver-market-data

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-026 | `GET /fundamentals/DHANBANK/{income,balance,cashflow}` at default (annual) and `?period=quarterly`, plus `?period=bogus`, on the candidate's own sidecar (:52343). Cross-checked quarterly cashflow against AAPL to isolate provider vs route behavior. | Annual default unchanged (FY-end periods only, 2023-2026). Quarterly balance includes `2026-06-30` (Q1 FY27) — matches certification. Quarterly cashflow for DHANBANK returns an empty `periods` list, but AAPL quarterly cashflow returns 5 periods fine, so the `period=quarterly` route/provider path (`yfinance_provider.py:1006-1011`, `ticker.quarterly_cashflow`) works; DHANBANK's empty result is a yfinance data-availability gap for that ticker (not part of the certified claim, which covered income/balance only) — noted, not a regression. Invalid `period=bogus` returns 422 (schema validation). | holds |

Evidence: `raw/set-16/R15-DATA-026.txt`.
