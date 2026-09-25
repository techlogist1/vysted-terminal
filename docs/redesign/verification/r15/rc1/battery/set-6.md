# batch-3/W2-agent-frontend-gate (set-6)

Candidate sha 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a. These mechanisms live entirely in
frontend TS/TSX (no sidecar endpoint, no CLI entry point) and the task forbids running
vitest and forbids a GUI. Per the task's `ci_pinned` rule I located the exact committed test
that certifies each entry's mechanism (all in the repo at HEAD, not the scratch/removed
worktree files batch-3's own verifier used) and read its body to confirm it still asserts the
exact claimed behaviour. I did not execute these tests (no vitest run) — verdict is
`ci_pinned`, naming the test.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-080 | `src/store/proposed-changes.test.ts:128` "AUTO mode applies a UI/chart/watchlist change on enqueue, no manual accept" + `:139` "AUTO mode keeps data-write and settings changes pending and acks them staged" | Read the test bodies at HEAD: asserts `set_chart_symbol` auto-applies under AUTO while `portfolio_delete_position`, `write_note`, `set_region`, `save_screen` stay pending and ack `staged`. Matches the AUTO_APPLIED_KINDS=[panel,chart,watchlist] constant in `types/proposed-change.ts:38`. | ci_pinned (proposed-changes.test.ts) |
| R15-CODE-FRONTEND-008 | same test as AGENT-080 (shared root cause — policy copy) | same | ci_pinned (proposed-changes.test.ts) |
| R15-CODE-FRONTEND-003 | `src/store/notes.test.ts:26-50` "appendGeneral (R10 write_note seam)" | Read the test body: append to existing body joins with `\n\n` separator, preserving indentation/trailing newlines — matches write_note's append-not-replace fix. | ci_pinned (notes.test.ts) |
| R15-CODE-FRONTEND-014 | `src/lib/host-actions.test.ts:1209` "save_layout without a name updates the active saved layout" + `src/store/notes.test.ts:64` "empty symbol falls back to the general bucket" | Read both bodies: `save_layout({})` on an active layout named "My desk" updates that layout; falls back to "Agent layout" only when the active name is exactly "default". `appendSymbolNote("", ...)` falls into the General bucket. | ci_pinned (host-actions.test.ts + notes.test.ts) |
| R15-UI-001 | `src/modules/notes/NotesPanel.test.tsx:46` "shows an agent write_note into the open note, and the next keystroke keeps it" + `:66` "a scope switch inside the debounce window saves each scope's own text" | Read both bodies: an agent `write_note` write is visible immediately and survives the next keystroke's debounce-save; a scope switch mid-debounce saves each scope's own text — the two originally-certified sub-repros. | ci_pinned (NotesPanel.test.tsx) |
| R15-UI-002 | `src/components/CommandPalette.test.tsx:192` "a ticker pick commands the chart through the always-consumed chart-command channel" | Read the body: typing "nvda", clicking the Symbols row sets `useChartCommandStore` to `{symbol:"NVDA"}` and opens a chart panel when none exists — exact original mechanism. | ci_pinned (CommandPalette.test.tsx) |
| R15-AGENT-014 | `src/lib/plugin-bootstrap.test.ts:50` "registers a pre-installed agent pack's agents once; a disabled one is not synced" | Read the body: `bootstrapPlugins()` calls `syncPluginAgents("vysted-lenses", true)` once for an enabled plugin pack, and never for a disabled one. | ci_pinned (plugin-bootstrap.test.ts) |

## Notes
- No GUI and no vitest run per task constraints; all six mechanisms are pure store/lib logic
  with a committed, still-present test asserting the exact original claim, read at HEAD on
  the candidate sha. None showed source-level drift from the certified mechanism (the
  AUTO_APPLIED_KINDS constant, the append-seam, the save_layout/notes fallback rules, the
  chart-command channel, and the plugin-agent sync call are all unchanged in shape from what
  batch-3's verifier describes).
- No regressions found in this set. No new defects found.
