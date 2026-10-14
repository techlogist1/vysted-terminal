# set-81 — unplanned-3 (rc1-battery-18, round 4)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar on :52358. Raw probe output
under `battery/raw/set-81/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-030 | in-process `run_backtest` on a flat market: buy 10 then sell -100 (independent qty from the pinned test's -20) | `sold = min(abs(intent.quantity), position.quantity)` reconciliation (backtest_engine.py:400-403) caps the sell at the held 10; equity = capital − fees exactly, no phantom-share cash minted | holds |

COVERAGE: 1/1 ids raw; no raw: none.
