# Set: batch-3/W5-india-data-witnesses (set-9) — rc1-battery-17, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd, sidecar :52357

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-005 | GET /fundamentals/VERTEX, JUMBO, JNPR | VERTEX book_value 1.369 + price_to_book field_meta status flagged ("shares 74,012,189 disagrees by 50% with 148,024,378 implied by mcap/price"); JUMBO 54.361 flagged vs 57.01; JNPR 70.02 flagged vs 60.17 | holds |
| R15-LEAD-002 | 3 rounds GET /fundamentals/{TCS,INFY,ITC,HDFCBANK,SBIN} X-Vysted-Region: IN | round 1 (cold process) 14.6-15.7 s each; round 2 0.38-1.95 s; round 3 0.41-0.56 s; ownership witness cached after first call (no 4-8.5 s steady state) | holds (cold first-call 15 s noted, see notes) |
| R15-RESEARCH-011 | in-process nearest-quarter merge (NSE 2026-06-30, BSE split 2026-03-31) -> ownership_check._fetch_latest -> semantics._ownership_leg | institutions basis 'BSE shareholding filing, 2026-03-31'; promoter basis 'NSE shareholding filing, 2026-06-30' | holds |
| R15-RESEARCH-013 | fast._filings_leg with real corporate_announcements tool, + simulated BSE-down | JUMBO provider 'bse'; RELIANCE/AMAL 'nse+bse' (AMAL now NSE-listed, sources NSE+BSE); BSE-down simulation -> 'nse' | holds |
| R15-DATA-019 | GET /disclosures/announcements?symbol={JUMBO,TTC,AMAL}&limit=25 | counts 19 / 17 / 21 (was 0/2/1); each states windows (BSE 2026-04-06..2026-10-03) + coverage 'covered' | holds |
| R15-DATA-021 | GET /disclosures/shareholding?symbol=SIL | 20 patterns; every split_as_of == own quarter_end, none copied from a distant quarter (2021-09..2024-06 carry BSE split of their own quarter) | holds |
| R15-DATA-022 | GET /disclosures/shareholding?symbol=SMR | count 1, quarter_end 2026-06-04 (IPO-dated pattern kept; was count 0) | holds |
| R15-AGENT-010 | in-process agent resolve_symbol tool on 5 queries with 5 ms ticker coroutine | max event-loop stall 57 ms (was 300-900 ms/30 s), includes cold master load | holds |

COVERAGE: 8/8 ids raw; no raw: none
