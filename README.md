# Vysted Terminal

Open-source, AI-native desktop finance terminal. **v1.0 in active development.**

---

## Overview

Vysted Terminal is an open-source, AI-native finance terminal built to deliver Bloomberg-level market
coverage without the proprietary lock-in. The platform centers on a plugin architecture: first-party
and third-party plugins extend a well-defined TypeScript contract (`types/plugin.ts`) to add data
sources, panels, commands, and agent nodes. All market data keys are operator-supplied — the
terminal itself is bringable-your-own-keys and processes data locally by default, with no data
leaving the machine unless a plugin explicitly routes it outward.

Tradesa V2 is the first plugin being built on the platform. It validates the plugin contract end-to-end
and will ship alongside v1.0. Its presence in the roadmap is primarily a proof-of-platform exercise,
not a statement about product focus.

This repository is the Phase 0 foundation: the repo scaffolding, CI, core shell (command palette,
welcome panel), Python sidecar, plugin contract, licensing, and architecture documentation. Phase 0
produces no user-visible features beyond an empty terminal window; it establishes the structural
baseline that every subsequent phase builds on.

---

## Prerequisites

| Dependency              | Required version | Notes                                       |
| ----------------------- | ---------------- | ------------------------------------------- |
| Node.js                 | 24+              | LTS or Current                              |
| pnpm                    | 10+              | `npm i -g pnpm`                             |
| Rust (stable toolchain) | latest stable    | `rustup toolchain install stable`           |
| C/C++ build tools       | —                | VS Build Tools 2022 on Windows              |
| Python                  | 3.13+            | Used by the FastAPI sidecar and PyInstaller |

**Windows:** Install [Visual Studio Build Tools 2022](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
with the "Desktop development with C++" workload. WebView2 Runtime must also be present (ships with
Windows 11; downloadable separately for Windows 10).

---

## Local Development

```bash
git clone https://github.com/techlogist1/vysted-terminal.git
cd vysted-terminal
pnpm install
pnpm tauri dev
```

The first `pnpm tauri dev` invocation builds the Python sidecar binary via PyInstaller before
launching the Tauri dev server. This one-time compilation step takes approximately 1–2 minutes.
Subsequent runs skip it unless the sidecar source changes.

---

## Project Layout

| Path         | Contents                                                              |
| ------------ | --------------------------------------------------------------------- |
| `src/`       | Next.js 16 frontend (React 19, TypeScript, Tailwind 4, shadcn/ui)     |
| `src-tauri/` | Rust Tauri 2.x core — windowing, sidecar lifecycle, IPC commands      |
| `sidecar/`   | Python 3.13 FastAPI sidecar, bundled to a binary by PyInstaller       |
| `types/`     | Shared TypeScript types; `plugin.ts` is the canonical plugin contract |
| `styles/`    | Design tokens (`tokens.css`) — Tailwind 4 `@theme` variables          |
| `docs/`      | Architecture documentation and the sanitized blueprint                |

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

---

## License

Free for personal, academic, and open-source use under
[AGPL-3.0](./LICENSE). Commercial use requires a paid license — see
[`COMMERCIAL_LICENSE.md`](./COMMERCIAL_LICENSE.md).

---

## Status

Phase 0 (foundation) complete. v1.0 in active development; see [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md)
for the roadmap.
