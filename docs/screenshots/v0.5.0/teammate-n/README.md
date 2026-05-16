# Teammate N — Node Editor screenshots (v0.5.0)

## What this folder is for

The five populated screenshots called out in the Teammate N section of
the v0.5.0 mega-sprint plan:

1. Empty canvas with palette visible at 1920×1080.
2. Empty canvas with palette visible at 2560×1440.
3. 5-node research workflow on canvas at 1920×1080
   (`fetch_quote AAPL → fetch_history AAPL → compute.indicator RSI →
   ai.agent_invoke researcher → action.log`).
4. 5-node research workflow on canvas at 2560×1440.
5. Run overlay showing per-node timing post-run at 1920×1080.
6. Run overlay showing per-node timing post-run at 2560×1440.
7. Properties panel populated on a selected node at 1920×1080.
8. Properties panel populated on a selected node at 2560×1440.

## Verification path used at handoff

`chrome-devtools` MCP cannot synthesize `isTrusted` drag-drop events,
so the populated graphs cannot be produced through chrome-devtools
alone (per the `CLAUDE.md` Gotcha and the plan's Teammate-N
deliverable: "chrome-devtools MCP screenshots of POPULATED graphs —
just the render, not the interactions").

The intended capture pattern at integration time:

1. Lead runs `pnpm tauri dev` so a real sidecar is up.
2. Lead opens the Node Editor panel via cmd+K → "Open Node Editor".
3. Lead manually drags from the palette to build the 5-node research
   workflow with edges, saves it via the Save dialog.
4. Lead clicks Run — the run overlay populates per-node timing as the
   sidecar streams `WorkflowRunEvent` SSE frames.
5. Capture via chrome-devtools MCP `take_screenshot` at both
   1920×1080 and 2560×1440 (`resize_page` between captures).
6. Save into this folder as `canvas-empty-{1920,2560}.png`,
   `canvas-5node-{1920,2560}.png`,
   `canvas-run-overlay-{1920,2560}.png`,
   `canvas-properties-{1920,2560}.png`.

## Worktree-session verification fallback

In the worktree session itself, the substitute proof of correctness is
the unit-test suite under `src/modules/node-editor/*.test.{ts,tsx}` —
42 tests covering:

- Graph manipulation (add/remove node, connect/disconnect edges,
  config patch) — `graph-state.test.ts`.
- Save round-trip (`flowToSpec` → `specToFlow` → `flowToSpec` equality)
  — `graph-state.test.ts`.
- Run-overlay reducer (every `WorkflowRunEvent` kind, including
  out-of-order frames) — `workflow-run-overlay.test.tsx`.
- Palette render + drag MIME stamping — `node-palette.test.tsx`.
- Panel toolbar wiring + save dialog POST + load list — 
  `NodeEditorPanel.test.tsx`.
- Registry: 10 built-ins, plugin contributions union, id-collision
  policy — `node-registry.test.ts`.

The unit tests prove the data model and event-stream reducer are
correct; the populated screenshots, when captured at lead-integration,
prove the visual rendering on top of that data is correct.
