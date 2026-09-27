# set-20 — batch-6/W1-india-exchange-data (rc1-battery-12)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, sidecar :52352 (source, live NSE calls, no mocks).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-017 | curl /disclosures/shareholding?symbol={JNPR,DHOOTTRANS,SUMAX}; curl /quotes/SUMAX | all 200 with real data (JNPR promoter 85.94%, DHOOTTRANS promoter 82.78%, SUMAX promoter 69.67%); SUMAX quote 200 price=109.15 provider=nse_direct — no "not a known NSE/BSE instrument" 502 anywhere | holds |

COVERAGE: 1/1 ids raw; no raw: none.
