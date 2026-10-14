# set-53 — batch-11/W5-data-reference (rc1-battery-4)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-013 | Own repro: run the sp500 screen and check for ~15 named delisted tickers still present + BXP/NVR/UDR missing. Checked `sidecar/services/screener_universes/sp500.json` at candidate sha (503 symbols, snapshot_date 2026-09-24) + live `GET /screener/universe?id=sp500` on `:52344` | 0 of the 14 named delisted tickers present; BXP, NVR, UDR all present (live universe True/True/True); 503 total symbols matches the certified count | holds |

Raw: `battery/raw/set-53/R15-LEAD-013.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
