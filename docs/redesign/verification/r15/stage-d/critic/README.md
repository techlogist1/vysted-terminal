<!-- CRITIC of README.draft.md at 4d893147def983623de681effd1bfbae2e7441c5 -->

# Critic — README.draft.md (target: README.md)

Sha: 4d893147def983623de681effd1bfbae2e7441c5 · model: Opus 5.5 · label: stage-d-critic-readme
Read cold as a stranger on a clean Mac; every claim checked against the repo at the sha
(`git show 4d893147:<path>`, `git cat-file -e`), FACTS.md at the same sha, the lead-note refresh
rules, and one world probe (GitHub releases API).

## Verdict: REVISE

All nine findings from the f4444790 pass are fixed. What remains: the draft leaves out the
one-sentence known limitation of the keyless local-model lane that the binding refresh rules
require in the README (finding 1). It also sends plugin authors to a guide that documents a
retired mechanism without saying so (finding 5). The other findings are the version sentence
the refresh rules ask for, stale provenance labels, and precision fixes.

Counts: 7 findings: wrong 2, missing 4, stale 1, unverifiable 0.

## Findings

### 1. MISSING: no known-limitation sentence for the keyless local-model lane
- Location: BYOK section, local-model bullet (line 92). Nothing elsewhere either.
- Evidence: `grep -n -i 'limitation\|release notes\|fabricat\|invented' README.draft.md` returns
  0 hits. The sibling `RELEASE_NOTES.draft.md:176` carries `### Known limitations at rc1 — agent
  chat with a keyless local model`. The refresh rule (lead note, rule 2) requires "README says it
  in one sentence and points at the release notes". FACTS.md:171-189 lists R15-LEAD-030/037/038
  as `blocked_tier4` known limitations. The fail-safe is at `types/proposed-change.ts:38-46`
  (a portfolio write always stages for review).
- Failure: a stranger who picks the "no key, fully offline" path is never told that the agent
  can state an unfetched figure or claim a write it never made. That is the single documented
  limitation of this release.
- Fix: after line 92, add one sentence: "Known limitation: with a keyless local model the
  agent can state a price or metric that no successful tool call returned, or say a portfolio
  change was made when nothing was written. A portfolio change never applies without your
  review. See the release notes, 'Known limitations at rc1 — agent chat with a keyless local
  model'." Do not reuse the struck clause "figures for companies whose call succeeded are
  grounded against the tool result" (FACTS.md:177).

### 2. MISSING: the version sentence does not say how 0.9.0 lands
- Location: Status (line 159, plus the VERIFY comment at lines 159-161).
- Evidence: every version source reads `0.8.0` at the sha (FACTS.md:18-27: `package.json:3`,
  `src-tauri/Cargo.toml:3`, `src-tauri/tauri.conf.json:4`, `sidecar/app.py:329`,
  `src/lib/plugin-bootstrap.ts:38`). Refresh rule 4 says: keep 0.8.0, and say that 0.9.0 lands
  when the prepared version branch merges right after the r15-rc1 tag. The reader-visible text
  says only "Version 0.8.0". The comment says "once the bump has landed on the promoted sha", which
  names neither the branch nor the tag.
- Fix: "Version 0.8.0 at this commit. The 0.9.0 bump is prepared on its own branch and merges
  right after the r15-rc1 tag (tag and sha: confirmed at the tag)." Do not say r15-rc1 exists.
  FACTS.md:148 confirms there is no `r15-*` tag.

### 3. STALE: provenance citations name the superseded sha f4444790 in reader prose
- Location: lines 10, 15, 25, 32, 96, 100, 104 and 133, plus the comment at line 161.
- Evidence: `grep -n f4444790 README.draft.md` returns 10 lines (lines 1 and 170 are the
  markers). The draft is stamped `4d893147`. I re-checked every cited fact at 4d893147 and each
  one still holds (see "Checked and correct"), so only the label is stale. Line 10's
  "(README.md at f4444790, 'Overview')" is also circular: the target file cites itself. The
  f4444790 critic already asked for these to be stripped (its finding 9).
- Fix: delete every "at f4444790" parenthetical and keep the bare relative links. If the lead
  wants the trail until rc2, restamp to 4d893147 and strip at promotion.

### 4. WRONG: the install section points the reader at an unreachable source
- Location: Download and install (lines 38-40): "no code-signing identity at this sha … (open
  items in this run's decision log)".
- Evidence: a stranger cannot resolve "this sha" or "this run's decision log". The real source
  exists at the sha: `docs/redesign/DECISIONS_FOR_OPERATOR.md:133` (§2.8 R15-RELEASE-001,
  unsigned desktop bundles) and `:146` (§2.9 R15-RELEASE-002, no GitHub release pipeline).
  The claim itself is true. `git ls-tree 4d893147 .github/workflows/` lists only
  `build.yml, lint.yml, test.yml`, and `tauri.conf.json` has no `signingIdentity`. A world
  probe with `curl -A <browser UA> https://api.github.com/repos/techlogist1/vysted-terminal/releases`
  returned HTTP `200` and the body `[ ]`, meaning zero releases.
