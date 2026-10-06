# batch-9/W4-market-lanes-errors-quant (rc1-battery-23, shard 23)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar `:52363`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-066 | Cold 20-name NSE batch, warm repoll, concurrent SPY-vs-batch | Cold batch 82.7s / 22.7s (NSE upstream variance); warm repoll 0.002s (EOD-cached, not re-fetched every poll); contended SPY 10.4s vs idle 0.49s during a fresh cold batch — same caveat batch-9 recorded (8.6s) | holds |
| R15-DATA-062 | GET /quotes?symbols=RELIANCE.NS, COCHINSHIP.NS+MAZAGONDOCK.NS, ZZZNOTREAL.NS+RELIANCE.NS | Returned symbol is stamped with the full requested spelling (`RELIANCE.NS`, not suffix-stripped `RELIANCE`); unknown symbol silently absent from array (no count-mismatch signal, backend join unaffected) | holds |
| R15-LIFECYCLE-021 | GET /system/provider-health, GET /health | `fallthroughs` array present and populating live (`nse`/`bse` counts with last_error/last_at) from real request activity; /health unaffected as designed | holds |
| R15-UI-053 | GET /macro/catalog?provider=imf, GET /macro/<encoded-slash-id>?provider=imf for all 10 current catalog ids | All 10 slash-containing ids return 200 with observations; WEO/IND.NGDP_RPCH.A 2031 = 6.513934, byte-identical to batch-9's cited figure | holds |
| R15-DATA-065 | GET /history/{SPY,AAPL,RELIANCE.NS,TCS.NS}?timeframe=1mo/1wk | Current monthly/weekly bars all read freshness `eod`, none `stale` | holds |
| R15-DATA-073 | In-process `services.locale._NSE_HOLIDAYS`/`_US_HOLIDAYS`, regenerator file check | NSE 2026 holidays = 20 dates, byte-identical list to batch-9's "all 20 dates matching live NSE holiday-master"; `sidecar/services/resolver_masters/regenerate_holidays.py` exists (the fix: a regenerator now exists where none did before) | holds |
| R15-UI-051 | Source check: `BondPricerPanel.tsx`/`OptionPricerPanel.tsx` for hard-coded `$`, and for `formatMoney`/`currencyAffix` usage | No hard-coded `$` template found on price fields (only a guarding comment); clean/dirty price and accrued interest all route through `formatMoney(value, displayCurrency)`; a region-aware `displayCurrency` select is present | holds |

COVERAGE: 7/7 ids raw; no raw: none.
