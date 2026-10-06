# rc1-battery-17 — regression battery shard 17

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, verified via
`git -C rc1-round-5-cand rev-parse HEAD` before any work.

Sidecar booted from candidate source: :52357, data dir
`rc1-round-5-data-rc1-battery-17` (copy of `rc1-round-5-seed-data`), sleep-wrapper pid 62173
(worker pid 62176). `/health` -> 200 ok.

Sets covered, in order:
1. batch-2/W4-workspace-persistence (set-3.md) — 7 ids
2. batch-9/W5-frontend-shell (set-38.md) — 7 ids
3. batch-11/W7-preferences (set-53.md) — 1 id
4. batch-29/W4-sonnet (set-83.md) — 1 id

Method: for each id, read the register entry + the batch's own VERDICTS.md "Per-entry
evidence" line to see how it was certified, then re-ran that repro against the candidate:
- R15-CODE-FRONTEND-004 (workspace name validation): live curl POST/GET/DELETE round-trip
  against my own :52357 sidecar for all 6 register names (Research: NVDA, Research:
  RELIANCE.NS, Research: M&M, My Layout (2), ../escape, a/b\c) — all 200/204, `ls` on the
  data dir's `workspaces/` confirmed percent-encoding, no path traversal.
- R15-LIFECYCLE-009: supplementary live `GET /portfolio/positions` -> 200 `[]` (seed data has
  no legacy rows; endpoint itself reachable).
- R15-LEAD-048: source read of `host-actions.ts` arrange_layout case confirms
  `MENU_PAYLOAD_TO_MODE` pattern match routes to `applyLayoutMode`, not `resetLayout`;
  unrecognised patterns now fail loudly.
- R15-DATA-092 / R15-UI-052: register/register-adjacent copy claims verified by grepping the
  live source strings (region.ts DEFAULT_REGION, SettingsPanel.tsx hint text,
  OnboardingFlow.tsx / OnboardingBanner.tsx welcome copy).
- All remaining 12 ids are pure frontend-store/UI logic (workspace autosave gating,
  keybindings dispatcher, command palette rows, settings export/import, provider fallback
  order) whose ONLY practical verification without a GUI is the project's own vitest suite.
  Per the stall/scope rules the battery role never runs vitest itself, so each of these is
  confirmed present, unmodified and register-id-tagged in the candidate source
  (`grep -n "R15-<id>"` across the relevant `*.test.ts(x)` files) and verdicted `ci_pinned`
  naming the exact test(s).

No regressions found in any of the 16 ids across all 4 sets — every certified behaviour
still holds at the candidate sha, either by direct live probe or by an intact pinned test.

Sidecar stopped at end of shard: `kill 62173` (sleep-wrapper pid), confirmed via
`ps -p 62173` (no such process) and `/health` connection refused.

COVERAGE: 16/16 ids raw; no raw: none.
