# Vysted Terminal

Open-source, AI-native desktop finance terminal — Bloomberg-level data coverage,
agent-assisted, **local-first**, and **bring-your-own-keys**. No account, no hosted
backend, no telemetry: data and secrets stay on your machine.

> **Redesign in flight.** Vysted is being reframed into an **agent-native finance
> workspace** — a hybrid of a dense pro command-station and an agent-first assistant
> that drives the terminal for you. See **[`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md)**
> for an honest inventory of what exists today and
> **[`specs/001-agent-native-redesign/spec.md`](./specs/001-agent-native-redesign/spec.md)**
> for where it's headed.

---

## Overview

Vysted Terminal is a Tauri desktop app with three cooperating processes on one machine
(loopback only): a **Rust core** (windowing, OS keychain, sidecar lifecycle), a
**Next.js static-export frontend** (the panel cockpit), and a **Python FastAPI sidecar**
(data + AI compute), plus two bundled MCP subprocesses (OpenBB fundamentals/macro,
SEC EDGAR filings).

What's in the box today:

- **A multi-panel cockpit** (dockview) — Chart (50 server-computed indicators + drawing
  tools), Watchlist, News (RSS + optional NewsAPI, sentiment), Portfolio, Equity
  Overview, plus Macro, SEC Filings, Earnings, Analyst Ratings, Screener, Quant
  (QuantLib), Backtest, and a Node Editor / workflow surface.
- **An agentic AI copilot** — a real tool-use loop in the sidecar: the model calls
  read/host-action tools to pull data and drive the terminal. 13 first-party agents
  (a terminal-aware copilot + 12 investor personas) plus user-authored custom agents.
- **BYOK across 7 LLM providers** (Anthropic, OpenAI, Gemini, Groq, Ollama, DeepSeek,
  xAI). Keys live in the OS keychain and never persist to disk.
- **Read-only broker connect** — genuine Kite Connect OAuth + read-only account /
  positions / P&L (Kite, Dhan, Angel One). A §6.5 execution-safety layer (paper-default,
  kill-switch, append-only audit log) exists in code; **order execution is not enabled**.
- **A plugin platform** — one serializable `VystedPlugin` contract (six capabilities:
  data, panels, commands, agents, nodes, control plane) so the terminal is extensible.
- **MCP on both sides** — Vysted proxies bundled MCP data servers *and* re-exposes its
  own capabilities as MCP tools for external agents (Claude Desktop / Code).

**Honest status:** green on every machine-checkable gate (`pnpm ci-local`, 619 vitest,
942 pytest, §6.5 9/9 safety audit) and broadly tested; **live UX, populated visuals, and
any BYOK/live-broker round-trip are operator-verified, not CI-verified** (the harness
can't drive the webview with real data). The app currently ships **unsigned with no
release pipeline**, and version strings sit at `0.8.0` pending a release cut. See
[`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md) for the full works/buggy/deferred map.

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
with the "Desktop development with C++" workload. WebView2 Runtime must also be present
(ships with Windows 11; downloadable separately for Windows 10).

---

## Local Development

```bash
git clone https://github.com/techlogist1/vysted-terminal.git
cd vysted-terminal
pnpm install
pnpm tauri dev
```

The first `pnpm tauri dev` builds the Python sidecar binaries via PyInstaller before
launching (a one-time ~1–2 minute step; subsequent runs skip it unless sidecar source
changes). Before any release tag, run the CI-parity gate and the binary smoke-test:

```bash
pnpm ci-local                       # lint + format + typecheck + clippy + ruff + tests
node scripts/smoke-test-sidecars.mjs # spawn each sidecar binary, probe /health + MCP bind
```

---

## Project Layout

| Path         | Contents                                                              |
| ------------ | --------------------------------------------------------------------- |
| `src/`       | Next.js 16 frontend (React 19, TypeScript, Tailwind 4, shadcn/ui)     |
| `src-tauri/` | Rust Tauri 2.x core — windowing, keychain, sidecar lifecycle, IPC     |
| `sidecar/`   | Python 3.13 FastAPI sidecar (+ MCP subprocesses), bundled by PyInstaller |
| `types/`     | Shared TypeScript types; `plugin.ts` is the canonical plugin contract |
| `plugins/`   | Bundled plugins (example, openbb-mcp, tradesa-v2)                     |
| `styles/`    | Design tokens (`tokens.css`) — Tailwind 4 `@theme` variables          |
| `docs/`      | Architecture docs — start at [`docs/README.md`](./docs/README.md)     |

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

Free for personal, academic, and open-source use under [AGPL-3.0](./LICENSE). Commercial
use requires a paid license — see [`COMMERCIAL_LICENSE.md`](./COMMERCIAL_LICENSE.md).

## Status

Phases 0–10 merged to `main` (data layer, charting, AI copilot, node editor + backtest,
broker read-only + §6.5 safety, macro/research/QuantLib, integrations hub). The
agent-native redesign is being specified; build follows operator review. See
[`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md) and [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md).
