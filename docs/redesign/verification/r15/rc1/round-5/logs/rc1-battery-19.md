# rc1-battery-19 — regression battery shard 19

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, worktree
`.../scratchpad/rc1-round-5-cand` (verified HEAD before starting). Data dir
`rc1-round-5-data-rc1-battery-19` (cp of the round-5 keyless seed). One sidecar booted from
candidate source for the whole shard on :52359 (worker pid 64862, paired sleep pid 64861),
health confirmed ok, stopped at the end of the run.

Sets (batch-3/W2-agent-frontend-gate = set-6, batch-10/W6-chart-notes-blueprint = set-44,
batch-12/W3-as-of = set-57, batch-30/WB-R15-LEAD-051 = set-85), 16 ids total, all re-run
against the fresh candidate boot — none judged from the diff alone.

- Live-sidecar-checkable ids (R15-AGENT-014 custom-agents round-trip, R15-LEAD-026
  unknown-symbol reason, R15-DATA-068 as_of on 4 fundamentals/earnings endpoints,
  R15-LEAD-051 exchange_financials.cadence() via an in-process python call against the
  candidate's sidecar venv) were re-run live and hold.
- Doc/count-based ids (R15-DOCS-004, R15-DOCS-005, R15-DATA-078, R15-CODE-PLATFORM-024)
  were re-checked by reading the current doc text and counting/grepping the current
  source — all hold, matching their batch's closure evidence.
- Pure-frontend logic ids with a committed, unmodified pinned test exactly matching the
  register repro (R15-AGENT-080, R15-CODE-FRONTEND-003/008/014, R15-UI-002, R15-UI-024,
  R15-UI-048) were verified by reading the test (present, unmodified, asserts the exact
  behaviour) — per the shard's own rule, never executed (vitest suites are the heavy
  lane's) — verdict ci_pinned.
- R15-UI-001 (4 sub-repros): sub-repros 1+3 have a pinned test each; sub-repros 2+4 have
  no committed test citing this entry, so they were verified by reading the current
  shownRef/pendingRef/flush sync architecture in NotesPanel.tsx directly (which replaced
  the buggy prevScopeRef/debouncedMd design the entry was filed against) — holds overall.

No regressions found across the 16 ids. No new defects noticed outside the assigned ids.
No blocked_env, no needs_gui in this shard.

COVERAGE: 16/16 ids raw; no raw: none.
