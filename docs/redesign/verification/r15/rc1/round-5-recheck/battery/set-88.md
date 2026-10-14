# unplanned-2 (shard rc1-battery-17)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52357, keyless seed data.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-059 | Own repro (per LEAD NOTE): `curl -H 'X-Vysted-Region: IN' :52357/disclosures/announcements?symbol=FOCUS`. | `count:44`, all 44 rows `"exchange":"NSE"` (0 rows containing `543312` or a BSE exchange tag), `"sources":["NSE"]`, `"note":"BSE FOCUS is a different company; only the NSE feed is served"`. Exactly matches the stated own repro (fixed in the round-5 bounded fix round, fix 52fd29e9, int 769b1f31, fresh-verifier certified, merged 794bc68f) — no scrip-543312 rows, no mixed-exchange bleed. | holds |

Raw: `battery/raw/set-88/R15-LEAD-059.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
