# batch-12/W2-screener-ordering (rc1-battery-6, gate round 5-recheck, candidate 949c3c9f)

Own sidecar :52346 (candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, seed-data copy `rc1-round-5-recheck-data-rc1-battery-6`).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-043 | Live `POST /screener/run` custom `[AAPL, RELIANCE.NS, MSFT, TCS.NS]`, `sort_by market_cap desc, limit 2` | `[RELIANCE.NS 1.659e13 INR, AAPL 4.98e12 USD]`; `coverage: "screened 4 of 4 — 0 unavailable · spans INR, USD — ranked within each currency"` — exact match to cert, currency-aware ranking + unit note present | holds |
| R15-DATA-112 | Live `POST /screener/run` custom `[MANIKA.NS, RELIANCE.NS, TCS.NS]`, `sort_by market_cap` both `desc` and `asc` | desc → `[RELIANCE.NS, TCS.NS, MANIKA.NS(null)]`; asc → `[TCS.NS, RELIANCE.NS, MANIKA.NS(null)]` — the null-market_cap row (missing currency) sorts LAST in both directions, exact match to cert | holds |
| R15-DOCS-018 | `docs/CURRENT_STATE.md` §3.3 vs `sidecar/services/provider_registry.py` module docstring; live `GET /health` | CURRENT_STATE.md now describes a preference-order resolver naming `nse_direct`(15)/`nse`(20)/`bse`(25) ahead of yfinance, matching the registry docstring's "PREFERENCE ORDER" model; live `/health` confirms the chain (`quote: "ccxt (nse_direct, nse, bse, yfinance fallback)"`) | holds |

Evidence: `raw/set-58/R15-DATA-043.txt`, `raw/set-58/R15-DATA-112.txt`, `raw/set-58/R15-DOCS-018.txt`.

COVERAGE: 16/16 ids raw; no raw: none.
