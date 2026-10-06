# batch-12/W7-instrument-region-on-the-chart-indian-index-calendar (round 4, candidate 1006c6da)

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-090 | `GET /quotes/^NSEI`, `^BSESN`, `^NSEBANK`, `^CNXIT`, `^INDIAVIX`, `AAPL` under `X-Vysted-Region: IN` and `US` (live, this round); source read `sidecar/routers/quotes.py:29-45` + `sidecar/services/locale.py:280-308` (`freshness_for`) | Live at Sun 2026-09-27 02:01 IST — no exchange (NSE or US) is open right now, so every symbol reads `eod` under BOTH region headers (no "live" case reproducible this session; the cert's live repro ran Friday 11:07 IST during NSE hours). What DOES hold: `freshness` is identical for every symbol regardless of the `X-Vysted-Region` header — `_label_freshness` derives `region = instrument_region(quote.symbol, quote.provider)` (the instrument's own exchange), never the session/user region, matching the certified fix exactly (`freshness_for` keys off the instrument's calendar, not the caller's locale) | holds |

Evidence: `raw/set-62/R15-UI-090-{NSEI,BSESN,NSEBANK,CNXIT,INDIAVIX,AAPL}_{IN,US}.txt` (note: on-disk filenames retain the literal `%5E` from the caret URL-encoding), `raw/set-62/R15-UI-090-source-and-notes.txt`.

Note: the exact "closed-US-quote reads live during NSE hours" cross-region case could not be forced live this session (Sunday, all exchanges closed) — verdict rests on the region-header-independence observed live plus the source fix being unchanged and matching the certified description; this is a repro-timing constraint, not a blocked_env (no upstream outage — the fix's own precondition, a market being open, simply isn't true right now).

COVERAGE: 1/1 ids raw; no raw: none.
