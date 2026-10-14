# R15-UI-009 — fresh GUI verify at ace7dd768c3b809b0e72b20b20cfc94eea2368bd

Verifier: Opus 5.5 (fresh context, label gui-verify-R15-UI-009). Inputs: register entry, this entry's DRIVE.md, captures + raw/, CAPTURES.jsonl, presence.log, code at ace7dd7.

Claim under test (title + fix_shape + note): Export CSV in Watchlist, Portfolio and (fresh) Screener in the packaged macOS app must each show the saved path on screen and write the file under `<app data>/exports/csv/` — not silently no-op.

## Registration / presence
All 11 PNGs in this folder hash-match a CAPTURES.jsonl row with tool `scripts/rig/rig.py capture`, window_owner `Vysted Terminal`. Each evidence capture follows a presence.log line for this entry (idle >= 900 s, sentinel present): 04/06 (taken 01:58:06Z / 01:58:22Z) after pre-batch-A 01:57:47Z idle 1202.5; 10 (02:15:18Z) after pre-batch-B 02:13:55Z idle 930.9; 11 (02:30:54Z) after pre-batch-C 02:30:48Z idle 933.6. No unregistered captures.

## Per part
| Part | Evidence | What it shows | Ruling |
|---|---|---|---|
| Portfolio Export CSV | ace7dd7-04-portfolio-export-clicked.png; raw/ace7dd7-exports-ls-after-batchA.txt, raw/ace7dd7-csv-headers-after-batchA.txt | Populated portfolio (Portfolio · 2, MV $4,506.65); status strip "Saved …/com.vysted.terminal/exports/csv/vysted-portfolio-portfolio.csv"; file 296 B, portfolio header | holds |
| Watchlist Export CSV | ace7dd7-06-watchlist-export-clicked.png; same raw files | 7 priced rows; strip "Saved /private/tmp/clau… …watchlist.csv" (right edge clipped by narrow panel, begins/ends correctly); file 420 B, watchlist header | holds |
| Screener Export CSV (fresh, after a run) | ace7dd7-10 (before click) vs ace7dd7-11 (5 s after click); raw/ace7dd7-batch-C.log (click ok); raw/ace7dd7-exports-ls-final.txt, raw/ace7dd7-csv-headers-final.txt | 10 and 11 are visually identical: "18 matched … 456 ms", "Export CSV NIFTY50", no saved path, no toast, no error. File vysted-screener-nifty50.csv (3.5 KB, 18 rows) was written at the click time | DEFECT VISIBLE: the user-facing control is still silent |

Code at ace7dd7 corroborates (not a substitute for the capture): `src/modules/screener/ScreenerResultsTable.tsx:283-285` `downloadScreenerCsv` does `void downloadCsv(...)`, discarding the result; the file has no exportStatus / "Saved" surface (grep finds none), so a success and a failure are both invisible on screen.

## Ruling: not_certified
The note requires each of the three panels to show the saved path. Watchlist and Portfolio do; Screener writes the file but shows nothing (capture 11 = capture 10), which is the entry's "silent dead control" symptom from the user's view. Fix: give the screener the same Saved <path> / Export failed status strip.
