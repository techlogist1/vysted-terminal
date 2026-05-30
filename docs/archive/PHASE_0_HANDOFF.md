# Phase 0 — Handoff

**Phase 0: Foundation — complete.** Tagged `v0.1.0`. This document hands off to Phase 1.

Repo: https://github.com/techlogist1/vysted-terminal · Local: `C:\dev\vystedterminal`

---

## What shipped

All 15 brief deliverables, one commit per deliverable:

| #   | Deliverable                                                         | Where                                                                                |
| --- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 1   | Repo init, GitHub repo, origin, initial push                        | `.gitignore` `.gitattributes`, `techlogist1/vysted-terminal`                         |
| 2   | Flat repo structure                                                 | `src/` `src-tauri/` `sidecar/` `types/` `styles/` `docs/` `.github/`                 |
| 3   | Tauri 2.x + Next.js 16 + TS + Tailwind/shadcn/Zustand/Framer Motion | `package.json`, `src-tauri/`, `next.config.ts`, `tsconfig.json`, `eslint.config.mjs` |
| 4   | Vysted design tokens                                                | `styles/tokens.css` (Tailwind 4 `@theme`), mapped in `src/app/globals.css`           |
| 5   | Mock "Welcome" panel                                                | `src/app/page.tsx`, `src/app/layout.tsx` (fonts)                                     |
| 6   | cmd+K command-palette skeleton                                      | `src/components/CommandPalette.tsx`, `src/store/command-palette.ts`                  |
| 7   | `VystedPlugin` contract (RISK-CRITICAL)                             | `types/plugin.ts` — all six capabilities                                             |
| 8   | Python sidecar + Tauri lifecycle + PyInstaller bundling             | `sidecar/`, `src-tauri/src/lib.rs`, `scripts/ensure-sidecar.mjs`                     |
| 9   | CI: build / lint / test, Windows + macOS + Linux                    | `.github/workflows/{build,lint,test}.yml`                                            |
| 10  | Licensing                                                           | `LICENSE` (AGPL-3.0), `COMMERCIAL_LICENSE.md` (DRAFT), `CONTRIBUTING.md` (CLA noted) |
| 11  | `CLAUDE.md` — lean, operator-approved                               | `CLAUDE.md` (a living document; see below)                                           |
| 12  | `README.md`                                                         | `README.md`                                                                          |
| 13  | `.gitignore`                                                        | `.gitignore`                                                                         |
| 14  | `docs/BLUEPRINT.md` — operator-sanitized                            | `docs/BLUEPRINT.md`                                                                  |
| 15  | Tag `v0.1.0`                                                        | pushed to origin once CI green + handoff written                                     |

Verified end-to-end: `pnpm install && pnpm tauri dev` from a clean state opens the
Vysted Terminal window with the Welcome panel; cmd+K / ctrl+K opens the command
palette, Esc closes it; the Python sidecar is spawned on an auto-assigned port,
logs healthy, and is killed on exit (no orphans). All static checks green:
`pnpm typecheck/lint/format:check/test`, `cargo fmt/clippy/test`, `ruff` + `pytest`.

## Library versions locked

**Frontend (`package.json`):** next 16.2.6 · react / react-dom 19.2.6 · typescript 6.0.3 ·
tailwindcss 4.3.0 · @tailwindcss/postcss 4.3.0 · zustand 5.0.13 · framer-motion 12.38.0 ·
lucide-react 1.14.0 · clsx 2.1.1 · tailwind-merge 3.6.0 · class-variance-authority 0.7.1 ·
@tauri-apps/cli 2.11.1 · @tauri-apps/api 2.11.0 · @tauri-apps/plugin-shell 2.3.5 ·
@tauri-apps/plugin-updater 2.10.1 · **eslint 9.39.4** (see deviations) · prettier 3.8.3 ·
vitest 4.1.6 · pnpm 10.32.1. Exact transitive versions: `pnpm-lock.yaml`.

**Rust (`src-tauri/Cargo.toml` → `Cargo.lock`):** tauri 2.11.1 · tauri-build 2.6.1 ·
tauri-plugin-shell 2.3.5 · tauri-plugin-updater 2.10.1 · serde 1 · serde_json 1 ·
edition 2021. Built with cargo 1.94.1 locally / 1.95.0 on CI runners.

**Python sidecar (`sidecar/requirements.txt` + `requirements-dev.txt`):**
fastapi 0.136.1 · uvicorn[standard] 0.46.0 · pyinstaller 6.20.0 · ruff 0.15.12 ·
pytest 9.0.3 · httpx 0.28.1. Targets Python 3.13.

