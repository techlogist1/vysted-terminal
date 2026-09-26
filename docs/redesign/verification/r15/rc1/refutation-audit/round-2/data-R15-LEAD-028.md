# R15-LEAD-028 / rc1-verifier:8: partial

Refutation audit round 2, group data. Own sidecar :52360 (pid 4861) from source at HEAD a3275f64. The code tree equals candidate 4c6dfe8c (the non-docs diff is empty). Written 18:23 IST.

## Entry repro (numeric scrip code on the data routes) and the verifier's /fundamentals refutation
```
== GET /fundamentals/506597.BO
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
HTTP 404
== GET /fundamentals/544774.BO
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
HTTP 404
== GET /fundamentals/532540.BO
{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found","action":"Check the symbol or series id."}
HTTP 404
== GET /fundamentals/AMAL.BO
{"symbol":"AMAL.BO","name":"Amal Ltd","sector":"Basic Materials","industry":"Chemicals","sector_source":"yfinance","currency":"INR","financial_currency":null,"ratio_price":673.05,"market_cap":8320689664.0,"pe_ratio":28.032068,"forward_pe":null,"peg_ratio":null,"price_to_book":6.909171,"price_to_sales":2.88041,"ev_to_ebitda":19.276,"book_value":97.414,"dividend_yield":0.0022,"dividend_per_share":1.
HTTP 200
== GET /quotes/506597.BO
{"symbol":"AMAL","price":673.05,"change":-15.050000000000068,"change_percent":-2.1871820956256456,"volume":5406.0,"open":689.0,"high":694.95,"low":665.0,"prev_close":688.1,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}
HTTP 200
== GET /quotes/544774.BO
{"symbol":"SMR","price":94.0,"change":-2.0,"change_percent":-2.083333333333333,"volume":9000.0,"open":94.0,"high":94.0,"low":92.0,"prev_close":96.0,"currency":"INR","market_state":"CLOSED","timestamp":"2026-09-25T00:00:00Z","provider":"bse","freshness":"eod"}
HTTP 200
== GET /history/544774.BO?range=1y
{"symbol":"SMR","timeframe":"1d","bars":[{"timestamp":"2026-06-08T00:00:00Z","open":102.95,"high":108.05,"low":102.4,"close":103.05,"volume":154000.0},{"timestamp":"2026-06-09T00:00:00Z","open":100.0,"high":100.1,"low":97.9,"close":97.9,"volume":31000.0},{"timestamp":"2026-06-10T00:00:00Z","open":93.5,"high":93.5,"low":93.05,"close":93.05,"volume":14000.0},{"timestamp":"2026-06-11T00:00:00Z","open
HTTP 200
== GET /history/506597.BO
{"symbol":"AMAL","timeframe":"1d","bars":[{"timestamp":"2025-09-11T00:00:00Z","open":890.0,"high":910.0,"low":871.55,"close":882.6,"volume":10622.0},{"timestamp":"2025-09-12T00:00:00Z","open":896.0,"high":899.0,"low":875.0,"close":884.3,"volume":9226.0},{"timestamp":"2025-09-15T00:00:00Z","open":885.05,"high":897.25,"low":868.0,"close":880.95,"volume":6656.0},{"timestamp":"2025-09-16T00:00:00Z","o
HTTP 200
```
Sibling yfinance-served routes addressed by code (own sidecar):
```
/fundamentals/506597.BO/income    -> 200 {"symbol":"506597.BO","periods":[],"lines":[],"provider":"yfinance"}   (empty)
/fundamentals/506597.BO/ratings   -> 200 all-zero counts, consensus null                                        (empty)
/earnings/506597.BO/estimates     -> 502 provider_error
```
sidecar.log: `provider yfinance failed for fundamentals ... yfinance has no instrument data for '506597.BO'` (the same for 544774.BO and 532540.BO). Control: /fundamentals/AMAL.BO -> 200 Amal Ltd.

## Code
The scrip-code to ticker canonicalisation exists only in the BSE lane: sidecar/services/bse_provider.py:454-470 `_require_bse`, plus correctness_gate.py:136-142. The quote and history routes use them. /fundamentals, the statements, ratings and earnings routes are served by openbb-mcp and yfinance. sidecar/services/yfinance_provider.py:226 `if s.startswith("^") or s.endswith(".BO"): return s` passes `506597.BO` to Yahoo unchanged, and Yahoo has no such symbol, so the request 404s or comes back empty.

## Verdict: partial
The entry is titled "404s on data routes" and gives 506597.BO and 544774.BO as examples. The quote and history routes now answer by code (AMAL 673.05 and SMR 94.0 from bse; history bars from bse). /fundamentals still 404s for the entry's own examples, and statements, ratings and earnings are empty or 502. The verifier is right.

Failure count: 2 (stage-c batch-11 not_certified; this gate refutation).
