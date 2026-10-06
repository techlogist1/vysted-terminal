# rc1-battery-10 — gate round 5

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, worktree verified via `git rev-parse HEAD`.
Own sidecar booted from candidate source on :52350, data dir `rc1-round-5-data-battery-10`
(copy of the ISO seed), reused across all three sets. Sleep pid 50082, worker pid 50085.

Sets covered: batch-7/W5-agent-writes-portfolio (set-28, 9 ids), batch-9/W2-research-search-news
(set-35, 4 ids), batch-12/W2-screener (set-56, 3 ids). 16/16 ids total.

## Method

- Live-testable entries (sidecar-reachable): R15-AGENT-044 (`/resolve`), R15-DATA-094
  (`/news`, `/news/sources/status`, sidecar.log grep), R15-LIFECYCLE-018 (source + boot log),
  R15-DATA-043, R15-DATA-112 (`/screener/run`), R15-DOCS-018 (doc vs source diff) — all
  re-run live against the candidate and matched their batch certification exactly. No
  regressions.
- Frontend-only entries with no sidecar API surface (R15-AGENT-032, R15-AGENT-041,
  R15-AGENT-043, R15-UI-017, R15-UI-033, R15-UI-034, R15-UI-035, R15-UI-036, R15-UI-037):
  per the harness rule ("never run vitest or pytest suites... an entry certified only
  through a pinned test → verdict ci_pinned naming the test"), did not execute vitest.
  Confirmed the pinned test still exists with the exact certified assertion string, and
  spot-checked the certified source mechanism (line numbers/behaviour) is unchanged.
- R15-CROSS-PLATFORM-002: the actual defect is a Windows-only cp1252 decode crash that
  cannot reproduce on macOS's UTF-8 locale. Ran the small pinned scanner test file
  (`sidecar/tests/test_tests_encoding.py`, 3 tests, 0.45s) in-process as the closest live
  check available; all pass. Recorded ci_pinned since the platform-specific crash itself
  is unreachable here.

## Result

0 regressions, 0 new defects, 0 chain failures, 0 gate8, 0 environment. 6 holds (live),
9 ci_pinned (frontend/platform-only, pinned tests confirmed intact), 1 ci_pinned
(CROSS-PLATFORM-002, platform-specific).

Stopped own sidecar (kill 50082) at end of shard.

COVERAGE: 16/16 ids raw; no raw: none.
