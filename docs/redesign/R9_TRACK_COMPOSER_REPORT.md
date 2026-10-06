# R9 Track C — Composer Claude-exact + reading surfaces (report)

Branch: `worktree-agent-r9-composer` (from 004 HEAD `6f835e6`). All work against
`R9_DESIGN_SYSTEM.md`. Verification from this worktree: **full vitest suite 142
files / 1384 tests green** (135 on the partition: 117 chat + 18 research),
`pnpm typecheck` clean, `pnpm lint` 0 errors (one pre-existing
EquityOverviewPanel exhaustive-deps warning, untouched),
`node scripts/audit-design-tokens.mjs src/modules/chat src/modules/research`
**CLEAN** (was 51 violations), `pnpm prettier --check` clean on the partition.

## Commits

| sha       | deliverable                                                                                   |
| --------- | --------------------------------------------------------------------------------------------- |
| `a2c33f3` | C1 — Claude-exact composer: controls inside the field, depth heat, plus-menu absorption       |
| `434ad5a` | C2 — keyless-fallback nudge banner + brief reading surfaces to the law                        |
| `a3fb83f` | C1/C3 — self-capture polish round (verbatim chips, stacked hints, empty roster) + R9 captures |
| (this)    | C3 — kill list + this report                                                                  |

## C1 — the composer

Reference anatomy replicated structurally (`claude-composer.png`), Vysted skin
(sharp-ish 4px controls, zinc, mono — law §5):

- **ONE field container** (`ChatSidebar.tsx` `Composer`): textarea on top
  (auto-grow 1–6 lines, "Ask anything…"), controls row INSIDE at the bottom:
  `[+ 28×28/16px] ··· [depth pill] [model text] [send 28×28/16px]`.
- **The five-chip strip is dead.** `ComposerMetaRow.tsx`,
  `meta-row-collapse.ts(.test)` deleted. Redistribution exactly per brief:
  - **Plus menu** (`ComposerPlusMenu.tsx`) absorbs: **Persona** (drill-in
    roster, concierge-first, display names only, checked active, quiet empty
    state), **Autonomy** ASK/AUTO rows (don't close the menu — it's a mode),
    **Mode** Agent/Delegate rows (⌥1/⌥2 hotkeys unchanged), then the
    catalog-derived Context/Scope/Route-to mention sections (one source of
    truth: `STATIC_MENTIONS`; insert path byte-identical to typing) and the
    slash-commands primer.
  - **Model** (`ModelControl.tsx`): Claude's quiet-text pattern — designed
    short form via `formatModelLabel` ("Qwen2.5 7B"), `charcoal-400` hover
    lume, **no pill chrome**; opens the provider · model popover (capability
    pips, refresh, no-key affordance preserved verbatim).
  - **Depth** (`DepthControl.tsx`): ONE segmented pill left of the model text.
    Active stop label at rest ("Deep") in its heat token; hover/focus expands
    to all three stops; an animated thumb slides under the active stop —
    **180ms `--ease-shared`**, `useReducedMotion` collapses every morph to an
    instant swap. The live pulse (run in flight at that depth) rides the
    active label, revalued to the token. Dotted rail + dot artifact dead.
- **Depth-keyed send** (law §4): armed fill = `--color-depth-normal/deep/ultra`
  per the active stop, icon flipped dark (`charcoal-950`) for contrast; the
  streaming **stop morph keeps the SENT depth's token** (`sentDepth` rides the
  props from `lastSentDepth`, so a mid-run selector change never recolors the
  live run's stop).
- **Queue/drain machinery untouched**: chips above the field, FIFO drain,
  Enter-queues-while-streaming, stop aborts via the lifted `abortRef` — the
  existing tests for all of it pass unchanged.
- **Collapse ladder** (`composer-collapse.ts`, test-pinned): pure function of
  the measured controls-row width (ResizeObserver) —
  `full ≥380` (full model text, depth expands) → `compact ≥310` (model text
  two words) → `icons <310` (model → 14px icon + tooltip, depth →
  active-stop-only, click cycles N→D→U). The 280px dock floor (≈238px row) and
  the 320px dock are pinned on `icons`; monotonicity swept 1000→1px.

## C2 — reading surfaces

