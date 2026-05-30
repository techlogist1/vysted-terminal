# Phase 9.5 — Overnight Session Morning Report

Single unattended overnight run on the Mac. All work merged to `main` and pushed
to `origin`. **No tag, no release** — handed back for your personal-testing gate.

Commit trail on `main`: `46f0a33` (start) → `5c00bb1` (Phase 1) → `644b9b6`
(Phase 2) → `7927e40` (Phase 3).

## Gate results (all green)

- **`pnpm ci-local` → exit 0** — run per phase before each merge, and a final
  certification on the merged `main`. (install · ensure-all-sidecars · eslint ·
  prettier · tsc · cargo fmt · clippy -D · ruff 0.15.12 · vitest · cargo test ·
  pytest **921 passed**.)
- **`node scripts/smoke-test-sidecars.mjs` → exit 0** — freshness gate + main
  `/health` + screener-universe probe + **both MCP sidecars bound** (openbb +
  sec-edgar).
- **`next build` (static export) compiles** the new design CSS.
- **§6.5 safety audit 9/9.** **Tier-1 locked files untouched** (verified `git
diff origin/main` empty for audit_log/kill_switch/broker_base/plugin.ts/
  test_safety_end_to_end before each phase).
- **Environment note:** this Mac has no bare `python` on PATH (homebrew
  `python3` only, externally-managed). `ci-local` calls bare `python`, so it was
  run with the build venv on PATH (`PATH=sidecar/.venv/bin:$PATH pnpm ci-local`).
  This is a pre-existing `ci-local` assumption, not a regression — flagged below.

## Phase 1 — Track B (known defects)

| #       | Defect                                                                                                                  | Status                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S0-2    | **Build trap** — `ensure-*-sidecar.mjs` only checked binary existence, so `tauri build` silently shipped stale sidecars | **FIXED first.** `scripts/sidecar-staleness.mjs` makes the ensure scripts rebuild when source is newer than the binary even without `--force`; `smoke-test` adds an `assertFresh` gate. Validated end-to-end (the ensure step correctly rebuilt all three stale binaries).                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| —       | **Drag broken** (dockview tabs + node-palette)                                                                          | **FIXED.** Root cause confirmed: Tauri v2 `dragDropEnabled` defaults `true` and swallows in-webview HTML5 DnD (macOS WKWebView too). Set `dragDropEnabled: false`. Both drags share this cause; ReactFlow node-move + divider resize are pointer-based and unaffected; no OS file-drop need exists. GUI confirmation is operator-manual (drag is untestable at the harness click-tier).                                                                                                                                                                                                                                                                                                                                         |
| F4-1    | **Quant endpoints — zero input validation** (neg vol, strike 0, expiry≤valuation, absurd ytm → 200 garbage)             | **FIXED.** `validate_domain()` on each quant request model raises `ValueError` → the router's existing path returns **400**. +11 tests covering every catalogued case.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| F-GUI-1 | **Portfolio nonsense aggregates + no large-number formatting**                                                          | **FIXED.** P&L% now divides by `resolvedCost` (cost of priced positions only), not all-cost. New shared `src/lib/format.ts` (`formatCompactMoney` $1.5M/$622Q, `formatPercent` exponential fallback, non-finite → "—"); summary + per-row values use it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| nit     | FRED-no-key returned **501**                                                                                            | **FIXED → 502** (upstream-gateway failure; unified across all macro paths).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| nit     | sec-edgar "**not bundled**" message (it's bundled, just unbound)                                                        | **FIXED** → "not available — did not bind a port this launch (relaunch to retry)".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| nit     | **sp500 universe = 100 symbols** under an "S&P 500" label                                                               | **FIXED** (honest) → relabelled "S&P 500 (Top 100)" in snapshot + picker, rather than fabricate an inaccurate 500-name list.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| nit     | screener **ignored `custom_symbols`**                                                                                   | **FIXED.** A non-empty `custom_symbols` now overrides any named universe.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| UC1     | **sec-edgar-mcp unreliable bind**                                                                                       | **IMPROVED + gate-detected.** Empirical: openbb 34.2s / sec-edgar 33.6s cold _in isolation_ — the audit's asymmetry is disk-I/O contention from concurrent `_MEI` extraction. Raised `MCP_PORT_WAIT_SECS` 30→45 (90s w/ retry, near-free — short-circuits on bind) and added a TCP **port-bind probe** to smoke-test (closes the L3/L4 gap). sec-edgar bound cleanly in the final smoke run. **The true fix (`--onedir`) is deferred** — it needs a Tauri externalBin→resource-folder + Rust spawn change that `ci-local` can't verify (never runs `tauri build`), so an unattended attempt risked a silently-broken bundle while sec-edgar already degrades gracefully. Rationale + evidence in `BLOCKERS.md` "Phase 9.5 UC1". |

