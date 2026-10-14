# batch-27/W1-sonnet (set-74)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, own sidecar :52355, live outside-world
network (yfinance).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-117 | live `GET /fundamentals/{TSM,HDB,AAPL,IBN}` (IBN is a fresh case, not in the original certified sample) | TSM: price_to_book & book_value withheld ("USD listing value against TWD statements"), pe_ratio 33.55 ok; HDB: same pattern (INR), pe_ratio 16.09 ok; AAPL (USD/USD control): price_to_book 46.34 ok, book_value 7.36 ok; IBN (fresh, USD/INR): price_to_book & book_value withheld, pe_ratio 17.34 ok | holds |
| R15-LEAD-040 | source check (`_RESOLVE_POOL` dedicated executor, `resolve_async`/`autocomplete_async` call sites, grep for any remaining `to_thread(symbol_resolver...)` call site) + live HTTP: 16 concurrent `/resolve` + `/resolve/autocomplete` calls (unique queries) vs `/quotes/AAPL` timing | `_RESOLVE_POOL` (4 workers) confirmed dedicated, not the shared default to_thread pool; 0 remaining `to_thread(symbol_resolver...)` call sites anywhere; `/quotes/AAPL` under the 16-way resolve storm: 0.30-0.36s vs 0.44s idle — no starvation | holds (caveat: this sidecar's resolver_masters cache was already warm from the seed data dir / earlier probes, so the live check reproduces the fixed-pool MECHANISM under concurrency rather than a from-cold-boot repro of the original literal case; the source-level dedicated-pool check is the stronger evidence here) |

COVERAGE: 2/2 ids raw; no raw: none.
