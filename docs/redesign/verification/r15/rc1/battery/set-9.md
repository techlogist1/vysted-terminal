# batch-3/W5-india-data-witnesses (rc1-battery-1, candidate 4c6dfe8c)

Note: several ids in this set (DATA-015 partially, DATA-021, DATA-024, DATA-029,
DATA-035, DATA-039, DATA-041) actually closed in batches 4/5 per the register's
`closure_evidence`, not batch-3 — evidence below cites the entry's real closing
batch, re-run live against the candidate.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-005 | `GET /fundamentals/JNPR`, `/fundamentals/JUMBO`, `/fundamentals/TCS` live; `grep "disagrees by" correctness_gate.py` | JNPR/JUMBO/TCS all 200 (JNPR hit a transient yahoo 429 first try, retry 200); `correctness_gate.py:780` book-value-vs-computed flag mechanism byte-identical to batch-3 cert. Today's JNPR/TCS snapshots don't carry a book_value disagreement to trigger the flag (data-dependent), so the flag itself wasn't observed firing today — code path confirmed unchanged instead. | holds |
| R15-DATA-015 | `GET /fundamentals/ELCIDIN` live | `price_to_book 0.23935114` present; 52-week bounds present in payload (full field list). Matches the shape batch-5 certified (ELCIDIN high+low both flagged). | holds |
| R15-DATA-021 | grep `_merge_bse_split`/`_SPLIT_MERGE_MAX_DAYS` (100) in `corporate_disclosures.py:1228-1280`; direct BSE SHP probe | Merge logic + 100-day bound byte-identical to the batch-3-certified shape. `api.bseindia.com` SHP endpoint still returns 403 (Akamai) from this IP — same environment condition the ORIGINAL certification itself worked around. Live re-derivation with real rows blocked by that same upstream condition. | holds |
| R15-DATA-024 | `GET /disclosures/deals?symbol=` for KOPRAN, ADANIENT, CCDL, IGARASHI | counts: KOPRAN 62, ADANIENT 34, CCDL 106, IGARASHI 77 — all nonzero with bulk/SAST rows present | holds |
| R15-DATA-029 | `GET /earnings/INFY/estimates`, `/earnings/RELIANCE.NS/estimates` | First attempt hit a live Yahoo breaker cooldown (502 provider_error, confirmed via `/system/provider-health` `yahoo.cooldown_remaining`); after cooldown cleared, INFY.NS → INR EPS 19.58006 (matches the batch-4-certified figure exactly), RELIANCE.NS → non-empty real estimates (analyst_count 2/3) | holds |
| R15-DATA-035 | in-process `bse_provider._bhavcopy_for`/`_marker_after_day` against a temp cache dir (3 cases: same-day marker, next-day marker, real content) | same-day marker NOT honoured (None); next-day marker honoured (`''`); a real-content day is served regardless of mtime — all 3 match the certified behaviour exactly | holds |
| R15-DATA-039 | `GET /sec/filings?symbol=INFY` | 40 filings returned (F-6, 6-K, 20-F, 4, 3, 3/A, 144 form types present) vs base's 0 | holds |
| R15-DATA-041 | in-process `_compare_symbols({'symbols':['RELIANCE.NS','RENTOMOJO.NS']})` and a fresh 3-symbol case | `note: "windows not comparable: RENTOMOJO has 7 bars since 2026-09-17"`, best/worst both null; fresh case `[RELIANCE.NS,TCS.NS,ARCIL.NS]` → best TCS, worst RELIANCE, ARCIL named in the note — mechanism fires exactly as certified | holds |

COVERAGE: 8/8 ids raw; no raw: none.