- Transcript: body-13 in dock (unchanged), user turn in the quiet bordered
  container (no size delta), **16px block rhythm** (message list `gap-4`,
  in-message block `gap-4`, panel padding `px-4 py-4`), step traces stay
  behind the tertiary disclosure.
- Brief panel: prose-16 only ≥420px column (the existing `@container`
  downshift — intact), metric cards re-tuned to the grid (table cells `py-1`
  land data rows at 28px), table parse untouched (`brief-blocks.test.ts`
  green).
- **Keyless-fallback nudge (gate 2)**: `types/brief.ts` gains optional
  `backend?: string` (additive, documented); `BriefPanel` renders ONE quiet
  banner when `brief.backend === "keyless-fallback"` — "Limited keyless
  search — set up Unlimited local research for full capability" → opens the
  Settings panel. Dismissible per-brief (keyed on `createdAt`; the next
  fallback brief re-shows it), **never** on `searxng` / `research-model:*` /
  absent ids. Fixture-tested (4 tests in `BriefPanel.test.tsx`).

## C3 — stray-item audit

Kill list appended to `verification/R9_DEFECT_CATALOGUE.md` (Team C section):
meta-row strip, dotted depth rail, standing "Context: none" row, queue-chip
uppercase, truncated menu hints, bare empty-roster header — all dead. Items
audited and kept are listed there with reasons.

## Self-captures (headless Chrome, port 5174)

`docs/redesign/verification/r9/composer/` — 1280×900 @2x:
`01-rest`, `02-armed-normal` (lume send), `03-armed-deep` (peach),
`04-armed-ultra` (ember), `05-streaming` (stop morph keeps depth token),
`06-queued` (verbatim chips), `07-narrow-320` (icons step, zero overlap),
`08-plus-menu` (root: persona/autonomy/mode/context), `09-depth-expanded`
(three stops + thumb), `10-model-popover`, `11-persona-drill`.
Driven by a CDP harness against `pnpm exec vite --port 5174` using the
DEV-only `window.__vystedChatDebug` store seam (tree-shaken from prod builds).
Side-by-side against `references/r9/claude-composer.png`: anatomy matches —
one container, + inside-left, quiet model text + depth control inside-right
beside the send square; Vysted keeps its own radius/zinc/mono per law §5.

## Decisions (Tier 2/3, in-commit)

1. Persona picker = drill-in view inside the plus menu (matches Claude's
   submenu pattern; a 14-agent flat section would dwarf the menu).
2. Autonomy/Mode = `menuitemradio` rows with stacked full-text hints (ARIA-
   conforming inside `role=menu`; picking does not close — they're modes).
3. Depth at the icons step cycles on click (every stop reachable at 280px
   without an overlay; radiogroup semantics return at ≥310px).
4. Depth thumb at rest stays under the active label (quiet chip presence —
   the affordance reads without inviting the old chip-strip look).
5. Scroll caps (`max-h-*` on pickers/popovers/trays) are annotated
   `tokens-ok:` as layout-not-rhythm; one 14px icon (`size-3.5`) inside the
   h-7 model control is annotated per law §3 (14px inside h-7).

## NEEDS-MANUAL-CHECK

1. **Lead integration (one line, outside my partition):** `briefFromInput`
   in `src/lib/host-actions.ts` must pass the wire field through —
   `backend: str(input, "backend") || undefined` — for the nudge to fire
   end-to-end at runtime. Types, render, and fixture tests are ready; I did
   not touch the lead-owned file. Team A guarantees the id on the wire.
2. Live-rig (real pointer + real stream): depth-pill hover expansion + thumb
   morph, send⇄stop morph mid-stream, and macOS reduced-motion ON (headless
   verified the mouseover/focus paths and reduced-motion only via code).
3. Settings → Research SECTION deep-link: the nudge opens the Settings panel;
   if Team D ships section anchors, point the nudge at the Research section.
4. **Worktree trap for other tracks:** Vite's file watcher does NOT pick up
   edits when the repo root lives under `.claude/worktrees/...` (dot-dir
   ignore) — restart the dev server after edits before capturing, or stale
   modules are served (cost me one false capture round).
5. The reference verifier should judge STRUCTURE, not radius — Vysted stays
   4px-control / zinc / mono by law §5 while Claude uses large pill radii.
