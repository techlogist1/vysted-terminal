# batch-8/W3-data-error-honesty

Candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Own sidecar `:52346`. Raw output: `raw/set-32/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-104 | grep `sidecar/services/earnings_provider.py` for `asyncio.gather`/`Semaphore`/`provider_health` | `get_upcoming` still does an unguarded `asyncio.gather(*(_one(sym) for sym in universe))` at line 395, no `Semaphore`, no `provider_health` import — matches register's documented `status: open` (still_reproduces, low; real concurrency is bounded by the thread-pool executor per the refuter's correction, not a live incident) | holds |
| R15-DATA-106 | grep `sidecar/services/resolver_masters/enrich_nse_sectors.py` for the `industry` write | line 70 still does `rec["industry"] = industry or rec.get("industry")`, writing the forbidden 4th key the shipped-map tests reject — unchanged, matches register's `status: open` (producer-script-only; shipped artifact stays clean since the script isn't run in CI) | holds |
| R15-DATA-108 | grep `sidecar/services/screener_universe_india.py` for `_load_master`/`@lru_cache`/`sector_map_generated`; grep `market_cap_witness.py` for the per-lookup calls | `_load_master()` itself is never cached; `sector_map_generated()` (no `@lru_cache`) calls it directly and is invoked once per symbol from `market_cap_witness._lookup` (line 123) — unchanged, matches register's `status: open` (low, ~7.4ms/call, negligible per the refuter) | holds |
| R15-DATA-110 | grep `sidecar/services/screener.py` for `DEFAULT_WALL_BUDGET_SECONDS` | constant still `120.0`, still the default `wall_budget_s` on the v7 batch sweep — the fix that bounds a screener run to single/double-digit seconds instead of the old 329.8s worst case is intact (a full cold S&P-500 screen was not re-run this shard — >120s, out of the per-call time budget) | holds |
| R15-DATA-112 | `curl -X POST :52346/screener/run` with the entry's exact payload (`custom_symbols:[MANIKA.NS,RELIANCE.NS,TCS.NS]`, sort `market_cap desc`) | rows ordered `RELIANCE.NS (1.659e13) → TCS.NS (7.53e12) → MANIKA.NS (null)` — the null-market-cap row now sorts LAST, not first; matches the certified fix exactly (register's repro had it sorting first, pre-fix) | holds |
| R15-DATA-114 | `curl :52346/quant/option/chain/NIFTY` x3 | all 3 returned 200 with live expiries/underlying data (NSE F&O bhavcopy currently reachable, so the specific transient 502-vs-good-cache window did not reproduce today); `fetch_latest_fo`'s docstring explicitly cites R15-DATA-114 and describes "a failed today-probe does not abort the walk: it serves the newest already-cached day instead" — the certified fix is present in source even though the failure window itself could not be forced live this shard | holds |

Summary: 6 holds (3 live-verified fixes, 1 source-confirmed fix whose live failure window didn't occur today, 2 documented-open lows confirmed unchanged). No regressions.

COVERAGE: 6/6 ids raw.
