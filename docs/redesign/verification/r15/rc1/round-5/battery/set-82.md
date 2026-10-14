# batch-29/W3-sonnet (round 5, candidate 9bc600ec, rc1-battery-3)

Own sidecar :52343 (candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, seed-data copy `rc1-round-5-data-battery-3`).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-049 | Live `POST /screener/run {universe:"nifty50", criteria:[]}`, `GET /resolve?q=TATAMOTORS`, `GET /quotes/TMPV.NS` | Screener: `evaluated_count=50`, `skipped_count=0`, `coverage="screened 50 of 50 — 0 unavailable"`, TMPV present / TATAMOTORS absent from results. `/resolve`: `resolved.symbol="TMPV"`, `confidence=1.0`, `former_name:"TATAMOTORS"`, `rename.renamed_from:"TATAMOTORS"`. `/quotes/TMPV.NS`: 200, `nse_direct`, price 290.45 — exact match to the batch-29 certification | holds |
| R15-LIFECYCLE-020 | In-process against real `provider_health` (reset, then 2 weight=1.0 "user" 429s, then 2436 weight=0.0 "warm" 429s replicating `_WARM_THROTTLE_WEIGHT`, then 1 more weight=1.0 429) + source read `screener.py:170` (`_WARM_THROTTLE_WEIGHT = 0.0`) + `yahoo_batch_provider.py:337` (`record_rate_limited(..., weight=throttle_weight)`) + live `GET /system/provider-health` | After 2 user 429s: `consecutive_throttles=2.0`, circuit closed. After 2436 warm-weight-0.0 429s: unchanged (`ct=2.0`, `opens_total=0`) — the warm 429s advanced nothing. The next user 429 opened the circuit (`opens_total=1`) after only 3 total user-weighted throttles. Live booted sidecar: `yahoo open=false, ct=0` — matches the batch-29 certification exactly | holds |

Evidence: `raw/set-82/R15-LEAD-049-screener-nifty50.json`, `raw/set-82/R15-LEAD-049-resolve.json`, `raw/set-82/R15-LEAD-049-quote-tmpv.json`, `raw/set-82/R15-LIFECYCLE-020-inproc.txt`, `raw/set-82/R15-LIFECYCLE-020-live-health.json`.

COVERAGE: 2/2 ids raw; no raw: none.
