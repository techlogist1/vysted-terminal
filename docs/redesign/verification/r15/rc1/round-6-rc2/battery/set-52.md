# Battery set-52: batch-11/W5-data-reference (candidate ace7dd76, shard rc1-battery-3)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-013 | read candidate sidecar/services/screener_universes/sp500.json; diff against live Wikipedia S&P 500 wikitext | 503 symbols, snapshot 2026-09-24; none of MMC FI ANSS CTLT DAY DFS HES HOLX IPG JNPR K MRO WBA CTRA present; BXP, NVR, UDR present; live diff 0 missing (1 'extra' CBOE is a scratch-regex miss of the wikitext parse) | holds |

COVERAGE: 1/1 ids raw; no raw: none
