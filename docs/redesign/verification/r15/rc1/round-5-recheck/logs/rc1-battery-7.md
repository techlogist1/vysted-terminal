# RC1 round-5-recheck — REGRESSION BATTERY shard 7 (rc1-battery-7)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Sets: batch-6/W5-host-actions-portfolio
(set-24, 9 ids), batch-9/W1-agent-runtime (set-35, 4 ids), batch-28/W3-sonnet
(set-77, 3 ids). 16 ids total.

## Sidecar

- Seed data copied: `rc1-round-5-recheck-seed-data` -> `rc1-round-5-recheck-data-rc1-battery-7`.
- Booted from `rc1-round-5-recheck-cand/sidecar` on `127.0.0.1:52347` per
  `ISO_STACK.md`'s "Main sidecar, from source" recipe.
- **Port-squat found and resolved**: port 52347 (this shard's assigned port) was
  already bound by a stale orphaned process (PID 47234, cwd
  `.../rc1-round-5-cand/sidecar` — an earlier gate round, not round-5-recheck —
  started 14:48:44, PPID 1, no live sleep-pipe parent). Verified via `lsof -p`
  (cwd) and `ps` (start time/PPID) before touching it, per the same pattern the
  preflight role already used on the shared-stack ports. Killed it (SIGTERM,
  clean exit), rebooted this shard's own sidecar (sleep pid **69255**), confirmed
  `/health` ok on the correct candidate + data dir. One probe (CODE-AGENT-005) that
  ran against the stray process before this was caught was re-run against the
  confirmed-correct sidecar and produced the identical result — no evidence was
  kept from the stray process.
- Stopped at the end of this shard's work: `kill -TERM 69255`.

## Sets

- **set-24** (batch-6/W5, 9 ids) — all frontend-only (`src/lib/host-actions.ts`,
  `src/store/portfolios.ts`). No sidecar route, no GUI. Per the shard's rule
  ("never run vitest suites; an entry certified only through a pinned test ->
  ci_pinned"), every id was checked via a grep + read of its own COMMITTED,
  named pinned test on the candidate (the register id appears literally in each
  test's `it(...)`/`describe(...)` title) — never the diff, never executing
  vitest. R15-CODE-PLATFORM-022 was the exception: its own register repro IS a
  grep (import-site audit), so that grep was re-run live and holds (the dead
  client is now fully absent from `src/`, not just import-orphaned).
- **set-35** (batch-9/W1, 4 ids) — all live: two Ollama agent runs through
  `vy.py` under the shared local-model lock (AGENT-046, CODE-AGENT-008), one
  direct `curl POST /llm/chat` (CODE-AGENT-005), one direct-sqlite legacy-row
  insert + GET/PUT + in-process `schemas.openai_tools` call (LIFECYCLE-025).
  CODE-AGENT-008's first run completed cleanly (116.0s) but vy.py's default
  `--max-event 400` truncated the `publish_brief` payload in the printed log; a
  second run with `--max-event 4000 --out <file>` was attempted for the
  untruncated payload but stalled behind another shard's concurrent Ollama call
  holding the shared lane — killed it (releasing the lock for other shards) once
  the first run's already-solid evidence (tool_result ok:true, research steps,
  auto-publish tool_use with the structured payload shape) was judged sufficient
  rather than spend more of the shared lane's time for marginal extra detail.
- **set-77** (batch-28/W3, 3 ids) — all live `curl` against the sidecar's REST
  routes (disclosures, deals, SEC filings/insider), each with one fresh case
  beyond the certification's own examples.

## Result

16/16 holds. Zero regressed, zero ci_pinned-as-a-fallback-because-untestable
(the 8 pinned-test verdicts in set-24 are a deliberate, rule-directed choice,
not a gap), zero needs_gui, zero blocked_env. No findings.

COVERAGE: 16/16 ids raw across all 3 sets (see each set's own trailer line).
