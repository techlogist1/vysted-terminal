# R7 Track C — integration notes (chat → lead)

Shared needs the chat track cannot wire itself (ownership boundary). Each item
names the exact seam.

## 1. Sidecar honoring of `options.research_depth` (REQUIRED)

- The composer's three-stop depth slider (`src/store/research-depth.ts`,
  `'normal' | 'deep' | 'ultra'`) rides every foreground send: `handleSend`
  threads `researchDepth` into the invocation `options`, and `streaming.ts`
  (`wireOptions`) puts it on the wire as snake_case **`research_depth`** in the
  request body's `options` for BOTH `/agents/{id}/invoke` and `/llm/chat`.
- The sidecar currently ignores the key (free-dict options) — the lead wires
  the runtime to map it onto the research tool's depth tier. Suggested mapping:
  `normal → quick`, `deep → deep`, `ultra → heavy` (the `BriefDepth`
  vocabulary). Verified by `src/modules/chat/streaming.test.ts`.

## 2. Delegate lane carries it camelCase (FYI)

`launchDelegateRun` (lead-owned `src/lib/delegate-runs.ts`) receives
`options: { history, deepResearchBackend, researchDepth, … }` — the durable-run
path serializes options as-is, so the runs API sees `researchDepth` camelCase.
If the sidecar should read one spelling on both paths, map it in
delegate-runs the way `streaming.ts` does.

## 3. Depth persistence (OPTIONAL, lead's call)

`useResearchDepthStore` is deliberately session-state zustand (per the brief).
If persistence is wanted it should ride the workspace blob
(`serializeWorkspace`/`deserializeWorkspace` + a page.tsx autosave
subscription), not localStorage.

## 4. Unchanged contracts (verified by tests)

- `chat-pending` is now a real FIFO but `queuePrompt`/`consumePrompt` keep the
  palette one-shot semantics byte-compatible (no palette change needed).
- The brief's "Go deeper" escalation path (`agent-command` →
  `escalateResearchDepth` → chat `handleSend`) is untouched; the chat-side
  "+DEEP · GO ALL OUT" affordance is replaced by the slider, the deterministic
  `research <subject> at depth=<tier>` prompt path still works.
- `AgentHud.tsx` is deleted (only ChatSidebar imported it); the model popover
  in `ComposerMetaRow.tsx` carries the same catalog fallback ladder, capability
  pips (`modelOptionLabel`) and refresh.
