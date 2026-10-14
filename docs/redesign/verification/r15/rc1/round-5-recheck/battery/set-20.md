# set-20 — batch-5/W5-screener-earnings-sec (rc1-battery-4)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Sidecar `:52344` (own data dir
`rc1-round-5-recheck-data-battery-4`, seeded from `rc1-round-5-recheck-seed-data`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-110 | `POST /screener/run` sp500 + P/E<20 + mcap>1e11 + Technology (own repro's default-screen shape) | `evaluated_count:502, skipped_count:1 (missing_field:pe_ratio on INTC), duration_ms:164, partial:false, throttled:false` — 0.2% skip (target <5%), 164 ms (target sub-second) | holds |
| R15-UI-055 | Own repro needs a Yahoo-throttled IP + the rendered table (GUI). Live check: Yahoo is not throttled this run (R15-DATA-110 above: `throttled:false`), so the empty-state path can't be live-triggered here. Backend `partial` contract re-read at `screener.py:941-951`: `partial = (state.partial and skip_details) or any(reason in {budget_exhausted,rate_limited,timeout})` — matches fix_shape. Two vitest tests pin the frontend half. | source confirms the fix is still in place; frontend behaviour unverifiable without GUI/throttle | ci_pinned (`ScreenerResultsTable.test.tsx` "R15-UI-055: a run that evaluated nothing says so instead of blaming the filters"; `ScreenerPanel.test.tsx` "R15-UI-055: throttled with no stale/snapshot rows shown claims no cached values") |
| R15-UI-056 | Own repro is a vitest-fed SSE error frame (`src/store/screener.ts`); certified via vitest only | test still present, handler still parses `frame.event==='error'` | ci_pinned (`screener.test.ts` "R15-UI-056: the stream's error frame puts the server's reason in store.error") |
| R15-CODE-DATA-006 | Own repro is a design-level store-protocol read; certified via vitest only | test + `finish()`/`isCurrent()` guard still present in `screener.ts` | ci_pinned (`screener.test.ts` "R15-CODE-DATA-006: run A's late unary fallback does not touch run B's result or status") |
| R15-CODE-DATA-004 | `GET /screener/default-universe` with `X-Vysted-Region: IN`, `US`, and no header | `IN -> {"universe":"nifty50"}`, `US -> {"universe":"sp500"}`, no-header -> `nifty50` (session default region is IN); `adoptRegionDefaultUniverse()` in `store/screener.ts:313-318` still calls this endpoint and only sets universe when `!universeChosen` | holds |
| R15-LIFECYCLE-017 | Own repro is a stubbed-adapter pytest; certified via pytest + code read | `test_enrichment_code_bug_logs_warning_and_progress_completes` still present in `sidecar/tests/test_b5_screener.py`; `except (TimeoutError, ProviderError)` + `WARNING` log + `finally: done += 1; emit(...)` still present in `screener.py` | ci_pinned (`test_b5_screener.py::test_enrichment_code_bug_logs_warning_and_progress_completes`) |
| R15-UI-045 | Own repro is a vitest-fed operator-change UI flow; certified via vitest, both editors | both tests present; the shared carry-through logic still present in `ScreenerCriteriaBuilder.tsx` | ci_pinned (`ScreenerCriteriaBuilder.test.tsx` "R15-UI-045: an operator change carries the typed threshold through"; "R15-UI-045: the nested-group editor keeps the value across an operator change too") |
| R15-DATA-028 | `GET /earnings/upcoming?days=60` with default region (IN, no watchlist) and with `X-Vysted-Region: US` | default/IN region returns NSE Indian names (TCS, HCLTECH, ICICIPRULI, CEATLTD, ...), not the 10 US mega-caps; `earnings_tools._earnings_upcoming` calls `earnings_provider.get_upcoming` directly (same code path); `get_region()=='IN'` branch at `earnings_provider.py:452-456` still routes to the NSE/BSE board-meeting feed | holds |
| R15-DATA-032 | `GET /earnings/INFY/estimates` (own repro's literal endpoint) | `eps_estimate_median:null, eps_estimate_stddev:null` (no longer fabricated), `estimate_analyst_count:8` vs `revenue_analyst_count:16` (no longer conflated) | holds |
| R15-DATA-067 | `GET /earnings/upcoming?days=60` for JPM/TSLA (US region) and INFY (IN region) | JPM 2026-10-13 `fiscal_period:null`; TSLA 2026-10-22 `fiscal_period:null`; INFY `fiscal_period:null` — no longer inferred/mislabelled | holds |

Raw: `battery/raw/set-20/<id>.txt`.

COVERAGE: 10/10 ids raw; no raw: none.
