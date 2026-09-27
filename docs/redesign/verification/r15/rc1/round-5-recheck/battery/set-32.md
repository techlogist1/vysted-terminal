# set-32 — batch-8/W3-data-error-honesty (rc1-battery-20, round 5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar `:52360`, data dir
`rc1-round-5-recheck-data-rc1-battery-20`. Re-ran each id's ORIGINAL repro (round-5
`battery/set-31.md` "Per-entry evidence" — this batch's certification was filed under set-31
in that round, not set-32; ids match this shard's assignment), not judged from the diff.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-030 | in-process: `errors.error_frame(exc)` for RuntimeError/ValueError/TypeError/KeyError, and `errors.humanize(None, httpx.ConnectError(...))` | all four internal exceptions -> `code:"internal"`, `"The terminal hit an internal error."`; a real `httpx.ConnectError` through `humanize` still -> `code:"network"` — matches round-5 cert exactly | holds |
| R15-AGENT-061 | in-process `fundamentals._classify_reason(text, kind)` with the register's exact two `ProviderError` message strings, `kind="not_found"`; live `GET /fundamentals/KSE.NS` and `/fundamentals/509470.BO` | both classify `not_found` (not `provider_error`); both symbols return real Yahoo fundamentals records (`field_meta.name.status: "ok"`) — matches round-5 cert | holds |
| R15-DATA-081 | live `GET /quotes/BTC%2FUSDT?asset_class=crypto`, `GET /history/ETH%2FUSDT?range=1y&asset_class=crypto` | quote 200 `{"symbol":"BTC/USDT","price":84548.02,...,"provider":"ccxt:binance"}`; history 365 bars via `ccxt:binance`. Watchlist-row-opens-chart sub-claim rests on `src/modules/watchlist/WatchlistPanel.test.tsx` (not re-run — vitest is the heavy lane's) | holds |
| R15-LEAD-005 | live `GET /quotes/NSRGY` and `/quotes/TKOMY` with `X-Vysted-Region: US` (request wall clock ~2026-09-27T15:01Z) | both returned `"timestamp":"2026-09-25T20:00:00Z"` (Friday's close) — NOT the request time; matches round-5 cert | holds |
| R15-UI-029 | source read: `src/modules/macro/MacroSeriesPicker.test.tsx:111` + `src/store/macro.ts` `loadCatalog` | pinned test (naming R15-UI-029 verbatim) and the store's `loadCatalog` catch-block comment both present, unmodified in intent | ci_pinned (MacroSeriesPicker.test.tsx:111) |
| R15-UI-030 | source read: `src/modules/macro/MacroPanel.test.tsx:116` + `src/lib/use-sidecar-retry.ts` | pinned test (naming R15-UI-030 verbatim) asserts a provider-tab switch calls the new provider's default once, never through the 12-attempt (`MAX_ATTEMPTS = 12`) cold-boot retry hook — present, unmodified in intent | ci_pinned (MacroPanel.test.tsx:116) |

Raw: `battery/raw/set-32/R15-{AGENT-030,AGENT-061-classify,AGENT-061-KSE,AGENT-061-509470,DATA-081-quote,DATA-081-history,LEAD-005-NSRGY,LEAD-005-TKOMY,UI-029,UI-030}.txt`

COVERAGE: 6/6 ids raw; no raw: none.
