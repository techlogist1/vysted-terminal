# batch-2/W2-instrument-identity (set-1), shard rc1-battery-7, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-012 | in-process resolve() with injected NSDL->GUJENERGY (+SHREE->AJMERA) rows | NSDL -> BSE NSDL (NSDL.BO), rename None; SHREE -> Shree Marutinandan Tubes BSE, rename None; genuine ZOMATO->ETERNAL still renamed | holds |
| R15-CODE-DATA-001 | GET /resolve?q=FOCUS; /disclosures/shareholding?symbol=FOCUS | NSE Focus Lighting isin/bse_code null (BSE candidate carries INE0DXR01010/543312); shareholding split_source None for all patterns (first own-sidecar attempts 502 from NSE connection resets, then 200; shared :52152 identical) | holds |
| R15-DATA-018 | GET /resolve zomato/ZOMATO/autocomplete/SEQUENT/VIYASH | zomato,ZOMATO -> ETERNAL with rename note; autocomplete lists ETERNAL; SEQUENT -> VIYASH; VIYASH former_name SEQUENT | holds |
| R15-DATA-001 | GET /fundamentals/{DAL,CHTR,SMR,SUMAX}/income, DAL/balance, RELIANCE.NS (region IN) | DAL.BO, CHTR.BO, SMR.BO March FY INR scale (DAL rev 2.07cr, not Delta); SUMAX -> SUMAX-SM.NS empty (no US fund data); RELIANCE.NS unchanged | holds |
| R15-DATA-003 | GET /disclosures/shareholding + announcements ?symbol=AMAL, region US | coverage not_applicable "AMAL is not an NSE/BSE instrument"; AMAL.BO/IN control carries 71.35 | holds |
| R15-CODE-DATA-005 | grep predicates (design) | market_cap_witness/ownership_check/range_check bind is_applicable = witness.is_india_listing; one is_block_error (witness.py); one is_india_target (relevance.py, imported by disclosures.py) | holds |

COVERAGE: 6/6 ids raw; no raw: none
