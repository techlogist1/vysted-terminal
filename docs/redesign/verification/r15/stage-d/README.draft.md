<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->

# Vysted Terminal

Vysted Terminal is a desktop finance terminal: a Tauri app that pairs a multi-panel
market cockpit (charts, watchlist, news, portfolio, screener, macro, SEC filings, a
node-editor/workflow surface) with an agentic AI copilot that can read data and drive
the terminal on your behalf. It runs entirely on your machine — a Rust core, a
Vite + React frontend, and a Python FastAPI sidecar talk to each other over `127.0.0.1`
only, with bring-your-own-keys for every AI provider (README.md at f4444790, "Overview").

> **Redesign in flight.** Vysted is being reframed into an agent-native finance
> workspace. [`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md) is the honest
> inventory of what exists today; [`specs/001-agent-native-redesign/spec.md`](./specs/001-agent-native-redesign/spec.md)
> is where it's headed (both present at f4444790).

<p align="center">
  <img src="docs/screenshots/v0.8.0/research-cockpit-hero.png" width="880"
       alt="Vysted Terminal — ask the agent to research NVDA and a visual, cited brief lands in the cockpit: a metric-card grid, a key-metrics table, and a written valuation analysis, beside a live research trace." />
</p>

## What it is not

- **No trading.** Trading was removed from the product permanently
  (D81, 23 Sep 2026 — `docs/BROKER_INTEGRATIONS.md` at f4444790). There is no broker
  connection, no order placement, no paper or live trading account, and no
  paper/live switch anywhere in the app. Your manually tracked portfolio (the
  Portfolio panel — holdings you enter by hand, with P&L and CSV export) is not
  trading and stays.
- **Not investment advice.** Nothing the app displays or the AI copilot generates,
  including agent output, is a trade recommendation
  (`COMMERCIAL_LICENSE.md` at f4444790, "No warranty for trading losses").

## Download and install (macOS)

<!-- fill at rc2: release asset URL and the Gatekeeper steps once the lead publishes -->

No signed, installable release is published yet: there is no release pipeline and
no code-signing identity at this sha, so a built `.dmg` would be Gatekeeper-blocked
on every machine it reached (open items in this run's decision log). Until that
ships, run Vysted from source.

## Build from source

| Dependency              | Required version | Notes                                       |
| ------------------------ | ----------------- | -------------------------------------------- |
| Node.js                 | 24+               | LTS or Current                              |
| pnpm                    | 10+               | `npm i -g pnpm`                             |
| Rust (stable toolchain) | latest stable     | `rustup toolchain install stable`           |
| C/C++ build tools       | —                 | Xcode Command Line Tools on macOS; VS Build Tools 2022 on Windows; `build-essential` on Linux |
| Python                  | 3.13 (exactly)    | `brew install python@3.13`, or set `VYSTED_PYTHON` to a 3.13 interpreter — the sidecar build refuses any other version |

**macOS:** `xcode-select --install`.

**Windows:** Visual Studio Build Tools 2022 with the "Desktop development with C++"
workload, plus the WebView2 Runtime (ships with Windows 11; downloadable separately
for Windows 10).

**Linux:** `build-essential` plus the webkit2gtk/gtk packages
`.github/workflows/build.yml` installs before building
(`libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf libgtk-3-dev
libssl-dev`).

```bash
git clone https://github.com/techlogist1/vysted-terminal.git
cd vysted-terminal
pnpm install
pnpm tauri dev
```

The first `pnpm tauri dev` builds three Python sidecar binaries via PyInstaller
before launching (a one-time step; later runs skip it unless sidecar source
changes). Before trusting a build, run the CI-parity gate and the binary
smoke-test:

```bash
pnpm ci-local                        # lint + format + typecheck + clippy + ruff + tests
node scripts/smoke-test-sidecars.mjs # spawn each sidecar binary, probe /health + MCP bind
```

`pnpm ci-local` shells out to a bare `python` for the ruff/pytest steps
(`package.json`'s `ci-local` script), and macOS ships no `python` at all — point it at
the 3.13 interpreter the sidecar build already resolved, e.g.
`source sidecar/.venv/bin/activate` after the first `pnpm tauri dev`.

## BYOK — bring your own keys

Vysted works without any key: quotes, charts, news, screeners, and web research
(a keyless DuckDuckGo floor) all run out of the box. The AI copilot and deep
research need a model, either:

- a local model run through [Ollama](https://ollama.com) — no key, fully offline, or
- one of seven keyed providers — Anthropic, OpenAI, Gemini, Groq, DeepSeek, xAI, and
  OpenRouter (a broker that routes to most of the above through one key) — plus
  Ollama, all eight in one dropdown — the exact list the sidecar's provider registry
  ships (`sidecar/config/model_registry.json` at f4444790).

Keys are entered in the frontend and stored through the Tauri `keychain_set` /
`keychain_get` / `keychain_delete` commands (`src-tauri/src/keychain.rs` at
f4444790): the OS keychain in a release build, or a local, git-ignored
`dev-keystore.json` file under the app's data directory in a debug build only (the
file-keystore code is compiled only into debug builds — `cfg(debug_assertions)` — so
a release binary has no file path to fall back to). The
frontend's keychain wrapper (`src/lib/keychain.ts` at f4444790) is the only path
that touches credentials and never uses `localStorage`/`sessionStorage`/cookies.
A stored key is sent to the sidecar once per request to reach the provider you
configured; the sidecar does not persist it beyond that request — or, for a
background agent run, beyond that run. Nothing about
your keys, and no request content, goes to a Vysted-run server — there isn't one.

## Plugin contract

Third-party extensions implement one serializable contract,
[`types/plugin.ts`](./types/plugin.ts) — six capabilities (data, panels, commands,
agents, nodes, control plane). It and its runtime-support types
([`types/plugin-runtime.ts`](./types/plugin-runtime.ts)) are licensed separately
from the rest of the codebase under [Apache-2.0](./LICENSE-APACHE), specifically so
plugin authors are never bound by the core license — confirmed by the SPDX headers
on both files (`// SPDX-License-Identifier: Apache-2.0`) and on the bundled example
plugin (`plugins/example/index.ts`, `plugins/example/example.test.ts`); the example
plugin's `manifest.json` carries no header (JSON can't) but is named explicitly in
`LICENSING.md`'s Apache-2.0 list. See
[`docs/PLUGIN_DEVELOPMENT.md`](./docs/PLUGIN_DEVELOPMENT.md) to build one.

