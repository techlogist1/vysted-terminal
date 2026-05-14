# Contributing to Vysted Terminal

Contributions are welcome. This document covers the mechanics: environment setup, coding standards,
the commit and PR workflow, the Contributor License Agreement, and a note on the plugin contract.

**Scope note.** This repository is at Phase 0 — the foundation is in place, but feature work is
gated by the phase-by-phase roadmap in [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md). If you are
planning a non-trivial contribution, open an issue first to confirm it aligns with the current
phase's scope before investing time in implementation.

---

## Dev Setup

Prerequisites are identical to those listed in the [README](./README.md):

- **Node.js 24+**
- **pnpm 10+**
- **Rust stable toolchain** (`rustup toolchain install stable`)
- **C/C++ build tools** — VS Build Tools 2022 on Windows, Xcode CLT on macOS, `build-essential`
  on Linux
- **Python 3.13+**

After cloning:

```bash
pnpm install
```

Then `pnpm tauri dev` to verify the dev build opens without errors.

---

## Coding Standards

All standards below are enforced by CI. A failing lint or type-check blocks merge.

### TypeScript (frontend)

- `strict: true` is set in `tsconfig.json`. No implicit `any`.
- **Prettier** (`prettier`) formats all TypeScript, TSX, JSON, and CSS files. Run `pnpm format`
  before committing; `pnpm format:check` is run in CI.
- **ESLint** (`eslint`) is configured via `eslint.config.mjs`. Run `pnpm lint`.
- Type-check: `pnpm typecheck` (`tsc --noEmit`).

### Rust (Tauri core)

- Format with `rustfmt`: `cargo fmt --manifest-path src-tauri/Cargo.toml`.
- Lint with Clippy, warnings treated as errors:
  `cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings`.

### Python (sidecar)

- Formatted and linted with **ruff** (config in `sidecar/ruff.toml`): `ruff check sidecar/` and
  `ruff format sidecar/`.

---

## Commits and Pull Requests

**Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
```

Common types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.

**Pull requests:**

- Target the `main` branch.
- CI runs three workflows (build, lint, test) across Windows, macOS, and Linux. All matrix jobs
  must be green before a PR can merge.
- Include a brief description of what changed and why. Reference the relevant issue or roadmap
  phase where applicable.
- Keep PRs focused. A PR that mixes unrelated concerns will be asked to split.

---

## Contributor License Agreement

Vysted Terminal is dual-licensed under AGPL-3.0 (open-source) and a commercial license
(see [`COMMERCIAL_LICENSE.md`](./COMMERCIAL_LICENSE.md)). To keep both licensing tracks legally
sound, all contributors must agree to a Contributor License Agreement (CLA) before their
contribution can be merged.

**The formal CLA process is still being finalized** and will be in place before v1.0. In the
meantime, contributors confirm CLA agreement by including the following statement in their PR
description:

> I have read the CONTRIBUTING.md CLA section and agree to license my contribution under the
> project CLA, permitting Vysted Terminal to include it under both the AGPL-3.0 and the commercial
> license.

This statement is a placeholder acknowledgement, not a waiver of any rights. The finalized CLA
document will supersede it.

---

## Plugin Contract

`types/plugin.ts` is the canonical interface between the Vysted Terminal core and all plugins —
first-party and third-party. It is risk-critical: a breaking change to this file breaks every
plugin.

Any PR that modifies `types/plugin.ts` **requires explicit maintainer sign-off** before merge, in
addition to passing CI. Open an issue describing the proposed change and rationale before writing
code. Additive, backwards-compatible additions are easier to land than type-level breaking changes;
breaking changes will be batched into a versioned contract release.
