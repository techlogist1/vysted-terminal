# batch-12/W3-as-of-on-the-ratings-consensus-estimate-revenue-currency (rc1-battery-19, set-58)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Sidecar `:52359`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-068 | Live `GET /fundamentals/AAPL/ratings` twice, then `GET /fundamentals/MSFT/ratings` (uncached) on `:52359` | Both AAPL calls return the identical `as_of: "2026-09-26T22:18:49.030463Z"` (the cache row's write time, not re-stamped `now()`); the uncached MSFT call stamps its own fresh fetch time `"2026-09-26T22:18:49.583247Z"`. Matches the batch-12 certification exactly (same mechanism, fresh symbols). | holds |

COVERAGE: 1/1 ids raw; no raw: none.