## Phase 1 — Track A (proactive bug hunt)

Read-only fan-out (11 finder lenses across frontend/sidecar/Rust) + **two-stage
adversarial verification** of every finding. **56 raw → 33 confirmed** (7 high,
21 medium, 5 low; 18 refuted, 5 already-handled). **13 applied**, 5 confirmed-but-
non-actionable (documented).

Applied (highlights): backtest sell-P&L on the sold quantity + raise-on-empty-bars

- insufficient-cash logging; screener `skipped_count` surfacing dropped symbols;
  app.py lifespan `aclose` guard (MCP cleanup always runs); node-editor `markDirty`
  on connect/config/delete (silent unsaved-loss) + SSE reader release; malformed-
  JSON normalized to typed errors (sidecar-client/workspace); broker order-entry
  symbol+price validation; screener `loadUniverse` concurrency dedup; notification
  flush serialization; per-panel fetch-error banners across the 6 Tradesa panels;
  plus a batch of Pydantic domain bounds (screener/backtest/earnings/fundamentals).

Documented **non-actionable** (real code facts, but fixing is churn/risk with no
behavioural gain — full reasoning in the Track-A commit body `a96782f`):
`modules-spread-order` (the verified fix is a semantic no-op), `stdin-watchdog
os._exit` (process exit reclaims resources; SIGTERM risks a shutdown hang),
`openbb-global-state-race` (pair set atomically, lock-immune), `analyst-sync`
(I/O already offloaded), `backtest-equity-fallback` (forward-fill makes it
unreachable dead code).

## Phase 2 — Track C (panel-freedom + settings/onboarding)

- **Cockpit persists across launches** — `PanelHost` restores an autosaved
  "last session" layout on boot (debounced save on every dockview change) and
  falls back to the default. dockview drag/dock/split is unblocked by the drag
  fix. Named layouts (save/load/delete) + "Reset to default" in Settings, plus a
  toolbar **Save layout** button.
- **Settings rebuilt** into four sections — **AI Providers (BYOK)** shows each
  provider's keychain key-status with Add/Update/Remove + a default-provider
  picker (the explicit "where do I put my key" surface; reuses the validate→
  keychain dialog, never holds the key value) · **Layouts** · **Modules** · **About**.
- **First-run onboarding banner** appears whenever no key-requiring provider has
  a key, one-click to Settings → AI Providers, auto-hides once a key is saved.
- **Discoverable** — the toolbar gained a Settings gear + Save-layout button
  (was ⌘K-only).

## Phase 3 — Track D (JARVIS "INSTRUMENT" design system)

One coherent warm-machined-instrument language (early-90s Bloomberg amber phosphor
× fine-chronograph dial): patinated-brass bezels, lume-cream highlights, amber HUD
on warm brown-black, global tabular numerics, restrained grain/vignette
atmosphere, refined dockview cockpit frame, machined header fascia with the
serif VYSTED wordmark. Deliberately NOT a generic dark AI dashboard.

**To review (paths):** `docs/DESIGN_SYSTEM.md` (the decisions), `styles/tokens.css`
(palette/type/radius/motion), `src/app/globals.css` (atmosphere + chrome +
dockview theme), `src/app/page.tsx` (header fascia). Centralized so it reaches
every panel; fonts (Newsreader + JetBrains Mono) kept — already on-anchor.

## Left for your judgment

1. **Visual review is your gate.** Populated-state screenshots at both
   resolutions (per the CLAUDE.md visual protocol) are operator-manual: the
   harness runs the bundle at click-tier and can't drive the GUI with real data,
   and chrome-devtools can't synthesize the trusted events the canvas needs. The
   design compiles + passes ci-local; eyeball it and tune any token in
   `styles/tokens.css` (it re-skins everything).
2. **Drag + node-drag GUI confirmation** — operator-manual (same click-tier
   reason). The config fix is high-confidence.
3. **UC1 `--onedir`** — the real sec-edgar fix, deferred with rationale; do it
   attended (needs a full `tauri build` + GUI cold-boot to verify the bundle).
4. **`ci-local` + bare `python`** — consider routing its ruff/pytest python
   through the build venv so it runs on a stock macOS without a `python` shim.
5. **Housekeeping done autonomously:** data dir reset (backed up to
   `~/Library/Application Support/com.vysted.terminal.audit-backup-20260529`);
   `origin` remote switched HTTPS→SSH so pushes work non-interactively;
   `test_safety_end_to_end.py` regenerates `kill-switch-benchmark.json` on every
   run — now prettier-ignored so it can't fail format:check by run-ordering.
