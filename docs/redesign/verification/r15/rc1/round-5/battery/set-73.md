# batch-27/W1-sonnet (set-73) — rc1-battery-22, gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, sidecar :52362.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-117 | live `GET /fundamentals/TSM`, `/HDB`, `/AAPL` | TSM: `price_to_book`/`book_value`/`price_to_sales` all `status:"withheld"` (mixed USD/TWD basis), `pe_ratio=33.55 ok`. HDB: same shape, USD/INR. AAPL (USD/USD control): all four `ok` (P/B 46.34, book 7.36, P/S 10.66, P/E 39.07) — unchanged. Exact match to the certified per-entry evidence. | holds |
| R15-LEAD-040 | grep of fix shape (`_RESOLVE_POOL` at all 5 call sites, no bare `to_thread(symbol_resolver...)` left) + live 16-concurrent cold `/resolve` + `/resolve/autocomplete` storm timing an unrelated `/quotes/AAPL` | grep: 0 hits for a bare `to_thread(symbol_resolver...)`; `_RESOLVE_POOL` (4 workers) backs `resolve_async`/`autocomplete_async`. Live: the unrelated quote took 1.80s under the 16-request storm (register's pre-fix baseline was ~9.4s stall; batch-27's own fix measurement was 1.19s under an 8+8 storm) — no starvation. | holds |

COVERAGE: 2/2 ids raw; no raw: none.
