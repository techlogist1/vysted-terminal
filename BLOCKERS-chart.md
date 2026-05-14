# Chart panel — partial / deferred indicators

Teammate A, Phase 1.B. The chart panel ships all 20 required indicators with
server-side computation. Every indicator's **math is implemented and unit-tested**
in `sidecar/services/indicators.py`. The notes below cover indicators whose
_rendering_ or _semantics_ are simplified within Phase 1.B scope — none is a hard
blocker, and none needs operator input (Tier-2/Tier-3 calls per CLAUDE.md
"Decision authority").

## Partial — rendering simplified

### Volume Profile — computed, not yet drawn in the panel

- **Sidecar:** fully implemented. `compute_volume_profile` distributes total
  traded volume across 24 price buckets; `test_volume_profile_buckets_sum_to_total_volume`
  verifies the buckets sum to the series volume.
- **Contract fit:** Volume Profile is a _price-axis histogram_, not a time
  series. To return it through the shared `IndicatorSeries` contract without a
  contract change, each bucket is emitted as one point whose `time` field holds
  the price-level label and whose `value` holds the volume at that level — a
  deliberate, documented overload of the `time` field.
- **Panel gap:** `ChartPanel.tsx` renders every `separate`-pane indicator as a
  lightweight-charts line series keyed on time. Volume Profile's price-label
  "times" do not parse as timestamps, so its points are filtered out and the
  series renders empty — i.e. selecting Volume Profile currently shows nothing
  on the chart. Drawing it correctly needs a horizontal-histogram custom series
  (a lightweight-charts custom series primitive) or a dedicated price-bucket
  pane, which is larger than Phase 1.B chart scope.
- **Deferred to:** a follow-up that adds a horizontal-histogram renderer. The
  data is already available to consume.

### Parabolic SAR — drawn as a line, not dots

- **Sidecar:** fully implemented (`compute_parabolic_sar`) — Wilder's iterative
  algorithm with the acceleration-factor ramp; `test_parabolic_sar_defined_from_second_bar`
  covers it.
- **Panel:** rendered as a normal price-pane line series. The conventional
  presentation is a series of dots flipping above/below price. lightweight-charts
  has no dot-marker series type out of the box; a markers primitive would do it.
  The line still tracks the SAR values correctly — only the visual convention
  differs.

## Simplified semantics (intentional, in scope)

### VWAP — running, not session-anchored

`compute_vwap` accumulates volume-weighted price across the whole supplied
series. True VWAP resets each trading session; the sidecar has no intraday
session-boundary information from the history endpoint, so it treats the window
as one session — a running VWAP. Correct for daily+ timeframes; an
approximation for intraday. The line label notes this.

### Ichimoku — no forward cloud projection

`compute_ichimoku` computes all five classic lines (Tenkan, Kijun, Senkou A/B,
Chikou) with the standard 9/26/52 windows and the ±26 shifts. Senkou spans that
the shift pushes beyond the series window are dropped — the panel does not draw
a future-projected cloud. The historical portion of every line is correct.

## Fully working (no caveats)

RSI, MACD, MA, EMA, SMA, Bollinger Bands, Volume, ADX, Stochastic, ATR, OBV,
MFI, CCI, Williams %R, ROC — computed server-side and rendered as price-pane
overlays or synced oscillator panes.
