# batch-25/W3-sonnet — shard rc1-battery-12

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-028 | Live GET /fundamentals, /history, /quotes on own sidecar (:52352) for numeric BSE scrip codes 506597.BO, 544774.BO, 500325.BO, 532540.BO | All resolve 200 (AMAL, SMR Jewels, Reliance, TCS); history 72 bars bse; income 5 periods; quote 673.05 INR | holds |
| R15-DATA-064 | Live GET /history, /indicators for 30m timeframe on RELIANCE.NS, SPY, AAPL, TCS.NS | 767/286/286/2526 real bars, no empty series; /indicators 200 not 502 | holds |

COVERAGE: 2/2 ids raw; no raw: none.
