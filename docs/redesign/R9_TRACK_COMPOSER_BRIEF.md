# R9 Track C — Composer Claude-exact + reading surfaces

Branch: `worktree-agent-r9-composer` from 004 HEAD. Partition is EXCLUSIVE. Push every
concrete deliverable. **Read `docs/redesign/R9_DESIGN_SYSTEM.md` FIRST and build against
it — the app's previous rendered look was the bug (D26), not the target.**

## Files you own

`src/modules/chat/**` (ChatSidebar.tsx, ComposerMetaRow.tsx, ComposerPlusMenu.tsx,
mentions.ts, pickers), `src/modules/research/**` (brief-blocks.tsx etc.),
`src/store/research-depth.ts`, `src/store/chat-pending.ts` + `src/store/chat-history.ts`
(only if the rebuild requires — preserve public store APIs), their tests.
DO NOT touch tokens.css/globals.css (lead), SettingsPanel (D), other modules (E).

## C1 — The composer (gate 8: side-by-side vs the Claude reference)

Reference: `docs/redesign/references/r9/claude-composer.png` (captured from the live Claude
desktop app). Its anatomy, which you replicate STRUCTURALLY (Vysted stays sharp-cornered,
zinc, mono — see law §5):

- ONE field container. Text input row on top (auto-grow 1–6 lines, placeholder "Ask
  anything…"). A controls row INSIDE the container at the bottom: **+ button far left**
  (16px icon, h-7 hit target), then minimal chips; **send button far right** (h-7,
  28×28, 16px icon), morphing to stop (square) while streaming. Queue chips + drain
  behavior preserved exactly (stop/queue machinery in chat-pending/chat-history).
- **The five-chip strip below the input DIES.** What lives where (decided):
  - **+ menu** absorbs: persona/agent picker (Route-to), context/scope, slash commands —
    your existing ComposerPlusMenu sections, redesigned to the law.
  - **Inline quiet text control, right side beside send** (Claude's "Fable 5 High"
    pattern): model name in designed short form (e.g. "DeepSeek V4 Flash") — opens the
    model/provider popover. Quiet charcoal-400, hover lume; no pill chrome.
  - **Depth selector**: a single compact control left of the model text — three stops
    N/D/U rendered as one segmented pill with an animated thumb (180ms shared easing,
    reduced-motion honored). Active stop label visible at rest ("Deep"); expands to all
    three on hover/focus. No dotted rail, no dot-touching-pill — that artifact dies.
  - **ASK/AUTO** moves into the + menu as an "Autonomy" row (it's a mode, not a
    per-message control). Agent/Delegate toggle likewise into the + menu.
- **Depth-keyed send**: armed send fill = `--color-depth-normal` (lume) / `--color-depth-deep`
  (peach) / `--color-depth-ultra` (ember) per active stop; icon color flips for contrast;
  the active depth stop in the selector carries the same token. While streaming at a depth,
  the stop morph keeps the depth color (the live pulse stays, revalued to the token).
- Narrow widths: the controls row collapses (model text → icon, depth → active-stop-only)
  via a measured ladder; nothing overlaps down to the 280px dock floor. Test-pin the ladder.

## C2 — Transcript + brief reading surfaces

- Transcript proportions to the law: body-13 in dock, user message in a quiet container
  (no size delta), 16px block rhythm, step traces behind the tertiary disclosure as today.
- Brief panel (brief-blocks.tsx): prose-16 only ≥420px column (downshift below), metric
  cards on the grid, table parse intact.
- **Keyless-fallback nudge banner** (gate 2): when the published brief's backend id is
  `keyless-fallback`, render one quiet banner: "Limited keyless search — set up Unlimited
  local research for full capability" linking to Settings→Research (palette command or
  panel-open). Honest, dismissible per-brief, never on searxng/research-model backends.
  (Team A guarantees the id; build against a fixture brief.)

## C3 — Stray-item audit (your partition)

Every control in chat/research modules either works perfectly and earns its place, or
dies. Append kills to `verification/R9_DEFECT_CATALOGUE.md` kill list with one-liners.

## Gates (in-worktree)

vitest green (yours + suite), `node scripts/audit-design-tokens.mjs` CLEAN on your files
(zero violations — you are rebuilding, no excuses), lint+format+typecheck. Visual
self-check: run `pnpm dev -- --port 5174`, capture composer states (rest, armed at each
depth, streaming, queued, narrow 320px dock) with headless Chrome
(`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --screenshot=…
--window-size=…`), save to `docs/redesign/verification/r9/composer/` IN YOUR WORKTREE and
compare against the reference yourself ruthlessly before declaring done — the lead's
fresh-context verifier will reject anything off-reference. Write
`docs/redesign/R9_TRACK_COMPOSER_REPORT.md`.
