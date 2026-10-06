# set-84 lows-P2/market-data-providers-1 (rc1-battery-12, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-017 | live GET /disclosures/shareholding?symbol=CSL.NS (and CSL.BO) (raw: raw/set-84/R15-LEAD-017.txt) | 49 patterns, 49 unique quarter_end, 2026-08-20 once | holds |
| R15-CODE-DATA-008 | in-process registry with ValueError + TypeError from two non-last providers (sync+async) (raw: raw/set-84/R15-CODE-DATA-008.txt) | both resolve to 'good' after falling through | holds |
| R15-CODE-DATA-010 | in-process data_cache: 3 backdated rows, read 2 stale keys (raw: raw/set-84/R15-CODE-DATA-010.txt) | stale reads return None and rows evicted (3 -> 1); fresh row survives | holds |
| R15-DATA-104 | in-process get_upcoming over 120 symbols; breaker-open case (raw: raw/set-84/R15-DATA-104.txt) | max concurrent fetches 8 (cap 8); breaker open -> 0 fetches | holds |
| R15-CODE-DATA-013 | live GET /sec/filings/{acc}/sections on :52352; openapi paths (raw: raw/set-84/R15-CODE-DATA-013.txt) | 404; no section path in openapi | holds |
