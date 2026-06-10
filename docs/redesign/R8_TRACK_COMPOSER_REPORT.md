# R8 Track C — Composer & Chat (report)

Branch: `worktree-agent-r8-composer`. All work against `docs/redesign/R8_PROPORTION_LAW.md`.
Verification (from this worktree): `pnpm test` 141 files / 1327 tests green, `pnpm lint`
0 errors (one pre-existing `EquityOverviewPanel` exhaustive-deps warning, untouched),
`pnpm typecheck` clean, `pnpm format:check` clean.

## Commits

| sha       | deliverable                                                              |
| --------- | ------------------------------------------------------------------------ |
| `b80e723` | 1 — Claude-reference composer (plus-menu, 28px accent send ⇄ stop morph) |
| `357bde4` | 2 — chip affordances + accented animated depth slider                    |
| `9e24e77` | 3 — meta-row responsive collapse ladder                                  |
| `ea1a0bf` | 4 — transcript typography per law §1 + real tables in chat               |
| `9ee8d09` | 5 — header model short forms + dot collapse + named runs tooltip         |

## 1. Claude-reference composer

- One bordered field, textarea on top (auto-grow + 144px max + scroll preserved:
  `ChatSidebar.tsx:1334` `Composer`), controls row INSIDE the field below it
  (`ChatSidebar.tsx:1565-1576`).
- PLUS at bottom-left, 28×28 / 16px icon, quiet until hover:
  `ComposerPlusMenu.tsx:49` (component), `:40` (`buildPlusMenuSections` — sections
  Context/Scope/Route-to derived from `STATIC_MENTIONS`, plus the "Slash commands…"
  row). Menu rows insert via the parent's `pickMention` (`ChatSidebar.tsx:1429`) →
  the ONE shared insert path `insertMentionToken` (`mentions.ts:149`), so a menu pick
  is byte-identical to typing (space-separation parity included). "Slash commands…"
  → `primeSlashCommands` (`ChatSidebar.tsx:1446`) inserts "/" + focuses; `matchSlash`
  opens the picker.
- SEND bottom-right 28×28 / 16px arrow-up, accent when armed, morphs to the STOP
  square while streaming with a scale/opacity crossfade, `useReducedMotion` →
  instant swap: `SendStopButton` (`ChatSidebar.tsx:1591`).
- Stop/queue sacred: `abortRef`/`drainingRef`/queue-chip wiring untouched; the
  existing ChatSidebar tests (queue order, chip removal, stop-marks-stopped,
  abort-on-signal) all pass unchanged.
- Vitest: `mentions.test.ts` (`insertMentionToken` ×6), `ComposerPlusMenu.test.tsx`
  (section derivation ×3, menu interaction ×3).

## 2. Chip affordances + animated depth

- `MetaChip` (`ComposerMetaRow.tsx:45`): hairline border + hover bg/text step +
  `cursor-pointer` + h-6, `text-caption` (law §1: meta rows are caption, not micro),
  row gap `gap-1.5`.
- `AutonomySegments` (`ComposerMetaRow.tsx:220`): cursor-pointer + hover bg step,
  caption type, bordered segmented unit kept.
- `DepthSlider` (`ComposerMetaRow.tsx:146`): ACTIVE stop always carries the accent
  (law §5); one-shot scale pop on depth change (keyed remount, 1.6→1); gentle 1.8s
  repeating pulse while `liveDepth === depth`; both gated by `useReducedMotion`.
  `min-w-[3.5rem]` floor.

## 3. Collapse ladder (spec)

Pure function of measured row width (`meta-row-collapse.ts:29`,
breakpoints `:22`), fed by a ResizeObserver on the row (`ComposerMetaRow.tsx:446`;
container width is dock-set, so no measure→render feedback loop; unmeasured → "full"):

| row width (content box) | step       | rendering                                                                                                  |
| ----------------------- | ---------- | ---------------------------------------------------------------------------------------------------------- |
| ≥ 470px                 | `full`     | full labels, depth text label, lens cap 9rem, model cap 13rem                                              |
| 380–469px               | `short`    | labels stay, depth label drops, lens 6rem / model 8rem caps                                                |
| 250–379px               | `icons`    | mode/lens/model = 12px icon + tooltip; ASK/AUTO + depth dots stay                                          |
| 170–249px               | `overflow` | autonomy + provider/model fold into "⋯" popover (`ComposerMetaRow.tsx:675`); visible: mode, lens, depth, ⋯ |
| < 170px                 | `two-row`  | two stacked 24px rows (`ComposerMetaRow.tsx:710`) — nothing hides, nothing clips                           |

