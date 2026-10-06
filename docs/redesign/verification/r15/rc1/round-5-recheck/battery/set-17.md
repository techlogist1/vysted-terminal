# batch-5/W2-resolver-market-data (set-17.md) — rc1-battery-21, round 5-recheck

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar :52361 (own data dir
`rc1-round-5-recheck-data-battery21`), shared openbb-mcp/sec-edgar-mcp :52153/:52154.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-097 | design repro (negative-cache LRU). Source re-check: `_live_lookup` caches empty results only until `_LIVE_EMPTY_TTL_SECONDS=300.0` while non-empty rows stay cached indefinitely; pinned test `test_live_lookup_empty_result_expires_and_a_hit_does_not`. | Fix code present verbatim; matches fix_shape. Not executed (battery role never runs pytest suites). | ci_pinned |
| R15-DATA-057 | `GET /resolve?q=Dhanalakshmi+Bank` | candidates[0]=DHANBANK (NSE, confidence 0.792, former_name="The Dhanalakshmi Bank Limited"); DHAN-RE (expired rights line) no longer appears at all. | holds |
| R15-LEAD-011 | `GET /history/%5ENSEI?range=1mo` region IN | 200, non-empty `bars` (real OHLC rows back to 2026-08-25), no `in_eod_only`/0-bar failure. | holds |
| R15-DATA-015 | `GET /fundamentals/ELCIDIN` region IN | `fifty_two_week_low=102210.0`, `high_date=2026-04-20`, `listing_date=2026-04-20` (new field) — listing_date == high_date signals the range is "since listing", not a true 52w window, so the app can now relabel honestly (fix_shape's labeling option). | holds |
| R15-DATA-037 | `GET /history/BTC%2FUSDT?range=1mo\|1y\|5y&asset_class=crypto` | 1mo=30 bars, 1y=365 bars, 5y=1826 bars — distinct spans (previously identical 200-bar series for every range). Source confirms `range_` now threaded provider_registry→ccxt_provider.get_ohlcv→`_since_ms`. Note: `asset_class=crypto` is required on the query — omitting it (as raw `%2F`-encoded curl without the param) falls through to nse/bse/yfinance and 404s; that's the pre-existing, out-of-scope routing quirk the register's own evidence flagged as a "side observation, not part of this finding". | holds |
| R15-LEAD-009 | `GET /earnings/INFY/history` with `X-Vysted-Region: IN` then `US`, same TTL window | IN: `symbol=INFY.NS`, EPS in INR (19.17); US: `symbol=INFY`, EPS in USD (0.20) — cache key now folds the region-resolved Yahoo symbol, so a region switch inside TTL serves the correct listing's data, not a stale cross-region hit. | holds |
| R15-DATA-072 | design repro (record_success missing on 5 paths). Source re-check: `provider_health.record_success(YAHOO)` now present in `get_history`, `get_income_statement`, `get_balance_sheet`, `get_cash_flow`, `get_analyst_rating` (plus pre-existing `get_quote`/`get_fundamentals`). Live confirm: `GET /history/AAPL?range=1mo` → 200, provider=yfinance, 22 bars. | holds |

COVERAGE: 7/7 ids raw; no raw: none.
