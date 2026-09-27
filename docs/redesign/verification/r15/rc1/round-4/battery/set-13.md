# set-13 — batch-4/W4-market-data-gate (rc1-battery-15)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, own sidecar :52355.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-016 | `curl /fundamentals/DAL`, `curl /history/DAL?range=1y` | fifty_two_week_high/low both null, status `withheld`, reason "no trades in 52 weeks (last trade 2025-03-12); withheld"; `/history/DAL` 1y: provider `none`, 0 bars | holds |
| R15-DATA-047 | `curl /fundamentals/ABBOTINDIA` | dividend_per_share 525.0 `flagged` ("below the 656 actually paid in the trailing 12 months by 20%…"), dividend_per_share_ttm 656.0 `ok` | holds |
| R15-DATA-049 | `curl /fundamentals/{VIYASH,ICON,ELCIDIN}` | VIYASH/ICON: ttm 0.0, yield 0.0, reason "no dividends paid (trailing 12m)"; ELCIDIN: ttm 25.0, yield 0.024% with reason "trailing-12m dividends paid (25) / price (103800)" | holds |
| R15-DATA-034 | in-process `yahoo_batch_provider.fundamentals_from_v7` with `trailingAnnualDividendYield` 1.5, 0.9, 0.03 | 1.5 and 0.9 → `dividend_yield=None`, field_meta `withheld`, "a dividend yield of 150.00%/90.00% exceeds the plausible fraction bound of 25%"; 0.03 → `dividend_yield=0.03`, no field_meta entry (no 2.0 bound remains) | holds |
| R15-DATA-082 | in-process `ccxt_provider._ticker_to_quote` (no last/close; last=0,close=0) + `correctness_gate.validate_quote`; `curl /quotes?symbols=BTC/USDT,ETH/USDT&asset_class=crypto` | no-field ticker raises `ProviderError`; last=0/close=0 builds Quote(price=0.0) then gate raises `CorrectnessError: non-positive price 0.0`; live crypto quotes return real prices (BTC 84153.35, ETH 2684.97), freshness `live` | holds |
| R15-LIFECYCLE-004 | modified copy of `parser_drift.py` (SIDECAR path repointed at candidate's sidecar; content otherwise identical) section A, plus a direct `provider_registry.get_history` re-run with the same OHLV-rename stub | `_rows_to_bars` on renamed rows raises `nse_direct: historical row for 2026-09-22 lacks CH_OPENING_PRICE, CH_TRADE_HIGH_PRICE, CH_TRADE_LOW_PRICE, CH_TOT_TRADED_QTY (payload shape changed)`; `provider_registry.get_history` falls through to provider `nse`, 26 bars, 0 flat, 0 zero-volume | holds |
| R15-DATA-035 | in-process `bse_provider._download_bhavcopy`/`_bhavcopy_for` with a temp cache dir, mocked HTTP responses, day 2026-09-23 | HTML-200 writes no marker; 404 writes empty marker; same-day marker not honoured by `_bhavcopy_for` (returns `None`, re-fetches); live fetch of 2026-09-23 returns real 5,060-row (866,264-byte) file | holds |
| R15-DATA-036 | `curl /history/KSE.BO?range=1y` twice, warm cache, timed | 0.49 s then 0.35 s (vs base's ~11.9 s / ~8.7 s order of magnitude), provider `bse`, 255 bars, last close 180.8 matching BSE close for the date | holds |

Note: R15-DATA-036's first curl on bare symbol `KSE` (no suffix) resolved via autocomplete to a coincidental `KSE.NS` (NSE) match, not the BSE-only scrip 519421 the entry is about — re-ran against `KSE.BO` explicitly (matches `/resolve?q=519421`'s `yahoo_symbol`) to hit the intended code path.

COVERAGE: 8/8 ids raw; no raw: none.
