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
capabilities without contract changes. Phase 5 also ships global broker execution
plugins on the same contract — broker execution is v1.0 scope, gated behind the
safety layer in `docs/BLUEPRINT.md` §6.5.

## Model assignment (multi-phase build)

- **Opus** — lead. Owns risk-critical files: the plugin contract, CI workflows,
  Tauri config, licensing, and this file.
- **Sonnet** — mechanical work only (component JSX, design tokens, boilerplate
  docs). The lead reviews every diff before merge.
- **Haiku** — log parsing and high-volume mechanical scanning.

## Decision authority

How a session resolves a choice depends on its blast radius. Four tiers:

1. **Locked** — decisions in `docs/BLUEPRINT.md` §2 "Locked Decisions Summary".
   Never reopen. _E.g._ the stack (Tauri + Next.js + Python sidecar); AGPL-3.0 +
   commercial dual license; global broker execution in v1.0 scope.
2. **Spec-derivable** — the phase brief or blueprint settles it on a careful
   read. Decide and proceed; no asking, no documentation beyond the commit.
   _E.g._ which Pydantic models a phase needs (the brief enumerates them); a
   brief's stated teammate merge order; that the AI chat sidebar is Phase 3.
3. **Spec-ambiguous, derives from DNA** — the spec is silent, but the product
   positioning (finance sandbox, max extensibility, local-first, BYOK,
   research-lab voice) points to an answer. Decide from positioning, record it
   as a one-line append to `CHANGELOG.md` or `docs/BLUEPRINT.md`, continue.
   _E.g._ dockview chosen as layout engine; rationale: max sandboxability per
   product positioning; supports BLUEPRINT §5.2 customization primitives
   natively. _E.g._ sidecar-owned vs Tauri-owned persistence; lexicon vs
   model-based sentiment given the PyInstaller `--onefile` constraint.
4. **High blast radius** — the plugin contract (`types/plugin.ts`), licensing,
   the §6.5 execution safety model, or core architecture (the layer model, the
   sidecar boundary). Block and ask the operator. _E.g._ any `types/plugin.ts`
   change; altering AGPL/commercial terms; weakening a §6.5 safeguard.

Only Tier 4 surfaces to the operator. Tiers 2 and 3 are autonomous — Tier 3 with
a documentation trail. Do not ask permission for spec ambiguities that DNA can
settle; that is what Tier 3 is for. `BLOCKERS.md` (repo root) is for genuine
Tier-4 blocks and hard blockers hit while the operator is unavailable.

## Gotchas

Non-obvious traps and their fixes — append a line or two as they are found, so
the next session does not re-learn them. (Phase 0 build notes live in
`CHANGELOG.md`.)

- **`types/data.ts` mirrors `sidecar/models/` by hand.** The sidecar's Pydantic
  models and their TypeScript counterparts in `types/data.ts` are kept in sync
  manually. Change a Pydantic model → update the matching interface in
  `types/data.ts` in the same commit.
- **Smoke-testing the sidecar binary orphans a worker.** The PyInstaller
  `--onefile` binary re-execs a worker child; `Stop-Process` on the bootloader
  PID leaves the worker alive, holding the binary locked — which breaks the next
  `ensure-sidecar.mjs` copy with `EBUSY`. When running the binary directly, kill
  it by name wildcard (`Get-Process vysted-sidecar*`), not by the spawned PID.
  The stdin-EOF watchdog only covers the Tauri-managed path.

## Reference docs

- `docs/BLUEPRINT.md` — full architectural blueprint. Read when architectural
  questions arise; do not load by default.
- `CHANGELOG.md` — build-time decisions, failed approaches, and per-phase
  outcomes. Read when you need the _why_ behind a choice.
