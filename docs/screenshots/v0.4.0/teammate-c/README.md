# Teammate C — Custom Agent Builder + per-panel context publishers

C shipped BLUEPRINT Module 36 (Custom Agent Builder) + the per-panel
context publishers that feed the chat sidebar's context badge. The
screenshot coverage at v0.4.0:

## Covered by Teammate A's screenshots

The chat sidebar's context badge (C's per-panel publisher chain) is
proven in A's populated-state shots:

- `../teammate-a/context-badge-1920x1080.png`
- `../teammate-a/context-badge-2560x1440.png`

These shots show the badge populated with chart panel state ("Context:
chart AAPL daily, RSI+MACD active") — exactly what C's per-panel
publisher commits enable. The badge cannot render that text without the
publisher chain being functional end-to-end.

## Covered by unit-integration tests

- `src/modules/panel-context-publishers.test.tsx` — cross-panel
  publisher integration (mount, publish-on-change, unmount cleanup,
  no-render-loop bound).
- `src/modules/chart/ChartPanel.test.tsx` — chart-specific publisher
  cases (timeframe change, indicator toggle).
- `src/modules/agent-builder/agent-builder.test.tsx` — form rendering,
  validation, save dispatch.
- `sidecar/tests/test_agents_store.py`, `test_custom_agents_router.py`
  — full Module 36 CRUD lifecycle.

## Deferred to Phase-4 polish

The Custom Agent Builder panel mid-edit screenshot pair (1920×1080 +
2560×1440) is the one populated-state shot not covered by either A's
captures or C's unit-integration tests. C's `BLOCKERS-C.md` flagged
this as Tier-3 documentation (the panel exists, all tests pass, only
the populated visual proof is missing); the lead aggregated the issue
into the v0.4.0 lead-level `BLOCKERS.md` (§"Phase-4 follow-ups") and
shipped without it. A Phase-4 polish pass with `pnpm tauri dev`
running can produce the shot in a single chrome-devtools session.

The full ship integration is otherwise verified — the unified
`src/store/agents.ts` hand-merge that landed at integration unions
first-party (A) + custom (C) records in a way that A's chat sidebar
and C's agent builder both consume, and that union is exercised by
both ChatSidebar.test.tsx and agent-builder.test.tsx.
