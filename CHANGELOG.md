# Changelog

Engineering log for Vysted Terminal — build-time decisions, failed approaches,
and per-phase outcomes. This is the _why_ record. Current-state docs live in
`CLAUDE.md` and `docs/BLUEPRINT.md`; this file is append-only history.

## Scope update — global broker execution in v1.0 (2026-05-14)

**Docs-only.** No code changed — `types/plugin.ts` and every other source file are
untouched. The existing plugin contract already supports broker plugins via
`getDataSources` / `getPanels` / `executeCommand`. This entry records a scope
decision taken between Phase 0 and Phase 1.

### Decision

Broker integrations move from the v1.1/v2.0 deferred lists into v1.0 with full
execution capability. Vysted Terminal is an open-source platform from day one, and
its value proposition — see your portfolio, analyze it with AI, execute — is
incomplete without the execute step. A read-only-only v1.0 ships a thinner product
than the positioning promises. Execution belongs in the first release.

### Scope

- Six broker plugins plus a ccxt crypto execution wrap (seven broker integrations
  total): Dhan, Angel One SmartAPI, Zerodha Kite Connect, Alpaca, Interactive
  Brokers, OANDA v20, and ccxt for crypto. Each is a separate plugin on the existing
  `VystedPlugin` contract.
- A shared execution safety layer is baked in, not optional — paper-mode default,
  per-order confirmation, configurable position-size limits, a local SQLite audit
  log, a global kill switch, an extra gate on AI-initiated orders, per-plugin
  read-only mode, and layered liability disclaimers. Full design in
  `docs/BLUEPRINT.md` §6.5.
- Phase 5 absorbs this: its estimate grows from ~3-5 days (Tradesa V2 alone) to
  ~6-8 days (Tradesa V2 + broker integration + safety layer). The phase is not split
  and the numbering is unchanged. The v1.0 calendar target still holds at the
  operator's 2-3 sessions/day velocity.

### Research corrections

The broker landscape was verified by web search this session. Four corrections to
earlier assumptions, recorded as historical decisions:

- **IBKR Python SDK is `ib_async`, not `ib_insync`.** `ib_insync` was forked to the
  `ib-api-reloaded` org and renamed `ib_async` after the original maintainer, Ewald
  de Wit, passed away in early 2024. `ib_async` (current v2.1.0) is the active
  library; use it going forward.
- **Zerodha Kite Connect pricing is ₹500/month (~$6 USD)**, not the ~$14/month
  figure assumed earlier. The price was reduced in May 2025 after NSE algo-trading
  regulatory clarification.
- **Kite Connect Personal API is free for execution + account data.** Order
  placement and account/holdings/positions endpoints are included at no cost; the
  paid ₹500/month Connect tier adds real-time and historical market data only.
- **Kite requires a static IP for order placement, since 1 April 2025.** This is a
  SEBI/NSE algo-trading regulation, not a Zerodha policy. Order requests from
  unregistered IPs are rejected; up to 2 static IPs are allowed per account; other
  endpoints (data, holdings, positions) work from any IP. A material UX constraint
  for Vysted users on residential dynamic IPs — the Kite plugin must surface it
  in-app.

## v0.1.0 — Phase 0: Foundation (2026-05-14)

The greenfield foundation: a working local dev environment plus all scaffolding
that Phases 1–7 plug into. `pnpm install && pnpm tauri dev` opens a Vysted
Terminal window with a Welcome panel and a cmd+K command palette; a Python
sidecar is spawned and supervised by the Tauri core.

### Shipped

- Greenfield repo + GitHub remote (`techlogist1/vysted-terminal`), flat
  (non-monorepo) layout.
- Tauri 2.x core (Rust) — windowing, Python sidecar lifecycle, updater plugin
  stub.
- Next.js 16 + React 19 + TypeScript frontend, statically exported.
- Tailwind 4 (CSS-first `@theme`) + shadcn/ui + Zustand + Framer Motion.
- Vysted design tokens (`styles/tokens.css`) — charcoal / amber / sage palette,
  serif + monospace type.
