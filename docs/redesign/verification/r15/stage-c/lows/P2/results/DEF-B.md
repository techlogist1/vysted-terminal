# R15 deferred-lows batch B — WRITER (Sonnet)

Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
Branch: worktree-agent-lows-DEF-B-4c6dfe8
IDs: R15-CROSS-PLATFORM-012, R15-UI-068, R15-UI-071, R15-UI-073, R15-UI-082

All 5 entries resolved. Outcomes: 4 fixed_untested (R15-CROSS-PLATFORM-012,
R15-UI-082, R15-UI-071, R15-UI-073) plus R15-UI-068 split fixed_untested
(primitive) / deferred_feature (porting 5 hand-rolled tables, ~4-day
estimate, nothing built for that half). No could_not, tier4, or
class_limitation outcomes this batch.

Off-lane rule in force throughout: no pytest/vitest/cargo/pnpm ci-local/tsc/
project-wide eslint were run. Every change below is untested pending
integration (py_compile + ruff + prettier only on touched files; acceptance
tests are written as source, never executed).

## R15-CROSS-PLATFORM-012 — fixed_untested

- Added `config.get_cache_dir()` (`CACHE_DIR_ENV=VYSTED_CACHE_DIR`, falls back
  to `get_data_dir()` when unset).
- `sidecar/main.py`: new `--cache-dir` CLI arg threaded to the env var.
- `src-tauri/src/lib.rs`: new `resolve_cache_dir()` using
  `app.path().app_local_data_dir()` (non-roaming on Windows); passed as
  `--cache-dir` alongside `--data-dir` when spawning the sidecar. Rust change
  is untested (never cargo per the off-lane rule) but written with care,
  mirroring the existing `resolve_data_dir` pattern exactly.
- `data_cache.py`, `fundamentals_store.py`, `searxng_manager.py` now resolve
  their DB/config paths under `get_cache_dir()` instead of `get_data_dir()`.
  User state (portfolio, notes, workspaces, audit log) is untouched.
