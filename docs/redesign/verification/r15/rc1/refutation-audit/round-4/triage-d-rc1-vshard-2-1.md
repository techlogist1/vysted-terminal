# triage-d / rc1-vshard-2:1 (tie R15-DATA-063) -> partial on R15-DATA-063 (severity low)

Audited 07:20 IST, HEAD bed3b166 (code == 01015033), own sidecar :52435.

## Entry
R15-DATA-063 title: "... the same illiquid symbol is a 200 empty chart and a 502 overlay error, **and indicators carry no freshness label**". fix_shape: "Wrap in the same except EmptySeriesError returning empty indicators **and stamp freshness from the series**". Batch-5 certified it with a residual noted: no typed reason on the empty payload.

## Live at HEAD
```
history/TCS     HTTP 200 keys ['bars','coverage_start','freshness','partial','provider','reason','symbol','timeframe'] provider nse_direct freshness eod, 26 bars
indicators/TCS  HTTP 200 keys ['indicators','provider','symbol','timeframe','volume_profile'] provider nse_direct (no freshness key), 1 indicator
history/HDFC.NS HTTP 200 provider none, freshness None, reason None, 0 bars
indicators/HDFC.NS HTTP 200 provider none, 0 indicators          <- entry's own repro (was 502): fixed
```
## Code
- `sidecar/models/indicators.py:67-74`: `IndicatorResponse` has symbol, timeframe, provider, indicators and volume_profile, and no freshness.
- `sidecar/services/indicators.py:1390-1396`: `compute()` copies `provider=series.provider` and drops `series.freshness`.
- `sidecar/routers/indicators.py:79-84`: the EmptySeriesError downgrade is in place.
- Consumers: the chart overlay (`src/modules/chart/api.ts:32`) and the workflow `compute.indicator` node (`services/workflow_nodes/builtin.py:126`). The node rehydrates a series that carries freshness and emits a result without it.

## Verdict
partial. The entry's stated repro (502 vs 200) is fixed. A stated part of its fix_shape ("stamp freshness from the series"), also named in its title, is not. The shard's claim holds as stated.
Severity: low (down from the shard's medium). The chart panel draws the overlay beside its own /history freshness badge for the same symbol, timeframe and range. Only a consumer that reads /indicators alone (a workflow node output) loses the as-of. No wrong value is shown.
Certification failures: the register note has no clause. The baseline is 0: no stage-c not_certified and no refutation-audit partial or regression. With this partial the count is 1.

End-of-audit (07:33 IST): own sidecar pid 90459 on :52435 stopped by pid (health now 000); no child processes; the repo working tree is unchanged apart from these output files.
