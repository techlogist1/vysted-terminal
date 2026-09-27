# Battery shard 17 — set-37 (batch-9/W3-fundamentals-identity-earnings)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, sidecar :52357.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-022 | live curl /quotes/{BHP.AX,0700.HK,7203.T,VOD.L} | all 4 quote correctly (AUD/HKD/JPY/GBp), no "possibly delisted" | holds |
| R15-LEAD-023 | in-process: yfinance_provider._quote_time(fake ticker: no metadata time, empty history) | raises typed ProviderError, not IndexError | holds |
| R15-LEAD-016 | live curl /earnings/AAPL/history | reported_date ~1mo after period_end on every row (not equal) | holds |
| R15-DATA-069 | live curl /fundamentals/AAPL/ratings/price-target-history | 10+ distinct per-firm/per-day target_from/target_to rows, not one Consensus point | holds |
| R15-UI-015 | live curl /macro/DGS10?provider=fred (502 reproduced) + node re-run of isTransientSidecarFailure | 502 classified non-transient (no retry loop); 503/0/TypeError still retry | holds |
| R15-DATA-052 | live curl /fundamentals/{ELCIDIN,NAPEROL} | ELCIDIN: Financial Services/Investment Company (was empty); NAPEROL: same (was Basic Materials/Chemicals) | holds |

COVERAGE: 6/6 ids raw; no raw: none.
