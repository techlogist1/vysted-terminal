# batch-8/W3-data-error-honesty (set-31) — rc1-battery-22, gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, sidecar :52362.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-030 | in-process: `errors.error_frame(exc)` for RuntimeError/ValueError/TypeError/KeyError, and `errors.humanize(None, httpx.ConnectError(...))` | all four internal exceptions -> `code:"internal"`, `"The terminal hit an internal error."` (never network/parse_error/provider blame); a real `httpx.ConnectError` through the OTHER function `humanize` still -> `code:"network"`. Matches certification exactly. | holds |
| R15-AGENT-061 | in-process `fundamentals._classify_reason(text, kind)` for the two register messages with `kind="not_found"`; live `GET /fundamentals/KSE.NS` and `/fundamentals/509470.BO` | both classify `not_found` (not `provider_error`); both symbols now return real Yahoo fundamentals records (KSE Limited, Bombay Oxygen Investments) instead of erroring. | holds |
| R15-DATA-081 | live `GET /quotes/BTC%2FUSDT?asset_class=crypto`, `GET /history/ETH%2FUSDT?range=1y&asset_class=crypto` | quote 200 `{"symbol":"BTC/USDT","price":85048.0,...,"provider":"ccxt:binance"}`; history 365 bars via `ccxt:binance`. The watchlist-row-opens-chart sub-claim rests on `src/modules/watchlist/WatchlistPanel.test.tsx` (not re-run this shard — vitest is the heavy lane's). | holds |
| R15-LEAD-005 | live `GET /quotes/NSRGY` and `/quotes/TKOMY` with `X-Vysted-Region: US` (request wall clock ~2026-09-27T10:18Z) | both returned, `"timestamp":"2026-09-25T20:00:00Z"` (Friday's close, matching Yahoo's stamped `regularMarketTime`) — NOT the request time. Confirms `as_of` is still the provider's quote time, not `now()`. | holds |
| R15-UI-029 | source read: `src/modules/macro/MacroSeriesPicker.test.tsx:111` + `src/store/macro.ts` `loadCatalog` | the pinned test (naming R15-UI-029 verbatim) and the store's `loadCatalog` catch-block (comment: "Recorded, not swallowed... Retry instead of a skeleton that never resolves (R15-UI-029)") both hold in the candidate tree. No non-vitest component-render harness available this shard. | ci_pinned (MacroSeriesPicker.test.tsx:111) |
| R15-UI-030 | source read: `src/modules/macro/MacroPanel.test.tsx:116` + `src/lib/use-sidecar-retry.ts` | the pinned test (naming R15-UI-030 verbatim) asserts a provider-tab switch calls the new provider's own default series exactly once, never through the 12-attempt cold-boot retry hook. Confirmed present, unmodified in intent. | ci_pinned (MacroPanel.test.tsx:116) |

COVERAGE: 6/6 ids raw; no raw: none.
