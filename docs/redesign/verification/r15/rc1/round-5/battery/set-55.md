# batch-12/W1-resolver (rc1-battery-18, candidate 9bc600ec)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-115 | live `GET /history/AMAL.BO?range=1y`, `/history/AMAL.NS?range=1y`, `/quotes/RELIANCE.BO` on own sidecar (:52358) | `AMAL.BO` -> provider `bse`, 255 bars from 2025-09-12 (before the fix: nse_direct, 28 bars); control `AMAL.NS` -> `nse_direct`, 29 bars; class pin `RELIANCE.BO` -> `bse` (matches batch-12's cert exactly) | holds |

COVERAGE: 1/1 ids raw; no raw: none.
