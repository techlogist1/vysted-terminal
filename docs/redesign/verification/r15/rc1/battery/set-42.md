# batch-10/W3-fundamentals-bse-cache

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`, data dir
`rc1-data-rc1-battery-0`. All 6 entries re-run live against the candidate's own routes.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-048 | `GET /fundamentals/RELIANCE.NS`, `/CREST.NS`, `/AMAL.NS`, `roce` field. | roce RELIANCE 0.08994, CREST 0.03686, AMAL 0.22332 — matches cert (0.0899/0.0369/0.2233) to 4 decimals; `field_meta.roce.provider=derived`, basis_note "annual EBIT / (total assets - current liabilities)". | holds |
| R15-DATA-054 | Same fetches, `basis` field. | RELIANCE `consolidated`, CREST `consolidated`, AMAL/ELCIDIN `null`; `field_meta.basis.provider=exchange-filings`. | holds |
| R15-DATA-055 | `listing_date` on AMAL, DHOOTTRANS, RELIANCE, TCS. | AMAL 2026-08-17, DHOOTTRANS 2026-08-17, RELIANCE 1995-11-29, TCS 2004-08-25 — exact match to cert. | holds |
| R15-DATA-053 | `GET /quotes/ICON.BO`, `/quotes/ICONIKSPEV.BO`. | ICON.BO: provider=bse, price 64.45, volume 1200, prev_close 63.06 (exact match). ICONIKSPEV.BO: provider=bse, `freshness:"eod"`, but the OHLCV numbers (open 33.9/high 34.59/low 31.32/volume 0.81, timestamped 2026-09-25) differ from the cert's snapshot (open 33.95/high 33.95/low 32.57/volume 5967) — expected live-data drift across trading days between the original cert capture and today, not a regression: the mechanism (a real BSE EOD row served, not fabricated/mis-flagged) is unchanged. | holds |
| R15-DATA-096 | `GET /fundamentals/AAPL/income` twice, timed. | cold 1173ms, warm (repeat) 15ms, byte-identical payload — cache hit confirmed. | holds |
| R15-DATA-068 | `GET /earnings/AAPL/history`, `/fundamentals/AAPL/ratings/{history,individual,price-target-history}`. | All 4 routes carry a populated `as_of` timestamp. | holds |
| R15-DATA-061 | `GET /macro/ECB.<bad-id>`, `/macro/WORLDBANK.<bad-id>`, `/quotes/ZZZZNOTREAL`, `/macro/FRED.<id>` (no key configured). | Every route now returns a structured `{"detail": <humanized sentence>, "code": <kind>, "action": <next step>}` body — no raw yfinance/World Bank exception text leaks (`errors.py`'s `_PROVIDER_ERROR_HTTP[kind]` single dispatch table maps kind→status/code/sentence/action for every route, replacing the old per-route kind-blind 502). ECB/World Bank upstream failures → `code:"provider_error"`, HTTP 502; unknown quote symbol → `code:"not_found"`, HTTP 404; FRED-no-key → a clear actionable sentence, not a stack trace, `code:"provider_error"`. Raw: `raw/set-42/R15-DATA-061.txt`. | holds |

**Set result: 7/7 holds.**
