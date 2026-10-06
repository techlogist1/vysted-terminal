# Set: lows-P3/disclosures-witnesses (set-94) — rc1-battery-10, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-021 | read compute_range window build (range_check.py:150-175) + grep windowed_ts | single `windowed` list drives coverage_days and bars; windowed_ts count 0 | holds |
| R15-DOCS-013 | read Range52w docstring + import _EXCHANGE_DIRECT_PROVIDERS | docstring lists nse_direct/nse/bse only; set = {nse, nse_direct, bse, jugaad}, yfinance absent | holds |

COVERAGE: 24/24 ids raw; no raw: none
