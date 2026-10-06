<!-- FACTS at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave -->

## Resolution

- sha = `4d893147def983623de681effd1bfbae2e7441c5` (full), sha7 = `4d893147`.
- ancestry: `git merge-base --is-ancestor 4d893147... 004-r4-experience-rebuild` → is an ancestor (in fact HEAD of that branch's docs history at capture time).
- mode: refresh. previous_sha (from the prior `FACTS.json` in this dir) = `f444479031d7d493b7955b9af041d18e7c7a40cc` ("docs(r15): stage-d docs-and-scans workflow script and plan").

## Delta since previous_sha

- `git log --oneline f4444790..4d893147` = 5 commits: `b7707120`, `b3b4034d`, `c8d807a6`, `3d64ca17`, and `4d893147` (HEAD) — see the log dump above the fold in the previous tool output; one-line: register.py-status-lags-the-JSON note, stage-d-docs.js note arg, run-report pre-refresh, version-branch-launch note, pacing-change-4 ack.
- `git diff --stat f4444790 4d893147` per top-level dir (numstat, files/+/-): `docs` 2086 files +207509/-867; `sidecar` 190 files +55420/-2430; `src` 124 files +6273/-1341; `scripts` 15 files +1027/-702; `types` 6 files +105/-15; `vitest.config.ts` 1 +1/-1; `specs` 1 +15/-7; `pnpm-lock.yaml` 1 +3/-0; `package.json` 1 +2/-1; `CHANGELOG.md` 1 +359/-0. (The large `docs`/`sidecar` counts are because `previous_sha` sits far back near the start of the R15 Stage-D wave, not evidence of a Stage-D write outside its lane — Stage D itself only ever touches `docs/redesign/verification/r15/stage-d/`.)

## Versions

Source: `git show <sha>:<path>` for each.

| Source | Value | path:line |
|---|---|---|
| package.json `"version"` | `0.8.0` | `package.json:3` |
| src-tauri/Cargo.toml `[package] version` | `0.8.0` | `src-tauri/Cargo.toml:3` |
| src-tauri/tauri.conf.json `"version"` | `0.8.0` | `src-tauri/tauri.conf.json:4` |
| sidecar/app.py `FastAPI(version=...)` | `0.8.0` | `sidecar/app.py:329` |
| `HOST_VERSION` (plugin-bootstrap.ts) | `0.8.0` | `src/lib/plugin-bootstrap.ts:38` |
| src-tauri/Cargo.lock `vysted-terminal` entry | `0.8.0` | `src-tauri/Cargo.lock:5486-5487` |

`version_consistent` = **true** (all six equal `0.8.0`).

`0.9.0` already appears at this sha in: `docs/BLUEPRINT.md:238` ("20 shipped in 0.9.0"), `docs/redesign/DECISIONS_FOR_OPERATOR.md:237` ("before any public 0.9.0 announcement"), test-fixture/coincidental hits in `sidecar/tests/test_schema_version.py:226,238` and `src/lib/plugin-runtime.test.ts:564` (semver-compare assertions using the literal `"0.9.0"`, not a real product version), and unrelated crate versions inside `src-tauri/Cargo.lock` (`rand_chacha`, `schemars`, etc. — coincidental crate versions, not this product's). No load-bearing "shipping version is 0.9.0" claim exists at this sha; per the lead note, 0.9.0 lands only when the prepared version branch (`worktree-agent-r15-version-0.9.0`) merges after the r15-rc1 tag.

### Every other `0.8.0` occurrence (`git grep -nF '0.8.0'`, excluding CHANGELOG.md/docs/archive/docs/redesign/verification/docs/screenshots/pnpm-lock.yaml)

99 hits total (see `v080.txt` in the scratchpad for the full list). Classed:

- **load_bearing** (code/config/test assertions that must move together at a real bump): `package.json:3,77` (product version + an unrelated devDependency pin `prettier-plugin-tailwindcss@0.8.0`, coincidental), `plugins/vysted-lenses/manifest.json:6`, `plugins/vysted-news/manifest.json:6`, `plugins/yfinance/manifest.json:6` (each plugin's `requiredHostVersion`), `sidecar/app.py:329`, `sidecar/tests/test_data_cache.py:131,133,141,142,150`, `sidecar/tests/test_schema_version.py:220,223,228,229,239`, `src-tauri/Cargo.lock:281,290,758,2426,2443,3351,3368,5487`, `src-tauri/Cargo.toml:3`, `src-tauri/tauri.conf.json:4`, `src/components/SettingsPanel.test.tsx:886`, `src/lib/plugin-agents.test.ts:77`, `src/lib/plugin-bootstrap.ts:38`, `src/lib/plugin-runtime.test.ts:511,521,530,555,558,560,563,564,565,568,569`, `src/lib/plugin-runtime.ts:133` (doc comment on a real parse path), `src/lib/workspace.test.ts:1574`, `src/modules/marketplace/MarketplacePanel.test.tsx:40`, `src/store/marketplace.test.ts:46`.
- **prose** (docs/report narrative, not enforced by any test or config): `BLOCKERS.md:3,45,212,262,278`, `README.md:15,53,66`, `docs/CURRENT_STATE.md:151,262,636,815,845`, `docs/redesign/AGENT_TOOLUSE_PLAN.md:5,82,241`, `docs/redesign/DECISIONS.md:120,131`, `docs/redesign/DECISIONS_FOR_OPERATOR.md:146`, `docs/redesign/HANDOFF_VERIFIED.md:22`, `docs/redesign/OVERNIGHT_BUILD_REPORT.md:4`, `docs/redesign/OVERNIGHT_BUILD_REPORT_R4S3.md:70,79,157,235,280`, `docs/redesign/R4_BUILD_SEQUENCE.md:9,187`, `docs/redesign/R4_DESIGN_LANGUAGE.md:367`, `docs/redesign/R9_TRACK_LOOP_REPORT.md:5`, `docs/redesign/REBUILD_R3_REPORT.md:3,17,108,130,174,239,301`, `docs/redesign/REBUILD_R3_SPEC.md:72,745,850,854`, `docs/redesign/REBUILD_R4_REPORT.md:9,124`, `docs/redesign/REBUILD_R4_SESSION2_REPORT.md:4,149`, `docs/redesign/REBUILD_R4_SPEC.md:10`, `docs/research/phase-10/blueprint-bugfix.md:3`, `docs/research/phase-10/blueprint-customizability.md:5,552`, `docs/research/phase-10/hunt-error-surfaces.md:409`, `docs/research/phase-10/hunt-rust-tauri.md:26,401`, `docs/research/phase-10/map-ai-copilot.md:173`, `docs/research/phase-10/map-extensibility.md:8`.

## Sidecars

- `bundle.externalBin` (`src-tauri/tauri.conf.json:40-44`): `binaries/vysted-sidecar`, `binaries/vysted-openbb-mcp-sidecar`, `binaries/vysted-sec-edgar-mcp-sidecar`.
- All three are built by one orchestrator, `node scripts/ensure-all-sidecars.mjs [--force]` (`scripts/ensure-all-sidecars.mjs`), which loops `SIDECAR_SPECS` from `scripts/sidecar-specs.mjs`. Per-sidecar ensure scripts also exist: `scripts/ensure-sidecar.mjs`, `scripts/ensure-openbb-mcp-sidecar.mjs`, `scripts/ensure-sec-edgar-mcp-sidecar.mjs`.
- `vysted-sidecar` (main): PyInstaller `--name vysted-sidecar`, `sourceDir = sidecar/`, `requirements-dev.txt`, entry is the FastAPI app in `sidecar/app.py`; spawned from `src-tauri/src/lib.rs:276` (`app.shell().sidecar("vysted-sidecar")`); venv `sidecar/.venv` (present on this machine).
- `vysted-openbb-mcp-sidecar` (mcp): PyInstaller `--name vysted-openbb-mcp-sidecar`, `sourceDir = sidecar/openbb_mcp_subprocess/`, `requirements.txt`, entry `openbb_mcp_server.app.app:main`; spawned from `src-tauri/src/openbb_mcp.rs`; venv `sidecar/openbb_mcp_subprocess/.venv` (present).
- `vysted-sec-edgar-mcp-sidecar` (mcp): PyInstaller `--name vysted-sec-edgar-mcp-sidecar`, `sourceDir = sidecar/sec_edgar_mcp_subprocess/`, `requirements.txt`, entry `sec_edgar_mcp.server`; spawned from `src-tauri/src/sec_edgar_mcp.rs`; venv `sidecar/sec_edgar_mcp_subprocess/.venv` (present).
- (`scripts/sidecar-specs.mjs` is the single source of truth for all three PyInstaller command lines, per its own header comment, R15-CODE-PLATFORM-026.)

## Scripts (`package.json` "scripts", verbatim)

```
dev = vite
build = vite build
lint = eslint . && node scripts/audit-design-tokens.mjs
format = prettier --write .
format:check = prettier --check .
typecheck = tsc --noEmit
test = vitest run
test:watch = vitest
sidecar:build = node scripts/ensure-sidecar.mjs --force
openbb-mcp-sidecar:build = node scripts/ensure-openbb-mcp-sidecar.mjs --force
sec-edgar-mcp-sidecar:build = node scripts/ensure-sec-edgar-mcp-sidecar.mjs --force
sidecars:build = node scripts/ensure-all-sidecars.mjs --force
ci-local = pnpm install --frozen-lockfile && node scripts/ensure-all-sidecars.mjs && pnpm lint && pnpm format:check && pnpm typecheck && cargo fmt --manifest-path src-tauri/Cargo.toml --check && cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings && python -m pip install ruff==0.15.12 && ruff check sidecar && ruff format --check sidecar && pnpm test && cargo test --manifest-path src-tauri/Cargo.toml && cd sidecar && python -m pip install -r requirements-dev.txt && pytest
tauri = tauri
tauri:mcp = tauri dev --features dev-tools
tauri:dev = pnpm tauri:mcp
```
Source: `package.json` (`"scripts"` block) at the sha.

## CI (`.github/workflows/*.yml`)

Three workflows, each triggered `on: push: branches: [main]` and `pull_request:` (no other trigger), each with an OS matrix `[windows-latest, macos-latest, ubuntu-latest]`:

- `build.yml` — `name: build`, job `build`.
- `lint.yml` — `name: lint`, job `lint`.
- `test.yml` — `name: test`, job `test`.

Source: `.github/workflows/{build,lint,test}.yml` lines 1-13 each.

## Plugins (`plugins/`)

Directory listing (`git ls-tree <sha>:plugins`): `example`, `openbb-mcp`, `vysted-lenses`, `vysted-news`, `yfinance`.

The `CLAUDE.md` "add to both BUNDLED_PLUGINS and PLUGIN_COMPANIONS" model described in this repo's project instructions is **stale at this sha**: `src/lib/plugin-bootstrap.ts` no longer defines `BUNDLED_PLUGINS`/`PLUGIN_COMPANIONS` (grep for both returns nothing in that file). The catalog now lives in `src/lib/marketplace.ts:59` as `CATALOG_ROWS: CatalogRow[]`, with 5 entries matching the 5 plugin dirs one-to-one by `pluginId`: `vysted-yfinance` (`:63`), `openbb-mcp` (`:79`), `vysted-lenses` (`:94`), `vysted-news` (`:108`), `vysted-example` (`:143`). `plugin-bootstrap.ts` derives panels/commands per plugin instance from the runtime (`moduleForPlugin`, `:134`) rather than a static companion map. This drift (docs vs. code) is filed as `R15-DOCS-015` — "plugin docs describe the retired panels.ts/PLUGIN_COMPANIONS model" (`docs/redesign/DECISIONS_FOR_OPERATOR.md:248`, status `blocked_tier4` per the register).

Licence headers/fields were not individually opened per plugin manifest at this pass beyond the `requiredHostVersion` fields already noted in **Versions**; each plugin's own licence posture is out of this fact-gathering role's scope (see `types/plugin.ts` / example plugin note in project CLAUDE.md: plugin contract + example plugin are Apache-2.0, the rest under the repo's PolyForm license — unverified path:line here, carried from project instructions only).

## Agents (`sidecar/agents/*.json`)

14 files total minus `_schema.json` = **13** first-party agents: `buffett`, `copilot`, `dalio`, `druckenmiller`, `graham`, `klarman`, `lynch`, `marks`, `munger`, `portfolio_advisor`, `researcher`, `soros`, `strategy_critic` (plus `README.md`, not a JSON agent). `sidecar/tests/test_agent_runtime.py:213` asserts `len(json_files) == 13` ("the roster — keep in sync with the count tests"), consistent. Other roster-count references: `sidecar/tests/test_agents_router.py:37`, `sidecar/tests/test_capability_completeness.py:117-118`, `sidecar/tests/test_health.py:38-42`, `sidecar/tests/test_mcp_server.py:123`.

## Panels (`src/modules/*/index.ts`)

21 module dirs under `src/modules/` (`agent-builder, analyst-ratings, backtest, chart, chat, earnings, equity-overview, macro, marketplace, news, node-editor, notes, platform, plugin-manager, portfolio, quant, research, safety, screener, sec, watchlist`; `index.ts` and `panel-context-publishers.test.tsx` also live at that level but are not module dirs).

`panels:` arrays exist in every module's `index.ts` except `chat` (`panels: []`) and `safety` (no `index.ts` panels line at all — `safety` registers no panels). Sampled panel/command ids (path = `src/modules/<mod>/index.ts`):

- `agent-builder`: panel `agent-builder`, command `agent-builder.open`.
- `analyst-ratings`: panel `analyst-ratings`, command `analyst-ratings.open`.
- `backtest`: panel `backtest`, command `backtest.open`.
- `chart`: panel `chart`, command `chart.open`.
- `earnings`: panel `earnings-calendar`, command `earnings.open-calendar`.
- `equity-overview`: panel `equity-overview`, command `equity-overview.open`.
- `macro`: panel `macro`, command `macro.open`.
- `marketplace`: panel `marketplace`, command `marketplace.open`.
- `news`: panel `news`, command `news.open`.
- `node-editor`: panel `node-editor`, command `node-editor.open`.
- `notes`: panel `notes`, command `notes.open`.
- `platform`: panel `settings`, commands `platform.open-settings`, `platform.save-workspace`, `platform.load-workspace`, `platform.new-research-space`.
- `plugin-manager`: panel `plugin-manager`, command `plugin-manager.open`.
- `portfolio`: panel `portfolio`, command `portfolio.open`.
- `quant`: panels `option-pricer`, `greeks-dashboard`, `option-chain`, `bond-pricer`, `yield-curve`; commands `quant.open-option-pricer`, `quant.open-greeks-dashboard`, `quant.open-option-chain`, `quant.open-bond-pricer` (+ one more not sampled).
- `research`: panel `brief`, command `research.open`.
- `screener`: panel `screener-panel`, command `screener.open`.
- `sec`: module id `sec-filings`, panel `sec-filings`, command `sec-filings.open`.
- `watchlist`: panel `watchlist`, command `watchlist.open`.

(No broker/order/trading panel exists anywhere in this listing — consistent with D81, trading removed from the product.)

## Register (`docs/redesign/verification/vysted-r15-register.json`)

`counts` field (authoritative per the lead note — never `register.py status`, which lags): `raw=887, entries=652, rejections=76, critical=16, high=116, medium=293, low=227`.

By status (computed from `entries[].status`, matching the lead note's figures exactly): `fixed=391, open=206, blocked_tier4=25, removed_with_feature=14, needs_gui=11, not_a_defect=5` (sums to 652), **as of `4d893147`**. Update as of `4c6dfe8c` (batch-24 merged `6778f892`): `R15-LEAD-035` moved `open` → `blocked_tier4`, so the current split is `fixed=391, open=205, blocked_tier4=26` (register JSON, read directly).

**Open critical/high/medium** (severity-status intersection): **zero as of `4c6dfe8c`.** (Was exactly **one** — `R15-LEAD-035`, medium, subsystem `agent-tools` — at this file's `4d893147` capture; see the Known-limitations block and trailer below for the disposition.)

**needs_gui** (11): `R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025, R15-UI-050, R15-UI-083, R15-UI-084, R15-DOCS-024, R15-LIFECYCLE-040`.

**blocked_tier4** (25): `R15-AGENT-017, R15-RELEASE-001, R15-RELEASE-002, R15-RELEASE-003, R15-RELEASE-004, R15-AGENT-049, R15-AGENT-064, R15-CODE-FRONTEND-013, R15-CODE-PLATFORM-010, R15-CODE-PLATFORM-015, R15-CODE-PLATFORM-071, R15-CODE-PLATFORM-073, R15-CROSS-PLATFORM-001, R15-DOCS-002, R15-DOCS-003, R15-DOCS-015, R15-UI-044, R15-UI-088, R15-CODE-PLATFORM-063, R15-DOCS-008, R15-DOCS-011, R15-RELEASE-012, R15-LEAD-030, R15-LEAD-037, R15-LEAD-038`.

## Decisions (`docs/redesign/DECISIONS_FOR_OPERATOR.md`)

Section headings present (`### N.M title`), by section: §1 (1.1-1.4, historical/closed context — 1.2 SUPERSEDED by D81), §2 (2.1-2.21, mostly Tier-4 open blockers; 2.3/2.4/2.5 marked CLOSED: removed with the feature (D81)), §3 (3.1-3.6, accepted gaps / operator-blocked / done-revertable items), §4 (4.1-4.12, the "battery"/LEAD items — every item in §4 that states a status says `open, blocked_tier4` or, for the four LEAD items, a specific disposition):

- 4.5 R15-CODE-PLATFORM-063 — status: `open, blocked_tier4` (`:416`).
- 4.6 R15-DOCS-008 — status: `open, blocked_tier4` (`:433`).
- 4.7 R15-DOCS-011 — status: `open, blocked_tier4` (`:446`).
- 4.8 R15-RELEASE-012 — status: `open, blocked_tier4` (`:460`).
- 4.9 R15-LEAD-030 — status: `blocked_tier4`, fresh verifier concurred in batch-23 (`:524`); recommendation `blocked_tier4` (`:483`).
- 4.10 R15-LEAD-035 — status **as of `4d893147`**: `open` — fresh verifier REFUSED `blocked_tier4` this round; under-match fix goes through batch-24, then concurrence (`:574-578`); recommendation (once concurred) `blocked_tier4` (`:555`). **Update as of `4c6dfe8c`:** status is now `blocked_tier4` — NOT via concurrence. Batch-24 (merge `6778f892`) shipped the named narrowing-only fix, which holds as a strict subset, but a fresh verifier REFUSED certification a fourth time (`stage-c/batch-24/VERDICTS.md`, `LEAD-035-CONCURRENCE.md`); the lead invoked the operator's three-failure rule (pacing change 4) and set `blocked_tier4` as an ESCALATION, not an adjudication-away. `DECISIONS_FOR_OPERATOR.md` §4.10 now carries the operator's two options at rc1: (a) accept the residual as documented with the verifier's wording, or (b) authorise one bounded round for the verifier's further-named guard on rc2 — the lead recommends (b).
- 4.11 R15-LEAD-037 — status: `blocked_tier4`, fresh verifier concurred on corrected wording (`:608`); recommendation `blocked_tier4` (`:593`).
- 4.12 R15-LEAD-038 — status: `blocked_tier4`, fresh verifier concurred (`:647`); recommendation `blocked_tier4` (`:634`).

Every §2.x item that states "Why Tier-4" is a Tier-4 item by definition (touches a Tier-1 locked file/surface: `.github/`, `tauri.conf.json`, `types/plugin.ts`, `CLAUDE.md`, or a core-architecture/spec reversal) — 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14, 2.15, 2.16, 2.17, 2.18, 2.19, 2.20, 2.21 each carry an explicit "Why Tier-4:" line; 2.1, 2.2, 2.6, 2.7 do not (open but not Tier-4-flagged in this pass).

## Git

- `base_tag` = **`r13-bedrock`** (newest tag matching `r13-*`/`r15-*` that is an ancestor of the sha; no `r15-*` tag exists yet at this sha — r15-rc1 has not been cut, per the lead note).
- Commits since `r13-bedrock..4d893147`: **879** total, **265** `--first-parent`.
- First-parent merge subjects since the base tag (most recent first, `git log --first-parent --merges`): `c155e5ad` (Stage C batch 22, W1 only), `86ae79c4` (batch 21), `1abef99b` (batch 20), `ec7f7cd6` (batch 19), `ebc5ed41` (batch 18), `292ba53a` (batch 17), `d64640d2` (batch 16), `74ee3468` (batch 15), `17301f54` (batch 14), `a217a529` (batch 13), `ef33c7f6` (batch 12), `57897778` (rc1 gate fix rounds 1-2), `4097dac4` (batch 11), `f407107f` (batch 10), `6b702305` (batch 9), `68bb7aa4` (batch 8), `e81c9e7c` (batch 7, non-merge fix commit tagged first-parent), `5e147317` (batch 6), `1574ed8e` (batch 5), `dcbe7bae` (batch 4), `c81d879b` (batch 3), `806a90ca` (batch 2), `a122dbf6` (feat(d81): remove trading from the product, Stage C batch 1), `0290aaa0` (durable GUI rig merge), `2d99cdab` (pre-push secrets/stray-capture guard merge). (Batch-23/24 have not yet reached a first-parent merge commit at this sha — batch-23 int went unmerged per `d38a090f`/`0c18af28`; batch-24 was still in flight.) **Update as of `4c6dfe8c`:** batch-24 reached a first-parent merge, `6778f892` ("merge(r15): batch-24 — LEAD-035 no-tool cue narrowed to a closed tail"), and its dir is now tracked at `docs/redesign/verification/r15/stage-c/batch-24/`: `PLAN.md`, `VERDICTS.json`, `VERDICTS.md`, `LEAD-035-CONCURRENCE.md`, `verifier-evidence/`, `writer-evidence/` (confirmed on disk).
- Stage-C dirs under `docs/redesign/verification/r15/stage-c/` at the sha: `batch-2` through `batch-23` (22 batch dirs; no `batch-24` tracked yet at this sha — it exists only as an untracked live dir with `PLAN.md` so far, sibling wave, not read further per lane rules), plus `lows`, `lows-triage`, `REMOVAL_PLAN.md`, and three `LEAD_FOUND.applied-batch-{3,6,18}.json` files. All 22 batch dirs have both `PLAN.md` and `VERDICTS.md`. `VERDICTS.md` tally/verdict line per batch: batch-2 through batch-9 = "approve" (no numeric tally captured in the heading grep, full text is in each `VERDICTS.md`); batch-10 = approve, 50 certified / 1 needs GUI / 4 not certified / 1 concurred; batch-11 = approve, 18 certified / 0 needs GUI / 2 not certified / 3 concurred proposals; batch-12 = 19 certified / 3 not certified (RESEARCH-007, DOCS-017, AGENT-090) / 0 needs_gui; batch-13 = approve, 2 certify; batch-14 = approve; batch-15 = approve, no entry certifies but branch doesn't regress; batch-16 = approve, 2 certify, LEAD-030 not certified; batch-17 = approve, 1 certified (LEAD-031), LEAD-030 not certified; batch-18 = approve, 2 certified (LEAD-033, LEAD-034), LEAD-030 not certified; batch-19 = approve, 0 certified, LEAD-030 not certified a fifth time; batch-20 = approve, 0 certified, LEAD-030 not certified a sixth time (LEAD-036 also not certified); batch-21 = approve, 0 certified, LEAD-030 not certified a seventh time (LEAD-035/036 notes); batch-22 = **block**; batch-23 = **block**.
- `CHANGELOG.md` section headings newer than `r13-bedrock` (`## ...`): batch-17 through batch-2 (17 Stage-C batch entries), "R15 rc1 gate — round 1", and "R15 Stage C — trading removed (D81, 2026-09-23)" — see the full heading list captured above (17 headings total, newest-first from batch-17 down to batch-2, plus the gate-round-1 and trading-removed headings).
- `docs/redesign/DECISIONS.md` D-numbers added since `r13-bedrock` (`git log --first-parent -p` on that file, `+` lines matching `| D<N> |`): **D81 through D92** (12 new decisions), consistent with D81 = the trading-removal decision referenced throughout.

## Licence

- `LICENSE` first heading: `# PolyForm Strict License 1.0.0`.
- `LICENSE-APACHE` present at this sha: **yes**.
- `LICENSING.md` present at this sha: **yes**.
- `package.json` `"license"`: `"SEE LICENSE IN LICENSE"`.
- `src-tauri/Cargo.toml`: no `license =` key; `license-file = "../LICENSE"` (`:8`).

## Tools (local machine, at capture time — not part of the sha's tree)

- `gitleaks`, `trufflehog`, `cargo-license`, `pip-licenses`: **none found** on `PATH` (`which` returned nothing for all four).
- `pnpm --version` = `10.32.1`.
- `cargo --version` = `cargo 1.95.0 (f2d3ce0bd 2026-03-21)`.
- The three sidecar venvs are **all present**: `sidecar/.venv`, `sidecar/openbb_mcp_subprocess/.venv`, `sidecar/sec_edgar_mcp_subprocess/.venv`.


## Known limitations at rc1 — agent chat with a keyless local model
source: `docs/redesign/DECISIONS_FOR_OPERATOR.md` §4.9–4.12 and `docs/redesign/verification/vysted-r15-register.json`; added by the disposition docs writer at `0c18af28` (not by the Stage D wave)
- one known-limitation class: with a keyless local model the agent can fabricate a figure, or claim a completed write, when it has no tool result to ground the claim; no further filter round this release
- **R15-LEAD-030** (high) — status `blocked_tier4`; a fresh verifier concurred in batch-23 (`docs/redesign/verification/r15/stage-c/batch-23/LEAD-030-CONCURRENCE.md`); briefing wording, verbatim:
  > With a keyless local model, the agent can still state an invented price or metric as if a tool had returned it when the figure is about a company no successful tool call in that turn covered — one named in the same paragraph as a company whose call succeeded (under a name the guard cannot map, or never looked up at all), or any company in a turn where no call failed or no tool was called — and a figure-less fabricated result dump or a code fence left open from an earlier round can also render, while figures for companies whose call succeeded are grounded against the tool result and every shape pinned in eight fix rounds is replaced by an honest "returned no data" note.

  Struck by the batch-23 disposition verifier: the clause "figures for companies whose call succeeded are grounded against the tool result" — the guard never checks a figure for a subject whose call succeeded (batch-23/DISPOSITION-CONCURRENCE.md, LEAD-037 section).
- **R15-LEAD-035** (medium) — status `blocked_tier4` as of `4c6dfe8c`, under the operator's three-failure rule (an ESCALATION, NOT a fresh-verifier concurrence — see the trailer below); briefing wording, verbatim (the batch-24 verifier's accurate-for-`d1290f66` wording, `stage-c/batch-24/LEAD-035-CONCURRENCE.md` §4):
  > With a keyless local model, the "don't use tools" detector is a fixed phrase list: an unrecognised no-tool phrasing keeps the tools, so the agent may still read data and propose a portfolio change (always held for your review, never applied; under AUTO a watchlist or chart change does apply) and can occasionally state a price it never fetched, while a data request that qualifies a no-tool instruction after a comma or in reported speech ("Don't use any tools, except price_data …", "No tools, other than the price lookup …", "He says don't use tools, but …") still loses every tool and the agent then usually states an invented price as if fetched.
- **R15-LEAD-037** (medium) — status `blocked_tier4`; the batch-23 disposition verifier concurred on the corrected wording; briefing wording, verbatim:
  > With a keyless local model, a figure the agent states for a company whose data call succeeded is not checked against that result at all, so it can give an older bar's value from the same payload as the current price (2 of 18 live runs, 5-6% off) or a figure that appears nowhere in the payload (1 of 18: ₹20,820 for a ₹2,082 stock).
- **R15-LEAD-038** (medium) — status `blocked_tier4`; the batch-23 disposition verifier concurred; briefing wording, verbatim:
  > With a keyless local model, when you tell the agent not to use tools and ask for a portfolio change in the same message, it makes no call and nothing is written or queued, but its reply can say the change was made or staged for your review and can describe holdings that do not exist.
- fail-safe facts:
  - a portfolio write never auto-applies: `data-write` changes always stage for review, and AUTO skips review only for `panel`, `chart` and `watchlist` (`types/proposed-change.ts:38-46`, `AUTO_APPLIED_KINDS` / `autoApplies`)
  - the review queue (the proposed-changes gate) is the only path for a portfolio write, and it needs a tool call; a narrated write stages nothing (batch-22 n-avoid-functions: `calls=[]`, no `tool_use` event; batch-23: `/portfolio/positions` stayed `[]` across all 38 live runs)
  - there is no `audit_orders` table: D81 removed it with trading, and `sidecar/tests/test_no_trading_surface.py` bans the token outside `types/plugin.ts`, so no order row can exist
  - figures for companies whose call succeeded are grounded against the tool result, and every shape pinned in LEAD-030's eight fix rounds is replaced by an honest "returned no data" note (b17–b22 probe outputs byte-identical to batch-22's, 0 new BAD)
- post-launch design change: claim grounding (a figure against the field and the own-clause subject it claims, including the verifier's bounded LEAD-030 ninth fix in `LEAD-030-CONCURRENCE.md` §3; a completed-write claim against a tool call that landed this turn) plus a structured no-data turn when no tool returned data

pointer to newer evidence (Stage D, this refresh at `4d893147`): batch-24 (LEAD-035's named narrowing-only fix) was still in flight at this sha — its live dir has only `PLAN.md`, no `LEAD-035-CONCURRENCE.md` yet, so the R15-LEAD-035 disposition above (`open`, pending concurrence) is still current; do not mark it `blocked_tier4` until a concurrence file lands.

pointer to newer evidence (second pass, at `4c6dfe8c`/`a3842f6a`): batch-24 merged as `6778f892` — its named narrowing-only fix HOLDS as a strict subset (0 new strips on 97 phrasings, 0 over-strips on the 67 pinned phrasings, the 7 previously over-matched data prompts call `price_data` live 21/21), but a fresh verifier REFUSED the `blocked_tier4` concurrence a fourth time (4 of 18 fresh qualified-negation data requests still lose every tool; the local model invents a price in 6/8 live runs) and instead named a further narrowing-only guard it would certify (`stage-c/batch-24/LEAD-035-CONCURRENCE.md` §3). Under the operator's three-failure rule (pacing change 4, Sat 26 Sep 04:15 IST), the lead set `R15-LEAD-035` to `blocked_tier4` at `4c6dfe8c` — an ESCALATION to the operator, not a concurrence-based adjudication. `DECISIONS_FOR_OPERATOR.md` §4.10 carries the operator's two options at rc1: (a) accept the residual as documented with the verifier's wording above, or (b) authorise one bounded round for the named guard on rc2 — the lead recommends (b). Every prose block above that still says `open`/"pending batch-24's concurrence" describes the `4d893147` capture only, superseded by this note.
