# Vysted Terminal

Open-source, AI-native finance desktop terminal — Bloomberg-level coverage with a
plugin architecture, local-first, bring-your-own-keys. Built as a Tauri desktop
app; Tradesa V2 is the first plugin proving the platform.

## Living document

This file is project DNA, not a frozen spec — it is expected to evolve. When you
(a future phase's Claude Code session) learn something the next session would
need, update this file in the same PR that introduced the change:

- A convention emerged or changed → update **Coding standards**.
- A non-obvious trap was diagnosed and solved → append to **Gotchas**.
- The model-assignment rules need adjusting → update **Model assignment**.

Rules: surgical edits only — change the line that is wrong, don't rewrite whole
sections. Keep the file under ~2k tokens and current-state-only. Build-time
decisions, failed approaches, and per-phase outcomes belong in `CHANGELOG.md`,
not here. The operator reviews the diff before it is committed.

## Stack

- **Frontend:** Next.js 16 (App Router, static export) + React 19 + TypeScript,
  Tailwind 4 + shadcn/ui, Zustand, Framer Motion
- **Desktop core:** Tauri 2.x (Rust) — windowing, keychain, auto-updater, sidecar
  lifecycle
- **Sidecar:** Python 3.13 FastAPI service on localhost — data + AI compute; the
  port is assigned by the Tauri core at launch
- **Package manager:** pnpm

## Layout

- `src/` — Next.js frontend
- `src-tauri/` — Rust Tauri core
- `sidecar/` — Python FastAPI sidecar
- `types/` — shared TypeScript types (plugin contract)
- `styles/` — design tokens
- `docs/` — architecture docs

## Coding standards

- TypeScript strict mode; no `any` in shared contracts — use `unknown`.
- Prettier + ESLint (TS), rustfmt + clippy (`-D warnings`), ruff (Python) — all
  enforced in CI.
- Conventional commit messages; one commit per concrete deliverable.
- Builds must stay green on Windows, macOS, and Linux.

## Plugin contract constraints

`types/plugin.ts` defines the `VystedPlugin` interface — the single highest-risk
file in the project. Every plugin and every future phase plugs into it. Six
capabilities: data, panels, commands, agents, nodes, control plane. **Changing
this contract is a breaking change for every downstream plugin.** Never edit it
without weighing the blast radius. Tradesa V2 (Phase 5) must implement all six
capabilities without contract changes.

## Model assignment (multi-phase build)

- **Opus** — lead. Owns risk-critical files: the plugin contract, CI workflows,
  Tauri config, licensing, and this file.
- **Sonnet** — mechanical work only (component JSX, design tokens, boilerplate
  docs). The lead reviews every diff before merge.
- **Haiku** — log parsing and high-volume mechanical scanning.

## Gotchas

Non-obvious traps and their fixes — append a line or two as they are found, so
the next session does not re-learn them. (Empty at the end of Phase 0; the
Phase 0 build notes live in `CHANGELOG.md`.)

## Reference docs

- `docs/BLUEPRINT.md` — full architectural blueprint. Read when architectural
  questions arise; do not load by default.
- `CHANGELOG.md` — build-time decisions, failed approaches, and per-phase
  outcomes. Read when you need the _why_ behind a choice.
