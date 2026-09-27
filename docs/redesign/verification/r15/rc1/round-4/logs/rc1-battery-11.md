# rc1-battery-11 — regression battery shard 11 (round-4)

Sets: batch-7/W5-agent-writes-portfolio (set-29, 9 ids), batch-10/W7-panels-marketplace (set-46, 5 ids),
batch-27/W1-sonnet (set-78, 2 ids). Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad.

Sidecar: booted from `<cand>/sidecar` on :52351, data dir `rc1-round-4-data-battery-11` (copied from
rc1-round-4-seed-data). Sleep-launcher pid 84303 (stopped at end of run). /health ok at boot.

Result: all 16 entries hold. 7 verified live/static (holds): R15-AGENT-044, R15-UI-032, R15-UI-028,
R15-CODE-PLATFORM-072, R15-DATA-077, R15-DATA-117, R15-LEAD-040. 9 are pure frontend-TS logic where
the original certification rode a vitest-executed path; this role does not run vitest suites, so those
are ci_pinned naming the committed, register-id-tagged test (host-actions.test.ts / ChatSidebar.test.tsx /
PortfolioPanel.test.tsx), backed by a static read of the exact cited fix code at the candidate sha.

No regressions. No new defects found outside the entries' own scope.

COVERAGE: 16/16 ids raw; no raw: none.
