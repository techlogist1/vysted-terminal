# Set 70 — batch-25/W5-opus (regression battery shard 14)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-015 | in-process `services.research.verify._row_domains` (feeding `services.research.finance.registrable_domain`, the vendored-PSL-backed algorithm) over the register's own case C/D URL pairs and controls, plus `services.research.deep.distinct_web_domains` over the fresh RBI/BSE pair | `www.nseindia.com` + `nsearchives.nseindia.com` → `{nseindia.com}` (n=1, same registrable domain — feeds `cross_check`'s `independence < min_domains(2)` gate, which short-circuits to `UNVERIFIED` with 0 LLM verdict calls per the code path at `verify.py`'s `cross_check`). Two-subdomain SearXNG-only case → n=1, same gate. Control B (reuters.com + moneycontrol.com) → n=2, clears the gate (`agree`/`corroborated` reachable). Fresh `www.sebi.gov.in` + `sebi.gov.in` → `{sebi.gov.in}` n=1, unverified (the `.gov.in` suffix is not itself the registrable root). Fresh `m.economictimes.com` + `economictimes.indiatimes.com` → 2 distinct registrable domains (`economictimes.com`, `indiatimes.com`) — agree reachable. `deep.distinct_web_domains` over `www/rbidocs.rbi.org.in` + `www/api.bseindia.com` → `{rbi.org.in, bseindia.com}`, exact match to the cert. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
