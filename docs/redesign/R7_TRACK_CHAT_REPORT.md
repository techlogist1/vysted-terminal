# R7 Track C — Composer & Narration — Final Report

Branch `worktree-agent-r7-chat`, worktree `.claude/worktrees/r7-chat`. Five feature
commits, all pushed:

| Commit    | Deliverable                                                                   |
| --------- | ----------------------------------------------------------------------------- |
| `0a08fa1` | research-depth store + `research_depth` wire threading                        |
| `fb37302` | real FIFO prompt queue + stopped-stream finalization                          |
| `e9029df` | one-unit composer — inside send/stop, 24px chip meta row, depth slider, queue |
| `8eed703` | integration notes (research_depth seams) + track brief                        |
| `ccf8f83` | prose-first narration — disclosure line + joined-rounds paragraph fix         |

## Gates (final, full-suite)

- `pnpm typecheck` — clean.
- `pnpm lint` — 0 errors. (1 pre-existing warning in
  `src/modules/equity-overview/EquityOverviewPanel.tsx:665`, outside this track.)
- `pnpm test` (ALL files) — **132 files / 1136 tests, all green.**
- `prettier --check` on every changed file — clean.
- No stubs, no TODOs in owned files (grep-verified).

## Shipped (file:line)

### Composer (ONE unit)

- **Bordered field, send/stop inside** — `src/modules/chat/ChatSidebar.tsx:1302`
  (`Composer`). One `rounded-control` inset unit (`:1496`): auto-growing textarea
  (`rows=1`, grows to ~6 lines via the existing measure logic), send button pinned
  INSIDE bottom-right (`:1533`), morphing to a **stop square** while streaming
  (`:1523`–`:1532`, `title="Stop — the partial answer stands"`). Monochrome — the
  send/stop never takes the accent.
- **Stop plumbing** — AbortController lifted to `abortRef`
  (`ChatSidebar.tsx:367`, assigned at `:753`); `onStop` → `abortRef.current?.abort()`
  (`:1127`). The abort path finalizes the partial message via
  `stopAssistantMessage` (`src/store/chat-history.ts:220`; `stopped` flag `:52`) and
  the transcript marks it with a quiet tertiary `stopped` caption
  (`ChatSidebar.tsx:1063`–`1064`). Distinct from the error path.
- **Queue** — typing stays enabled while streaming; `onSend` enqueues when a stream
  is live (`ChatSidebar.tsx:1122` → `useChatPendingStore.queuePrompt`). Visible
  text-micro chips with `[x]` render ABOVE the field (`QueuedPrompts`,
  `ChatSidebar.tsx:1191`–`1218`). Drain effect (`:936`–`:962`) sends IN ORDER, one
  at a time through the same `handleSend`, guarded by `drainingRef` + a
  `streamingMessageId` re-check between sends.
  `src/store/chat-pending.ts` is now a **real FIFO** (`queue: string[]`,
  `queuePrompt` / `consumePrompt` / `removePrompt` / `clearQueue`) — the palette
  one-shot semantics (`queuePrompt` + `consumePrompt` returns head once, `null`
  when empty) are a strict subset and unchanged.
- **Meta row** — `src/modules/chat/ComposerMetaRow.tsx` (new, 499 lines). ONE quiet
  24px text-micro row below the field:
  `[mode chip] [lens chip] [depth slider] ··· [autonomy chip] [model chip]`.
  Mode/lens/model chips open a SINGLE anchored popover (raised + hairline, opens
  above the row; one at a time; click-outside + Escape dismiss, `:286`–`:310`).
- **Depth slider** — `ComposerMetaRow.tsx:133`–`:192` (`DepthSlider`): three dots
  on a thin dotted rail, stops Normal / Deep / Ultra (label + title on
  hover/active), active dot+label `text-bright` (`lume`) at rest and **peach
  (`amber-400` = `#fab283`) ONLY while a research run is live at that depth**
  (`liveDepth` = `lastSentDepth` while `researchLive`, `ChatSidebar.tsx:296,372,1145`).
  Sets `useResearchDepthStore`.
