# set-52 — batch-11/W5-data-reference (rc1-battery-15)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-013 | read `sidecar/services/screener_universes/sp500.json` directly, check named delisted/missing tickers | snapshot_date 2026-09-24, 503 symbols. All previously-cited delisted names (MMC, FI, ANSS, CTLT, DAY, DFS, HES, HOLX, IPG, JNPR, K, MRO, WBA, CTRA) absent. All 3 previously-missing constituents (BXP, NVR, UDR) present. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
