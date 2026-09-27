# set-83 — batch-29/W3-sonnet (rc1-battery-19, gate round 5-recheck)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52359 (fresh copy of
rc1-round-5-recheck-seed-data, IN profile). Raw: `battery/raw/set-83/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-020 | GET /system/provider-health on own sidecar + source read of screener.py/fundamentals_warm.py/app.py | Circuit closed, opens_total=0 (matches cert); warm loop follows region default (`_warm_follow_region`) and warm-loop 429s record weight 0.0 (`_WARM_THROTTLE_WEIGHT`), so they cannot open the user-shared Yahoo circuit — both the region-blind-sp500 defect and the round-4 shared-circuit-weight follow-up are fixed | holds |
| R15-LEAD-049 | POST /screener/run {universe:nifty50}; GET /resolve?q=TATAMOTORS; GET /quotes/TMPV.NS | nifty50 sweep 50/50 evaluated, 0 skipped, TMPV present/TATAMOTORS absent; resolve candidates [TMPV,TMCV,TSLA] TMPV first; /quotes/TMPV.NS 200 nse_direct 290.45 — all three match cert exactly | holds |

COVERAGE: 2/2 ids raw.

COVERAGE: 15/15 ids raw across set-6, set-25, set-83; no raw missing.