- **Depth store** — `src/store/research-depth.ts` (new):
  `depth: 'normal'|'deep'|'ultra'`, session-state zustand (NOT persisted, per
  brief — persistence is the lead's seam).
- **Wire threading** — `handleSend` reads the store at call time and threads
  `researchDepth` into invocation `options` (`ChatSidebar.tsx:700`–`:704`);
  `src/modules/chat/streaming.ts:43` (`wireOptions`) maps it to snake_case
  **`research_depth`** in the wire body for BOTH `streamChat` (`:61`) and
  `streamAgentInvocation` (`:96`); all other option keys pass through unchanged.

### Narration (language first)

- **Disclosure** — `ActivityTrace`, `ChatSidebar.tsx:206`–`:264`. WHILE STREAMING
  the live activity (plan → animated research trace → tool-step lines) renders as
  before — the one place the peach accent belongs. Once the run finishes, the
  whole trace collapses into ONE tertiary text-micro line ABOVE the prose:
  `▸ Worked for 12s · 7 steps` (duration = the SUM of measured step latencies —
  the same number the expanded trace footer shows; never a fabricated wall-clock).
  Expands per-message to the existing PlanView/ResearchActivity/tool-step detail;
  default COLLAPSED. `formatElapsed` exported from `ResearchActivity.tsx:55`.
- **Joined-rounds fix** — `src/store/chat-history.ts`: `roundBoundaryPending` flag
  (`:77`) set by `_markRoundBoundary` (`:118`) in `appendToolStep`,
  `appendResearchStep`, `setPlan`, and `markBriefPublished` when the message
  already has prose; the next `appendAssistantDelta` (`:160`–`:178`) consumes it
  and prepends `\n\n` unless the content already ends with whitespace. Unit test
  reproduces the exact bug: `"…look."` + [tool step] + `"Set SPY…"` → paragraph
  break (`src/store/chat-history.test.ts`).
- `firstSentences` collapse for brief-published turns and `MarkdownBody`
  rendering kept; tool-step labels stay humanized (`readToolLabel`,
  `ChatSidebar.tsx:185`) inside the disclosure.

### Tests added/updated

- `src/store/research-depth.test.ts` (new), `src/store/chat-pending.test.ts`
  (+FIFO/remove/clear coverage), `src/store/chat-history.test.ts` (+103 lines:
  joined-rounds repro, boundary-on-empty no-op, whitespace-tail no-op, stop
  semantics), `src/modules/chat/streaming.test.ts` (+68: `research_depth`
  snake_case on both endpoints, passthrough of other keys),
  `src/modules/chat/ChatSidebar.test.tsx` (+225: lens display-name, slider →
  store → options, mode/model popovers, queue drain order, chip `[x]`, stop
  square → `stopped`, disclosure collapse/expand, live trace while pending). No
  behavior coverage deleted — existing assertions updated for the new DOM only.

## Behavior parity — every old control → where it lives now

| Old (4 stacked chrome rows)                                               | Now                                                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Row 1: `Agent \| Delegate` mode tabs                                      | Mode chip → popover (`ComposerMetaRow.tsx:332`–`:357`)                                                                                                                                                                                                                                                                                               |
| Row 1: `LENS` select (could show raw id `warren`)                         | Lens chip → roster popover; label is ALWAYS the display name: `activeAgent?.name ?? humanizeAgentId(id)` (`ChatSidebar.tsx:1135`; chip `ComposerMetaRow.tsx:360`–`:400`)                                                                                                                                                                             |
| Row 2: `+DEEP · GO ALL OUT` (ResearchDepthControl)                        | Three-stop depth slider (`ComposerMetaRow.tsx:133`). The deterministic "go deeper" escalation (brief → `agent-command` → `handleSend`) is untouched and verified by `agent-command.test.ts`                                                                                                                                                          |
| Row 2: `ASK AUTO` autonomy toggle                                         | 24px segmented ASK/AUTO chip (`ComposerMetaRow.tsx:193`–`:228`), same `agent-autonomy` store                                                                                                                                                                                                                                                         |
| Row 3: `PROVIDER` select + model select + refresh (AgentHud)              | Model chip → anchored popover with provider list, grouped models, capability pips (`· no tools`, `· ⌕`), the no-tools warning, and the refresh affordance (`ComposerMetaRow.tsx:410`–`:494`). Same catalog fallback ladder (live catalog → provider knownModels → static map). **`AgentHud.tsx` deleted** (-141 lines; only ChatSidebar imported it) |
| Row 4: input + outside send button                                        | The one bordered field; send INSIDE bottom-right, morphs to stop while streaming                                                                                                                                                                                                                                                                     |
| Delegate `BudgetConfig`                                                   | Kept, renders above the field in delegate mode (`ChatSidebar.tsx:1109`)                                                                                                                                                                                                                                                                              |
| Slash/mention pickers, SuggestionChips, spaces tabs, export, ContextBadge | Kept in place, styling brought to the law where touched                                                                                                                                                                                                                                                                                              |
| Per-step ms rows expanded above prose                                     | Behind the `▸ Worked for …` disclosure, default collapsed post-run                                                                                                                                                                                                                                                                                   |
| `✓ RESEARCHED 335 · 7 STEPS` telemetry header                             | Gone; the disclosure line is the only telemetry at rest                                                                                                                                                                                                                                                                                              |

## Integration notes (the lead wires — full detail in `INTEGRATION_NOTES_R7_CHAT.md`)

1. **Sidecar honoring of `options.research_depth` (REQUIRED)** — the frontend now
   sends it on every foreground send (`/agents/{id}/invoke` and `/llm/chat`); the
   sidecar currently ignores unknown option keys. Suggested mapping onto the
   research tool's tier: `normal → quick`, `deep → deep`, `ultra → heavy`.
2. **Delegate lane carries camelCase `researchDepth`** — `launchDelegateRun`
   (lead-owned `src/lib/delegate-runs.ts`) serializes options as-is; map it there
   the way `streaming.ts wireOptions` does if one wire spelling is wanted on both
   paths.
3. **Depth persistence (optional)** — store is session-state by design; if wanted,
   ride the workspace blob (`serializeWorkspace`/`deserializeWorkspace` + a
   page.tsx autosave subscription), never localStorage.

## What to eyeball live

- The composer reads as ONE unit: queue chips → bordered field (send inside) →
  one quiet 24px meta row. No stacked select rows anywhere.
- Lens chip shows "Warren Buffett"-style display names, never `warren`.
- Depth slider: dotted rail, label tracks the active stop; goes peach only while
  a research run sent at that depth is streaming, back to text-bright after.
- Mid-stream: send button is a stop square; clicking it leaves the partial answer
  with a tertiary `stopped` caption (no error styling).
- Type two prompts while a run streams → two removable chips → they send in order
  after the stream ends.
- A finished multi-tool answer shows `▸ Worked for Ns · M steps` above clean
  prose; expanding reveals the old plan/research/tool detail; paragraph breaks
  between model rounds (no more `…look.Set SPY…`).
- Model popover: capability pips + refresh + the no-tools warning, anchored above
  the row, raised surface + hairline.

## NEEDS-MANUAL-CHECK

- **Real-network stop:** tests abort a mocked SSE stream (jsdom). Verify against
  the live sidecar that aborting mid-`/agents/{id}/invoke` lands on the
  `stopped` path (not the error toast) and that the sidecar drops the upstream
  LLM call.
- **`research_depth` is a no-op until the lead's sidecar mapping ships** —
  expected; the slider still drives the store + wire today.
- **Popover clipping at narrow sidebar widths:** popovers position absolutely
  above the meta row (no portal). Check the model popover (the widest) at the
  sidebar's minimum width and on the mobile-search route from screenshot 41.
- **Queue drain × delegate mode:** the drain is gated on `streamingMessageId`;
  delegate launches don't stream in the transcript, so queued prompts fire
  immediately after the launch acknowledgment. Confirm that ordering feels right
  live.
- **Visual law pass:** 32px field row / 24px meta controls / 0px containers /
  4px controls verified in JSDOM class assertions only — eyeball at 1920×1080
  and 2560×1440 per the screenshot protocol.
