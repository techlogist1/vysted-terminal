# batch-25/W3-sonnet — rc1-battery-15 (gate round 5, candidate 9bc600ec)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-064 | Live curl against own sidecar (:52355): `/history/RELIANCE.NS?timeframe=30m&range=1y`, `/history/SPY?timeframe=30m`, `/indicators/SPY?indicators=rsi,sma&timeframe=30m` (`raw/R15-DATA-064.raw.txt`) | RELIANCE.NS 30m returns 767 bars, `reason:null`, `partial:true`, `coverage_start:"2026-07-06"` (previously empty with reason `in_eod_only`). Default SPY 30m returns 286 bars. `/indicators` returns 200 with real computed RSI/SMA series (previously 502 "correctness gate: empty series"). Source: `yfinance_provider._TIMEFRAME_MAP["30m"] = ("30m", "1mo")` (within Yahoo's 60-day intraday cap; was `"3mo"`). | holds |
| R15-LEAD-028 | Live curl: `/fundamentals/506597.BO`, `/fundamentals/544774.BO`, `/quotes/506597.BO`, `/history/544774.BO?range=1y`, `/fundamentals/532540.BO`, plus `/fundamentals/500325.BO` + `/history/500325.BO?range=1y` (the round-2 refutation's specific control case) (`raw/R15-LEAD-028.raw.txt`) | `506597.BO` → "Amal Ltd" (AMAL.BO); `544774.BO` → "SMR Jewels Limited" (72 history bars); `532540.BO` → TCS; `500325.BO` → "Reliance Industries Limited" (255 history bars) — the exact case the round-2 refutation audit found broken (`500325.BO` returning TCS/128 bars) now resolves correctly to Reliance. Source `yfinance_provider._yahoo_symbol` now maps a numeric `.BO` scrip code through `symbol_resolver.bse_symbol_for_code` before the correctness gate walk. | holds |

COVERAGE: 2/2 ids raw; no raw: none.
