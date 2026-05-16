# BLOCKERS-N.md — Teammate N (Node editor frontend)

Per-teammate self-report for v0.5.0. Lead aggregates into the root
`BLOCKERS.md` at integration.

## Hard blockers

None. All Tier-1/2 deliverables complete.

## Soft items / known carry-forwards

### 1. Canvas-drag screenshots deferred to lead-integration

`chrome-devtools` MCP cannot synthesize `isTrusted` events for
react-flow's drag-drop / connect gestures (per the existing CLAUDE.md
Gotcha that covers lightweight-charts; the same constraint applies to
react-flow). The Teammate-N deliverable acknowledges this and accepts
the documented fallback: extensive unit tests on the data model +
chrome-devtools screenshots of populated graphs captured by the lead
at integration when a real Tauri dev session can be run.

Coverage I shipped to compensate:

- `graph-state.test.ts` — 16 tests on add/remove/update + spec
  round-trip.
- `workflow-run-overlay.test.tsx` — 9 tests on the SSE-event reducer
  + render paths.
- `node-palette.test.tsx` — 4 tests including drag-MIME stamping.
- `node-registry.test.ts` — 9 tests on the 10 built-ins + plugin
  union + id collision policy.
- `NodeEditorPanel.test.tsx` — 6 tests on toolbar + save dialog
  POST + load list + plugin-node palette pickup.

42 tests total; `pnpm typecheck && pnpm lint && pnpm format:check`
clean.

### 2. workflow store ownership

The plan section says "frontend store from Teammate W consumes the
response" for save. Teammate W's `src/store/workflow.ts` is part of
their scope, not mine — I therefore inlined `fetch` calls in
`NodeEditorPanel.tsx` against the sidecar routes (`getSidecarBaseUrl`
+ `fetch(new URL(...))`, the same pattern Teammate C used for the
custom-agent CRUD in v0.4.0). If Teammate W's store ships, the panel
should be migrated to consume it at lead-integration; until then the
inline fetches are the load-bearing path.

### 3. dockview panel CSS overlap with react-flow base CSS

react-flow's stylesheet is imported at the top of `NodeEditorPanel.tsx`
(`@xyflow/react/dist/style.css`). I did NOT touch `globals.css` — the
import is module-scoped. The CLAUDE.md dockview-cascade Gotcha noted
that `.dockview-theme-vysted` must override after the dockview base
import; react-flow's stylesheet has its own namespace (`.react-flow`
selectors) so I don't expect cascade conflicts, but worth a
visual-verification pass when the lead captures the populated
screenshots.

## Tier-1 lock verification

- `git diff origin/main -- types/plugin.ts` is empty.
- `git diff origin/main -- types/` is empty.
- `git diff origin/main -- sidecar/` is empty.

## Branch

`agent-N` — pushed to remote at the close of the worktree window.
