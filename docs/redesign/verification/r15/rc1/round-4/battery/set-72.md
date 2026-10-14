# batch-25/W3-lead-028-data-064

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Live GETs against my sidecar :52348.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-064 | `GET /history/RELIANCE.NS?timeframe=30m&range=1y`, `GET /history/SPY?timeframe=30m&range=1y`, `GET /indicators/SPY?indicators=rsi,sma&timeframe=30m` | RELIANCE.NS 30m/1y: 767 bars, `reason:null, partial:true, coverage_start:"2026-07-06"` (exact match to the batch-25 cert numbers); SPY 30m/1y: 780 real bars (was 286 at cert time — live-data drift over 2 days, still nonzero real bars, not the old empty-series bug); `/indicators/SPY` 30m → HTTP 200 with real RSI values (was 502 "correctness gate: empty series" on base) | holds |
| R15-LEAD-028 | `GET /fundamentals/506597.BO`, `/fundamentals/544774.BO`, `/fundamentals/506597.BO/income`, `/quotes?symbols=506597.BO`, `/history/544774.BO?range=1y` | 506597.BO → `AMAL.BO "Amal Ltd"` 200; 544774.BO → `SMR.BO "SMR Jewels Limited"` 200; income → 5 periods; quotes → 200, `price:673.05 INR, provider:bse`; history 1y → real daily bars from 2026-06-08. All match the batch-25 cert evidence verbatim. Note: this entry is flagged in the lead's three-failure list (two prior certification failures) — it holds cleanly on THIS live re-repro, no regression to report. | holds |

Raw: `battery/raw/set-72/*.txt`.
