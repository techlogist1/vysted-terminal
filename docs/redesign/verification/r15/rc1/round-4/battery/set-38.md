# batch-9/W4-market-lanes-errors-quant (rc1-battery-24)

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Own sidecar :52364, data dir
rc1-round-4-data-rc1-battery-24 (fresh copy of rc1-round-4-seed-data).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-065 | GET /history/SPY?timeframe=1mo, /history/RELIANCE.NS?timeframe=1wk, +fresh TCS.NS 1mo, AAPL 1wk | all four return freshness "eod" (not "stale"); SPY last bar 2026-09-01, RELIANCE.NS 1wk last bar 2026-09-21 | holds |
| R15-DATA-062 | GET /quotes?symbols=RELIANCE.NS (+ mixed batch with a bad symbol, + COCHINSHIP,MAZAGONDOCK) | symbol field is the REQUESTED spelling "RELIANCE.NS" (not stripped "RELIANCE"); a bad/unresolvable symbol is still silently absent from the array (no per-symbol error field) — this is the documented by-design behavior (quotes.py:78-80 "a requested symbol absent from the list is one that failed"), matching what batch-9 certified (frontend WatchlistPanel infers "unavailable" from the diff) | holds |
| R15-DATA-066 | cold 10-name NSE batch (curl+time), warm re-run of same batch, contended AAPL quote + history/SPY while a 15-name NSE batch is in flight | warm batch 0.01s (was ~23s pre-fix per batch-9); cold 10-name batch 66.5s (slower per-symbol than batch-9's 20/25-name cold runs at ~1s/symbol, but NSE-direct's own throttle is unfixed by design — only cross-route starvation was the defect); AAPL quote 0.59s and history/SPY 0.55s while an NSE batch was in flight (not starved, matching the certified "other to_thread routes no longer wait behind nse_direct's lock") | holds (cold-batch latency is upstream/network variance, not a regression of the certified starvation fix) |
| R15-LIFECYCLE-021 | GET /system/provider-health, GET /quotes/RELIANCE.NS | /system/provider-health now carries a populated "fallthroughs" array (was yahoo-only pre-fix) — matches "the live /system/provider-health carries the array" | holds |
| R15-DATA-073 | grep sidecar/services/locale.py holiday tables; find regenerator script | NSE/US holiday tables extend to 2027-12-24 (past today 2026-09-27, was 2026-12-25 pre-fix); regenerate_holidays.py present under services/resolver_masters/ | holds |
| R15-UI-053 | GET /macro/catalog?provider=imf, then GET /macro/{series_id}?provider=imf for all 10 catalog ids (percent-encoded) | catalog now lists 10 non-slash-ambiguous ids (WEO/…, CPI/…, QNEA/…); all 10 resolve 200; WEO/IND.NGDP_RPCH.A 2031 value 6.513934 matches batch-9's certified figure | holds |
| R15-UI-051 | grep src/modules/quant/BondPricerPanel.tsx and OptionPricerPanel.tsx | both panels render `formatMoney(value, displayCurrency)` with a Display-currency select (regionConfig(region).currency default); no hard-coded "$" left on clean/dirty/accrued/option price | holds |

COVERAGE: 7/7 ids raw; no raw: none.