- One mock Welcome panel; cmd+K / ctrl+K command palette skeleton (no commands
  wired).
- Python 3.13 FastAPI sidecar with a `/health` endpoint; PyInstaller one-file
  bundling via `scripts/ensure-sidecar.mjs`; spawned by the Tauri core on a
  free port and killed on exit.
- `types/plugin.ts` — the `VystedPlugin` contract, all six capabilities.
- CI: `build` / `lint` / `test` workflows, matrixed across Windows, macOS, and
  Linux.
- Licensing: AGPL-3.0 (`LICENSE`) + draft commercial dual-license
  (`COMMERCIAL_LICENSE.md`).
- Docs: `README.md`, `CONTRIBUTING.md`, `CLAUDE.md`, sanitized
  `docs/BLUEPRINT.md`.

### Decisions

- **Next.js 16**, not the literal "Next.js 14" named in the brief — operator-
  approved; the same brief also required "latest stable as of May 2026".
- **Python 3.13** (the installed version), not 3.12 — operator-approved; fully
  supported by FastAPI and PyInstaller.
- **ESLint pinned to 9.39.4**, not 10.x — `eslint-config-next@16.2.6` ships
  `eslint-plugin-react@7.37.5`, which calls `context.getFilename()`, removed in
  ESLint 10. The Next 16 lint preset is not yet ESLint-10-compatible.
- **`types/plugin.ts` uses `unknown`** where blueprint §3.3 wrote `any` (the
  `subscribe` event and `executeCommand` args) — a flagged hardening so type
  safety is not lost at every plugin boundary.
- **Tailwind 4 (CSS-first).** Design tokens are an `@theme` block in
  `styles/tokens.css`; semantic shadcn mapping lives in `src/app/globals.css`.
- **Bundle targets** explicitly `[deb, appimage, nsis, app, dmg]` — excludes
  `rpm` (no `rpmbuild` on `ubuntu-latest`) and `msi` (avoids a WiX dependency).
- **Sidecar build is idempotent** and wired into Tauri's `beforeDevCommand` /
  `beforeBuildCommand`, so a bare `pnpm tauri dev` builds the sidecar on first
  run.
- **Updater is a real-keypair stub** — the public key is in `tauri.conf.json`;
  the private key `src-tauri/vysted-updater.key` is gitignored and handed to the
  operator for Phase 7. `createUpdaterArtifacts` stays `false`.
- `rustfmt` and `clippy` components were added to the local Rust toolchain via
  `rustup component add` — required by the lint workflow.

### Failed approaches & fixes

- **ESLint flat config via `FlatCompat`** threw a circular-reference error
  validating `eslint-config-next`'s shareable configs. Fixed by importing
  `eslint-config-next`'s native flat-config arrays directly and dropping
  `@eslint/eslintrc`. (ESLint 10 itself then proved incompatible — see
  Decisions.)
- **PyInstaller `--onefile` orphaned the sidecar worker.** The one-file
  bootloader re-execs a worker child; killing the bootloader (Tauri's
  `child.kill()`, or a `Stop-Process`) left the worker alive and holding a lock
  on the binary. Fixed with a stdin-EOF watchdog in `sidecar/main.py`: when the
  Tauri core drops the `CommandChild`, stdin closes and the worker self-exits.
- **`ensure-sidecar.mjs` copy hit `EBUSY`** — a freshly built `.exe` is briefly
  locked by antivirus / the search indexer. Added a copy-retry with backoff.
- **Flaky `macos-latest` CI build** — `cargo metadata` resolved to `rustup-init`
  on some runner images. Fixed by prepending `~/.cargo/bin` to `$GITHUB_PATH`
  and re-asserting `rustup default stable` in all three workflows.

### Known issues / cosmetic

- `pnpm tauri dev` exits with code `4294967295` on Windows when the window is
  closed — a WebView2-teardown artifact, not a real failure. Does not affect
  `tauri build` or CI.
- GitHub Actions notes that `actions/*` and `pnpm/action-setup` still run on
  Node 20 (deprecation notice, not an error). Revisit before the June 2026
  enforcement date.
