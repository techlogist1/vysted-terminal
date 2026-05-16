# Teammate N — Node Editor screenshots (v0.5.0)

Populated screenshots for the v0.5.0 Node Editor (Phase 4 visual workflow surface).

## Captured shots

All eight populated screenshots in this folder were captured against
`pnpm dev` (Next.js dev server) with the sidecar's `/workflow/saved` and
`/workflow/run` routes mocked at the `fetch` boundary. The mocked
responses are real wire shapes — `WorkflowSpec` JSON and
`WorkflowRunEvent` SSE frames — exactly matching `types/workflow.ts` and
Teammate W's `models/workflow.py`. The render path through
`NodeEditorPanel.tsx`, `node-palette.tsx`, `VystedNode.tsx`, and
`workflow-run-overlay.tsx` is exercised end-to-end.

- `canvas-empty-1920.png` / `canvas-empty-2560.png` — fresh canvas with
  toolbar + palette + properties placeholder visible. Confirms the
  palette renders all 10 built-in node types grouped into TRIGGERS /
  TRANSFORMS / CONDITIONS / ACTIONS.
- `canvas-5node-1920.png` / `canvas-5node-2560.png` — the five-node
  research workflow loaded via `Load`: `fetch_quote AAPL →
  fetch_history AAPL → compute.indicator RSI → ai.agent_invoke
  researcher → action.log`, with bezier edges connecting all four
  hops. Confirms the layout, custom-node renderer, and edge wiring.
- `canvas-properties-1920.png` / `canvas-properties-2560.png` — the
  Compute Indicator node selected; the right rail shows the typed
  properties form for `compute.indicator` (TYPE, ID, INDICATOR select
  with `rsi` chosen, PERIOD input with `14`, Delete-node action).
- `canvas-run-overlay-1920.png` / `canvas-run-overlay-2560.png` — the
  populated run overlay after a 5-node SSE stream completes. Shows the
  per-node OK badges, individual durations (38ms / 124ms / 17ms /
  1242ms / 4ms), pretty-printed output JSON for each node, the overall
  5/5 · 1425ms summary, and the Run-again button.

## Why these shots use mocked sidecar at the fetch boundary

`chrome-devtools` MCP cannot synthesize `isTrusted` events, which means
react-flow's canvas drag-drop and edge-connect gestures cannot be
driven through the MCP (per the CLAUDE.md isTrusted Gotcha that already
covers lightweight-charts). The plan's Teammate-N section
acknowledges this — Playwright is the eventual real-event tool, and in
the worktree session we fall back to:

1. Loading a workflow spec through `/workflow/saved/{id}` (read-only
   path, no gesture required) so the populated canvas renders from
   wire data exactly as the production flow would.
2. Mocking the SSE stream at the `fetch` boundary with the real
   `WorkflowRunEvent` frame shapes — same path the production flow
   takes when `pnpm tauri dev` is up.

The data-model + reducer paths exercised here are the same ones
covered by the 42 unit tests under `src/modules/node-editor/*.test.{ts,
tsx}` — the screenshots prove the visual rendering on top of that data
is correct.

## Lead-integration follow-up

At lead-integration the lead should retake these eight shots against a
real `pnpm tauri dev` session — same workflow, but with the sidecar
actually executing the run. The mocked-fetch shots prove the
frontend's contract handling; the real-sidecar shots will prove the
sidecar end-to-end. Both sets should land in this folder; overwriting
the mocked-fetch shots is allowed once the real-sidecar shots exist.