## What's stubbed (intentionally — Phase 0 is scaffolding)

- **Command palette** opens but has no commands — the registry/command list arrives in Phase 1+.
- **Sidecar** exposes only `/health` — no data providers, no AI, no MCP server yet.
- **No real data, no plugins, no AI** anywhere — pure scaffold + the plugin contract.
- **Updater** is wired (plugin registered, real signing keypair, `tauri.conf.json` endpoints +
  pubkey) but `bundle.createUpdaterArtifacts` is `false` and the updater is never called at
  runtime. Phase 7 turns it on.
- **CI bundles are unsigned.** Code signing (SignPath for Windows, ad-hoc for macOS) is Phase 7.
- `SidecarPort` is `manage()`d into Tauri state but unused in Phase 0 (`#[expect(dead_code)]`) —
  Phase 1 panels will read it to reach the sidecar.

## Deviations from the brief (all flagged, none silent)

- **Next.js 16, not the literal "Next.js 14"** — operator-approved; the brief also required
  "latest stable as of May 2026". Cascaded to React 19, Tailwind 4, current shadcn/ui.
- **Python 3.13, not 3.12** — operator-approved; the installed version, fully supported.
- **ESLint pinned to 9.39.4, not 10.x** — `eslint-config-next@16.2.6` ships
  `eslint-plugin-react@7.37.5`, which uses `context.getFilename()`, removed in ESLint 10. The
  Next 16 lint preset is not yet ESLint-10-compatible. Revisit when Vercel ships an update.
- **`types/plugin.ts` uses `unknown`** where blueprint §3.3 wrote `any` (the `subscribe` event
  and `executeCommand` args) — operator-reviewed and approved.
- **Bundle targets** are explicit `[deb, appimage, nsis, app, dmg]` — excludes `rpm` (no
  `rpmbuild` on `ubuntu-latest`) and `msi` (avoids a WiX dependency). All unsigned.
- **Blueprint source** was `vystedterminalblueprint.md` in the repo root (not in `lokuvault`
  as the brief stated) — operator corrected the path; it is now `docs/BLUEPRINT.md`.
- **`CLAUDE.md` is a living document** + **`CHANGELOG.md` added** — operator-directed during
  the Gate 1 review. CHANGELOG.md is the per-phase "why" log (decisions, failed approaches).
- **`styles/tokens.css` was lead-written**, not Sonnet-delegated — it is a build dependency of
  Task 4's `globals.css`, and its content was fully specified in the approved plan. The Sonnet
  subagent did the genuine JSX/doc work (Welcome panel, command palette, README, CONTRIBUTING).
- **`rustfmt` + `clippy` components** were added to the local Rust toolchain via
  `rustup component add` — they were not pre-installed; this is the same setup CI performs and
  is required by deliverable 9's lint workflow.

See `CHANGELOG.md` → "v0.1.0 — Phase 0" for the full decision log, including the failed
approaches and their fixes (ESLint flat-config, the PyInstaller `--onefile` worker-orphan, the
`EBUSY` copy-retry, and the macOS CI `cargo → rustup-init` root cause).

## Operator action items before Phase 1

- [ ] **Store the updater signing private key.** `src-tauri/vysted-updater.key` is gitignored.
      Save it somewhere durable and add it as a CI secret (`TAURI_SIGNING_PRIVATE_KEY`) for
      Phase 7 — if it is lost, the auto-updater cannot be enabled without shipping a new pubkey.
- [ ] **CLA process** is still to be finalized (noted in `CONTRIBUTING.md` and
      `COMMERCIAL_LICENSE.md`). Decide on a CLA mechanism before accepting external contributions.
- [ ] Optional: GitHub Actions warns the `actions/*` runners still use Node 20 (deprecation
      notice, not an error) — revisit before the June 2026 enforcement date.
- [ ] Optional: `pnpm install` notes ignored build scripts (`sharp`, `unrs-resolver`). Neither
      is needed (`sharp` is unused — `next.config.ts` sets `images.unoptimized`); no action
      required unless a future phase needs them.

## GO — Phase 1

> **Phase 1 — Data layer (OpenBB ODP + ccxt + yfinance) + 5 core panels with real data.**
> Fresh Claude Code window, Opus 4.7, plan mode first. Repo at `C:\dev\vystedterminal`,
> tagged `v0.1.0`. Read `CLAUDE.md`; read `docs/BLUEPRINT.md` §4 (Data Layer) and §3.3
> (plugin contract) before planning.
