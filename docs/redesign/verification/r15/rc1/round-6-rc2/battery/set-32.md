# batch-8/W3-data-error-honesty (set-32), shard rc1-battery-9, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-061 | in-process fundamentals._fetch_once with ProviderError(kind='not_found') for both register messages; live /fundamentals/KSE.NS | both classify not_found (pre-fix provider_error); network kind stays provider_error; KSE.NS now returns a real record | holds |
| R15-AGENT-030 | in-process error_frame on the four register exceptions; ConnectError humanize | all four -> code internal 'The terminal hit an internal error.' with type: message in detail; real ConnectError still network | holds |
| R15-LEAD-005 | GET /quotes/AAPL on Saturday vs Yahoo chart regularMarketTime | timestamp 2026-10-02T20:00:01Z == Yahoo regularMarketTime 20:00:01Z (request time 2026-10-03T00:3x Z) | holds |
| R15-DATA-081 | GET /quotes/BTC%2FUSDT?asset_class=crypto, ETH/USDT quote, /history/ETH%2FUSDT?asset_class=crypto | BTC 84594.43 USDT ccxt:binance 200; ETH quote 200; history returns bars (pre-fix 404). Frontend legs vitest-pinned | holds |
| R15-UI-030 | vitest-only MacroPanel; grep pin | MacroPanel.test.tsx:116 'a provider tab loads that provider's own default once, never through the cold-boot retry (R15-UI-030)' exists; /macro/catalog?provider=ecb 200 | ci_pinned |
| R15-UI-029 | vitest-only picker/store; grep pins | MacroSeriesPicker.test.tsx:111 and macro.test.ts:153 exist; /macro/catalog?provider=ecb 200 | ci_pinned |

COVERAGE: 6/6 ids raw; no raw: none
