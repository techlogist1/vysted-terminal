# batch-5/W5-screener-earnings-sec — rc1-battery-4 (round 5)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52344 (fresh seed-data copy).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-004 | `GET /screener/default-universe` with `X-Vysted-Region` IN/US/none | IN→nifty50, US→sp500, none→nifty50 (session default); route has a live caller | holds |
| R15-CODE-DATA-006 | grep for pinned test | `src/store/screener.test.ts:310` "R15-CODE-DATA-006: run A's late unary fallback does not touch run B's result or status" present, targets exact invariant | ci_pinned (src/store/screener.test.ts:310) |
| R15-DATA-028 | `GET /earnings/upcoming?days=7` with `X-Vysted-Region: IN` | 6 events, all `.NS` NSE symbols (DEEPA, MOMSBELIEF, PRASOLCHEM, ANSALAPI, VIPULLTD, MPIMANIPAL) — no US mega-cap default list | holds |
| R15-DATA-032 | `GET /earnings/INFY.NS/estimates`, `GET /earnings/AAPL/estimates` | `eps_estimate_median` and `eps_estimate_stddev` both `null` for INFY.NS and AAPL (no fabricated approximation); INFY revenue_analyst_count=16 vs estimate_analyst_count=8 (no longer copied across) | holds |
| R15-DATA-067 | `GET /earnings/upcoming` (IN), `/earnings/*/estimates`, `/earnings/AAPL/history` | `fiscal_period` is `null` everywhere (upcoming events, estimates, history rows) — no more late-by-one-quarter inferred label | holds |
| R15-DATA-110 | `POST /screener/run` sp500, pe_ratio<20, limit 50, fresh data dir | evaluated_count 478/503 (5% skipped), partial:false, throttled:false, duration_ms ~713 | holds |
| R15-LIFECYCLE-017 | code read + pinned pytest | `services/screener.py:1129-1146` splits `(TimeoutError, ProviderError)` (DEBUG, field-missing) from generic `Exception` (WARNING, "unexpected enrichment error"); `emit()` moved to `finally` so progress advances on failure. Pinned test `test_b5_screener.py::test_enrichment_code_bug_logs_warning_and_progress_completes` present | ci_pinned (sidecar/tests/test_b5_screener.py:70) |
| R15-UI-045 | grep for pinned tests | `ScreenerCriteriaBuilder.test.tsx:71` and `:93` both present ("an operator change carries the typed threshold through" / nested-group editor) | ci_pinned (src/modules/screener/ScreenerCriteriaBuilder.test.tsx:71,93) |
| R15-UI-055 | live sp500 run (not throttled here) + pinned vitest for the forced evaluated:0 case | Code at `ScreenerResultsTable.tsx:536` still branches on `evaluated_count === 0` to "Nothing could be screened" + throttled copy, never "loosen a threshold"; pinned tests in `ScreenerResultsTable.test.tsx:336` and `ScreenerPanel.test.tsx:325` cover the exact forced state | ci_pinned (src/modules/screener/ScreenerResultsTable.test.tsx:336) |
| R15-UI-056 | grep for pinned test | `src/store/screener.test.ts:339` "the stream's error frame puts the server's reason in store.error" present, asserts `state.error === "missing universe snapshot 'nifty50.json'"` | ci_pinned (src/store/screener.test.ts:339) |

COVERAGE: 10/10 ids raw; no raw: none.
