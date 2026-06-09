# R7 Track C — Composer & Narration Brief (worktree: worktree-agent-r7-chat)

Rebuild the chat surface — ONE calm composer + language-not-telemetry narration — inside
THIS worktree only: `~/Documents/dev/vysted-terminal/.claude/worktrees/r7-chat`. Branch
`worktree-agent-r7-chat`. NEVER write to the main repo path.

## Ground rules

- You OWN: `src/modules/chat/**`, `src/store/chat-history.ts`, `src/store/chat-pending.ts`,
  a new `src/store/research-depth.ts`, their tests. NOTHING else (not host-actions, not
  CommandPalette, not other stores — the lead is editing those concurrently; shared needs →
  `docs/redesign/INTEGRATION_NOTES_R7_CHAT.md`).
- Gates per commit: `pnpm typecheck && pnpm lint && pnpm vitest run src/modules/chat src/store/chat-history.test.ts` + prettier on changed files.
- Conventional commits per deliverable; push to `origin worktree-agent-r7-chat`.
- Design law: docs/redesign/VYSTED_DESIGN.md (read fully). Mono, ladder, monochrome (peach
  = LIVE agent activity only — the streaming caret/running indicators MAY use it),
  containers 0px / controls 4px, 32/24 heights, no shadows, no arbitrary text sizes.
- The send PIPELINE in handleSend (slash parsing, provider/key resolve, delegate lane,
  proposed-changes gate, runs rail) is correct — REBUILD THE SURFACE AROUND IT, don't
  break its contracts. All existing tests must stay green (update assertions for the new
  DOM, never delete behavior coverage).

## Current diseases (verified live — screenshots 01-tab-Chart.png, 41-route-mobile-search.png

in the MAIN repo's docs/redesign/verification/r7/)

1. FOUR stacked chrome rows around one input: "Agent | Delegate | LENS [Vysted Copilot]" /
   "+DEEP · GO ALL OUT | ASK AUTO" / "PROVIDER [DeepSeek] [deepseek-v4-flash] [refresh]" /
   the input row. The lens chip can show a raw agent id ("warren") instead of a display name.
2. No stop button; no typed-prompt queue while streaming.
3. Narration leads with telemetry: "✓ RESEARCHED 335 · 7 STEPS" + per-step ms rows render
   EXPANDED above the prose; the prose itself has the joined-rounds bug ("…look.Set SPY…" —
   missing paragraph break when a new model round starts after tool execution).

## Target — the composer (Cursor-grade, ONE unit)

- One bordered field (inset fill, 1px border, rounded-control): auto-growing textarea
  (min-h one line, max ~6 lines) + send/stop button INSIDE the field's bottom-right.
- BELOW the field, ONE quiet 24px meta row (text-micro, tertiary):
  `[mode chip: Agent|Delegate] [lens chip: display-name] [depth slider] ··· [autonomy chip: ASK|AUTO] [model chip: provider · model]`
  Each chip is a 24px compact control. Clicking mode/lens/model chips opens a SINGLE
  anchored popover (raised+hairline) with the respective options — the standing selects
  rows are deleted. The lens chip ALWAYS shows the agent's display name (resolve id →
  name; never a raw id). Model popover keeps the capability pips & refresh that exist today.
- THE DEPTH SLIDER: a segmented three-stop control (the mandate's words: "smooth, dotted,
  restrained accent on the active stop") — three dots connected by a thin rail, stops
  labeled on hover/active as Normal / Deep / Ultra, the ACTIVE stop's dot + label use
  accent ONLY while a research run is live at that depth, otherwise text-bright. It sets
  `useResearchDepthStore` (new store: depth: 'normal'|'deep'|'ultra', persisted via the
  workspace-blob pattern? NO — keep it session-state zustand for now; the lead wires
  persistence + the sidecar threading). On send, thread `researchDepth` into the
  invocation `options` (snake_case `research_depth` in the wire body — add it in
  streaming.ts options passthrough). The old ResearchDepthControl ("+DEEP · GO ALL OUT")
  and the brief's read-only mirror hooks stay functional but the chat-side affordance is
  REPLACED by the slider (keep the deterministic escalation prompt path for the brief's
  "go deeper" — it routes through agent-command; don't break it).
- STOP: while streaming, the send button morphs into a stop square; clicking aborts the
  in-flight run (the AbortController already exists in handleSend — lift it to a ref so
  the composer can reach it), the partial message finalizes (existing aborted path), and
  the transcript marks it "stopped" quietly (caption, tertiary).
- QUEUE: typing while streaming stays enabled; Enter pushes to a visible queue (chips
  above the field, text-micro, removable [x]); when the stream ends, queued prompts send
  IN ORDER (drain one at a time through handleSend). Implement in chat-pending.ts as a
  real FIFO (rename semantics carefully — the palette one-shot behavior must keep working).
- Slash/mention pickers, suggestion chips, spaces tabs, export, ContextBadge stay; bring
  their styling to the law where touched.

## Target — narration (language first, telemetry behind disclosure)

- The assistant message renders PROSE FIRST. The step trace (plan, research steps, tool
  steps, timings) collapses into ONE quiet disclosure line above the prose:
  `▸ Worked for 12s · 7 steps` (text-micro, tertiary; expands to the existing
  ResearchActivity-style detail; expanded state per-message, default COLLAPSED once the
  run finishes; WHILE STREAMING the live activity line shows as today — live activity is
  the one place the peach accent belongs).
- Fix the joined-rounds bug in `src/store/chat-history.ts`: when appendToolStep/
  appendResearchStep (or any non-delta event) lands on a message that already has prose,
  set a boundary flag; the NEXT appendDelta prepends "\n\n" if the existing content
  doesn't already end with whitespace. Add a unit test reproducing "…look." + [tool step]
  - "Set SPY…" → paragraph break.
- Keep `firstSentences` collapse for brief-published turns; keep MarkdownBody rendering.
- Tool step labels stay humanized (readToolLabel) — inside the disclosure.

## Done =

No stubs. Gates green (full `pnpm test` at the end — all 129 files). Committed + pushed.
Final report `docs/redesign/R7_TRACK_CHAT_REPORT.md`: shipped file:line, behavior parity
notes (every old control → where it lives now), INTEGRATION_NOTES (the lead wires:
sidecar honoring of options.research_depth; depth persistence if wanted), what to eyeball
live, NEEDS-MANUAL-CHECK.
