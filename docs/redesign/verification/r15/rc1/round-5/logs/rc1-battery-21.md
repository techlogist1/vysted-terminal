# rc1-battery-21 — regression battery shard 21

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98 (confirmed via
`git -C rc1-round-5-cand rev-parse HEAD`).

Data dir: `rc1-round-5-data-rc1-battery-21` (cp -R from `rc1-round-5-seed-data`).
Sidecar booted from candidate source, one instance for the whole shard, port
`:52361`, sleep pid `64753` (stopped at end of run). Health confirmed ok
(`providers.openbb-mcp: "available"`) before any repro.

Sets covered (see `battery/set-{9,24,72,87}.md` for the full per-id table):
- set-9 — batch-3/W5-india-data-witnesses: DATA-005, DATA-019, DATA-021,
  DATA-022, LEAD-002, RESEARCH-011, RESEARCH-013 — all 7 hold.
- set-24 — batch-7/W1-india-exchange-data: DATA-014, DATA-027, DATA-050,
  DATA-060, DATA-076, LEAD-015 — all 6 hold.
- set-72 — batch-26/W2-sonnet: AGENT-010, LEAD-039 — both hold.
- set-87 — unplanned-2: CODE-DATA-023 — holds.

No regressions found in this shard. No vitest/pytest suites were executed
(per role rules); two entries (RESEARCH-011, RESEARCH-013) and AGENT-010 cite
their pinned tests by name alongside a direct source-mechanism read, since
their register evidence is a code-path fix rather than a live-probeable
symptom on a normal request; RESEARCH-011/013/AGENT-010 were also cross-checked
against a matching live call or the exact fix-shape code present in the
candidate tree.

Notable re-confirmations against the register's exact cited numbers: SIFY
major_shareholders sum to 83.78% (sec-20f lane); FUSION revenue_ttm 1,714.42 Cr
NSE vs Yahoo 858.2 Cr withheld; DAL revenue_growth 45.2% (BSE) matches
screener's 7.26/5.00-1; DHANBANK quarterly gaps: ["2025-09-30"]; LEAD-002
ownership-witness TTL cache turned a 15.74s cold /fundamentals/TCS call into
1.1s on repeat.

COVERAGE: 16/16 ids raw; no raw: none.
