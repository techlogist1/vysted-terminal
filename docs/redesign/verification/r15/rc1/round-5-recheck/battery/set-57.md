# set-57 — batch-12/W1-resolver-and-venue-identity (rc1-battery-20, round 5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar `:52360`, data dir
`rc1-round-5-recheck-data-rc1-battery-20`. R15-DATA-115 was certified in round-5 under
`battery/set-55.md` ("batch-12/W1-resolver"). Re-ran the ORIGINAL repro.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-115 | live `GET /history/AMAL.BO?range=1y`, `/history/AMAL.NS?range=1y`, `/quotes/RELIANCE.BO` on own sidecar (:52360) | `AMAL.BO` -> provider `bse`, 255 bars; control `AMAL.NS` -> `nse_direct`, 29 bars; class pin `RELIANCE.BO` -> `bse` — matches round-5 cert exactly | holds |

Raw: `battery/raw/set-57/R15-DATA-115-{AMAL-BO,AMAL-NS,RELIANCE-BO}.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
