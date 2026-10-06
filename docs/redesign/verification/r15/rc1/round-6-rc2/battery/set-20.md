# Set: batch-6/W1-india-exchange-data (set-20) — rc1-battery-17, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd, sidecar :52357

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-017 | GET /disclosures/{shareholding,announcements,results}?symbol={JNPR,SUMAX,DHOOTTRANS,QUALIANCE,SHANTIINOR}; extras: /quotes/SUMAX, /fundamentals/JNPR | all 15 calls HTTP 200 coverage covered (were 502): JNPR promoter 85.94, 25 announcements; SUMAX/QUALIANCE/SHANTIINOR (NSE Emerge) served from sources ['NSE'] with 9/6/4 announcements, promoter 69.67/63.66/56.05; DHOOTTRANS 82.78; SUMAX quote 200 price 101.25; JNPR held_percent_institutions 0.0384 now field_meta status "flagged" | holds |

COVERAGE: 1/1 ids raw; no raw: none