- Fix: replace "at this sha" with "yet", and replace the parenthetical with "(tracked in
  [`docs/redesign/DECISIONS_FOR_OPERATOR.md`](./docs/redesign/DECISIONS_FOR_OPERATOR.md)
  §2.8–2.9)".

### 5. MISSING: the plugin guide the README recommends documents a retired mechanism
- Location: Plugin contract (lines 122-123): "See `docs/PLUGIN_DEVELOPMENT.md` to build one."
- Evidence: `git show 4d893147:docs/PLUGIN_DEVELOPMENT.md` lines 286 and 348-351 tell authors
  to ship a sibling `panels.ts` that `plugin-bootstrap.ts` "reads via `PLUGIN_COMPANIONS`".
  Running `git grep -c 'PLUGIN_COMPANIONS\|BUNDLED_PLUGINS' 4d893147 -- src/lib/plugin-bootstrap.ts
  src/lib/marketplace.ts` finds no match (rc=1). The catalog is now `src/lib/marketplace.ts:59`
  `CATALOG_ROWS` (FACTS.md:83). The drift is registered as R15-DOCS-015, `blocked_tier4`
  ("Plugin docs describe a plugin system that no longer exists", register JSON at the sha).
- Failure: a plugin author follows the guide and ships a `panels.ts` that nothing reads, so
  the panels never appear.
- Fix: append "Its panel-registration section (the `panels.ts` / `PLUGIN_COMPANIONS` glue)
  predates the current plugin runtime and is being rewritten (R15-DOCS-015). Use
  [`plugins/example/`](./plugins/example/) as the working reference."

### 6. MISSING: the Ollama path names no model, and "fully offline" overreaches
- Location: BYOK section, line 92: "a local model run through Ollama — no key, fully offline".
- Evidence: in `sidecar/config/model_registry.json` at the sha, the `ollama` entry has
  `default_model: "qwen2.5:7b"`, `known_models: ["qwen2.5:7b", "llama3.1:8b"]` and
  `default_base_url: "http://127.0.0.1:11434"`. A fresh Ollama install has no model pulled, so
  the copilot has nothing to call. The copilot's data tools (quotes, news, SEC) still fetch
  from the network: the DuckDuckGo floor is `sidecar/services/search/ddg.py`, and SEC fetches
  send a network User-Agent at `sidecar/services/sec_filings_provider.py:89`. Only the model
  runs offline. The known-limitation lane is `llama3.1:8b` (lead note, rule 2).
- Fix: "a local model through [Ollama](https://ollama.com): no key, and the model runs on your
  machine (market data still comes from the network). Pull a model first, for example
  `ollama pull qwen2.5:7b` (the default) or `llama3.1:8b`."

### 7. WRONG (minor, non-blocking): OpenRouter is called "a broker"
- Location: BYOK section, line 94: "OpenRouter (a broker that routes to most of the above through one key)".
- Evidence: line 26 of the same draft says "There is no broker connection". D81 removed brokers
  from the product (`docs/BROKER_INTEGRATIONS.md:3-5` at the sha). OpenRouter is an LLM router,
  not a broker. In a finance README, "broker" next to D81 contradicts the "What it is not"
  section on a first read.
- Fix: "OpenRouter (a router that reaches most of the above through one key)".

## Stranger-on-a-clean-Mac walk-through

Following the draft top to bottom on a clean Mac works:

1. Install the prerequisites in the table: Xcode CLT, Node 24 (`.node-version` = `24`), pnpm 10
   (`packageManager: pnpm@10.32.1`), rustup stable (`Cargo.toml:7` sets `rust-version = "1.77"`;
   there is no `rust-toolchain` or `rust-toolchain.toml` at the sha), and exactly Python 3.13.
2. Run `git clone`, then `pnpm install`, then `pnpm tauri dev`. `package.json:21` defines
   `"tauri": "tauri"`, and `@tauri-apps/cli` 2.11.1 is a devDependency.
3. The `beforeDevCommand` (`tauri.conf.json:9`, `node scripts/ensure-all-sidecars.mjs && pnpm
   dev`) builds the three sidecars into `sidecar/**/.venv` on 3.13 (`scripts/sidecar-specs.mjs:259-265`,
   `scripts/build-python.mjs:12,44-50`). It then starts Vite on `:5173` (`devUrl`), and the
   debug app launches.
4. The debug build uses the git-ignored `dev-keystore.json`, so there is no keychain prompt
   (`keychain.rs:11-12,92`, `.gitignore:60-61`).
