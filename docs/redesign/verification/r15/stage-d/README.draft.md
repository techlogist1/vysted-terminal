<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->

# Vysted Terminal

Vysted Terminal is a desktop finance terminal: a Tauri app that pairs a multi-panel
market cockpit (charts, watchlist, news, portfolio, screener, macro, SEC filings, a
node-editor/workflow surface) with an agentic AI copilot that can read data and drive
the terminal on your behalf. It runs entirely on your machine — a Rust core, a
Vite + React frontend, and a Python FastAPI sidecar talk to each other over `127.0.0.1`
only, with bring-your-own-keys for every AI provider.

> **Redesign in flight.** Vysted is being reframed into an agent-native finance
> workspace. [`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md) is the honest
> inventory of what exists today; [`specs/001-agent-native-redesign/spec.md`](./specs/001-agent-native-redesign/spec.md)
> is where it's headed.

<p align="center">
  <img src="docs/screenshots/v0.8.0/research-cockpit-hero.png" width="880"
       alt="Vysted Terminal — ask the agent to research NVDA and a visual, cited brief lands in the cockpit: a metric-card grid, a key-metrics table, and a written valuation analysis, beside a live research trace." />
</p>

## What it is not

- **No trading.** Trading was removed from the product permanently
  (D81, 23 Sep 2026 — `docs/BROKER_INTEGRATIONS.md`). There is no broker
  connection, no order placement, no paper or live trading account, and no
  paper/live switch anywhere in the app. Your manually tracked portfolio (the
  Portfolio panel — holdings you enter by hand, with P&L and CSV export) is not
  trading and stays.
- **Not investment advice.** Nothing the app displays or the AI copilot generates,
  including agent output, is a trade recommendation
  (`COMMERCIAL_LICENSE.md`, "No warranty for trading losses").

## Download and install (macOS)

<!-- fill at rc2: release asset URL and the Gatekeeper steps once the lead publishes -->

No signed, installable release is published yet: there is no release pipeline and
no code-signing identity yet, so a built `.dmg` would be Gatekeeper-blocked
on every machine it reached (tracked in
[`docs/redesign/DECISIONS_FOR_OPERATOR.md`](./docs/redesign/DECISIONS_FOR_OPERATOR.md)
§2.8–2.9). Until that ships, run Vysted from source.

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

- a local model through [Ollama](https://ollama.com): no key, and the model runs on
  your machine (market data still comes from the network). Pull a model first, for
  example `ollama pull qwen2.5:7b` (the default) or `llama3.1:8b`, or
- one of seven keyed providers — Anthropic, OpenAI, Gemini, Groq, DeepSeek, xAI, and
  OpenRouter (a router that reaches most of the above through one key) — plus
  Ollama, all eight in one dropdown — the exact list the sidecar's provider registry
  ships (`sidecar/config/model_registry.json`).

Known limitation: with a keyless local model the agent can state a price or metric
that no successful tool call returned, or say a portfolio change was made when
nothing was written. A portfolio change never applies without your review. See the
release notes, "Known limitations at rc1 — agent chat with a keyless local model".

Keys are entered in the frontend and stored through the Tauri `keychain_set` /
`keychain_get` / `keychain_delete` commands (`src-tauri/src/keychain.rs`):
the OS keychain in a release build, or a local, git-ignored
`dev-keystore.json` file under the app's data directory in a debug build only (the
file-keystore code is compiled only into debug builds — `cfg(debug_assertions)` — so
a release binary has no file path to fall back to). The
frontend's keychain wrapper (`src/lib/keychain.ts`) is the only path
that touches credentials and never uses `localStorage`/`sessionStorage`/cookies.
A stored key is sent to the sidecar once per request to reach the provider you
configured; the sidecar does not persist it beyond that request — or, for a
background agent run, beyond that run. Nothing about
your keys, and no request content, goes to a Vysted-run server — there isn't one.

## SearXNG — optional, unlimited local search

SearXNG is a self-hosted, open-source metasearch engine: pointing Vysted's research
feature at one gives it an unmetered, private search backend instead of the public
scrape it otherwise falls back to. The whole query flow stays local — no vendor REST
call, no API key, no telemetry (`sidecar/services/search/searxng.py:3-6`).

Run it from **Settings → Research → Unlimited (Local)**: with Docker Desktop or
OrbStack running, one click pulls the official `searxng/searxng` image, starts it as
a loopback-bound container named `vysted-searxng`, and health-checks it until it's
serving JSON search (`sidecar/services/searxng_manager.py:66-67,338-351,698-790`).
There is no manual `docker run` command to copy here — the manager owns pull,
configure, start, and teardown end to end, and none is documented anywhere else in
this repo. A remote or already-running instance can be used instead via the same
panel's "Advanced: custom instance URL" field (`src/store/search-settings.ts:179-184`).

Without it — or before setup finishes — research quietly falls back to the keyless
tier (DuckDuckGo, Brave, and Mojeek in rotation, each rate-limited "by nature" and
gated by its own circuit breaker), never to an error state. Settings shows this
plainly: the SearXNG row's status chip reads "Docker not found," "Not set up," or
"Degraded — engines blocked," with a quiet note under it — "Until set up, research
uses limited keyless search." — that stays visible until the instance is actually
`ready`.
<!-- degraded-behaviour sourced from: src/store/search-settings.ts:5-8 (keyless-fallback,
     never a user-facing error state); sidecar/services/search/registry.py:86-88 (None =
     honest fallback signal, caller floors to keyless); sidecar/services/searxng_manager.py:3-4
     (T1 keyless "rate-limited by nature"); src/components/SettingsPanel.tsx:839-862 (status
     chip copy), 925 (fallback note), 1016-1022 (degraded copy) -->

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
[`docs/PLUGIN_DEVELOPMENT.md`](./docs/PLUGIN_DEVELOPMENT.md) to build one — its
panel-registration section (the `panels.ts` / `PLUGIN_COMPANIONS` glue) predates the
current plugin runtime and is being rewritten (R15-DOCS-015). Use
[`plugins/example/`](./plugins/example/) as the working reference.

## License

The core is **source-available**, not open-source: free for noncommercial use under
[PolyForm Strict 1.0.0](./LICENSE); any commercial use, modification, or
redistribution needs a paid commercial license
([`COMMERCIAL_LICENSE.md`](./COMMERCIAL_LICENSE.md), plain-language summary in
[`LICENSING.md`](./LICENSING.md)). Every commit made before the relicensing commit
remains available under its original AGPL-3.0 terms — relicensing only changes the
terms for new work going forward (`LICENSING.md`). The plugin contract
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

Version 0.8.0 at this commit. The 0.9.0 bump is prepared on its own branch and
merges right after the r15-rc1 tag (tag and sha: confirmed at the tag).
Phases 0–10 are merged to `main` (data layer, charting, AI copilot,
node editor + backtest, agent-write safety, macro/research/QuantLib, integrations
hub); trading was removed from the product (D81). An agent-native redesign is in
flight on top of that baseline — see
[`docs/CURRENT_STATE.md`](./docs/CURRENT_STATE.md) for what's built, buggy, or
deferred, and [`docs/BLUEPRINT.md`](./docs/BLUEPRINT.md) for the architecture.
<!-- VERIFY: whether the sha this build ships from is signed off as release-ready by the lead at rc2; this draft states no release pipeline exists per this run's decision log only -->

<!-- refresh f4444790 to 4d89314: no change to any source this draft draws on (docs/README.md, package.json, specs/001-agent-native-redesign/spec.md moved between the two shas, but none of it is quoted here; version still 0.8.0 consistent everywhere per FACTS.md, no release pipeline landed) — header bumped, critic footer cleared for the critic's next pass, content otherwise unchanged from f4444790 -->

<!-- critic-footer -->

## Critic findings applied

1. applied — added a known-limitation sentence to the BYOK section (with fail-safe and
   a pointer to the release notes), sourced from `types/proposed-change.ts:38-46`
   (`AUTO_APPLIED_KINDS`) and RELEASE_NOTES.draft.md's "Known limitations at rc1"
   heading; did not reuse the struck grounding clause.
2. applied — replaced the VERIFY comment with reader-visible prose: version stays
   0.8.0 at this sha (FACTS.md:18-27, all six sources agree), 0.9.0 lands when the
   prepared version branch merges after the r15-rc1 tag; the tag itself is not
   claimed to exist.
3. applied — removed every "at f4444790" parenthetical from reader prose (the
   Overview, redesign-in-flight callout, both "What it is not" bullets, the BYOK
   provider-registry and keychain citations, and the licensing citation); kept the
   bare relative links. Left the process note at the file's end untouched — it is
   not reader-facing prose citing a fact, it documents the prior refresh step
   itself.
4. applied — "at this sha" became "yet", and the parenthetical now points at
   `docs/redesign/DECISIONS_FOR_OPERATOR.md` §2.8–2.9 (verified: §2.8 = R15-RELEASE-001
   unsigned bundles, §2.9 = R15-RELEASE-002 no release pipeline).
5. applied — added a sentence after the `docs/PLUGIN_DEVELOPMENT.md` link noting its
   panel-registration section predates the current runtime (verified:
   `src/lib/plugin-bootstrap.ts` at the sha uses `CATALOG_ROWS`/`marketplace.ts`, zero
   hits for `PLUGIN_COMPANIONS`/`BUNDLED_PLUGINS`; R15-DOCS-015 in the register JSON)
   and pointed authors at `plugins/example/` instead.
6. applied — named the default (`qwen2.5:7b`) and known (`llama3.1:8b`) Ollama models
   from `sidecar/config/model_registry.json` at the sha, replaced "fully offline" with
   "the model runs on your machine (market data still comes from the network)", and
   added the pull-a-model step.
7. applied — "a broker" became "a router" for OpenRouter, consistent with the "no
   broker connection" line in "What it is not".
