# xadv-keyless-3 — first boot's NSE EOD warm labels a holiday as a trade date (legacy fallback file)

Lens: a stranger's first boot on a Saturday (3 Oct 2026); the sidecar's background EOD warm runs at once on a clean profile.

## Observed (own stack :52900, clean profile, built binaries at d38b5d1a)
main.log:
```
15:07:59,009 INFO services.fundamentals_warm: fundamentals warm: bhavcopy EOD applied to 2923 NSE rows (trade date 2026-10-02)
```
data_cache.db (read-only open): key `nse_bhavcopy:20261002` present (7-day TTL, `_CACHE_TTL_SECONDS = 7 * 24 * 3600.0`, nse_bhavcopy.py:104).

2 Oct 2026 is an NSE holiday — the product's own table says so: `sidecar/services/locale.py:98  "2026-10-02",  # Mahatma Gandhi Jayanti`.

## Outside probes (direct, saved under SCRATCH/final-xadv-keyless/)
```
https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20261002_F_0000.csv.zip  -> 404   (primary: no file for the holiday)
https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20261001_F_0000.csv.zip  -> 200
https://archives.nseindia.com/products/content/sec_bhavdata_full_02102026.csv -> 200, 401205 bytes, rows read:
   "20MICRONS, EQ, 01-Oct-2026, 214.59, ..."   "RELIANCE, EQ, 01-Oct-2026, 1187.00, 1180.10, 1183.90, 1160.80, 1167.70, 1167.70, ..."
https://archives.nseindia.com/products/content/sec_bhavdata_full_01102026.csv -> 200, 401205 bytes, identical rows (DATE1 01-Oct-2026)
sec_bhavdata_full_03102026.csv / 05102026.csv -> 404 ; 30092026.csv -> 200 with DATE1 30-Sep-2026
```
So the legacy host serves 1 Oct's file under the holiday's 2 Oct name, and every row's own DATE1 column says 01-Oct-2026.

## Mechanism (code at d38b5d1a)
- `services/nse_bhavcopy.py` `fetch_latest` (~376-402): walks back from today; for 2 Oct `_fetch_day` gets primary 404 then fallback 200 with rows -> `return BhavcopyResult(trade_date=day, rows=rows)` with `day` = the REQUESTED date; it never consults `_is_trading_day` on an ok result (that check runs only on the `missing` branch).
- `parse_bhavcopy` (236-268) reads SYMBOL/SERIES/CLOSE/PREV_CLOSE/VOLUME/HIGH/LOW but ignores the row's `DATE1` / `TradDt`.
- `services/fundamentals_warm.py:270-283` writes `trade_date_iso = result.trade_date.isoformat()` into every item; `fundamentals_store.upsert_eod_batch` (478-510) stores it as `quote_timestamp` ("= the TRADE DATE, so the EOD basis is visible") with `provider = nse_bhavcopy`, and `row_to_pair` (617-650) materialises it as `Quote.timestamp`.

## Effect
Prices and prev_close are correct (they are 1 Oct's); the as-of DATE is wrong by one (a holiday), and the 7-day cache entry records the holiday as a trading day, so every bhavcopy walk until it expires re-applies the wrong label. On this machine the Yahoo v7 batch overwrote the rows minutes later (store now shows `yahoo-v7-batch|2026-10-01|2912`), so the wrong stamp is visible only where Yahoo is blocked — precisely the case the bhavcopy lane exists for (fundamentals_warm.py:256 docstring: "what keeps prices one-trading-day fresh on a Yahoo-blocked IP").

## R3 duplicate check (register at d38b5d1a)
Nearest: R15-LIFECYCLE-022 (fixed) — "A moved NSE bhavcopy archive path is read as a week of holidays ... the UDiFF-primary 404 never tries the live legacy fallback". Its fix ADDED the fallback attempt; this is a different mechanism (the fallback's file is accepted under a date it is not for). Not a regression of 022 (022's promise — a moved path is not read as holidays — still holds). No entry names DATE1 / holiday-dated fallback. New, low (R2: an as-of label one holiday day off; values correct).

Suggested fix shape (for the lead, not applied): take the trade date from the rows' own DATE1/TradDt (or reject an ok result for a date `_is_trading_day` says is closed).

VERDICT xadv-keyless-3: finding keyless:1
