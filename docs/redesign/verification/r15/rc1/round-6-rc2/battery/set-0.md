# set-0 — batch-2/W1-fundamentals-seam (battery shard 24, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-008 | GET /fundamentals/SIFY (US) on :52364 | currency USD, financial_currency INR, revenue_ttm 46,506,049,536 labelled INR basis; price_to_sales status withheld ("USD listing value against INR statements") | holds |
| R15-DATA-004 | GET /fundamentals/{DHANBANK,JONJUA,VERTEX,NAPEROL,DHOOTTRANS} with X-Vysted-Region: IN | all flagged vs exchange shareholding: DHANBANK "no promoter group reported", JONJUA 29.67%, VERTEX 36.43%, NAPEROL inst 1.77%, DHOOTTRANS promoter 82.78% | holds |
| R15-DATA-013 | GET /fundamentals/{DAL,SMR,JNPR,DHOOTTRANS} | DAL eps served 2.05 (BSE) and pe flagged "implies 24.5"; SMR eps/pe flagged vs 13.27; JNPR eps 0.91 ok; DHOOTTRANS eps 21.22 ~ NI/shares 21.17 | holds |
| R15-DATA-006 | GET /quotes/DAL (IN) + /fundamentals/DAL | timestamp 2025-03-12, change 0.0, freshness stale; price-derived field_meta as_of 2025-03-12 | holds |
| R15-DATA-070 | venv python: _parse_struct_time(None)/_parse_iso(None|garbage); fetch_news sort source | all None (no fabricated now); dated sorted newest-first then undated appended | holds (live RSS not fetched; unit-level call) |
| R15-DATA-033 | venv python: NaN/inf Quote and NaN/inf last-close series through correctness_gate | all four raise CorrectnessError (fall through to next lane) | holds |

COVERAGE: 6/6 ids raw; no raw: none
