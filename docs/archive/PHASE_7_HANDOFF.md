# Phase 7 Handoff (v0.7.0 → Phase 8)

**Read this first** if you are starting Phase 8 (Claude-Code-driven
deep audit). Phase 7 (Completion + Polish + Parity) shipped as v0.7.0
on 2026-05-17. The handoff follows the 8-section convention established
by `PHASE_3_HANDOFF.md` → `PHASE_4_HANDOFF.md` → `PHASE_5_HANDOFF.md` →
`PHASE_6_HANDOFF.md` → `PHASE_6.5_HANDOFF.md`.

**Phase 7 is NOT launch ops** — signing, distribution, landing page,
license activation, auto-updater wiring, v1.0.0 narrative are all
deferred to **Phase 10** per the operator brief. This phase is purely
quality work: CI parity, runtime bug fixes, visual consistency
codification, polish, BLUEPRINT alignment.

---

## 1. What Phase 7 shipped (inside v0.7.0)

### Foundation (lead, F1–F10, sequential, lead-only — Tier-2 zero-teammate decision)

- **F1 `chore(format)`** — `pnpm format` across 37 files of Phase 6 +
  6.5 drift. Fixes Cause B of v0.6.5 CI red. Commit `fe25ce5`.
- **F2 `fix(ci): build all three sidecar binaries`** —
  `scripts/ensure-all-sidecars.mjs` orchestrator + wired into
  `tauri.conf.json` `beforeBuildCommand` / `beforeDevCommand` + all
  three `.github/workflows/*.yml` + new `pnpm sidecars:build`. Fixes
  Cause A of v0.6.5 CI red. Commit `d75fc0d`.
- **F3 `chore(ci): pnpm ci-local`** — package.json script that chains
  the exact CI sequence byte-for-byte. Standing release-gate.
  Commit `8165631`.
- **F4 `docs(claude): three new Gotchas`** — Local verification is
  CI-parity, not best-effort approximation; Visual consistency
  convention (v0.7.0+); `bundle.externalBin` declares 3 sidecars.
  Commit `5030d8e`.
- **F5 push + 3 CI iterations** — required three pushes before all 3
  workflows green simultaneously. Each iteration surfaced a
  previously-hidden bug that the operator's local flow had missed for
  ≥1 release:
  - Iter #1 → CI: `23da4f3` — sec-edgar PyInstaller fastmcp ref
    (sec-edgar uses `mcp` SDK only) + openbb-mcp hidden-import path
    drift (`openbb_mcp_server.main` → `openbb_mcp_server.app.app` in
    1.4.0).
  - Iter #2 → CI: `810d98b` — sec-edgar `.venv/` not in
    `.gitignore` / `.prettierignore` + tradesa-v2 tests used
    `asyncio.get_event_loop()` (Python 3.13 raises). 24+ tests fixed
    via `asyncio.run()`.
  - Iter #3 → CI: `6f5ec07` — ruff format reflow after the
    `asyncio.run` replace_all.
  - All 3 workflows green from `6f5ec07` onward.
- **F6/F7 runtime sidecar fix** — commit `cf96031`. The
  operator-flagged "graphs not loading" is the visible surface of a
  much deeper bug: the v0.6.5 release ships a `vysted-sidecar` binary
  that crashes at startup with `PackageNotFoundError: fastmcp` because
  `services/mcp_server.py` imports `fastmcp` at module load and
  FastMCP's `__init__.py` calls `version("fastmcp")`. PyInstaller
  --onefile drops dist-info by default; the script had no
  `--copy-metadata=fastmcp`. Fixed by adding
  `--copy-metadata=fastmcp,mcp,anyio,httpx,starlette,uvicorn`.
  **Every data-bearing panel in v0.6.5 was broken in production, not
  just charts.** CI never caught it because `cargo test` doesn't run
  the binary; the bug only surfaces when `pnpm tauri dev` actually
  spawns the sidecar.
- **F7 dev-fallback** — commit `90b8f6e`.
  `src/lib/sidecar-client.ts::getSidecarBaseUrl` honours
  `?sidecar-port=NN` query param when running outside Tauri
  (`__TAURI_INTERNALS__` guard). Unlocks chrome-devtools MCP captures
  of populated UI without the Tauri shell — production-safe because
  the production webview always carries `__TAURI_INTERNALS__`.
