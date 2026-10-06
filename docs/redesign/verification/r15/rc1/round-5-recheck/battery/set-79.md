# Set 79 — batch-28/W5-opus (rc1-battery-24)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar on `127.0.0.1:52364`, live network reached (yfinance v7 batch, NSE F&O bhavcopy, BSE quote). 2 via HTTP against the running sidecar, 2 via in-process python against the candidate's own `sidecar/.venv`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-045 | in-process `yahoo_batch_provider.fetch_quotes_batch(16 symbols)` — the exact class of the register's "curl_cffi batch transport" fresh case | `rows returned: 16`, `failures: {}` — matches batch-28's certified fresh case verbatim ("16 rows, failures {}") | holds |
| R15-LEAD-044 | in-process `screener._fetch_pair("HAL", ...)` under a simulated IN session, once with no region override and once with the sp500 universe's intrinsic region | no override: `Hindustan Aeronautics Limited` (the bug shape); with `_UNIVERSE_REGION["sp500"]="US"`: `Halliburton Company` — the fix demonstrably changes the resolved entity | holds |
| R15-DATA-114 | 3 consecutive `GET /quant/option/chain/NIFTY` on :52364 | HTTP 200/200/200 (0.67s, 0.03s, 0.03s — cached after the first probe), 276 contracts, expiry 2026-09-29; no 502 on any of the 3 | holds |
| R15-DATA-053 | `GET /quotes/SBIN.BO?asset_class=equity` on :52364 | `volume=234000`, `open=980.0 high=985.9 low=977.0 prev_close=978.5` — matches batch-28's certified fresh case ("SBIN.BO 234000 vs 233720") in shape (volume populated, OHLC present, low<=price<=high: 977<=982.5<=985.9) | holds |

COVERAGE: 4/4 ids raw; no raw: none.
