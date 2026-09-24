<!-- CRITIC of README.draft.md at f444479031d7d493b7955b9af041d18e7c7a40cc -->

# Critic — README.draft.md (target: README.md)

Sha: f444479031d7d493b7955b9af041d18e7c7a40cc · model: Fable 5.1 · label: stage-d-critic-readme
Read cold as a stranger on a clean Mac; every claim checked against the repo at the sha
(`git show <sha>:<path>`), FACTS.md, and one world probe (GitHub releases API).

## Verdict: REVISE

Findings 1–4 would either state a false fact to every reader (the frontend framework) or
make a top-to-bottom follow-through fail on a clean Mac (Python version, Xcode CLT,
`pnpm ci-local`'s bare `python`). The rest are precision fixes.

Counts: 9 findings — wrong 6, missing 2, stale 0, unverifiable 1.

## Findings

### 1. WRONG — the frontend is Vite + React, not Next.js
- Location: intro (line 9 "a Next.js frontend"); Project layout (line 131 "Next.js frontend").
- Evidence: `package.json:8` `"dev": "vite"`, `:9` `"build": "vite build"`, `:82` `"vite": "^8.0.16"`,
  `:68` `"@vitejs/plugin-react"`; `git show <sha>:package.json | grep '"next'` → no `next`
  dependency; `vite.config.ts:1-8` (`defineConfig`, `react()` plugin) and `index.html` exist
  at the repo root; `src-tauri/tauri.conf.json:8-9` `devUrl http://localhost:5173`,
  `beforeDevCommand "... && pnpm dev"` (= vite). Migration commit in the sha's history:
  `git log -S'"next":' <sha> -- package.json` → `8c2f9ab9 feat(shell): migrate Next.js -> Vite 8 + React 19 (WS1)`.
- Fix: line 9 → "a Vite + React frontend"; line 131 → "Vite + React 19 frontend (TypeScript,
  Tailwind, shadcn/ui)". (Note for the lead, out of this draft's scope: `README.md:27,155`,
  `CLAUDE.md` Stack and `docs/CURRENT_STATE.md:117,179,469` at the sha carry the same stale
  "Next.js 16 static-export" claim.)

### 2. WRONG — Python "3.13+" — the build demands exactly 3.13
- Location: Build from source table (line 51 "Python | 3.13+").
- Evidence: `scripts/build-python.mjs:12` `const WANT = "3.13"`; `:44-51` tries
  `python3.13`, `python3` (or `py -3.13`, `python` on Windows) and throws
  `No Python 3.13 found ... Install Python 3.13 (e.g. brew install python@3.13) or set VYSTED_PYTHON`
  unless the interpreter reports exactly `3.13`; `:3-6` explains Homebrew's `python3` is
  already 3.14. `scripts/ensure-sidecar.mjs:101-102` calls `ensureBuildVenv` before every
  build, and `tauri.conf.json:9` runs the ensure scripts inside `pnpm tauri dev`. CI pins the
  same: `.github/workflows/build.yml:44-46` `python-version: "3.13"`.
- Failure: a stranger with a current Homebrew Python (3.14) follows the table, runs
  `pnpm tauri dev`, and the beforeDevCommand aborts.
- Fix: "Python | 3.13 (exactly) | `brew install python@3.13`, or set `VYSTED_PYTHON` to a 3.13
  interpreter — the sidecar build refuses any other version".

### 3. MISSING — no macOS (or Linux) C toolchain prerequisite
- Location: Build from source table (line 50 "C/C++ build tools | — | VS Build Tools 2022 on
  Windows"); the section is the only install path the draft offers a Mac reader (line 41
  "run Vysted from source").
- Evidence: `CONTRIBUTING.md:24-25` at the sha lists "VS Build Tools 2022 on Windows, Xcode
  CLT on macOS, `build-essential` on Linux"; `.github/workflows/build.yml:18-31` installs
  `libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf libgtk-3-dev
  build-essential ... libssl-dev` on Linux before anything builds. The draft also dropped the
  Windows WebView2 note the current README carries (`README.md:125-127`).
