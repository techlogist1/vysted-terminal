# rc1-battery-15 log

Role: REGRESSION BATTERY shard 15 (Sonnet), stage-c batch-5 + batch-10 + batch-27 + batch-30.
Candidate sha 949c3c9fd49d61ecadc9813a8321bcdfd81178bd verified.
Sidecar: booted from candidate source on :52355, data dir rc1-round-5-recheck-data-battery-15, sleep pid 85469 (worker 85472).

## set-19 (batch-5/W4-platform-workflow-boundary) — complete
8/8 holds: R15-CODE-PLATFORM-004, R15-CODE-PLATFORM-019, R15-CODE-PLATFORM-005, R15-CODE-AGENT-012, R15-AGENT-059, R15-CODE-PLATFORM-020, R15-LEAD-001, R15-LEAD-003.
Raw: battery/raw/set-19/*.txt. See battery/set-19.md.

## set-48 (batch-10/unassigned) — complete
Holds: R15-CODE-PLATFORM-024, R15-CODE-PLATFORM-030, R15-DATA-078, R15-DOCS-005.
ci_pinned: R15-CODE-PLATFORM-014 (vitest-only certification, plugin-runtime.test.ts).

## set-74 (batch-27/W1-sonnet) — complete
Holds: R15-DATA-117 (live TSM/HDB/AAPL/IBN), R15-LEAD-040 (source + live storm, warm-cache caveat noted).

## set-86 (batch-30/WriterB-r15-lead-051) — complete
Holds: R15-LEAD-051 (in-process cadence() literal+fresh+held-back+control, plus live JONJUA).

## Summary
16/16 entries: 14 holds, 1 ci_pinned (R15-CODE-PLATFORM-014, vitest-only certification), 0 regressed, 0 needs_gui, 0 blocked_env.
No regressions found. findings/rc1-battery-15.json = [].

COVERAGE: 16/16 ids raw across all 4 sets; no raw: none.
