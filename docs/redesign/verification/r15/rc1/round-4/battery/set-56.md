# set-56 — batch-12/W1-resolver-and-venue-identity (rc1-battery-18, round 4)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar on :52358. Raw probe output
under `battery/raw/set-56/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-115 | live `GET /history/AMAL.BO?range=1y` against own sidecar (original repro symbol) | 255 bars over a full year (was NSE's 28-bar listing-limited response); sidecar log shows `nse_direct` and `nse` both explicitly reject `'AMAL.BO' is a BSE listing` and fall through to the BSE provider | holds |

COVERAGE: 1/1 ids raw; no raw: none.
