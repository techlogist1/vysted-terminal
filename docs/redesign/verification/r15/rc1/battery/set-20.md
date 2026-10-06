# batch-6/W1-india-exchange-data

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-017 | Live `GET /disclosures/{shareholding,announcements,results}?symbol=X` against candidate `4c6dfe8c` on `:52344` (own isolated data dir `rc1-data-rc1-battery-4`), for SUMAX, QUALIANCE (NSE-SME/Emerge symbols named in the original repro and its batch-6 certification) and JNPR (the original repro's primary NSE-mainboard symbol) | All 9 calls (3 symbols x 3 endpoints) return HTTP 200 with real data — SUMAX/QUALIANCE shareholding patterns (promoter/public percent, XBRL source URLs), live announcements (Sept 2026 press releases / resignations), and results calendars (JNPR: FY26 Q1 results event, NSE+BSE). No `502 "... is not a known NSE/BSE instrument"` anywhere. Matches the batch-6 (5e14731) closure: `nse_provider.py` routes SME/Emerge symbols to `index=sme` instead of the hard-coded `index=equities`. | holds |

COVERAGE: 1/1 ids raw; no raw: none.
