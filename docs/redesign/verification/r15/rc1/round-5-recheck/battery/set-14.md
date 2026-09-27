# batch-4/W4-market-data-gate (rc1-battery-13, shard 13)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, own sidecar :52353.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-016 | GET /fundamentals/DAL | `fifty_two_week_high`/`low` both null; field_meta `withheld`, reason "no trades in 52 weeks (last trade 2025-03-12); withheld" | holds |
| R15-DATA-047 | GET /fundamentals/ABBOTINDIA | `dividend_per_share=525` field_meta `flagged` ("below the 656 actually paid in the trailing 12 months by 20%…"); `dividend_per_share_ttm=656` | holds |
| R15-DATA-049 | GET /fundamentals/VIYASH, /fundamentals/ELCIDIN | VIYASH: ttm 0.0 / yield 0.0, reason "no dividends paid (trailing 12m)"; ELCIDIN: ttm 25.0, yield 0.0236%, reason "trailing-12m dividends paid (25) / price (103800)" | holds |
| R15-DATA-034 | in-process `yahoo_batch_provider.fundamentals_from_v7` on stub rows w/ yield 1.5, 0.9, 0.03 | 1.5 and 0.9 (150%/90%) withheld: "exceeds the plausible fraction bound of 25%"; 0.03 passes. No 2.0 (200%) bound remains — every v7 row runs through `correctness_gate.validate_fundamentals` (docstring cites R15-DATA-034) | holds |
| R15-DATA-082 | in-process `ccxt_provider._ticker_to_quote({'last':0,'close':0})` then `correctness_gate.validate_quote(...)`; live GET /quotes?symbols=BTC/USDT,ETH/USDT&asset_class=crypto | zero-price ticker passes `_ticker_to_quote` (0 is falsy but not None) but the gate rejects it: `CorrectnessError: non-positive price 0.0 for 'BTC/USDT'`; registry validator is `check_staleness=asset_class!='crypto'` (gate still runs for crypto, only staleness skipped). Live quotes: real prices, `freshness: live` | holds |
| R15-LIFECYCLE-004 | in-process: real RELIANCE historicalOR window, rename CH_OPENING_PRICE/CH_TRADE_HIGH_PRICE/CH_TRADE_LOW_PRICE/CH_TOT_TRADED_QTY, stub `nse_provider._get_json`, call `provider_registry.get_history('RELIANCE.NS','1d','1mo')` | log: "provider nse_direct failed for ohlcv, falling through: … lacks CH_OPENING_PRICE, CH_TRADE_HIGH_PRICE, CH_TRADE_LOW_PRICE, CH_TOT_TRADED_QTY (payload shape changed)"; served `provider=nse`, `n=26`, `flat_bars=0`, `zero_volume_bars=0` | holds |
| R15-DATA-035 | in-process `bse_provider._bhavcopy_for`/`_marker_after_day` w/ temp cache dir + real `_download_bhavcopy(2026-09-23)` | same-day marker (mtime on the trading day) → `None` (not honoured, re-fetches); after-day marker (mtime next day) → `""` (honoured); live download → 5,060-row real BSE bhavcopy served | holds |
| R15-DATA-036 | live GET /history/KSE.BO?range=1y&interval=1d (warm cache, second call) | 255 bars, `provider=bse`, 0.33s warm (pre-fix baseline ~11.9s per batch-4 cert); `_scrip_row` filters day-file lines by code/ticker instead of parsing the whole market (docstring cites R15-DATA-036) | holds |

Note: the BSE marker probe used `bse_provider._cache_dir()`, which is a fixed OS cache dir
(`~/Library/Caches/bse-bhavcopy`), not scoped by `VYSTED_DATA_DIR` — the probe removed its
same-day/after-day marker files after each check; the final live-download step left a correct
`2026-09-23.csv` in that shared cache (harmless — real, current data, not corruption).

COVERAGE: 8/8 ids raw; no raw: none.
