# R10 Track FRONTEND-DATA — screener streaming UI, saved screens, store seams

Branch: `worktree-agent-r10-fedata`. Read first: `verification/R10_DEFECT_CATALOGUE.md`
(E4 UI leg), DECISIONS D40, the contracts commit (types/screener.ts: new universe ids,
partial/coverage/freshness, ScreenerProgressFrame), `R9_DESIGN_SYSTEM.md` (visual law).

## Files you own (exclusive)

`src/store/screener.ts`, `src/modules/screener/**` (EXCEPT the UNIVERSE_LABELS
constant already updated in the contracts commit — extend freely beyond it),
`src/store/notes.ts`, `src/store/portfolios.ts` (or the portfolio client module —
whatever the panel uses), `src/modules/portfolio/**`, and their vitest files.
Do NOT touch host-actions.ts / brief / chat (Team FRONTEND-BRIEF), marketplace/
keychain (Team ERRORS), types/* (frozen), sidecar.

## 1. Streaming screener run — `src/store/screener.ts`

`runScreener` switches to `POST /screener/run/stream` with a fetch ReadableStream
reader: progress frames → `progress: {phase, done, total, detail} | null` state;
final `{"event":"result"}` frame → results. AbortController-based `cancelRun()`
(disconnect cancels server-side — Team SCREENER's contract). Keep a unary fallback
when the stream endpoint 404s (older sidecar). Surface `partial`, `coverage`,
`freshness` on the result state.

## 2. Saved screens + formula

- `savedScreens: {name, criteria, group, formula, universe}[]` persisted via the
  WORKSPACE BLOB rule (CLAUDE.md): add to serializeWorkspace/deserializeWorkspace —
  COORDINATION EXCEPTION: workspace.ts belongs to Team FRONTEND-BRIEF. To stay
  disjoint, persist savedScreens in the screener store via a store-level
  subscription registered in src/app/page.tsx ONLY IF page.tsx is free — it is NOT
  in any team's list, so: implement `saveScreen/deleteScreen/loadScreen` in the
  store with serialization helpers EXPORTED, and add a `// R10-INTEGRATION:` note in
  your report — the LEAD wires the two workspace.ts lines at merge. Build your tests
  against the store API directly.
- `applyFilters` gains `formula?: string` (sets the formula instead of clearing) and
  optional `run?: boolean` consumed by the host-action path (Team FRONTEND-BRIEF
  calls `useScreenerStore.getState().applyFilters(...)` then `runScreener()` when
  run=true — keep those store methods stable).

## 3. Panel — `src/modules/screener/`

- Universe picker shows the three India universes (labels exist).
- Progress treatment per the R9 law: a caption-13 progress line ("sweeping quotes
  850/2,100") + a quiet determinate bar (zinc-700 track, lume fill, 2px), Cancel
  button while running (morphs from Run). NO spinner-forever: progress is honest or
  the run errors honestly.
- Results header: coverage line + "PARTIAL" micro-11 badge when partial, freshness
  ("quotes 4m ago · deep fields 2d ago") as caption muted.
- Saved-screens strip: save current (name prompt inline, not a modal), load, delete.
- Formula box: paste-a-formula UX already exists from R7 — make sure it round-trips
  with saved screens and the caret-error rendering still works.

## 4. Notes + portfolio seams (for the agent write actions)

- `src/store/notes.ts`: ensure `setGeneral/setSymbolNote` cover append mode (add
  `appendGeneral/appendSymbolNote` if missing) — Team FRONTEND-BRIEF's write_note
  apply case calls these.
- Portfolio: verify the panel's manual-entry/edit/delete path against the sidecar
  routes (POST/PUT/DELETE /portfolio/positions) actually works (E6 said the agent
  couldn't write; the PANEL's own entry affordance must exist and work — if it is
  missing or vestigial, BUILD the minimal honest version: an "Add position" row form
  per the R9 forms law, h-8 controls). Export a typed client
  (`addPosition/updatePosition/deletePosition/refresh`) from the store for the
  host-action apply path.

## Gates before you push

pnpm lint/typecheck/format:check, FULL vitest green. Granular commits, push at each
green milestone.
