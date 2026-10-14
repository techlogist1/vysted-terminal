# set-19 — batch-5/W5-screener-earnings-sec (rc1-battery-3)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, own sidecar :52343 (data dir
`rc1-round-4-data-battery3`, copied from the isolated keyless seed).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-110 | Live `POST /screener/run` sp500, `pe_ratio<20` | evaluated 478/503, skipped 25 (4.97%), basis_counts {mixed:18, snapshot:166}, throttled:true, duration_ms 65.9; skip reasons: rate_limited×2, missing_field×23 | holds |
| R15-UI-055 | Code read (ScreenerResultsTable.tsx:535-542) + pinned vitest | `evaluated_count===0` branch renders "Nothing could be screened" + throttled copy; only meaningfully exercised via vitest | ci_pinned (ScreenerResultsTable.test.tsx:345-351, ScreenerPanel.test.tsx:325) |
| R15-UI-056 | Code read (store/screener.ts processFrame:551,607) + pinned vitest | `error` frame branch calls `finish()` with the server's message instead of falling through to "Stream ended without a result frame" | ci_pinned (store/screener.test.ts:339) |
| R15-CODE-DATA-004 | Live `GET /screener/default-universe` with `X-Vysted-Region: IN`/`US` | IN→`{"universe":"nifty50"}`, US→`{"universe":"sp500"}`; store.ts `adoptRegionDefaultUniverse()` only applies when `!universeChosen` | holds |
| R15-CODE-DATA-006 | Code read (screener.ts:402,443 shared `finish`/`runUnary`) + pinned vitest | superseded-run guard now lives in one shared helper instead of three duplicated blocks | ci_pinned (store/screener.test.ts:310) |
| R15-LIFECYCLE-017 | Code read (screener.py:1081-1096) | `(TimeoutError, ProviderError)` → DEBUG (expected miss); bare `Exception` → WARNING with type+message; `done+=1`/`emit` moved into `finally` | holds |
| R15-LIFECYCLE-020 | Code read (screener.py:1134,1312-1423) + live sidecar log | `start_warm_precompute` only arms; `_warm_follow_region()` runs inside `run_screener` and retargets per-request; live log shows zero "screener warm" activity between boot (01:49:16) and the first screener request, first warm line only at 01:52:58 | holds |
| R15-UI-045 | Code read (`withNumericOperator` shared by ScreenerCriteriaBuilder.tsx + CriterionGroupEditor.tsx) + pinned vitest | one shared helper carries the scalar through an operator change in both editors, incl. the nested-group editor | ci_pinned (ScreenerCriteriaBuilder.test.tsx:71,93) |
| R15-DATA-028 | Live `GET /earnings/upcoming` with `X-Vysted-Region: IN` (days=7) and `US` (days=60) | IN/no-watchlist → 6 real NSE names (DEEPA.NS, MOMSBELIEF.NS, PRASOLCHEM.NS, ANSALAPI.NS, VIPULLTD.NS, MPIMANIPAL.NS), provider "nse", currency INR; US/no-watchlist → unchanged 10-ticker default (JPM,TSLA,V,GOOGL,META,MSFT,AAPL,AMZN,NVDA,WMT) | holds |
| R15-DATA-032 | Live `GET /earnings/INFY/estimates` | `eps_estimate_median:null`, `eps_estimate_stddev:null`, `estimate_analyst_count:8` vs `revenue_analyst_count:16` (no longer aliased) | holds |
| R15-DATA-067 | Live `GET /earnings/INFY/estimates` + IN calendar probe | `fiscal_period:null` on the estimate row and on all 6 IN calendar events — no more month→quarter fabrication | holds |

COVERAGE: 11/11 ids raw; no raw: none.
