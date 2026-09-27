# batch-12/W3-as-of (shard rc1-battery-19)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar booted from candidate source
on :52359, data dir `rc1-round-5-data-rc1-battery-19` (copy of the round-5 keyless seed).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-068 | Live `GET /fundamentals/AAPL/ratings` twice (repeat within seconds), `GET /earnings/AAPL/history`, `GET /fundamentals/AAPL/ratings/history`, `GET /fundamentals/AAPL/ratings/price-target-history` on :52359, all fresh 9bc600ec live calls. | The base consensus envelope (`/fundamentals/AAPL/ratings`) now carries `as_of` (previously the batch-10 "issue seen outside the entries": this exact envelope had none) — `as_of:"2026-09-27T10:10:11.383703Z"` both calls, confirming a cache write-time stamp, not `now()`. `/earnings/AAPL/history`, `/fundamentals/AAPL/ratings/history`, `/fundamentals/AAPL/ratings/price-target-history` each carry their own `as_of` (verified `'as_of' in d` via python json parse — all True). | holds |

Raw: `battery/raw/set-57/R15-DATA-068.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
