# batch-2/W2-instrument-identity (set-1)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52352

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-001 | curl /resolve?q=FOCUS; curl /disclosures/shareholding?symbol=FOCUS | Focus Lighting (NSE) candidate now carries isin:null, bse_code:null (no cross-stamp from Focus Business Solution's INE0DXR01010/543312); every shareholding pattern for symbol=FOCUS shows split_source:null (withheld, never merged) | holds |
| R15-CODE-DATA-005 | grep is_applicable/_is_blocked/is_india_target across sidecar/services | market_cap_witness.py, ownership_check.py, research/range_check.py each `is_applicable = is_india_listing` imported from new services/witness.py (identity alias); dividend_actions.py's is_applicable calls the same shared is_india_listing; research/disclosures.py imports is_india_target from relevance.py (single copy) | holds |
| R15-DATA-001 | curl /fundamentals/{DAL,CHTR,SAFE}/income | all three resolve to their .BO Indian listing (March FY-end, Indian-scale revenue) instead of the US-ticker-collision company (Delta/Charter/Safehold) | holds |
| R15-DATA-012 | in-process symbol_resolver.resolve('NSDL','IN') after injecting a bogus NSDL->GUJENERGY rename row; live /resolve?q=SHREE,HSIL,WORTH,DTIL | NSDL (BSE-only) resolves to its own instrument, rename=None (bogus rewrite refused); live SHREE/HSIL/WORTH/DTIL each resolve to their own correct company, rename=None (no more AJMERA/AGI/WORTHPERI/DVL cross-stamp) | holds |
| R15-DATA-018 | curl /resolve?q=zomato\|ZOMATO\|SEQUENT | both resolve correctly to ETERNAL / VIYASH with former_name + rename note; core "No instrument matched" repro no longer reproduces. Pre-existing documented autocomplete-partial-prefix residual (register's own note) unchanged, not new. | holds |

COVERAGE: 5/5 ids raw; no raw: none.
