# batch-30/WriterB-r15-lead-051 (set-86)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, own sidecar :52355.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-051 | in-process: `FiledPeriods.cadence()` on (1) the entry's literal repro (IPO with only Jan-Mar 26 + Apr-Jun 26 filed), (2) a fresh single-quarter-only case, (3) held-back former-SME-migrant case, (4) pure half-yearly control; plus live `GET /fundamentals/JONJUA` (the real-world instance named in the certification) | (1) `quarterly-gap` (not half-yearly); (2) `quarterly-gap` (not half-yearly); (3) `quarterly` (trailing chain complete); (4) `half-yearly` unchanged (control); live JONJUA: `revenue_ttm`/`net_income_ttm` reason "the exchange filings leave a quarter of the trailing year unfiled or unparsed; kept, flagged" (quarterly-gap reading, matches batch-30's certified live case, not batch-29's pre-fix "a half-yearly filer") | holds |

COVERAGE: 1/1 ids raw; no raw: none.

---
FINAL SHARD COVERAGE: 16/16 ids raw across set-19 (8), set-48 (5), set-74 (2), set-86 (1); no raw: none.