- Failure: on a clean Mac neither `rustup` nor the Tauri Rust build works without Xcode
  Command Line Tools; the table says nothing.
- Fix: row notes → "Xcode Command Line Tools on macOS (`xcode-select --install`); VS Build
  Tools 2022 'Desktop development with C++' + WebView2 Runtime on Windows; `build-essential`
  plus the webkit2gtk/gtk list in `.github/workflows/build.yml` on Linux".

### 4. MISSING — `pnpm ci-local` needs a bare `python` on PATH, which a clean Mac does not have
- Location: Build from source (lines 62-66 "Before trusting a build, run the CI-parity gate
  ... `pnpm ci-local`").
- Evidence: `package.json:20` — `... && python -m pip install ruff==0.15.12 && ruff check
  sidecar && ... && cd sidecar && python -m pip install -r requirements-dev.txt && pytest`.
  The command pip-installs into whatever `python` resolves to; Homebrew's `python@3.13`
  provides `python3`/`python3.13` only, and macOS ships no `python`. The ensure scripts
  deliberately resolve `python3.13` themselves (`scripts/build-python.mjs:44`) — `ci-local`
  does not.
- Failure: the stranger's `pnpm ci-local` gets through the sidecar build and lint, then dies
  at `python: command not found` (or installs ruff/pytest into an unrelated interpreter).
- Fix: state the precondition next to the command: "`pnpm ci-local` expects `python` to be a
  3.13 interpreter with pip — e.g. `source sidecar/.venv/bin/activate` after the first
  sidecar build" — or, if the lead prefers a code fix, log it in the register and keep the
  README honest until it lands.

### 5. WRONG — Ollama counted among "eight BYOK providers"
- Location: BYOK section (lines 77-78 "one of eight BYOK providers ... Groq, Ollama, DeepSeek").
- Evidence: `sidecar/config/model_registry.json` providers → ids
  `anthropic, openai, gemini, groq, ollama, deepseek, xai, openrouter` (8), and the `ollama`
  entry is `{"id": "ollama", "label": "Ollama (local)", "requires_key": false, ...}`. The
  draft's own preceding bullet (line 76) presents Ollama as the no-key path; the current
  `README.md:41` counts "7 LLM providers" for the keyed set.
- Fix: "seven keyed providers — Anthropic, OpenAI, Gemini, Groq, DeepSeek, xAI, OpenRouter —
  plus Ollama, all eight in one dropdown".

### 6. WRONG — the release-build keystore guarantee is mis-attributed to a test
- Location: BYOK section (lines 85-86 "a release build is asserted, in a test, to never fall
  back to that file").
- Evidence: `src-tauri/src/keychain.rs:376-386` — the test's own doc: "Trivially true in
  debug; genuinely asserts the release arm under `cargo test --release`"; the release arm is
  `#[cfg(not(debug_assertions))]`. No gate runs `--release`: `.github/workflows/test.yml:75`
  and `package.json:20` both run plain `cargo test`. The actual guarantee is structural:
  `keychain.rs:92` `#[cfg(debug_assertions)] mod dev_keystore` and `:20-23` "compiled only in
  debug builds — in a release binary the file code does not exist".
- Fix: "the file-keystore code is compiled only into debug builds (`cfg(debug_assertions)`),
  so a release binary has no file path to fall back to".

### 7. WRONG (minor) — "does not persist it beyond that request" overstates for background runs
- Location: BYOK section (lines 89-90).
- Evidence: `sidecar/routers/runs.py:24` "The BYOK `api_key` crosses for the run only — it
  is never stored in the runs database"; `sidecar/models/workflow.py:110` "Held for the run
  only; never persisted or logged"; foreground path as stated: `src/lib/keychain.ts:13-15`,
  `sidecar/models/agent.py:81`, `sidecar/routers/agents.py:98`, `sidecar/models/llm.py:272`.
  A durable Delegate run holds the key in process memory for the run's lifetime, which
  outlives the HTTP request.
- Fix: "beyond that request — or, for a background agent run, beyond that run".

### 8. UNVERIFIABLE — "Version 0.9.0"
- Location: Status (line 141).
- Evidence: every source-of-truth version is `0.8.0` at the sha — `package.json:3`,
  `src-tauri/Cargo.toml:3`, `src-tauri/tauri.conf.json:4`, `sidecar/app.py:327`,
  `src/lib/plugin-bootstrap.ts:37` (FACTS.md:8-14, version_consistent True); no file is
  0.9.0 yet (FACTS.md:15). The current `README.md:52-53` says "version strings sit at 0.8.0
  pending a release cut". 0.9.0 is the stated target, so this is right for rc2 only if the
  bump lands on the promoted sha.
- Fix: add "version bump to 0.9.0 landed on the promoted sha" to the line-147 VERIFY comment;
  if it has not, print 0.8.0.

### 9. WRONG — draft-provenance citations sit in reader-facing prose
- Location: lines 10, 15, 25, 32, 80, 84, 87, 115 — "(README.md at f4444790, "Overview")",
  "(both present at f4444790)", "`docs/BROKER_INTEGRATIONS.md` at f4444790", etc. (8 sites
  outside the line-1 marker).
- Evidence: `grep -n 'f4444790' README.draft.md` → 9 lines including line 1. The sibling
  drafts carry the same convention (3 each in RELEASE_RUNBOOK.draft.md and
  CURRENT_STATE.draft.md), so this is probably the wave's evidence trail — but the target is
  the public README, and a stranger has no idea what "at f4444790" means. Does not break any
  step; listed so the promotion strips them rather than ships them.
- Fix: at rc2 delete every "at f4444790" parenthetical and turn the bare filenames into the
  relative links the rest of the draft already uses.

## Stranger-on-a-clean-Mac walk-through

Top to bottom, with findings 2-4 fixed, the reader reaches `pnpm tauri dev` and a running
debug build (no keychain prompt — debug uses the git-ignored `dev-keystore.json`,
`keychain.rs:11-12`, `.gitignore:60-61`; `@tauri-apps/cli` is a devDependency,
`package.json:61`; `.node-version` = `24`; `packageManager` = `pnpm@10.32.1`). Without
those fixes they stall at the sidecar build (wrong Python) or before it (no CLT). The
"no installable release" statement is honest: GitHub API `GET
/repos/techlogist1/vysted-terminal/releases` → HTTP 200, `[]` (zero releases, zero assets);
no `.github/workflows/release.yml` at the sha; `tauri.conf.json` `bundle` has no
`macOS.signingIdentity`.

## Checked and correct

- Line 1 is exactly `<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->`.
- No key, token, keystore content or secret shape anywhere in the draft (the only
  credential-adjacent strings are command names and a filename).
- Every path the draft names exists at the sha (`git cat-file -e` × 23: `docs/CURRENT_STATE.md`,
  `specs/001-agent-native-redesign/spec.md`, `docs/screenshots/v0.8.0/research-cockpit-hero.png`,
  `docs/BROKER_INTEGRATIONS.md`, `COMMERCIAL_LICENSE.md`, `types/plugin.ts`,
  `types/plugin-runtime.ts`, `LICENSE-APACHE`, `plugins/example/{index.ts,example.test.ts,manifest.json}`,
  `LICENSING.md`, `docs/PLUGIN_DEVELOPMENT.md`, `LICENSE`, `CONTRIBUTING.md`, `docs/README.md`,
  `docs/BLUEPRINT.md`, `sidecar/config/model_registry.json`, `src-tauri/src/keychain.rs`,
  `src/lib/keychain.ts`, `styles/tokens.css`, `scripts/smoke-test-sidecars.mjs`,
  `plugins/{yfinance,vysted-news,vysted-lenses,openbb-mcp}`).
- Commands: `pnpm install`, `pnpm tauri dev` (`package.json:21` `"tauri": "tauri"`),
  `pnpm ci-local` (`:20`), `node scripts/smoke-test-sidecars.mjs` all exist; the ci-local
  comment matches its steps; the smoke-test comment matches `smoke-test-sidecars.mjs:42-49`
  (polls `/health`, checks `/agents` roster and `/mcp/status`, spawns both MCP sidecars).
- "The first `pnpm tauri dev` builds three Python sidecar binaries" — `tauri.conf.json:9`
  `beforeDevCommand: node scripts/ensure-all-sidecars.mjs && pnpm dev`; `externalBin`
  lists exactly three (`tauri.conf.json:40-44`); staleness-aware rebuild per
  `scripts/sidecar-staleness.mjs` (CLAUDE.md Gotchas).
- Node 24+ (`.node-version` = `24`; `build.yml:40-41` uses it), pnpm 10+ (`packageManager`
  `pnpm@10.32.1`), Rust latest stable (`build.yml:49` `dtolnay/rust-toolchain@stable`;
  `Cargo.toml:7` `rust-version = "1.77"`; no `rust-toolchain` file at the sha).
- No trading: D81 wording and date match `docs/BROKER_INTEGRATIONS.md:3-5` and commit
  `a122dbf6` (2026-09-23, `feat(d81): remove trading from the product`); the draft never
  presents a broker, order, paper account or mode switch as a feature; the tracked
  Portfolio panel (CSV export via `@/lib/csv`, `PortfolioPanel.test.tsx:14-16`) is kept.
- "Not investment advice" quotes `COMMERCIAL_LICENSE.md:36-40` heading and text accurately.
- Licence: `LICENSE` first heading `# PolyForm Strict License 1.0.0`; `LICENSING.md:28-33`
  (AGPL-3.0 history rule) and `:40-51` (Apache-2.0 carve-out list, including the
  header-less `manifest.json`) match the draft verbatim in substance; SPDX
  `Apache-2.0` headers confirmed on `types/plugin.ts:1`, `types/plugin-runtime.ts:1`,
  `plugins/example/index.ts:1`, `plugins/example/example.test.ts:1`.
- Six plugin capabilities (data, panels, commands, agents, nodes, control plane) — CLAUDE.md
  Tier-1 section; `types/plugin.ts` present.
- Keychain path: `src/lib/keychain.ts:11-13` "the ONLY frontend path that reads or writes
  credentials, and it never touches localStorage / sessionStorage / cookies";
  `keychain.rs:12` `<app-data-dir>/dev-keystore.json`; `.gitignore:60-61`.
- Keyless floor: `sidecar/services/search/ddg.py` exists (DuckDuckGo).
- Panels named in the intro (charts, watchlist, news, portfolio, screener, macro, SEC
  filings, node editor) all appear in FACTS.md panels (lines 166-185).
- Contributions: `CONTRIBUTING.md:3-6` "Contributions are closed for now ... not accepting
  pull requests ... Issues and bug reports are still welcome"; `:12-13` open-an-issue-first.
- "Phases 0–10 are merged to `main`": `git log origin/main` shows the phase-10 merges
  (`3123e7cc`, `d9c34b2e`, `1c649a51`).
- Clone URL matches `git remote -v` (`github.com/techlogist1/vysted-terminal`).
- Plugin list in Project layout matches FACTS.md plugins (example, openbb-mcp, yfinance,
  vysted-news, vysted-lenses).
- The macOS production build is not claimed proven; the install section defers to rc2 and
  says why (no release, no signing identity) — consistent with DECISIONS_FOR_OPERATOR §2.8/2.9
  (FACTS.md:233-238).