## License

The core is **source-available**, not open-source: free for noncommercial use under
[PolyForm Strict 1.0.0](./LICENSE); any commercial use, modification, or
redistribution needs a paid commercial license
([`COMMERCIAL_LICENSE.md`](./COMMERCIAL_LICENSE.md), plain-language summary in
[`LICENSING.md`](./LICENSING.md)). Every commit made before the relicensing commit
remains available under its original AGPL-3.0 terms — relicensing only changes the
terms for new work going forward (`LICENSING.md` at f4444790). The plugin contract
and example plugin are the Apache-2.0 exception described above.

## Support and roadmap

- Issues and bug reports: [github.com/techlogist1/vysted-terminal/issues](https://github.com/techlogist1/vysted-terminal/issues).
- Pull requests are currently closed while the redesign is in flight; see
  [CONTRIBUTING.md](./CONTRIBUTING.md) — it stays as reference for when
  contributions reopen and asks that a non-trivial idea start as an issue first.
- Start reading the architecture at [`docs/README.md`](./docs/README.md); the
  in-flight redesign spec is under [`specs/`](./specs/001-agent-native-redesign/spec.md).

## Project layout

| Path         | Contents                                                                    |
| ------------ | ---------------------------------------------------------------------------- |
| `src/`       | Vite + React 19 frontend (TypeScript, Tailwind, shadcn/ui)                 |
| `src-tauri/` | Rust Tauri core — windowing, keychain, sidecar lifecycle, IPC               |
| `sidecar/`   | Python FastAPI sidecar (+ MCP subprocesses), bundled by PyInstaller         |
| `types/`     | Shared TypeScript types; `plugin.ts` is the canonical plugin contract       |
| `plugins/`   | Bundled plugins (example, openbb-mcp, yfinance, vysted-news, vysted-lenses) |
| `styles/`    | Design tokens (`tokens.css`)                                                |
| `docs/`      | Architecture docs — start at [`docs/README.md`](./docs/README.md)           |

## Status

Version 0.8.0 <!-- VERIFY: target is 0.9.0; every version source (package.json,
Cargo.toml, tauri.conf.json, sidecar/app.py, plugin-bootstrap.ts) reads 0.8.0 at
f4444790 — reprint as 0.9.0 only once the bump has landed on the promoted sha -->.
Phases 0–10 are merged to `main` (data layer, charting, AI copilot,
node editor + backtest, agent-write safety, macro/research/QuantLib, integrations
hub); trading was removed from the product (D81). An agent-native redesign is in
flight on top of that baseline — see
[`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md) for what's built, buggy, or
deferred, and [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md) for the architecture.
<!-- VERIFY: whether the sha this build ships from is signed off as release-ready by the lead at rc2; this draft states no release pipeline exists per this run's decision log only -->

<!-- critic-footer -->

## Critic findings applied

1. applied — "Next.js frontend" corrected to "Vite + React frontend" (intro line 9) and
   "Vite + React 19 frontend" in the Project layout table (line 149); verified
   `package.json`'s `dev`/`build` scripts run `vite`/`vite build`, no `next` dependency,
   `vite.config.ts` present at the sha.
2. applied — Python row changed to "3.13 (exactly)" with the `VYSTED_PYTHON`/
   `brew install python@3.13` guidance; verified `scripts/build-python.mjs:12` `WANT = "3.13"`
   and its throw message.
3. applied — added Xcode CLT / VS Build Tools 2022 + WebView2 / `build-essential` notes under
   the Build from source table; verified `CONTRIBUTING.md` and
   `.github/workflows/build.yml`'s Linux dependency list.
4. applied — added a note after the `ci-local`/smoke-test block that `pnpm ci-local` needs a
   bare `python` resolving to 3.13; verified `package.json`'s `ci-local` script shells to
   plain `python`.
5. applied — reworded to "seven keyed providers ... plus Ollama, all eight in one dropdown";
   verified `sidecar/config/model_registry.json` lists 8 ids including `ollama`.
6. applied — replaced the mis-attributed "asserted in a test" claim with the structural
   guarantee (`cfg(debug_assertions)` compiles the file-keystore code out of release builds);
   verified `src-tauri/src/keychain.rs`'s module doc and `release_never_uses_dev_keystore` test.
7. applied — added "or, for a background agent run, beyond that run"; verified
   `sidecar/routers/runs.py`'s module doc on the BYOK key's run-scoped lifetime.
8. applied — "Version 0.9.0" changed to "Version 0.8.0" with a VERIFY comment naming every
   version source and the promotion condition; verified `package.json`, `Cargo.toml`,
   `tauri.conf.json`, `sidecar/app.py` all read 0.8.0 at f4444790.
9. rejected: the critic's own prescribed fix is "at rc2 delete every 'at f4444790'
   parenthetical" — explicitly a promotion-time action for the lead (CLAUDE.md: "the lead
   promotes drafts at rc2"), not a Stage D reviser action, and the citations are the wave's
   shared evidence-trail convention (also present in the sibling RELEASE_RUNBOOK.draft.md and
   CURRENT_STATE.draft.md). Left as-is for this pass.
