# Set: batch-4/W4-market-data-gate (set-13) — rc1-battery-19 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-016 | GET /fundamentals/DAL; /history/DAL 1y and 5y (own sidecar :52359) | both 52w bounds None, withheld "no trades in 52 weeks (last trade 2025-03-12)"; 1y 0 bars; 5y 33 real bars ending 2023-12-07 | holds |
| R15-DATA-047 | GET /fundamentals/ABBOTINDIA | dividend_per_share 525 status flagged ("below the 656 actually paid in the trailing 12 months by 20%"), dividend_per_share_ttm 656 | holds |
| R15-DATA-049 | GET /fundamentals/VIYASH, /fundamentals/ELCIDIN | VIYASH ttm 0.0, yield 0.0 "no dividends paid (trailing 12m)"; ELCIDIN ttm 25, yield 0.000245 "trailing-12m dividends paid (25) / price (102155)" | holds |
| R15-DATA-034 | in-process fundamentals_from_v7 with yield 1.5 / 0.9 / 0.03 | 1.5 and 0.9 -> None, withheld "exceeds the plausible fraction bound of 25%"; 0.03 kept; no 2.0 bound left | holds |
| R15-DATA-082 | in-process registry.get_quote(BTC/USDT, crypto) with stubbed ccxt ticker; live /quotes crypto | no last/close -> ProviderError; last=0 -> CorrectnessError "non-positive price 0.0"; live BTC 84656.8 freshness live | holds |
| R15-LIFECYCLE-004 | in-process: real RELIANCE historicalOR window (10 rows), OHLV fields renamed, registry.get_history | nse_direct raises "lacks CH_OPENING_PRICE ... (payload shape changed)"; registry falls to provider nse, 26 bars, 0 flat, 0 zero-volume | holds |
| R15-DATA-035 | in-process bse_provider._download_bhavcopy / _bhavcopy_for in a temp cache | HTML-200 writes no marker; marker written on its own day not honoured (None); pre-fix mtime marker not honoured; live fetch 2026-09-23 returned 5060 rows | holds |
| R15-DATA-036 | warm 250-day temp cache of the real 5060-row day file, _assemble_history KSE (519421) 1y | 0.33 s / 0.32 s, 246 bars, last close 179.15 (was ~8.7 s) | holds |

COVERAGE: 8/8 ids raw (battery/raw/set-13/); no raw: none