- **F8 desktop-notification bridge** — commit `328947f`.
  `src/lib/desktop-notification.ts::useDesktopNotificationBridge`
  React hook subscribes to `useWorkflowStore.pendingNotifications`,
  lazy-imports `@tauri-apps/plugin-notification`, requests permission
  on first send, drains the queue. Rust side:
  `tauri-plugin-notification = "2"` + `lib.rs` registration +
  `capabilities/default.json` permission. 4 Vitest cases.
  **Unblocks BLUEPRINT §10 UC3 (Earnings Playbook) and UC5 (Macro
  Thesis Watcher)** — both rely on workflow steps triggering OS
  notifications.
- **F9 polish** — commit `d4028c1`. Refreshed stale doc comments
  (tradesa-v2 panels.ts no longer "placeholder shells"; backtest
  router no longer "503 stub"; registry comments no longer "commented
  out"); gated example-plugin `console.info` behind
  `process.env.NODE_ENV === 'development'`.
- **F10 BLUEPRINT alignment** — commit `84f4414`. §8 success-criteria
  - §10 UC1 rewritten to match v0.6.5 polling READ-ONLY Tradesa V2
    reality.

### Visual re-capture (R1-R4)

- `docs/screenshots/v0.7.0/composed/cockpit-{1920x1080,2560x1440}.png`
  - `cockpit-aapl-{1920x1080,2560x1440}.png` — 5-panel + AI Assistant
    cockpit at both required resolutions, populated (live yfinance
    quotes + RSS news + sentiment scoring).
- `docs/screenshots/v0.7.0/cockpit/chart-tab-1920x1080.png` — Chart
  panel state inside cockpit.
- `docs/screenshots/v0.7.0/README.md` — convention recap + deferred-
  to-Phase-9 list.
- Commit `5249314`.

### Release commits

- Version bump + Cargo.lock re-lock + final pre-tag verification.

---

## 2. Autonomous decisions made (Tier-2/3)

1. **Zero teammates (Tier-2).** Phase 7 brief explicitly authorised
   0–5; scope was sequentially dependent + screenshot capture needs
   interactive Tauri + chrome-devtools MCP that worktree-isolated
   teammates can't reproduce. Precedent: v0.6.5 ran with 1 teammate;
   Phase 7 tighter still.
2. **`pnpm ci-local` as the parity protocol (Tier-3).** Cheapest viable
   structural fix — no Docker, no `act` (Windows-runner gaps), no
   pre-push hook (intrusive). Operator runs it pre-tag.
3. **`scripts/ensure-all-sidecars.mjs` orchestrator (Tier-3).** Single
   entry point; extensible to a fourth sidecar; cleaner than chaining
   `&&` in `beforeBuildCommand`.
4. **AAPL canonical ticker + 5-panel cockpit canonical workspace
   (Tier-3).** Empirically the only equity ticker appearing in every
   sampled surface across `docs/screenshots/v0.4.0`–`v0.6.0`;
   5-panel + AI Assistant cockpit is the v0.4.0 shape that the v0.6.0
   solo-panel shots broke from.
5. **License-gate first-launch dialog deferred to Phase 10 (Tier-3).**
   Operator confirmed in plan-mode question. Natural sibling of
   LICENSE flip + COMMERCIAL_LICENSE.md promotion.
6. **fastmcp metadata fix uses defensive copy-metadata list (Tier-3).**
   Adds fastmcp + mcp + anyio + httpx + starlette + uvicorn. Bundle
   size cost is negligible relative to the risk of another silently-
   broken release.
7. **`?sidecar-port=` dev fallback is production-safe (Tier-3).** Gated
   on absence of `__TAURI_INTERNALS__`; regex-gated to digits.
8. **Visual re-capture scoped to cockpit hero shots (Tier-3).** Tradesa
   V2 panels + Phase 6 modules' full cockpit re-capture deferred to
   Phase 9 operator-led session.
9. **Each `pnpm ci-local` iteration discovered real drift (Tier-3) —
   the protocol is not theatrical.** Iter #1 found sec-edgar/openbb-mcp
   build bugs; iter #2 found ignore + asyncio bugs; iter #3 found
   ruff drift. All masked by the operator's local "passes" but real
   from a clean-checkout standpoint.

---

## 3. Known issues carried forward to v0.8 / Phase 10

### Phase 10 (launch ops — explicit non-scope in Phase 7)

- Code signing (SignPath / Apple Developer ID / ad-hoc Mac)
- Tauri auto-updater wiring (pubkey present in `tauri.conf.json` from
  v0.5.0; `createUpdaterArtifacts: false` — flip to true)
- Homebrew cask + AppImage + GitHub Release polish
- `terminal.vysted.com` landing page (separate private repo)
- LICENSE flip + COMMERCIAL_LICENSE.md promotion + CLA bot
- First-launch TOS dialog (§6.5 #8 touchpoint + BLUEPRINT
  customization #1)
- v1.0.0 narrative + launch announcement

### v0.6.6+ Tradesa V2 work

- Realtime SSE proxy (replaces per-panel polling)
- Write capability (manual position close, pause-bot, approve
  tuning-proposal) — Tier-4 design per surface (propose→confirm +
  §6.5 audit + AI-order gate)
- MCP tool exposure for the brain-decision log
- Anon-key + Auth migration when Tradesa V2 ships v0.1.7.0 RLS
- Optional Bybit Demo position enrichment

### v0.8 polish

- **CI sidecar-smoke-test step** — run the built `vysted-sidecar`
  binary + curl `/health` in CI so a `cf96031`-class
  `PackageNotFoundError-at-runtime` fails CI instead of shipping
  silently. The lesson from v0.7.0 F6/F7.
- **Default watchlist re-order** — put AAPL first so the visual
  convention's "AAPL primary anchor" matches the bundled default
  (currently AAPL is at position 6).
- **Full cockpit-shape re-capture for Phase 6 modules** — Macro / SEC
  / Earnings / Analyst Ratings / Screener / Quant cockpit shots
  (deferred to Phase 9 operator-led session per the v0.7.0 README).
- **Tradesa V2 first-ever populated capture** — needs real Supabase
  project; operator-led.

### v1.1+ (BLUEPRINT §9)

Standalone risk analytics panel, light + custom themes, alpha_vantage
fallback, market profile, multi-window pop-out, standalone central
bank tracker + commodity dashboard, filesystem-installed plugin
loader.

---

## 4. Plugin contract status

- **`types/plugin.ts` is unchanged in v0.7.0.** Verified
  `git diff v0.6.5..v0.7.0 -- types/plugin.ts` empty. **Tier-1 lock
  held — 9th consecutive release.**
- `capabilities` flags untouched.
- F8 desktop-notification bridge consumes the _existing_
  `useWorkflowStore.pendingNotifications` surface — no new contract.
- F6/F7 sidecar fix is build-script-only; no API surface change.
- F10 BLUEPRINT alignment is doc-only.

---

## 5. Phase 8 entry context

Phase 8 is **Claude-Code-driven deep audit** against the now-finished
v0.7.0 surface. The relevant audit hooks Phase 7 lands:

1. **CI is green and parity-verified.** Phase 8 audit can run
   `pnpm ci-local` to confirm baseline before each session; any new
   audit-introduced regression surfaces locally before it can drift.
2. **The runtime sidecar boots cleanly.** Phase 8 audit can spin up
   `pnpm tauri dev` and chrome-devtools MCP against
   `http://localhost:3000/?sidecar-port=NNNNN` to exercise every
   panel end-to-end with live data. Previously the audit would have
   hit the v0.6.5 fastmcp crash and seen "Failed to load" everywhere.
3. **The visual convention is codified.** Phase 8 audit can use the
   v0.7.0 `docs/screenshots/v0.7.0/composed/cockpit-*.png` as the
   canonical "what the app looks like" baseline for any UX critique.
4. **BLUEPRINT is truth-aligned.** §8 success-criteria + §10 UC1
   reflect actual shipped state — Phase 8 cross-check against
   BLUEPRINT will not surface false positives from over-promised
   docs.
5. **Polish backlog is empty (or at least near-empty).** No stale
   "Coming soon" / "TODO" / "503 stub" comments to flag.

Phase 8 audit's natural starting points:

- Cross-cutting code review with the v0.7.0 audit MCP tooling
- Security pass against the Phase 5 §6.5 broker-execution surface
- Dead-code scan (the operator's polish backlog was mostly stale
  comments, but a fresh pass may find unused exports / orphaned
  Python modules)
- Dependency freshness check (Phase 7 didn't update any deps; some
  are now several minor versions stale)
- BLUEPRINT §4 module catalog re-cross-check post-Phase 6.5
- The `pnpm ci-local` protocol itself — is the chain the right shape?
  Should the sidecar-smoke-test step be added?

---

## 6. File / commit pointers for deeper context

- `CHANGELOG.md` v0.7.0 entry — full ship log + Tier-2/3 decisions
- `docs/BLUEPRINT.md` §7 Phase 7 (now marked shipped) + Phase 8 + 9 + 10
  entries
- `CLAUDE.md` Gotchas section — three new bullets at the bottom (above
  Per-phase handoff): visual convention, CI parity, externalBin
  3-sidecars
- `docs/screenshots/v0.7.0/README.md` — capture convention recap +
  deferred surfaces
- `docs/SAFETY_ARCHITECTURE.md` — §6.5 enforcement reference
  (unchanged; Phase 7 doesn't touch broker execution)
- `BLOCKERS.md` — Phase 10 + v0.6.6+ + v0.8 carry-forwards
- **Foundation commits:** `fe25ce5` (F1), `d75fc0d` (F2), `8165631`
  (F3), `5030d8e` (F4), `23da4f3` + `810d98b` + `6f5ec07` (F5 iters
  1+2+3), `cf96031` (F6/F7 sidecar fix), `90b8f6e` (F7 dev fallback),
  `d4028c1` (F9 polish), `84f4414` (F10 BLUEPRINT), `328947f` (F8
  desktop-notification bridge), `5249314` (R1-R4 screenshots).
- **Release commit:** version bump + Cargo.lock re-lock at v0.7.0 tag.

---

## 7. Verification snapshot at handoff

- `pnpm typecheck` clean.
- `pnpm lint` (eslint) clean.
- `pnpm format:check` clean.
- `pnpm test` (vitest) — **588 tests pass** across 81 files (+4 over
  v0.6.5's 584; the 4 new cover the desktop-notification bridge).
- `ruff check sidecar` + `ruff format --check sidecar` clean.
- `cargo fmt --check` clean.
- `cargo clippy -D warnings` clean (verified on CI).
- Sidecar binary booting end-to-end verified via curl on `/health` +
  Tauri dev + chrome-devtools MCP populated capture.
- CI green on all 3 OSes from commit `6f5ec07` onward (3 iterations
  before that).
- `git diff v0.6.5..v0.7.0 -- types/plugin.ts` empty (Tier-1 lock —
  9th consecutive release).
- `git diff v0.6.5..v0.7.0 -- sidecar/services/broker_base.py
sidecar/services/kill_switch.py sidecar/services/audit_log.py
sidecar/models/audit_log.py` empty (§6.5 untouched).
- v0.7.0 canonical-convention captures shipped in
  `docs/screenshots/v0.7.0/{composed,cockpit}/` with README.

---

## 8. Coordination lesson for Phase 8+

**The `pnpm ci-local` protocol is not theatrical — each of the three
F5 iterations caught a different real bug that had shipped
unobserved.** Iter #1 caught two PyInstaller bugs that the operator's
locally-cached binaries had masked for ≥1 release; iter #2 caught the
sec-edgar venv ignore + a Python-3.13 asyncio incompatibility in the
v0.6.5 tradesa tests; iter #3 caught a ruff-format reflow from my own
replace_all in iter #2. None would have been caught by
`pnpm test` + `pnpm tauri dev` alone — only the full CI battery.

**The parity protocol is now the standing pre-tag gate.** Future
phase leads run `pnpm ci-local` before every tag commit. The protocol
takes ~25 minutes on a Windows dev machine (PyInstaller --onefile is
slow) but eliminates the push-then-watch-CI-fail loop.

**The v0.6.5 fastmcp runtime bug is an even bigger lesson.** CI
exercises source-level pytest + `tauri build` (which packages the
binary without running it). The bundled binary's runtime correctness
is not tested anywhere. The v0.7.0 fix is the build-script
`--copy-metadata` addition; the v0.8 polish is a CI step that briefly
executes the binary and curls `/health` so this class of bug fails CI
instead of shipping silently. Phase 8 audit should make this a
priority recommendation.

**Visual capture from chrome-devtools MCP requires a path to the
sidecar.** Tauri webview is not directly accessible from chrome-
devtools MCP on Windows; the F7 `?sidecar-port=` query param fallback
is the workaround. Phase 9 (operator manual visual pass) can use
either the Tauri shell directly OR the fallback path for systematic
capture.