- No migration of pre-existing cache files at the old path (fix_shape: "cheap
  now, a migration later" — explicitly deferred by the entry itself).
- Commit: b0e27eb2
- Test: `sidecar/tests/test_cache_dir.py` (3 cases: env-var used when set,
  falls back to data-dir when unset, the two diverge when both are set).
- Files: sidecar/config.py, sidecar/main.py, sidecar/services/data_cache.py,
  sidecar/services/fundamentals_store.py, sidecar/services/searxng_manager.py,
  sidecar/tests/test_cache_dir.py, src-tauri/src/lib.rs

## R15-UI-082 — fixed_untested

Original defect (sidecar's 400 detail discarded) was already fixed at the
triage sha — confirmed by reading `src/lib/workspace.ts` `sidecarFailure`,
which already surfaces `body.detail`. Fixed the residual polish the triage
note called out:

- `workspace_store.py` `_filename_stem`: now percent-encodes only path
  separators, Windows-reserved punctuation (`\ / : * ? " < > |`), control
  characters/NUL and literal `.` (still needed to keep dot-segments like
  `..` out of the stem). Every other Unicode character — including
  non-Latin scripts — is kept as its raw UTF-8 bytes. The `_MAX_STEM_BYTES`
  cap (200, unchanged) is now measured in encoded UTF-8 bytes, not code
  points, so a 32-character Devanagari name (86 bytes) no longer trips
  "too long" the way it did at ~9 encoded bytes/character.
- `SettingsPanel.tsx`: added `maxLength={200}` and a `title` hint on the
  layout-name input ("Up to 200 bytes when saved — shorter for non-Latin
  scripts.").
- Commit: 6afc62b5
- Test: `sidecar/tests/test_workspace.py` — added
  `test_a_32_char_devanagari_name_saves` and
  `test_a_name_whose_encoded_bytes_exceed_the_cap_is_still_rejected`.
- Files: sidecar/services/workspace_store.py, sidecar/tests/test_workspace.py,
  src/components/SettingsPanel.tsx

## R15-UI-073 — fixed_untested

Added `--color-caution` to `styles/tokens.css` (same hex as `--color-warning`
today — no visual change, purely a semantic split so the two tokens can
diverge later). Re-classed every non-data-provenance use of
`text-warning`/`bg-warning`/`border-warning` to `-caution` across 9 files
(StatusChrome, SettingsPanel ×8 sites, OnboardingFlow, PluginManagerPanel ×3,
ScreenerPanel ×1 of 3, AgentsRail ×3, ModelControl ×4, FilingsListTable,
MarketplacePanel ×2). Left `text-warning` on the 10 files that render an
actual data-provenance/freshness/completeness signal: DataBadges(+test),
BriefPanel, brief-blocks, ScreenerPanel (PARTIAL badge + throttle notice),
ScreenerResultsTable, ChartPanel, BacktestResultView, PortfolioPanel,
EquityOverviewPanel.

Also fixed the two color-only uses the entry named in AgentsRail: the
run-status dot went from `aria-hidden` to `role="img"` +
`aria-label`/`title` (Paused/Planned/Running/Failed), and the budget bar
became a real `role="progressbar"` with `aria-valuenow`/min/max instead of a
bare `aria-hidden` div.

Classification judgment call (Tier 3, DNA-derived — data-first, no operator
sign-off needed): "data provenance" = signals about the freshness/
completeness/reliability of MARKET DATA shown in a panel; everything else
(infra health, plugin/run lifecycle, config nags, generic form validation,
categorical coloring) is "caution". Recorded in the token comments and the
pinning test's own doc comment so the next writer can revisit the line if
they disagree.

- Commit: f791982d
- Test: `src/lib/warning-token-scope.test.ts` (new) — greps every non-test
  .ts/.tsx file under src/ and fails if any file outside the provenance
  allowlist uses text/bg/border-warning; also asserts the allowlist files
  still use the token (catches allowlist rot) and that both tokens exist in
  tokens.css.
- Files: styles/tokens.css, src/components/StatusChrome.tsx,
  src/components/SettingsPanel.tsx, src/components/OnboardingFlow.tsx,
  src/components/PluginManagerPanel.tsx, src/modules/screener/ScreenerPanel.tsx,
  src/modules/chat/AgentsRail.tsx, src/modules/chat/ModelControl.tsx,
  src/modules/sec/FilingsListTable.tsx, src/modules/marketplace/MarketplacePanel.tsx,
  src/lib/warning-token-scope.test.ts (new)

## R15-UI-071 — fixed_untested

Register evidence was a naive grep ("74/76 `<input>`s missing id/name") that
doesn't account for `aria-label` — checked all 4 `<input>`s in the one file
in scope (`SettingsPanel.tsx`, lines ~329/1082/1779/2113) and every one
already has an accessible name via `aria-label` (one also has `id`). This
matches the refuter's own `admitted_with_correction` note. The actual gap is
that nothing gates this automatically, so a future input could still ship
unlabelled. Fixed the gap, not a phantom labelling bug:

- `package.json`: added `eslint-plugin-jsx-a11y` (lint-time) and
  `vitest-axe` (runtime, in the same test file that already renders
  `SettingsPanel`).
- `eslint.config.mjs`: registered the plugin and enabled only
  `jsx-a11y/label-has-associated-control` (`assert: "either"`) — not the
  full `recommended` bundle, which spans unrelated concerns (alt-text,
  anchor validity, media captions, …) never audited across the ~39 files
  the low cites; widening the rule set is a follow-up, not this fix.
- `src/components/SettingsPanel.test.tsx`: added an axe smoke test on the
  panel's default (Preferences) render.
- Commit: 730d482e
- Test: the new axe assertion in `SettingsPanel.test.tsx` (`expect(await
  axe(container)).toHaveNoViolations()`) plus the new ESLint rule itself
  (a lint-time gate is its own regression test — any future unlabelled
  input in a `.ts`/`.tsx` file now fails `pnpm lint`, never run here per
  the off-lane rule).
- Files: package.json, eslint.config.mjs, src/components/SettingsPanel.test.tsx

## R15-UI-068 — split: fixed_untested (primitive) + deferred_feature (porting)

This low bundles two distinct root causes; splitting them rather than
under- or over-delivering against either:

**(a) `DataTable.tsx` primitive — fixed_untested.** The shared primitive put
`onClick` on a `<th>`, which is never keyboard-reachable (no tab stop, no
Enter/Space handling) — every sortable column across the app that renders
through it inherited the gap. Moved the handler into a nested
`<button type="button">` (natively focusable, fires for both Enter and
Space with no extra key code); `aria-sort` stays on the `<th>` per the
WAI-ARIA sortable-table pattern. Added `loading?: { rows }` (renders
`rows` `aria-hidden` skeleton rows, marks the table `aria-busy`) and
`empty?: ReactNode` (renders a single centered row when there are zero
rows/sections and not loading) — both opt-in, so every existing caller of
`DataTable` is unaffected. The existing sort test asserted a click on the
bare `<th>`; updated it to click the new button (the interaction target
moved, not weakened — `aria-sort`-on-`<th>` is still asserted) and added
three new tests for keyboard focus+activation, the loading-skeleton
render, and the empty-slot render.
  - Commit: 451a91f7
  - Test: `src/components/DataTable.test.tsx` — new cases "makes a
    sortable header keyboard-operable", "renders skeleton rows and marks
    the table busy when loading", "renders the empty slot when there are
    zero rows and not loading"; existing sort test updated to target the
    button.
  - Files: src/components/DataTable.tsx, src/components/DataTable.test.tsx

**(b) Porting the 5 hand-rolled tables — deferred_feature.** The register
names 6 files as bypassing `DataTable`; `src/modules/safety/
AuditLogViewer.tsx` does not exist at this base (`docs/redesign/verification/
vysted-r15-register.json` evidence line for it is stale) — confirmed via
`find`/`grep` across the whole tree, only `DisclaimerFlow.tsx` exists under
`src/modules/safety/`. The other 5 are real and confirmed still hand-rolling
a bare `<table>` at this base:
  - `src/modules/screener/ScreenerResultsTable.tsx` (576 lines, 354-line
    existing test suite)
  - `src/modules/watchlist/WatchlistPanel.tsx` (572 lines, 321-line
    existing test suite)
  - `src/modules/earnings/EarningsCalendarPanel.tsx` (577 lines, 319-line
    existing test suite; two hand-rolled `<table>`s)
  - `src/modules/backtest/BacktestResultView.tsx` (575 lines, no existing
    test file)
  - `src/modules/research/brief-blocks.tsx` (1094 lines, no existing test
    file; the hand-rolled table renders parsed markdown, not row objects)

Porting each means re-deriving its column set, sort/selection/click
behaviour, per-cell custom renderers (badges, sparklines, colour-coded
deltas, provenance chips) and section grouping into `DataColumn`/`DataSection`
shape without changing any visible behaviour, then re-verifying against (or
rewriting) the 3 existing 300+ line test suites — none of which can be run
under the off-lane rule, so a port done blind is a real regression risk
across widely-used panels (screener, watchlist, earnings, backtest, research
brief), not a bounded low-severity diff. Estimate: 1 focused day per table
for the 3 with existing suites (re-verify test-by-test against the ported
render), a half-day each for the 2 without (write the port + a new baseline
test), so **~4 days total**, plus a review pass — this is a feature-sized
port, not a fix, per the entry's own fix_shape ("port the plain survivors"
was one clause in a larger primitive-extension low, not a scoped diff).
Building nothing for this half; no files touched.

## Not built in this half of R15-UI-068
- No changes to ScreenerResultsTable.tsx, WatchlistPanel.tsx,
  EarningsCalendarPanel.tsx, BacktestResultView.tsx, brief-blocks.tsx.
