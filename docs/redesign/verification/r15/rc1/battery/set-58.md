# batch-12/W3-w3 (set-58)

Candidate 4c6dfe8c. Own sidecar :52342, data dir rc1-data-battery-2. Raw output: `raw/set-58/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-068 | Live: `GET /fundamentals/AAPL/ratings` twice back-to-back, then `GET /fundamentals/MSFT/ratings` (uncached) | Both AAPL calls returned the identical `as_of: 2026-09-26T01:31:45.853959Z` (the cache row's write time, never `now()` on a cache hit); the uncached MSFT call stamped a fresh, later `as_of` (01:31:46.42). Matches the certified fix exactly. | holds |
| R15-DATA-113 | Live: `GET /earnings/WIT/estimates`, plus fresh cases TSM/HDB/AAPL | WIT: `revenue_estimate_mean 244246846490.0`, `revenue_currency:"INR"`, `currency:"USD"`, `eps_estimate_mean 0.035` — revenue and EPS now carry DISTINCT currency labels (was a single ambiguous `currency` field pre-fix). Fresh: TSM -> `revenue_currency:"TWD"`, HDB -> `"INR"`, AAPL -> `"USD"` — each correctly reflects its own reporting currency. | holds |

Summary: 2 holds, 0 regressions.
