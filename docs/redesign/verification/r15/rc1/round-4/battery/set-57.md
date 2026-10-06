# batch-12/W2-screener-ordering-current_state-doc-drift (round 4, candidate 1006c6da)

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-043 | `POST /screener/run` custom `[AAPL, RELIANCE.NS, MSFT, TCS.NS]`, market_cap desc, limit 2; fresh case: `[AAPL,MSFT,INFY.NS,TCS.NS,RELIANCE.NS,GOOGL]` asc limit 3 | desc/limit2 → `[RELIANCE.NS (INR), AAPL (USD)]`; coverage note `"screened 4 of 4 — 0 unavailable · spans INR, USD — ranked within each currency"`. Fresh asc/limit3 → `[INFY.NS, TCS.NS, MSFT]` — round-robin per currency, note present — exact match to cert | holds |
| R15-DOCS-018 | `GET /fundamentals/AAPL`, `=TCS.NS` (live) + source read `docs/CURRENT_STATE.md:320-331` and `sidecar/services/provider_registry.py` rank table | `CURRENT_STATE.md` states preference-order dispatch (not the asset-class switch) and names `nse_direct` rank 15, `nse` (jugaad) rank 20, `bse` rank 25, region IN, ahead of yfinance rank 50 — `provider_registry.py` matches exactly (`rank=15/20/25/50`). Live: both AAPL and TCS.NS fundamentals served by `provider:"yfinance"` (matches cert's noted nit that openbb-mcp returns incomplete fundamentals) | holds |
| R15-DATA-112 | `POST /screener/run` custom `[MANIKA.NS, RELIANCE.NS, TCS.NS]`, no criteria, sort market_cap desc and asc | desc → `[RELIANCE.NS, TCS.NS, MANIKA.NS(null)]`; asc → `[TCS.NS, RELIANCE.NS, MANIKA.NS(null)]` — MANIKA's null market_cap sorts LAST in both directions, matching the cert fix and R15-UI-006's missing-values-last rule | holds |

Evidence: `raw/set-57/R15-DATA-043-{desc,fresh}.txt`, `raw/set-57/R15-DOCS-018-fundamentals-{AAPL,TCS}.txt`, `raw/set-57/R15-DOCS-018-source.txt`, `raw/set-57/R15-DATA-112-{desc,asc}.txt`.

COVERAGE: 3/3 ids raw; no raw: none.
