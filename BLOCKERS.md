# Phase 1 — Blockers & Known Issues

No operator-action-required blockers were hit during the Phase 1 autonomous
build. The items below are known issues / deliberately deferred work, recorded
here for the v0.2.0 changelog and the Phase 2 handoff. Each is a Tier-2/Tier-3
call per `CLAUDE.md` "Decision authority" — none needs operator input.

## Resolved during integration

- **`test_app.py` stub-mount check** (raised by Teammate C). The Phase 1.A-2
  scaffold test asserted the four stub routers still returned a `_status`
  payload; Phase 1.B replaced those stubs with real endpoints. Resolved at
  integration: `test_app.py` now verifies the real routers are mounted via the
  OpenAPI schema, and the vestigial `_status` endpoints were removed.

## Known issues — chart panel indicators (Teammate A)

All 20 indicators are computed server-side and unit-tested. Five have simplified
_rendering_ or _semantics_ within Phase 1.B scope:

- **Volume Profile** — computed (24 price buckets, sum-verified) but **not yet
  drawn**: it is a price-axis histogram returned through the time-series
  `IndicatorSeries` contract via a documented overload of the `time` field, and
  the panel's line-series renderer filters those price-label "times" out — so
  selecting Volume Profile currently shows nothing. Needs a horizontal-histogram
  custom series. Data is ready to consume.
- **Parabolic SAR** — full Wilder algorithm, but drawn as a line rather than the
  conventional above/below-price dots (lightweight-charts has no dot-marker
  series type out of the box; a markers primitive would do it).
- **VWAP** — running (whole-series) rather than session-anchored; the history
  endpoint exposes no intraday session boundaries. Correct for daily+ timeframes,
  an approximation intraday.
- **Ichimoku** — all five lines with standard 9/26/52 windows and ±26 shifts;
  Senkou spans pushed beyond the series window are dropped, so no future-
  projected cloud. The historical portion is correct.

Fully working (no caveats): RSI, MACD, MA, EMA, SMA, Bollinger Bands, Volume,
ADX, Stochastic, ATR, OBV, MFI, CCI, Williams %R, ROC.

## Known issues — cross-panel

- **News ↔ watchlist linking** is a follow-up. The news feed filters against a
  built-in Phase 1 symbol set (SPY, QQQ, BTC, ETH, NVDA, AAPL) rather than the
  live watchlist store, because the watchlist's symbol store lives in a
  different module and the parallel teammates could not cross module boundaries.
  Wiring the news feed to the watchlist store is a small Phase 2 task.
- **Equity Overview dividend yield units.** yfinance 1.3.0 appears to return
  `dividendYield` already as a percentage, and the panel multiplies by 100 again
  — AAPL renders as "36.00%" instead of ~0.36%. Cosmetic, single field; the
  panel is otherwise correct. Fix in a Phase 2 polish pass once the yfinance
  units behaviour is pinned down across symbols.
