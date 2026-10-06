# batch-25/W5-opus (set-71)

Re-proved live against candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-015 | In-process `services.research.verify._claim_evidence`, re-pointed at the candidate source (batch-25's own `r015.py` script was never committed, so reconstructed from the register's stated cases against the fixed function at `verify.py:317-345`). Case C: one domain (nseindia.com) reached by BOTH searxng + native. Case D: SearXNG-only, `www.sebi.gov.in` + `sebi.gov.in`. Control B: `m.economictimes.com` + `economictimes.indiatimes.com`. Plus the uncited-native-text case (+1 path). | Case C: `domains={nseindia.com}`, `independence=1` → verdict loop's own `independence < min_domains(2)` gate fires → 0 LLM verdict calls, UNVERIFIED (not the pre-fix double-counted `independence=2` AGREE). Case D: `domains={sebi.gov.in}`, `independence=1` → UNVERIFIED. Control B: `domains={economictimes.com, indiatimes.com}` (2 distinct registrable domains), `independence=2` → verdict runs (agree path reachable). Uncited-native case: `domains={rbi.org.in}` + native_text with no native_rows → `independence=2` (the `+1` still fires correctly when the native channel is genuinely a separate, uncited retrieval path). | holds |

COVERAGE: 1/1 ids raw; no raw: none.
