# set-16 — batch-5/W2-resolver-market-data (rc1-battery-16, candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-057 | `GET /resolve?q=Dhanalakshmi+Bank` on own sidecar :52356 | `needs_disambiguation:true`, candidates[0]=DHANBANK conf 0.8 former_name="The Dhanalakshmi Bank Limited"; DHAN-RE absent, CANBK conf 0.6429 second | holds |
| R15-DATA-097 | in-process (candidate venv): monkeypatched `yfinance.Search`, called `_live_lookup` twice immediately then once after `time.monotonic()+301` | call1 miss (network hit #1), call2 cached (no new hit), call3 post-301s re-hits network (hit #2) — exactly 2 network calls | holds |
| R15-LEAD-011 | `GET /history/%5ENSEI` `/%5EBSESN` `/%5ENSEBANK` region=IN, timeframe=1d, range=1mo | 23 bars each, reason=null (no `in_eod_only`) | holds |
| R15-DATA-063 | `GET /history/DAL` (empty series) vs `GET /indicators/DAL?indicators=rsi` | history: 200 bars=[]; indicators: 200 `{"indicators":[],"volume_profile":null}` — no 502 | holds |
| R15-DATA-015 | `GET /fundamentals/ELCIDIN` region=IN | fifty_two_week_high=137000.0 (flagged, reason cites NSE+BSE range 87,003–144,500), fifty_two_week_low=102210.0 (flagged, same reason) | holds |
| R15-DATA-037 | `GET /history/BTC%2FUSDT?asset_class=crypto` at range=1mo/1y/5y; `GET /history/ETH%2FUSDT?asset_class=crypto&timeframe=1h&range=1mo` | BTC: 30 / 365 / 1826 bars; ETH 1h/1mo: 720 bars — matches batch-5 cert exactly | holds |
| R15-LEAD-009 | `GET /earnings/INFY/estimates` and `GET /fundamentals/INFY/ratings`, region IN vs US | estimates: INFY.NS eps_mean 19.615 (INR) vs INFY eps_mean 0.205 (USD) — distinct symbols/values; ratings: IN consensus=buy vs US consensus=hold | holds |
| R15-DATA-072 | in-process (candidate venv): `provider_health.record_rate_limited(YAHOO)` x3 to open breaker, then real `yfinance_provider.get_history('MSFT','1h')` | breaker opens after 3 throttles (`is_open=True`), successful get_history (889 bars) closes it (`is_open=False`) | holds |

Note: probe for DATA-037/LEAD-011/DATA-063 initially used a nonexistent `interval=` query param (route takes `timeframe=`); the wrong-param runs are superseded by the corrected-param runs recorded in the raw files — no regression, probe error only.
