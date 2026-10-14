# batch-3/W5-india-data-witnesses (rc1-battery-21, set-9)

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52361 (own
data dir, cwd `<cand>/sidecar`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-005 | `GET /fundamentals/JUMBO`, `/JNPR`, `/VERTEX` | JUMBO book_value 54.361 flagged vs 57.01 (equity/shares); JNPR book_value 70.02 flagged vs 60.17 (14.1%); VERTEX shares_outstanding flagged 50% vs market-cap-implied share count. All three `field_meta.book_value.status == "flagged"` with the reason naming the disagreeing shares/equity figure. | holds |
| R15-LEAD-002 | 3 rounds `curl -H 'X-Vysted-Region: IN'` fundamentals for TCS/INFY/ITC/HDFCBANK/SBIN | round 1 (first-ever fetch on this fresh sidecar, no cache) 15.6-17.7s; round 2 (cache warm) 0.98-2.24s; round 3 1.69-2.15s — matches the certified pattern (one cold miss then sub-2.5s, the witness result is cached and not re-fetched per request) | holds |
| R15-RESEARCH-011 | in-process `corporate_disclosures.get_shareholding` + `ownership_check.get_exchange_ownership` for SIL.NS/RELIANCE.NS/TCS.NS; grep `semantics.py` | `ExchangeOwnership.source='NSE'` while `institutions_source='BSE'`/`institutions_as_of` carry the BSE quarter distinctly (not silently overwritten to NSE/latest.quarter_end); `semantics.py:595,597` reads `institutions_source`/`institutions_as_of` separately from `source`. Live BSE quarter matched NSE quarter this run (no nearest-quarter mismatch case surfaced live), but the carry-through mechanism the fix added is intact and exercised. | holds |
| R15-RESEARCH-013 | grep `services/research/fast.py:478`; `GET /disclosures/announcements` for JUMBO (BSE-only) vs AMAL (dual) | `fast.py:478` now does `value["provider"] = "+".join(sources)` (matches fix_shape exactly, replacing the hardcoded `'nse+bse'`); live sources: JUMBO `["BSE"]`, TTC `["BSE"]`, AMAL `["NSE","BSE"]` — a BSE-only listing would stamp `provider="bse"`, never `"nse+bse"` | holds |
| R15-DATA-019 | `GET /disclosures/announcements?symbol={JUMBO,TTC,AMAL}&limit=25` | JUMBO count 0→18 (cert: 18), TTC 2→16 (cert: 16, exact match), AMAL 1→21 (cert: 19, now 21 — grew further live, still far above 1); all responses carry `sources` populated | holds |
| R15-DATA-021 | grep `corporate_disclosures.py` (`_SPLIT_MERGE_MAX_DAYS = 100` at :1228, distance-bound check at :1263-1264); in-process `get_shareholding('SIL.NS')` full series | Distance bound present in code exactly as fixed. Live SIL series 2021-09→2026-06: every quarter now carries its own same-quarter BSE split (`split_as_of == quarter_end` in every row), with real distinct institutions% by era (4.14-4.95% in 2021-2022 vs 42.83-43.02% from 2022-Q3 on) — no quarter carries a copied value from >100 days away | holds |
| R15-DATA-022 | `GET /disclosures/shareholding?symbol=SMR`; in-process `bse_provider._shp_quarter_end('04 Jun 2026')` / `('30 September 2026')` | count 1, quarter_end 2026-06-04, promoter 65.74/FII 9.88/DII 0.84 (exact match to cert and screener.in pack); both 3-token and 2-token date formats parse correctly (`2026-06-04`, `2026-09-30`) | holds |

COVERAGE: 7/7 ids raw.
