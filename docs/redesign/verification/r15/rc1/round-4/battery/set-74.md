# batch-25/W5-research-043-research-015 (rc1-battery-14, set-74)

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52354.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-015 | (1) In-process probe calling the real `services.research.verify._claim_evidence` with the register's Case C (searxng www.nseindia.com + native nsearchives.nseindia.com), Case D (searxng-only, two subdomains of one example.com domain), and Control B (two genuinely distinct domains). (2) `pytest sidecar/tests/test_research_verify.py` (26 tests incl. the pinned `test_one_domain_reached_by_both_lanes_is_not_independent` and `test_two_hosts_of_one_registrable_domain_are_not_independent`). | Case C: domains={nseindia.com}, independence=1, distinct_lanes=False → below the ULTRA min_domains=2 floor, would go straight to UNVERIFIED with 0 verdict calls. Case D: domains={example.com}, independence=1 → same. Control B: domains={bloomberg.com,reuters.com}, independence=2 → proceeds to a verdict call (not pre-emptively unverified). All match the register's certified behaviour. Pytest: 26 passed. | holds |

COVERAGE: 1/1 ids raw in this set.
