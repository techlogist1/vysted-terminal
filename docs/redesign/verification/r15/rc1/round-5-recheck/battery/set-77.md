# set-77 (rc1-battery-7) — batch-28/W3-sonnet

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. All 3 entries live-tested against
this shard's own sidecar (`:52347`), reusing the register's own repro plus one
fresh case per id not in the original certification's examples.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-003 | `GET /disclosures/shareholding?symbol=AMAL` + `/announcements` under `X-Vysted-Region: US` | both `coverage:"not_applicable"` with an honest note, no Amal Ltd (BSE) data leak. Fresh case HAL/HAL.NS: HAL not_applicable, HAL.NS served (20 quarters) | holds |
| R15-DATA-024 | `grep -rniE 'bulk.?deal\|block.?deal\|\bsast\b' sidecar/ src/ types/` + `GET /disclosures/deals?symbol=KOPRAN` | grep now finds the route/tests/types (was zero); live KOPRAN returns 125 real bulk-deal rows. Fresh case SAKSOFT: 116 rows | holds |
| R15-DATA-038 | `GET /sec/filings/0000320193-25-000079/sections?identifier=AAPL` + `GET /sec/insider/AAPL?limit=50` | sections populated (word_count 1432/1430, was `[]`); insider returns 50 populated rows (was `[]`). Fresh case MSFT (insider + a different 8-K accession): both populated | holds |

Raw output for every id: `battery/raw/set-77/<id>.txt`.

COVERAGE: 16/16 ids raw; no raw: none.
