# Set: batch-5/W5-screener-earnings-sec (set-19) — rc1-battery-2 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-110 | POST /screener/run sp500 pe_ratio<20 on own sidecar :52342 | 200 in 0.6 s, evaluated 478, skipped 25 (missing_field, not rate_limited), 191 matches (not 0/506) | holds |
| R15-UI-055 | POST /screener/run custom, 3 bogus symbols (evaluated 0) + code/test check; throttle itself not reproducible (no Yahoo throttle) | evaluated_count 0 -> ScreenerResultsTable.tsx:535 "Nothing could be screened"; partial logic via _UNREACHED_SKIP_REASONS (screener.py:725,937); test ScreenerResultsTable.test.tsx:344 | ci_pinned (ScreenerResultsTable.test.tsx "Nothing could be screened") |
| R15-UI-056 | store error-frame handling | screener.ts:557-559 carries frame.message; pinned by screener.test.ts:337 | ci_pinned (src/store/screener.test.ts R15-UI-056) |
| R15-CODE-DATA-006 | design; code read | single finish() guard (screener.ts:408) used by all completion paths; pinned screener.test.ts:308 | ci_pinned (screener.test.ts R15-CODE-DATA-006) |
| R15-CODE-DATA-004 | GET /screener/default-universe with region IN / US / none | IN -> nifty50, US -> sp500, none -> nifty50; store adopts it (screener.ts universeChosen) | holds |
| R15-LIFECYCLE-017 | code read of enrichment path | unexpected Exception logged at WARNING (screener.py:1121), emit in finally (:1130-1133); test test_b5_screener.py:73 | ci_pinned (test_b5_screener.py R15-LIFECYCLE-017) |
| R15-LIFECYCLE-020 | boot sidecar, count 'screener warm' log lines before/after one run | 0 warm lines at boot, loop starts on first run via _warm_follow_region (screener.py:1349) and follows region default | holds |
| R15-UI-045 | tests exist at candidate | ScreenerCriteriaBuilder.test.tsx:71,93 (both editors) | ci_pinned (ScreenerCriteriaBuilder.test.tsx R15-UI-045) |
| R15-DATA-028 | GET /earnings/upcoming?days=14 region IN vs US | IN: 39 NSE market-wide events (TCS.NS, HCLTECH.NS ...), provider nse; US: yfinance JPM etc. (no AAPL..WMT default for IN) | holds |
| R15-DATA-032 | GET /earnings/INFY.NS/estimates | eps_estimate_median null, eps_estimate_stddev null, eps count 12 vs revenue_analyst_count 24 | holds |
| R15-DATA-067 | GET /earnings/upcoming?days=60 (US, IN), /earnings/AAPL/estimates | every event fiscal_period null (JPM 2026-10-13, TSLA 2026-10-22) | holds |

COVERAGE: 11/11 ids raw (battery/raw/set-19/); no raw: none
