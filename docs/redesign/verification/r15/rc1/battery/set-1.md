# batch-2/W2-instrument-identity

Sidecar under test: candidate `4c6dfe8c` (rc1-cand worktree), own sidecar `127.0.0.1:52340`,
data dir `rc1-data-rc1-battery-0` (seed copy). Live GETs for HTTP-shaped repros, in-process
python (candidate `.venv`) for the resolver repro, grep for the design-level entry.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-012 | In-process: `nse_symbol_change.set_active_map_for_tests({'NSDL': SymbolChange('NSDL','GUJENERGY',...)})` then `symbol_resolver.resolve('NSDL','IN')`; separately `resolve('ZOMATO','IN')`. | `resolve('NSDL','IN')` returns `symbol='NSDL', name='National Securities Depository Ltd', exchange='BSE', isin='INE301O01023', rename=None` — the injected rename row is NOT applied. `resolve('ZOMATO','IN')` still correctly returns `ETERNAL`. | holds |
| R15-CODE-DATA-001 | `GET /resolve?q=FOCUS`, then `GET /disclosures/shareholding?symbol=FOCUS`. | NSE candidate "Focus Lighting and Fixtures Limited" has `isin: null, bse_code: null` (no longer cross-stamped from Focus Business Solution). BSE candidate carries its own `isin`/`bse_code`. `/disclosures/shareholding?symbol=FOCUS` carries `split_source: null`. | holds |
| R15-DATA-018 | `GET /resolve?q=zomato`, `?q=ZOMATO`, `GET /resolve/autocomplete?q=ZOMATO`, `GET /resolve?q=SEQUENT`. | zomato/ZOMATO → `ETERNAL` with `rename.renamed_from: "ZOMATO"`; SEQUENT → `VIYASH` with `rename.renamed_from: "SEQUENT"`. No unresolved query. | holds |
| R15-DATA-001 | `GET /fundamentals/DAL/income`. | `symbol: "DAL.BO"`, `operating_revenue` for 2026-03-31 = `20,668,000` — Dynamic Archistructures' own figures, not Delta Air Lines'. | holds |
| R15-DATA-002 | `GET /quotes/SMR?asset_class=equity` (default IN) vs same with `X-Vysted-Region: US`; `GET /fundamentals/SMR` with the US header. | Default: IN SMR Jewels (`price 94.0 INR, provider bse`). With `X-Vysted-Region: US`: NuScale's real US quote (`price 8.42 USD, provider yfinance`) and `/fundamentals/SMR` returns `name: "NuScale Power Corporation", sector: "Industrials"` (first attempt hit a transient upstream `rate_limited` 200ms fundamentals throttle, not a resolver defect; retried 15s later and resolved correctly). | holds |
| R15-CODE-DATA-005 | grep across `sidecar/services/`: `def is_applicable`/`is_applicable =`, `is_block_error`, `def is_india_target`, `def _row_value`. | `is_applicable` in `market_cap_witness.py`, `ownership_check.py`, `research/range_check.py` are all the identical one-line alias `= is_india_listing`. `is_block_error` has exactly one definition (`services/witness.py:24`). `is_india_target` has exactly one definition (`research/relevance.py:374`). `_row_value` still has two independent definitions (`growth_check.py`, `earnings_quality.py`) — the documented residual, out of this entry's scope, not a regression. | holds |

**Set result: 6/6 holds.**
