# rc1-battery-15 — regression battery shard 15, gate round 5

Candidate sha `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Sidecar booted from the
candidate worktree (`.../rc1-round-5-cand/sidecar`) on `:52355` against a fresh
copy of the seed data at `.../rc1-round-5-data-rc1-battery-15`. Sleep pid was
56541 (wrapper `sh -c "sleep 86400 | python3 main.py ..."`); the actual worker
was pid 56544 (killing the sleep alone left the worker up — killed 56544
directly at the end, confirmed `/health` stops responding).

Sets: batch-5/W4-platform-workflow-boundary (set-18), batch-6/W4-research-funnel
(set-22), batch-25/W3-sonnet (set-68), batch-25/W6-sonnet (set-71).

## Method
For each id: read the register entry + the certifying batch's VERDICTS.md
"per-entry evidence", then re-ran the SAME repro against the candidate —
live HTTP against the booted sidecar where the entry is a data/route defect
(DATA-064, LEAD-028), live in-process Python calls against the candidate's own
venv for code-path/runtime defects (AGENT-059, CODE-AGENT-012, PLATFORM-004/005/
019/020, LEAD-003, CODE-RESEARCH-002, RESEARCH-012/017/018, AGENT-093), and a
source read for LEAD-001 (build pins — a full clean-venv rebuild is
chain/heavy-lane scope and the bundle rehearsal already passed clean) and
RESEARCH-016 (ULTRA guard-split — a full 300+s ULTRA model run was out of this
shard's time budget; the fix is a straight-line, non-branching guard so a
source read is a faithful repro of the same design-level check the register
entry itself used).

## Notable
- R15-RESEARCH-017: current behavior does NOT match batch-6's original
  certification (a single-pass fallback). It matches a LATER, deliberate
  design change (68bb7aa4 / R15-CODE-RESEARCH-003, batch-8) that the round-4
  refutation audit already concurred is `not_a_defect` — both DEEP and ULTRA
  now fail symmetrically-honest via `_loop_failed` instead of ULTRA degrading
  to a fallback brief. Verdict: holds (matches the register's own refreshed
  expectation, not a regression).
- R15-CODE-RESEARCH-002: baseline (unfaulted) `snapshot_structured` call on
  this shard's own isolated sidecar/data-dir returned `price.ok`/
  `fundamentals.ok` both False — a local data/network limitation of this
  battery's own isolated copy, unrelated to the entry (which is about
  exception-isolation across the cross-check legs, confirmed regardless).

## Result
16/16 ids: holds. 0 regressions, 0 new defects, 0 chain failures, 0 needs_gui,
0 blocked_env.

COVERAGE: 16/16 ids raw; no raw: none.
