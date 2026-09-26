# rc1-vshard-0 — adversarial sample verifier shard 0 (gate round 2)

- 2026-09-26 09:30 IST start. Candidate 81fbfe910d472ecd154fa62e42d86bce213a697e (worktree rc1-4c6dfe8-fix-int, `git rev-parse HEAD` confirmed).
- Round-1 log of this role moved (unread) to logs/round-1/rc1-vshard-0.md; round-1 data dir moved to rc1-data-rc1-vshard-0.round1.
- Fresh data dir: scratchpad/rc1-data-rc1-vshard-0 (cp -R of rc1-seed-data).
- Own sidecar: port 52600, source run from the candidate worktree, sleep pid 89329, worker 89330. /health ok.
- 09:4x DECISION: scripts/r15/vy.py refuses non-GET calls outside ports 52100-52399, so it cannot drive :52600. The shared :52152 stack runs checkout 4c6dfe8c (rc1-cand), NOT the candidate 81fbfe91 (diff touches research/citecheck.py + iter.py), so agent runs there are not at the candidate. Booted a SECOND own sidecar from the candidate worktree on :52396 (free, in vy.py's range) with its own fresh seed copy rc1-data-rc1-vshard-0-vy; sleep pid 99392, worker 99393. :52600 stays the curl/in-process target.
- An accidental vy.py R003 launch against :52152 was killed within seconds (stale sha); ledger may carry one partial row tagged rc1-vshard-0-R003-literal.
- 09:4x second sidecar for vy.py: port 52396 from the same candidate worktree, data dir rc1-data-rc1-vshard-0-vy, sleep pid 99392 (worker 99393).
- 09:4x-09:55 entries run in order DATA-006 → CODE-AGENT-003 (verdicts in verifier/shard-0.md). vy.py spend this shard: two gpt-4o-mini deep runs (BLUESTARCO $0.00468, VOLTAS $0.00593, vy estimates). No Ollama call was made (no lock taken): AGENT-008's acceptance is "by estimate", checked in-process.
- DECISION: an entry whose literal repro holds but whose title/fix_shape fails on a fresh case is reported verdict=refuted with evidence prefixed "NOT CERTIFIED:" (schema has no not_certified value).
- DECISION: frontend fresh cases ran in a scratch copy (scratchpad/vshard0/fe2: cp of src/types/styles/plugins/configs, node_modules symlinked read-only, vite cacheDir redirected to fe2/.vitecache) so the candidate worktree was never written.
- DECISION: AGENT-048 — a mock that RAISES from oneshot.complete_with_usage bypasses the repair cap (5 calls), but the real oneshot swallows every exception and timeout and returns ("", None), which IS counted; the realistic hanging-provider probe capped at 2. Not a refutation.
- 10:0x evidence copied to verifier/shard-0-evidence/; findings/rc1-vshard-0.json written; sidecars stopped (kill 89329 99392).
