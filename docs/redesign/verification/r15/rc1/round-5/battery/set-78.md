# set-78 — batch-28/W5-opus (rc1-battery-8)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52348 (source, data dir
`rc1-round-5-data-rc1-battery-8`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-053 | `GET /quotes/ICON`, `GET /quotes/AMAL` | volume populated (1200, 13368) + full OHLC/prev_close on both BSE quotes; register bug was `volume:null` + no OHLC | holds |
| R15-DATA-114 | 3x consecutive `GET /quant/option/chain/NIFTY`, 1s apart | 3/3 HTTP 200, consistent cached data, no 502 | holds |
| R15-LEAD-044 | `POST /screener/run` universe=sp500, `X-Vysted-Region: IN` | HAL/CCL/IEX/ACGL resolve to US entities (Halliburton, Carnival, IDEX, Arch Capital) in USD, not the Indian collisions named in the register; source confirms `_region_scope`/`_UNIVERSE_REGION` forces the universe's own region regardless of session region | holds |
| R15-LEAD-045 | direct probe `fc.yahoo.com` (404) + `v7/finance/quote` (429); `GET /fundamentals/AAPL` | upstream Yahoo crumb/v7 path still down live (environmental, matches the entry's own repro) but sidecar's yfinance fallback still serves real current data (Apple Inc., mcap ~4.98T) — the certified fix (graceful fallback) holds | holds |

Raw: `battery/raw/set-78/R15-{DATA-053,DATA-114,LEAD-044,LEAD-045}.txt`