5. The `source sidecar/.venv/bin/activate` advice for `pnpm ci-local` resolves. That venv is
   the main sidecar's build venv, and `requirements-dev.txt` pins `ruff==0.15.12` and
   `pytest==9.0.3`.

The "no installable release" statement is honest (finding 4 probe). The one gap in the
walk-through is the keyless copilot: without a pulled Ollama model it has nothing to call
(finding 6), and the reader is never warned about its known limitation (finding 1).

## Checked and correct

- Line 1 is exactly `<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->`.
- `grep -ic <banned word>` returns 0. The banned "low-latency…" phrase returns 0. The draft contains no
  key, token, keystore content or secret shape.
- Every path the draft names exists at 4d893147. `git cat-file -e` passed for 28 paths,
  including `specs/001-agent-native-redesign/spec.md`,
  `docs/screenshots/v0.8.0/research-cockpit-hero.png`, `LICENSE-APACHE`,
  `plugins/example/{index.ts,example.test.ts,manifest.json}`, `docs/README.md` (a real
  "Start here" index), `styles/tokens.css`, `scripts/smoke-test-sidecars.mjs`,
  `components.json` and `vite.config.ts`.
- Commands:
  - `pnpm install`, `pnpm tauri dev`, `pnpm ci-local` and `node scripts/smoke-test-sidecars.mjs`
    all exist (FACTS.md:47-66).
  - The ci-local comment matches its steps, and the bare-`python` caveat is correct.
  - The smoke-test comment matches `smoke-test-sidecars.mjs:39-49` (`/health` poll, `/agents`,
    `/mcp/status`, both MCP sidecars).
  - "Later runs skip it unless sidecar source changes" matches `scripts/sidecar-staleness.mjs:12-15`.
- Stack: Vite + React (`package.json:8` `"dev": "vite"`, `:83` `vite ^8.0.16`, no `next`). The
  three PyInstaller sidecars are `tauri.conf.json:40-44`.
- Prerequisites match the repo:
  - Node 24+ matches `.node-version`. There is no `engines` field.
  - pnpm 10+ matches `packageManager` and `build.yml` `version: 10.32.1`.
  - Rust stable matches `build.yml` `dtolnay/rust-toolchain@stable`.
  - Python "3.13 (exactly)" matches `build-python.mjs:12` `WANT = "3.13"`, the `VYSTED_PYTHON`
    override at `:32-38`, and `build.yml` `python-version: "3.13"`.
  - The Linux package list matches `build.yml:21-31` (`build-essential` is named separately,
    and `curl wget file` are omitted, which is harmless).
  - Xcode CLT, the Windows VS Build Tools and the WebView2 note are consistent with
    `CONTRIBUTING.md:24-25`. `CONTRIBUTING.md:26` still says "Python 3.13+", which is wrong.
    Out of this draft's scope; noted for the lead.
- No trading:
  - The D81 wording and date match `docs/BROKER_INTEGRATIONS.md:3-5`.
  - The draft never presents a broker, order, paper account or mode switch as a feature.
  - The tracked Portfolio panel is kept.
  - The "not investment advice" heading matches `COMMERCIAL_LICENSE.md:36-38`.
- Licence:
  - The `LICENSE` heading is PolyForm Strict 1.0.0.
  - The AGPL-3.0 history rule is at `LICENSING.md:28-33`.
  - The Apache-2.0 carve-out list at `LICENSING.md:40-53` includes `types/plugin-runtime.ts`
    and the header-less `manifest.json`.
  - SPDX `Apache-2.0` is line 1 of `types/plugin.ts`, `types/plugin-runtime.ts`,
    `plugins/example/index.ts` and `plugins/example/example.test.ts`.
- BYOK:
  - The provider set in `model_registry.json` is anthropic, openai, gemini, groq, deepseek, xai
    and openrouter (`requires_key: true`), plus ollama (`requires_key: false`). That is seven
    keyed plus Ollama, eight in total.
  - `keychain_set/get/delete` are at `keychain.rs:299,316`, the release/debug split at
    `:6,11,92`, and the frontend-only credential path at `src/lib/keychain.ts:11-14`.
  - The background-run key is held for the run only (`sidecar/routers/runs.py:24`).
  - "No Vysted-run server" holds. The only network endpoint in the app config is the updater,
    which points at GitHub releases (`tauri.conf.json:48-51`). Other `vysted.*` strings are a
    JSON-schema `$id`, User-Agent contact strings and an OpenRouter `HTTP-Referer` header, none
    of which is a server Vysted runs.
- Project layout: the plugin list matches FACTS.md:81 (example, openbb-mcp, vysted-lenses,
  vysted-news, yfinance).
- Status: "Phases 0–10 merged" matches the `CONTRIBUTING.md:8-10` scope note. The macOS
  production build is not claimed as proven, and install is deferred to rc2 with the reason
  stated.
