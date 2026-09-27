# batch-6/W1-india-exchange-data — rc1-battery-4 (round 5)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52344.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-017 | `GET /disclosures/announcements?symbol=<QUALIANCE|SHANTIINOR|SUMAX>`, `GET /disclosures/shareholding?symbol=<...>` | QUALIANCE: 4 announcements (real headlines, resignation notice), shareholding promoter 63.66% (exact match to certification). SHANTIINOR: 3 announcements (was 2 at certification time — NSE published one more real filing since, Sep 26; not a regression), shareholding promoter 56.05% (exact match). SUMAX: 7 announcements returned live this run (no 502; the certification-time 502 was a noted transport flake at that instant, and the SME-index routing itself resolves correctly here) | holds |

COVERAGE: 1/1 ids raw; no raw: none.
