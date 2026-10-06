# R15-DATA-064 / rc1-verifier:9: partial

Refutation audit round 2, group data. Own sidecar :52360 (pid 4861) from source at HEAD a3275f64. The code tree equals candidate 4c6dfe8c. Written 18:23 IST.

## Entry's own repro (no range) plus the verifier's explicit ranges, 5 symbols
```
18:17 IST
== GET /history/SPY?timeframe=30m
bars 286 provider yfinance reason None first 2026-08-26T09:30:00-04:00 detail None
== GET /history/SPY?timeframe=30m&range=3mo
bars 0 provider none reason None first None detail None
== GET /history/SPY?timeframe=30m&range=1y
bars 0 provider none reason None first None detail None
== GET /history/SPY?timeframe=30m&range=1mo
bars 286 provider yfinance reason None first 2026-08-26T09:30:00-04:00 detail None
== GET /history/SPY?timeframe=15m&range=3mo
bars 0 provider none reason None first None detail None
== GET /history/AAPL?timeframe=30m
bars 286 provider yfinance reason None first 2026-08-26T09:30:00-04:00 detail None
== GET /history/AAPL?timeframe=30m&range=3mo
bars 0 provider none reason None first None detail None
== GET /history/AAPL?timeframe=30m&range=1y
bars 0 provider none reason None first None detail None
== GET /history/AAPL?timeframe=30m&range=1mo
bars 286 provider yfinance reason None first 2026-08-26T09:30:00-04:00 detail None
== GET /history/AAPL?timeframe=15m&range=3mo
bars 0 provider none reason None first None detail None
== GET /history/RELIANCE?timeframe=30m
bars 286 provider yfinance reason None first 2026-08-26T09:00:00+05:30 detail None
== GET /history/RELIANCE?timeframe=30m&range=3mo
bars 0 provider none reason in_eod_only first None detail None
== GET /history/RELIANCE?timeframe=30m&range=1y
bars 0 provider none reason in_eod_only first None detail None
== GET /history/RELIANCE?timeframe=30m&range=1mo
bars 286 provider yfinance reason None first 2026-08-26T09:00:00+05:30 detail None
== GET /history/RELIANCE?timeframe=15m&range=3mo
bars 0 provider none reason in_eod_only first None detail None
== GET /history/RELIANCE.NS?timeframe=30m
bars 286 provider yfinance reason None first 2026-08-26T09:00:00+05:30 detail None
== GET /history/RELIANCE.NS?timeframe=30m&range=3mo
bars 0 provider none reason in_eod_only first None detail None
== GET /history/RELIANCE.NS?timeframe=30m&range=1y
bars 0 provider none reason in_eod_only first None detail None
== GET /history/RELIANCE.NS?timeframe=30m&range=1mo
bars 286 provider yfinance reason None first 2026-08-26T09:00:00+05:30 detail None
== GET /history/RELIANCE.NS?timeframe=15m&range=3mo
bars 0 provider none reason in_eod_only first None detail None
== GET /history/TCS.NS?timeframe=30m
bars 286 provider yfinance reason None first 2026-08-26T09:00:00+05:30 detail None
== GET /history/TCS.NS?timeframe=30m&range=3mo
bars 0 provider none reason in_eod_only first None detail None
== GET /history/TCS.NS?timeframe=30m&range=1y
bars 0 provider none reason in_eod_only first None detail None
== GET /history/TCS.NS?timeframe=30m&range=1mo
bars 286 provider yfinance reason None first 2026-08-26T09:00:00+05:30 detail None
== GET /history/TCS.NS?timeframe=15m&range=3mo
bars 0 provider none reason in_eod_only first None detail None
```
## Sibling caller: the agent's price_data tool (in-process, sidecar/.venv, scratch VYSTED_DATA_DIR)
`_price_data({'symbol':S,'timeframe':TF})` uses the tool's default range of '6mo' (services/agent_tools/price_data.py:44):
```
$AAPL: possibly delisted; no price data found  (period=6mo) (Yahoo error = "15m data not available for startTime=1774356550 and endTime=1790426950. The requested range must be within the last 60 days.")
provider yfinance failed for ohlcv, falling through: correctness gate: empty series for 'AAPL' from 'yfinance'
AAPL 30m ok False bars_returned None bars_available None window_start None err provider error: correctness gate: empty series for 'AAPL' from 'yfinance'
RELIANCE.NS 30m ok False bars_returned None bars_available None window_start None err provider error: correctness gate: empty series for 'RELIANCE.NS' from 'yfinance'
AAPL 15m ok False bars_returned None bars_available None window_start None err provider error: correctness gate: empty series for 'AAPL' from 'yfinance'
AAPL 1d ok True bars_returned 90 bars_available 127 window_start 2026-05-19T00:00:00-04:00 err None
```

## Code
- sidecar/services/yfinance_provider.py:130 now reads `"30m": ("30m", "1mo")`, so the default lookback is fixed.
- yfinance_provider.py:521-522: `interval, default_period = _TIMEFRAME_MAP...; period = range_ or default_period`. An explicit range is passed to Yahoo unclamped, so any range longer than Yahoo's 60-day sub-hour window returns empty. This is the entry's exact mechanism ("lookback exceeds Yahoo's 60-day intraday cap").
- sidecar/routers/history.py:55-78 `_empty_series_reason`: it returns `in_eod_only` for any empty intraday series on a known IN listing, even when an intraday provider (yfinance) serves that listing. The fix_shape's clause "only emit in_eod_only when no intraday provider serves the symbol" is unmet.
- The chart (ChartPanel.tsx:460-466) sends range=undefined, so the chart's own 30m now loads. That is the entry's repro.

## Verdict: partial
The entry's stated repro holds: 30m with no range returns 286 bars for SPY, AAPL, RELIANCE, RELIANCE.NS and TCS.NS. The same mechanism is still open on the shared function. The agent's price_data tool (default 6mo) returns an empty series at 30m and 15m for every symbol. Any /history call with a range longer than 60 days at a sub-hour interval returns [], and for Indian listings it carries the false `in_eod_only` blame the entry names. The verifier's refutation reproduces.

Failure count: 1 (this gate refutation). batch-5 certified it; no not_certified listing; not in round 1.
