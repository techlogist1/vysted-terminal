# rc1-battery-20 — regression battery shard 20 (round 5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Worktree
`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand`
confirmed at that sha before starting.

No prior round-5-recheck battery files for shard 20 (`set-9.md`, `set-32.md`, `set-10.md`,
`set-57.md` all absent at start) — fresh run, nothing to resume.

Sets assigned had stale "file" labels from an earlier round's numbering (the task's `file`
field names did not match round-5's actual set files for these ids — sets get renumbered each
round). Located each id's true round-5 certification by grepping `round-5/battery/*.md` for
the id, confirmed:
- batch-3/W5-india-data-witnesses → round-5 `battery/set-9.md` (file name did match)
- batch-8/W3-data-error-honesty → round-5 `battery/set-31.md` (not set-32)
- batch-3/unassigned (R15-RESEARCH-010) → round-5 `battery/set-8.md` (not set-10)
- batch-12/W1-resolver-and-venue-identity (R15-DATA-115) → round-5 `battery/set-55.md` (not set-57)

Own sidecar booted once for the whole shard, from candidate source
(`sidecar/main.py --port 52360 --data-dir rc1-round-5-recheck-data-rc1-battery-20`, data dir
copied from the round-5-recheck seed), reused across all four sets, `/health` confirmed ok
before any probe. Sleep-launcher pid 94226, stopped at end of shard.

All 15 ids re-run against their exact original repro (live curl, in-process python calls
against the candidate's own venv, or source-read of the pinned test for ci_pinned entries).
15/15 hold — no regressions, no new defects, no chain or gate8 issues found in this shard's
scope.

COVERAGE: 15/15 ids raw (7 set-9, 6 set-32, 1 set-10, 1 set-57); no raw: none.
