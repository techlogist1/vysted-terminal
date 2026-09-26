# R15 deferred-lows batch B — WRITER (Sonnet)

Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
Branch: worktree-agent-lows-DEF-B-4c6dfe8
IDs: R15-CROSS-PLATFORM-012, R15-UI-068, R15-UI-071, R15-UI-073, R15-UI-082

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

## R15-UI-071 — in progress

## R15-UI-068 — not started
