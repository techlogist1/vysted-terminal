# triage-d / rc1-vshard-2:2 (shard tie R15-DATA-015) -> partial, lands on R15-DATA-055

Audited 07:17-07:29 IST. HEAD bed3b166. `git diff --name-only 01015033 HEAD | grep -v '^docs/'` printed `CHANGELOG.md` (lead ledger commit d76a61be, docs only); `git diff --name-only 01015033 HEAD -- sidecar src src-tauri types plugins scripts package.json pnpm-lock.yaml` is empty, so the code audited equals 01015033. Own sidecar: `sidecar/.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 52435`, `VYSTED_DATA_DIR=<scratch>/refaudit4-triage-d/data`, MCP ports 0, pid 90459.

## Shard claim
rc1-vshard-2:2: "a listing younger than 52 weeks serves its since-listing extremes as the 52-week range with status ok and no 'since <date>' label" (JNPR: hi 282 / lo 232.11, field_meta status ok, label null; /history 1y = 36 bars from 2026-08-06).

## Register entries that cover it
- R15-DATA-015 (tie, fixed, wrong-52w-range): title is a truncated single-exchange series served as the 52w range (ELCIDIN). Its fix_shape ends with "when history is shorter than 52 weeks, label 'since <date>'".
- R15-DATA-055 (fixed, medium, missing-period-label): title "... a 33-day or 14-week-old listing's range is labelled '52w' with a '1Y change'". Raw repro DAT-P1-5 is JNPR itself. fix_shape: "listing_date from firstTradeDateMilliseconds; label the range 'since listing' when history < 52 weeks". Batch-9 not certified because the panel's since-listing leg was missing, then closed at f407107 (batch 10).
The residual's VALUES are right (there is no trading before listing), only the window LABEL is wrong. That is DATA-055's class, not DATA-015's (whose defect is wrong values from a truncated venue). DATA-015's own repro is fixed at HEAD (below).

## Commands at HEAD (port 52435)
```
$ curl :52435/fundamentals/ELCIDIN   (DATA-015 own repro)
ELCIDIN.NS 137000.0 102210.0 listing_date 2026-04-20
fifty_two_week_high flagged "... disagrees with the NSE + BSE exchange range 87,003.00-144,500.00 since 2025-09-12; kept, flagged"
fifty_two_week_low  flagged "52-week low 102,210.00 is 15% off the NSE + BSE exchange range ..."

$ curl :52435/fundamentals/JNPR     (shard repro)
{'symbol': 'JNPR.NS', 'fifty_two_week_high': 282.0, 'fifty_two_week_low': 232.11, 'listing_date': '2026-08-06', 'first_trade_date': '2026-08-06', 'currency': 'INR'}
meta_hi {'status': 'ok', ..., 'label': None}   fifty_two_week_high_date 2026-08-27, fifty_two_week_low_date 2026-08-06
fifty_two_week_change 0.024411798 (status ok)
```
JNPR at the user surface: `src/modules/equity-overview/EquityOverviewPanel.tsx:226-229` `listedUnderAYear` reads `fundamentals.listing_date` (2026-08-06, under 364 days), so line 1074 renders "since listing 232.11 - 282.00" and lines 843-846 drop the "1Y change" row. The agent's fundamentals tool dumps the whole model (`agent_tools/fundamentals.py:172`), listing_date and the 52w leg dates included. So for JNPR the shard read the wrong field: the label rides the typed `listing_date`, not `field_meta.label`. On JNPR alone the shard claim would be a verifier_error.

Fresh class cases (not NSE, so no listing_date):
```
$ curl :52435/fundamentals/{NAVN,MDLN,WLTH}
NAVN {'fifty_two_week_high': 30.88, 'fifty_two_week_low': 8.105, 'fifty_two_week_change': -0.029250026, 'listing_date': None, 'first_trade_date': '2025-10-30'} st_hi ok lbl None
MDLN {'fifty_two_week_high': 50.876, 'fifty_two_week_low': 31.49, 'fifty_two_week_change': -0.15463412, 'listing_date': None, 'first_trade_date': '2025-12-17'} st_hi ok lbl None
WLTH {'fifty_two_week_high': 14.75, 'fifty_two_week_low': 7.2, 'fifty_two_week_change': -0.27025092, 'listing_date': None, 'first_trade_date': '2025-12-15'} st_hi ok lbl None
$ curl ':52435/history/NAVN?timeframe=1d&range=1y'  -> yfinance 227 bars, first 2025-10-30 (IPO), partial False, coverage_start None
$ curl ':52435/history/MDLN?timeframe=1d&range=1y'  -> yfinance 194 bars, first 2025-12-17, partial False, coverage_start None
```
NAVN (IPO 2025-10-30, 332 days ago), MDLN and WLTH (Dec 2025 IPOs) have under 52 weeks of trading. `listing_date` is set only for `.NS` symbols from the NSE master (`sidecar/services/yfinance_provider.py:952`), so it is null for them. `listedUnderAYear` returns false, the panel labels the since-IPO range "52w", and it shows the since-IPO change as "1Y change". `first_trade_date` is on the wire and correct for these, but the panel never reads it.

## Verdict
partial. It lands on R15-DATA-055, re-tied from the shard's R15-DATA-015. DATA-055's stated repro (JNPR/DHOOTTRANS, NSE listings) holds at HEAD. A stated part of its fix_shape ("label the range 'since listing' when history < 52 weeks", driven by firstTradeDateMilliseconds) does not hold for any listing outside NSE. The fix sourced the date only from the NSE master. DATA-015 is not reopened: its own ELCIDIN repro holds (both bounds flagged).
Severity: medium, unchanged. The extremes are true; the window label and "1Y change" overstate the window by weeks to months.
Root cause: src/modules/equity-overview/EquityOverviewPanel.tsx:227 (`const listed = fundamentals?.listing_date;`). The under-a-year test ignores `first_trade_date`, and `listing_date` is NSE-only (sidecar/services/yfinance_provider.py:952).
Certification failures: DATA-055 register note has no 'certification failures so far' clause. The baseline is 1: batch-9 VERDICTS.json not_certified. There are 0 refutation-audit partial or regression verdicts. With this partial the count is 2.

Adjacent observation (not scored): `/history/NAVN?range=1y` returns 227 bars from the IPO with `partial=false, coverage_start=null`. This is the same shape as the shard-2 adjacent (1) near DATA-037. Separately, the screener's "1y change (frac)" column reads Yahoo's since-listing change for young listings.

End-of-audit (07:33 IST): own sidecar pid 90459 on :52435 stopped by pid (health now 000); no child processes; the repo working tree is unchanged apart from these output files.
