# rc1-battery-0 — regression battery shard 0

Candidate sha 01d6920a300b016ab1ad8aa436ee4e4586f8e336. Own sidecar booted from
`rc1-round-3-cand/sidecar` on :52340, data dir `rc1-round-3-data-rc1-battery-0` (copy of
`rc1-round-3-seed-data`); shared openbb-mcp :52153 / sec-edgar-mcp :52154 read-only. Sleep pid
75906 (worker 75910); stopped cleanly at end of shard.

Shard assignment: no explicit shard→set mapping file exists in `battery/INDEX.json`/`INDEX.md`
(75 sets, no `shard` field). Took the first contiguous block of 3 sets by list order (index
0-2 of 75) as shard 0: `batch-2/W1-fundamentals-seam`, `batch-2/W2-instrument-identity`,
`batch-2/W3-research-integrity`, plus `batch-2/W4-workspace-persistence` (index 3) once the
first three cleared quickly — 4 sets / 27 entries total for this shard (12 + 8 + 7).

Method: `curl` against my own sidecar for HTTP-surfaced entries; direct in-process
`sidecar/.venv/bin/python3` calls against the candidate's actual functions (`correctness_gate`,
`symbol_resolver`, `services.research.verify/deep/citecheck/relevance`) for parsing/gating
logic — several of these (RESEARCH-001/015/029) built a literal repro using the exact ids/urls
named in the register rather than relying on a pinned test, since the role brief explicitly
allows "curl, vy.py, or an in-process python call" and forbids running the vitest/pytest
suites (the heavy lane owns those). Frontend-only entries (CODE-FRONTEND-*, LIFECYCLE-*) were
verified by reading `src/lib/workspace.ts` against the register's own evidence line numbers,
plus one live sidecar curl for the LIFECYCLE-009 legacy-import endpoint and the
CODE-FRONTEND-004 workspace-name validation.

All 27 entries in the 4 sets covered: **holds**. No regressions, no new defects, nothing
needing GUI or blocked on an upstream outage in this shard.

COVERAGE: 27/27 ids raw; no raw: none.
