# batch-5/W2-resolver-market-data (set-16) — rc1-battery-22, gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, sidecar booted from source on :52362 with a fresh copy of
`rc1-round-5-seed-data`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-015 | `GET /fundamentals/ELCIDIN.BO` | `fifty_two_week_high=144500.0`, `fifty_two_week_low=87003.0`, both `field_meta.status="ok"`, `reason:null` — exact match to screener.in (1,44,500 / 87,003). Batch-5 certified a *flagged* outcome with the same correct values; the candidate now serves the correct values directly, unflagged (a later batch's fix, no longer just flagging the discrepancy). No wrong value is served. | holds |
| R15-DATA-037 | `GET /history/BTC%2FUSDT?range=1mo\|1y\|5y&asset_class=crypto` | 30 / 365 / 1826 bars respectively — matches batch-5's exact certified counts. | holds |
| R15-DATA-057 | `GET /resolve?q=Dhanalakshmi+Bank` | `candidates[0]=DHANBANK` confidence 0.792, `former_name:"The Dhanalakshmi Bank Limited"`; `CANBK` second at 0.6429. DHAN-RE (dead RE line) absent from candidates entirely. | holds |
| R15-DATA-072 | in-process probe (candidate's venv): 3x `provider_health.record_rate_limited(YAHOO)` opens the breaker, then a real `yfinance_provider.get_history("MSFT","1h","1mo")` call | breaker `is_open`=True after 3 throttles; `get_history` returned 154 bars and the breaker was `is_open`=False immediately after — matches the certified "one successful history call closes it". | holds |
| R15-DATA-097 | in-process probe against candidate's sidecar venv: `_live_lookup` with `time.monotonic` mocked, first call empty + cached, +301s later call (mocked yf.Search now returning a hit) returns the hit — TTL expiry confirmed live in-process. | holds |
| R15-LEAD-009 | `GET /earnings/INFY/estimates` with `X-Vysted-Region: IN` vs `US` | IN: `symbol=INFY.NS, eps_estimate_mean=19.615, currency=INR`. US: `symbol=INFY, eps_estimate_mean=0.205, currency=USD`. Distinct region-keyed responses, no cross-region leak. | holds |
| R15-LEAD-011 | `GET /history/%5ENSEI\|%5EBSESN\|%5ENSEBANK` with `X-Vysted-Region: IN` | 247 bars each, `reason:null` (no `in_eod_only`). | holds |

COVERAGE: 7/7 ids raw; no raw: none.