The 280px dock minimum ⇒ ~256px row width ⇒ `icons`: every control visible, depth
slider never under the lens chip; composer plus/send (28px squares in a flex row)
remain usable. The "⋯" popover reuses the exact model-popover body
(`ModelPopoverBody`, `ComposerMetaRow.tsx:283`) + `AutonomyRows` (`:256`) so the
two surfaces can't diverge. Vitest: `meta-row-collapse.test.ts` (step selection,
280px-dock anchor, monotonicity sweep 1000→1px, per-step plan, breakpoint order).

## 4. Transcript typography (law §1)

- User + assistant share text-body 13: `MessageBody` (`ChatSidebar.tsx:142`) wraps
  the shared `MarkdownBody` in a downshift container (`[&_p]/[&_ul]/[&_ol]` →
  `--text-body` + `leading-body`, lists `ml-5` = 1.25rem indent, `break-words` +
  `min-w-0` keep everything inside the dock column). The research module is NOT
  touched — the downshift lives entirely at the chat call-site.
- User turn = quiet bordered container ONLY (`ChatSidebar.tsx:1078`,
  `border-charcoal-700 bg-charcoal-850`); assistant reads as flat prose. Same type
  step, container is the distinguisher.
- Tables: `normalizePipeTables` (`chat-markdown.ts:65`, applied at
  `ChatSidebar.tsx:172`) synthesizes the GFM separator under separator-less pipe
  runs (fence-aware, idempotent) so chat renders REAL compact tables — the live
  "| Metric |…" wall-of-pipes is dead. The collapsed brief lead strips table rows
  first (`stripTableRows`, `chat-markdown.ts:97`, applied `ChatSidebar.tsx:165`)
  so a sentence slice can't reintroduce pipes.
- Tool-step trace: verified collapsed-by-default after completion (`ActivityTrace`
  unchanged; covered by the existing "collapses a finished run's step trace" test).
- Vitest: `chat-markdown.test.ts` ×10.

## 5. Header model label

- `formatModelLabel` (`StatusChrome.tsx:49`): formatter-level designed short forms —
  "deepseek-v4-flash" → "DeepSeek V4 Flash", org prefixes drop
  ("minimax/minimax-m3" → "MiniMax M3"), >24-char names trim MIDDLE segments
  ("Llama 3.1 70B … Free"). No mid-word CSS ellipsis anywhere on the label.
- Collapse: provider dot + short label → dot only below 880px window width
  (`StatusChrome.tsx:152`, pure CSS `min-[880px]:inline` — the header spans the
  window, so a viewport breakpoint is the robust measure); the tooltip always
  carries the exact `provider · model` ids.
- The active-runs ("+N") chip tooltip now NAMES what it counts
  (`StatusChrome.tsx:164`): "2 agent runs in progress: Warren Buffett, AI
  Researcher". (Note: the repo has no other "+1" overflow chip in the header —
  the runs counter is that chip; if the operator meant a different one it isn't
  in `src/components/` or `page.tsx`.)
- The composer meta-row model chip reuses the same formatter
  (`ComposerMetaRow.tsx` model chip), exact ids stay in popover rows + tooltips.
- Vitest: `StatusChrome.test.tsx` (formatter ×6, render + tooltip ×2).

## Needs visual verification on the live rig

1. Composer at 280 / 310 / 470 / 600px dock widths: ladder steps engage in order,
   no overlap, plus/send usable at 280.
2. Send⇄stop morph during a real stream (and with macOS reduced-motion ON).
3. Depth-stop pop on click + pulse during a live research run at that depth.
4. Plus-menu insert with a non-empty composer (space-separation) and the
   "Slash commands…" → `/` picker handoff.
5. A model reply containing a separator-less markdown table renders as a table
   live (streaming) and in the collapsed brief-published lead.
6. Header at a narrow window (<880px): model label collapses to the dot; runs
   tooltip names the running agents.
7. User-bubble vs flat-assistant contrast at the dock's default width — confirm
   the quiet `bg-charcoal-850` container reads as "what I typed" without shouting.

## Notes for the lead

- No new shared CSS utilities were needed — the chat downshift uses arbitrary
  variants over existing `@theme` tokens (`--text-body`, `leading-body`).
- `ComposerMetaRow` now imports `formatModelLabel` from
  `@/components/StatusChrome` (chat already imports from `@/components`; kept the
  formatter beside the surface that owns the defect).
- The send square now carries the accent when armed (the R8 brief's explicit
  call) — this widens the accent's previous "live activity only" role to the
  law-§5 "active = accent" reading; comments updated where they claimed otherwise.
