# batch-27/W1-sonnet — regression battery re-run (rc1-battery-11, round-4)

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad, sidecar booted from source on :52351.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-117 | `GET /fundamentals/TSM`, `GET /fundamentals/HDB` | TSM: price_to_book/book_value/price_to_sales all `null`, field_meta.status=withheld with the USD/TWD mixed-basis reason; pe_ratio 33.55 ok. HDB: price_to_book null, withheld with USD/INR reason. Matches the certified fix shape exactly. | holds |
| R15-LEAD-040 | 16 concurrent cold `/resolve` + `/resolve/autocomplete` (unique nonsense queries) fired in background; timed one `GET /quotes/AAPL` during the storm vs 3x idle baseline | idle ~0.4-0.7s; under storm 1.64s (no ~9s-class stall). Code check: `_RESOLVE_POOL` (4 workers) in `symbol_resolver.py:160`; `resolve_async`/`autocomplete_async` use `run_in_executor(_RESOLVE_POOL, ...)`; grep for leftover `to_thread(symbol_resolver...)` in routers/services = 0 hits. | holds |

COVERAGE: 2/2 ids raw; no raw: none.
