# Contributing to Vysted Terminal

**Contributions are closed for now.** We are not accepting pull requests at this time. Issues and
bug reports are still welcome — please open one if you hit a problem. This document is kept as
reference for when contributions reopen: environment setup, coding standards, the commit and PR
workflow, the Contributor License Agreement, and a note on the plugin contract.

**Scope note.** Phases 0–10 are merged (data layer, charting, agentic copilot, node editor +
backtest, agent-write safety, macro/research/QuantLib, integrations) and an
agent-native redesign is in flight — see [`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md) for the
honest works/buggy/deferred map and [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md) for the architecture.
If you are planning a non-trivial contribution, open an issue first to confirm it aligns with the
current direction before investing time in implementation.

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

## Licensing

Vysted Terminal is source-available under **PolyForm Strict 1.0.0** (noncommercial use) with a
commercial license as the only other path (see [`LICENSING.md`](./LICENSING.md) and
[`COMMERCIAL_LICENSE.md`](./COMMERCIAL_LICENSE.md)); the plugin contract and the example plugin
carry a separate **Apache-2.0** carve-out so third-party plugin authors are never blocked by the
core's license. Contributions are currently closed, so the Contributor License Agreement process
described below does not apply until they reopen.

**The formal CLA process is still being finalized** and will be in place before contributions
reopen. When they do, contributors will confirm CLA agreement by including a statement in their PR
description agreeing to license their contribution under the project CLA, permitting Vysted
Terminal to include it under both PolyForm Strict 1.0.0 and the commercial license.

---

## Plugin Contract

`types/plugin.ts` is the canonical interface between the Vysted Terminal core and all plugins —
first-party and third-party. It is risk-critical: a breaking change to this file breaks every
plugin.

Any PR that modifies `types/plugin.ts` **requires explicit maintainer sign-off** before merge, in
addition to passing CI. Open an issue describing the proposed change and rationale before writing
code. Additive, backwards-compatible additions are easier to land than type-level breaking changes;
breaking changes will be batched into a versioned contract release.
