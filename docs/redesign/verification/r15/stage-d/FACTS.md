<!-- FACTS at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave -->

# Stage D FACTS — f4444790

Mode: draft · previous_sha: (none — fresh run)

## versions
- package.json: `0.8.0` (package.json:3)
- src-tauri/Cargo.toml: `0.8.0` (src-tauri/Cargo.toml:3)
- src-tauri/tauri.conf.json: `0.8.0` (src-tauri/tauri.conf.json:4)
- sidecar/app.py FastAPI(version=...): `0.8.0` (sidecar/app.py:327)
- HOST_VERSION (src/lib/plugin-bootstrap.ts): `0.8.0` (src/lib/plugin-bootstrap.ts:37)
- src-tauri/Cargo.lock vysted-terminal entry: `0.8.0` (src-tauri/Cargo.lock:5487 (name block starts :5486))
- version_consistent: **True**
- '0.9.0' already appears anywhere: **True** — 0.9.0 already appears in docs/redesign/verification/r15/census/** (PROMISE_LEDGER.md, code/plugins.md, intent/ledger-*.json) as the target public-release version being discussed, and in plugins/*/manifest.json requiredHostVersion comparisons per code/plugins.md:305-306 discussing a future '<0.9.0' example. No source-of-truth version file is 0.9.0 yet at this sha.

### other 0.8.0 occurrences (excluding CHANGELOG.md, docs/archive, docs/redesign/verification, docs/screenshots, pnpm-lock.yaml)
- `BLOCKERS.md:3` [prose]
- `BLOCKERS.md:45` [prose]
- `BLOCKERS.md:212` [prose]
- `BLOCKERS.md:262` [prose]
- `BLOCKERS.md:278` [prose]
- `README.md:15` [prose]
- `README.md:53` [prose]
- `README.md:66` [prose]
- `docs/CURRENT_STATE.md:151` [prose]
- `docs/CURRENT_STATE.md:262` [prose]
- `docs/CURRENT_STATE.md:609` [prose]
- `docs/CURRENT_STATE.md:785` [prose]
- `docs/CURRENT_STATE.md:815` [prose]
- `docs/redesign/AGENT_TOOLUSE_PLAN.md:5` [prose]
- `docs/redesign/AGENT_TOOLUSE_PLAN.md:82` [prose]
- `docs/redesign/AGENT_TOOLUSE_PLAN.md:241` [prose]
- `docs/redesign/DECISIONS.md:120` [prose]
- `docs/redesign/DECISIONS.md:131` [prose]
- `docs/redesign/DECISIONS_FOR_OPERATOR.md:146` [prose]
- `docs/redesign/HANDOFF_VERIFIED.md:22` [prose]
- `docs/redesign/OVERNIGHT_BUILD_REPORT.md:4` [prose]
- `docs/redesign/OVERNIGHT_BUILD_REPORT_R4S3.md:3` [prose]
- `docs/redesign/OVERNIGHT_BUILD_REPORT_R4S3.md:70` [prose]
- `docs/redesign/OVERNIGHT_BUILD_REPORT_R4S3.md:79` [prose]
- `docs/redesign/OVERNIGHT_BUILD_REPORT_R4S3.md:157` [prose]
- `docs/redesign/OVERNIGHT_BUILD_REPORT_R4S3.md:235` [prose]
- `docs/redesign/OVERNIGHT_BUILD_REPORT_R4S3.md:280` [prose]
- `docs/redesign/R4_BUILD_SEQUENCE.md:9` [prose]
- `docs/redesign/R4_BUILD_SEQUENCE.md:187` [prose]
- `docs/redesign/R4_DESIGN_LANGUAGE.md:367` [prose]
- `docs/redesign/R9_TRACK_LOOP_REPORT.md:5` [prose]
- `docs/redesign/REBUILD_R3_REPORT.md:3` [prose]
- `docs/redesign/REBUILD_R3_REPORT.md:17` [prose]
- `docs/redesign/REBUILD_R3_REPORT.md:108` [prose]
- `docs/redesign/REBUILD_R3_REPORT.md:130` [prose]
- `docs/redesign/REBUILD_R3_REPORT.md:174` [prose]
- `docs/redesign/REBUILD_R3_REPORT.md:239` [prose]
- `docs/redesign/REBUILD_R3_REPORT.md:301` [prose]
- `docs/redesign/REBUILD_R3_SPEC.md:72` [prose]
- `docs/redesign/REBUILD_R3_SPEC.md:745` [prose]
- `docs/redesign/REBUILD_R3_SPEC.md:850` [prose]
- `docs/redesign/REBUILD_R3_SPEC.md:854` [prose]
- `docs/redesign/REBUILD_R4_REPORT.md:9` [prose]
- `docs/redesign/REBUILD_R4_REPORT.md:124` [prose]
- `docs/redesign/REBUILD_R4_SESSION2_REPORT.md:4` [prose]
- `docs/redesign/REBUILD_R4_SESSION2_REPORT.md:149` [prose]
- `docs/redesign/REBUILD_R4_SPEC.md:10` [prose]
- `docs/research/phase-10/blueprint-bugfix.md:3` [prose]
- `docs/research/phase-10/blueprint-customizability.md:5` [prose]
- `docs/research/phase-10/blueprint-customizability.md:552` [prose]
- `docs/research/phase-10/hunt-error-surfaces.md:409` [prose]
- `docs/research/phase-10/hunt-rust-tauri.md:26` [prose]
- `docs/research/phase-10/hunt-rust-tauri.md:401` [prose]
- `docs/research/phase-10/map-ai-copilot.md:173` [prose]
- `docs/research/phase-10/map-extensibility.md:8` [prose]
- `package.json:3` [load_bearing] — "version": "0.8.0"
- `package.json:76` [load_bearing] — unrelated dep prettier-plugin-tailwindcss pinned to 0.8.0, not the app version
- `plugins/vysted-lenses/manifest.json:6` [load_bearing] — requiredHostVersion
- `plugins/vysted-news/manifest.json:6` [load_bearing] — requiredHostVersion
- `plugins/yfinance/manifest.json:6` [load_bearing] — requiredHostVersion
- `sidecar/app.py:327` [load_bearing] — FastAPI(version=...)
- `sidecar/tests/test_data_cache.py:131` [load_bearing] — test assertion, uses 0.8.0 as an arbitrary cache-build-tag literal, not the app version
- `sidecar/tests/test_data_cache.py:133` [load_bearing]
- `sidecar/tests/test_data_cache.py:141` [load_bearing]
- `sidecar/tests/test_data_cache.py:142` [load_bearing]
- `sidecar/tests/test_data_cache.py:150` [load_bearing]
- `src-tauri/Cargo.lock:281` [load_bearing] — unrelated crate version, not vysted-terminal
- `src-tauri/Cargo.lock:290` [load_bearing]
- `src-tauri/Cargo.lock:758` [load_bearing]
- `src-tauri/Cargo.lock:2426` [load_bearing]
- `src-tauri/Cargo.lock:2443` [load_bearing]
- `src-tauri/Cargo.lock:3351` [load_bearing]
- `src-tauri/Cargo.lock:3368` [load_bearing]
- `src-tauri/Cargo.lock:5487` [load_bearing] — vysted-terminal entry itself
- `src-tauri/Cargo.toml:3` [load_bearing]
- `src-tauri/tauri.conf.json:4` [load_bearing]
- `src/components/SettingsPanel.test.tsx:831` [load_bearing] — test fixture asserting /system/diagnostics version echo
- `src/lib/plugin-bootstrap.ts:37` [load_bearing] — HOST_VERSION const
- `src/lib/plugin-runtime.test.ts:498` [load_bearing]
- `src/lib/plugin-runtime.test.ts:508` [load_bearing]

## sidecars
externalBin (src-tauri/tauri.conf.json:40-44): binaries/vysted-sidecar, binaries/vysted-openbb-mcp-sidecar, binaries/vysted-sec-edgar-mcp-sidecar

### binaries/vysted-sidecar
- ensure script: `scripts/ensure-sidecar.mjs`
- PyInstaller --name: `vysted-sidecar`, entry script: `sidecar/main.py`
- venv dir: `sidecar/.venv`, requirements: `sidecar/requirements-dev.txt`
- spawn file: `src-tauri/src/lib.rs` — start_main_sidecar() at lib.rs:269, app.shell().sidecar("vysted-sidecar") at lib.rs:276
### binaries/vysted-openbb-mcp-sidecar
- ensure script: `scripts/ensure-openbb-mcp-sidecar.mjs`
- PyInstaller --name: `vysted-openbb-mcp-sidecar`, entry script: `sidecar/openbb_mcp_subprocess/main.py`
- venv dir: `sidecar/openbb_mcp_subprocess/.venv`, requirements: `sidecar/openbb_mcp_subprocess/requirements.txt`
- spawn file: `src-tauri/src/openbb_mcp.rs`
### binaries/vysted-sec-edgar-mcp-sidecar
- ensure script: `scripts/ensure-sec-edgar-mcp-sidecar.mjs`
- PyInstaller --name: `vysted-sec-edgar-mcp-sidecar`, entry script: `sidecar/sec_edgar_mcp_subprocess/main.py`
- venv dir: `sidecar/sec_edgar_mcp_subprocess/.venv`, requirements: `sidecar/sec_edgar_mcp_subprocess/requirements.txt`
- spawn file: `src-tauri/src/sec_edgar_mcp.rs`

## scripts (package.json)
- `dev`: `vite`
- `build`: `vite build`
- `lint`: `eslint .`
- `format`: `prettier --write .`
- `format:check`: `prettier --check .`
- `typecheck`: `tsc --noEmit`
- `test`: `vitest run`
- `test:watch`: `vitest`
- `sidecar:build`: `node scripts/ensure-sidecar.mjs --force`
- `openbb-mcp-sidecar:build`: `node scripts/ensure-openbb-mcp-sidecar.mjs --force`
- `sec-edgar-mcp-sidecar:build`: `node scripts/ensure-sec-edgar-mcp-sidecar.mjs --force`
- `sidecars:build`: `node scripts/ensure-all-sidecars.mjs --force`
- `ci-local`: `pnpm install --frozen-lockfile && node scripts/ensure-all-sidecars.mjs && pnpm lint && pnpm format:check && pnpm typecheck && cargo fmt --manifest-path src-tauri/Cargo.toml --check && cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings && python -m pip install ruff==0.15.12 && ruff check sidecar && ruff format --check sidecar && pnpm test && cargo test --manifest-path src-tauri/Cargo.toml && cd sidecar && python -m pip install -r requirements-dev.txt && pytest`
- `tauri`: `tauri`
- `tauri:mcp`: `tauri dev --features dev-tools`
- `tauri:dev`: `pnpm tauri:mcp`

## ci
### .github/workflows/build.yml (name: build)
- on: {"push": {"branches": ["main"]}, "pull_request": {}}
- jobs: build
- OS matrix: windows-latest, macos-latest, ubuntu-latest
### .github/workflows/lint.yml (name: lint)
- on: {"push": {"branches": ["main"]}, "pull_request": {}}
- jobs: lint
- OS matrix: windows-latest, macos-latest, ubuntu-latest
### .github/workflows/test.yml (name: test)
- on: {"push": {"branches": ["main"]}, "pull_request": {}}
- jobs: test
- OS matrix: windows-latest, macos-latest, ubuntu-latest

## plugins
- **vysted-yfinance** (plugins/yfinance) — preinstalled: True, license field in manifest: None
  - This sha has replaced BUNDLED_PLUGINS/PLUGIN_COMPANIONS (as CLAUDE.md describes) with a single CATALOG_ROWS registry in src/lib/marketplace.ts (row() helper carries entry + discovered plugin + optional panelComponents in one object); all 5 plugins are catalog rows with preinstalled:true.
- **openbb-mcp** (plugins/openbb-mcp) — preinstalled: True, license field in manifest: None
- **vysted-lenses** (plugins/vysted-lenses) — preinstalled: True, license field in manifest: None
- **vysted-news** (plugins/vysted-news) — preinstalled: True, license field in manifest: None
- **vysted-example** (plugins/example) — preinstalled: True, license field in manifest: None
  - plugins/example/index.ts:1-2 carries an SPDX header: 'SPDX-License-Identifier: Apache-2.0' / 'Copyright (c) 2026 Lokavya Singh', matching CLAUDE.md's stated example-plugin Apache-2.0 licensing. No plugins/*/manifest.json has a license field.

## agents
- first-party agent JSON count: **13** (sidecar/agents/ (excludes README.md and _schema.json))
- ids: buffett, copilot, dalio, druckenmiller, graham, klarman, lynch, marks, munger, portfolio_advisor, researcher, soros, strategy_critic
- roster count assertion: `sidecar/tests/test_agent_runtime.py:213` — `assert len(json_files) == 13  # the roster — keep in sync with the count tests`

## panels
each src/modules/<name>/index.ts defines a VystedModule with panel id/title pairs; safety has no index.ts panel registration at this sha.
- **agent-builder**: agent-builder (Agent Builder)
- **analyst-ratings**: analyst-ratings (Analyst Ratings)
- **backtest**: backtest (Backtest)
- **chart**: chart (Chart)
- **chat**: chat (AI Assistant (module id/title only, no panel id found at grep depth used))
- **earnings**: earnings-calendar (Earnings Calendar)
- **equity-overview**: equity-overview (Equity Overview)
- **macro**: macro (Macro)
- **marketplace**: marketplace (Marketplace)
- **news**: news (News)
- **node-editor**: node-editor (Node Editor)
- **notes**: notes (Notes)
- **platform**: settings (Settings)
- **plugin-manager**: plugin-manager (Plugins)
- **portfolio**: portfolio (Portfolio)
- **quant**: option-pricer (Option Pricer), greeks-dashboard (Greeks Dashboard), bond-pricer (Bond Pricer), yield-curve (Yield Curve)
- **research**: brief (Brief)
- **screener**: screener-panel (Screener)
- **sec**: sec-filings (SEC Filings)
- **watchlist**: watchlist (Watchlist)
- modules with no panels found: safety

## register
source: `docs/redesign/verification/vysted-r15-register.json`
- counts: {"raw": 887, "entries": 626, "rejections": 76, "critical": 16, "high": 112, "medium": 279, "low": 219}
- severity x status: {"critical": {"fixed": 16}, "high": {"fixed": 100, "open": 3, "needs_gui": 4, "removed_with_feature": 1, "blocked_tier4": 4}, "medium": {"fixed": 153, "open": 114, "removed_with_feature": 9, "needs_gui": 2, "not_a_defect": 1}, "low": {"open": 205, "fixed": 10, "removed_with_feature": 4}}
- open high (3): R15-AGENT-007 (agent-runtime), R15-AGENT-017 (llm-adapters), R15-LEAD-022 (resolver)
- open medium (114): R15-AGENT-046 (agent-tools-catalog-ledger), R15-AGENT-049 (agent-runtime), R15-AGENT-050 (llm-adapters), R15-AGENT-053 (frontend-panels-agent-shell), R15-AGENT-057 (plugins), R15-AGENT-063 (research-extraction-synthesis), R15-AGENT-064 (mcp-servers), R15-AGENT-082 (frontend-panels-agent-shell), R15-AGENT-083 (agent-tools-catalog-ledger), R15-AGENT-084 (host-actions-proposed-changes), R15-AGENT-088 (frontend-panels-agent-shell), R15-CODE-AGENT-005 (llm-adapters), R15-CODE-AGENT-008 (agent-runtime), R15-CODE-AGENT-009 (agent-runtime), R15-CODE-AGENT-013 (agent-tools-catalog-ledger), R15-CODE-FRONTEND-013 (safety-audit), R15-CODE-FRONTEND-016 (frontend-stores), R15-CODE-PLATFORM-010 (rust-core), R15-CODE-PLATFORM-012 (plugins), R15-CODE-PLATFORM-013 (plugins), R15-CODE-PLATFORM-014 (plugins), R15-CODE-PLATFORM-015 (plugins), R15-CODE-PLATFORM-017 (workflow-engine), R15-CODE-PLATFORM-021 (portfolio), R15-CODE-PLATFORM-023 (portfolio), R15-CODE-PLATFORM-024 (rust-core), R15-CODE-PLATFORM-025 (rust-core), R15-CODE-PLATFORM-026 (scripts-build), R15-CODE-PLATFORM-027 (scripts-build), R15-CODE-PLATFORM-028 (scripts-build), R15-CODE-PLATFORM-029 (backtest), R15-CODE-PLATFORM-030 (backtest), R15-CODE-PLATFORM-071 (plugins), R15-CODE-PLATFORM-072 (plugins), R15-CODE-PLATFORM-073 (scripts-build), R15-CODE-RESEARCH-004 (research-retrieval-relevance), R15-CROSS-PLATFORM-001 (scripts-build), R15-CROSS-PLATFORM-002 (research-extraction-synthesis), R15-CROSS-PLATFORM-003 (market-data-providers-1), R15-CROSS-PLATFORM-004 (frontend-panels-shell-chrome), R15-DATA-048 (fundamentals-profile), R15-DATA-052 (resolver), R15-DATA-053 (market-data-providers-1), R15-DATA-054 (fundamentals-profile), R15-DATA-055 (fundamentals-profile), R15-DATA-059 (resolver), R15-DATA-061 (error-layer), R15-DATA-062 (market-data-providers-2), R15-DATA-065 (market-data-providers-2), R15-DATA-066 (market-data-providers-1), R15-DATA-068 (market-data-providers-3), R15-DATA-069 (market-data-providers-3), R15-DATA-071 (market-data-providers-1), R15-DATA-073 (market-data-providers-1), R15-DATA-077 (market-data-providers-1), R15-DATA-078 (market-data-providers-1), R15-DATA-079 (market-data-providers-1), R15-DATA-080 (fundamentals-profile), R15-DATA-087 (macro-quant), R15-DATA-092 (frontend-panels-shell-chrome), R15-DATA-094 (plugins), R15-DATA-095 (fundamentals-profile), R15-DATA-096 (fundamentals-profile), R15-DOCS-002 (scripts-build), R15-DOCS-003 (frontend-panels-shell-chrome), R15-DOCS-004 (frontend-panels-shell-chrome), R15-DOCS-005 (frontend-panels-shell-chrome), R15-DOCS-015 (plugins), R15-DOCS-016 (host-actions-proposed-changes), R15-DOCS-017 (screener), R15-DOCS-018 (market-data-providers-1), R15-LEAD-013 (market-data-providers-1), R15-LEAD-016 (market-data-providers-1), R15-LEAD-018 (llm-adapters-and-errors), R15-LEAD-023 (market-data-providers-1), R15-LIFECYCLE-015 (backtest), R15-LIFECYCLE-018 (research-retrieval-relevance), R15-LIFECYCLE-021 (market-data-providers-1), R15-LIFECYCLE-024 (workspace-layout), R15-LIFECYCLE-025 (agent-runtime), R15-LIFECYCLE-026 (market-data-providers-1), R15-RELEASE-005 (scripts-build), R15-RELEASE-006 (scripts-build), R15-RELEASE-007 (scripts-build), R15-RESEARCH-025 (screener), R15-RESEARCH-027 (research-depth-iter-deep), R15-RESEARCH-028 (research-retrieval-relevance), R15-RESEARCH-030 (disclosures-witnesses), R15-UI-010 (backtest), R15-UI-011 (backtest), R15-UI-015 (error-layer), R15-UI-016 (frontend-stores), R15-UI-018 (frontend-panels-shell-chrome), R15-UI-024 (frontend-panels-data-surfaces), R15-UI-027 (frontend-panels-shell-chrome), R15-UI-028 (macro-quant), R15-UI-032 (market-data-providers-3), R15-UI-033 (plugins), R15-UI-044 (safety-audit), R15-UI-047 (frontend-panels-shell-chrome), R15-UI-048 (frontend-stores), R15-UI-050 (frontend-panels-data-surfaces), R15-UI-051 (macro-quant), R15-UI-052 (frontend-panels-agent-shell), R15-UI-053 (macro-quant), R15-UI-058 (frontend-panels-shell-chrome), R15-UI-059 (fundamentals-profile), R15-UI-083 (frontend-panels-data-surfaces), R15-UI-084 (frontend-panels-agent-shell), R15-UI-085 (frontend-panels-shell-chrome), R15-UI-086 (frontend-panels-shell-chrome), R15-UI-087 (frontend-panels-shell-chrome), R15-UI-088 (workspace-layout), R15-UI-091 (frontend-panels-data-surfaces)
- needs_gui: R15-CODE-AGENT-001, R15-LIFECYCLE-001, R15-LIFECYCLE-008, R15-UI-009, R15-UI-022, R15-UI-025
- blocked_tier4: R15-RELEASE-001, R15-RELEASE-002, R15-RELEASE-003, R15-RELEASE-004
- open critical: none (0)

## decisions
source: `docs/redesign/DECISIONS_FOR_OPERATOR.md`
- **1.1** — The "sacred" enrich_nse_sectors.py edit is now committed (7a1cd8f)
  - closed: False · tier4: True
  - unblock: git revert 7a1cd8f
- **1.2** — SUPERSEDED (D81) — kill-switch-benchmark.json baseline dirtying pytest
  - closed: True · tier4: True
  - unblock: nothing to undo; deleted with the trading-removal feature
- **1.3** — Five local, never-pushed commits were rewritten once (the brief said "no history rewrite")
  - closed: False · tier4: True
  - unblock: nothing to undo on origin; to publish the brief, remove its line from .gitignore and commit it
- **1.4** — Relicensed to PolyForm Strict 1.0.0 (your decision, given 23 Sep 2026)
  - closed: False · tier4: True
  - unblock: git revert <relicense commit> (subject: 'chore(license): relicense core to PolyForm Strict 1.0.0')
- **2.1** — Your default provider lanes are unfunded — the app cannot answer on them
  - closed: False · tier4: True
  - unblock: top up OpenRouter (negative paid balance) or fund DeepSeek-direct ($0); restart the dev stack to pick up 043850c's gpt-5.x tool-calling fix
- **2.2** — Docker/OrbStack is not running, so SearXNG is down and research silently uses the keyless scraper
  - closed: False · tier4: True
  - unblock: start OrbStack before judging research depth
- **2.3** — CLOSED: removed with the feature (D81, 23 Sep 2026) — kill switch had no subscribers left once orders were removed
  - closed: True · tier4: True
  - unblock: revert the D81 removal commits (restores the whole trading layer)
- **2.4** — CLOSED: removed with the feature (D81) — paper/live mode switch deleted
  - closed: True · tier4: True
  - unblock: revert the D81 removal commits
- **2.5** — CLOSED: removed with the feature (D81) — PositionLimits deleted, nothing left to limit
  - closed: True · tier4: True
  - unblock: revert the D81 removal commits
- **2.6** — CI has never run on 004, and the last main run failed
  - closed: False · tier4: True
  - unblock: open a PR against main / fix the red main lint run so CI's push+pull_request triggers actually fire
- **2.7** — GUI rig: input-idle time is not proof you are away
  - closed: False · tier4: True
  - unblock: add an away-sentinel file (~/.vysted-rig-away, with expiry) required in addition to idle time — not added because it would make unattended runs refuse until the operator knows about it
- **2.8** — R15-RELEASE-001 — unsigned desktop bundles (Gatekeeper/SmartScreen block every install)
  - closed: False · tier4: True
  - unblock: at minimum set bundle.macOS.signingIdentity: "-" in tauri.conf.json for an ad-hoc seal (still needs operator sign-off, Tier-1 file); full fix needs a paid Apple Developer ID + notarization and a Windows code-signing cert
- **2.9** — R15-RELEASE-002 — no GitHub release pipeline (tags v0.6.0..v0.8.0 have zero installable builds)
  - closed: False · tier4: True
  - unblock: approve adding .github/workflows/release.yml (3-OS matrix via tauri-apps/tauri-action, createUpdaterArtifacts:true, TAURI_SIGNING_PRIVATE_KEY wired); also unblocks 2.10
- **2.10** — R15-RELEASE-003 — auto-updater is dead end-to-end
  - closed: False · tier4: True
  - unblock: approve 2.9 first (produces latest.json/.sig), then set createUpdaterArtifacts:true in tauri.conf.json; the consumer-side app.updater()?.check() call is not Tier-4 and can ship independently
- **2.11** — R15-RELEASE-004 — CI has never run on 004-r4-experience-rebuild
  - closed: False · tier4: True
  - unblock: open a draft PR for 004-r4-experience-rebuild (no workflow edit needed) so the existing pull_request trigger runs the 3-OS matrix; fix the red main lint run first so the signal is meaningful
- **3.1** — UNSURE-1 — user-side leftovers after upgrade (no code reads any of it; nothing purged)
  - closed: False · tier4: False
  - unblock: approve a one-time 'remove leftover broker credentials' purge step plus a CHANGELOG note on manually deleting audit_log.db and the keychain entries
- **3.2** — First-launch terms rewrite (was on the §6.5 surface, includes licence wording)
  - closed: False · tier4: False
  - unblock: review the exact copy in src/modules/safety/DisclaimerFlow.tsx before it ships (flagged Tier-4 by R15-UI-041)
- **3.3** — Accepted agent-write safety gaps (stated in docs/SAFETY_ARCHITECTURE.md, not silently dropped)
  - closed: False · tier4: False
  - unblock: tracked as R15-CODE-FRONTEND-013 (no durable audit trail beyond action_ledger's 10-min TTL) and R15-CODE-FRONTEND-008 (no stop control for AUTO beyond reject/run-cancel); no unblock proposed, accepted gaps
- **3.4** — BLOCKED-FOR-OPERATOR (Tier-1): no edit made, your call
  - closed: False · tier4: True
  - unblock: decide whether to keep the 'trading-bot' PluginType literal + JSDoc examples in types/plugin.ts as historical precedent or remove them (contract-breaking either way); apply the queued CLAUDE.md edits in docs/redesign/CLAUDE_MD_PROPOSAL.md when convenient; COMMERCIAL_LICENSE.md:36-48 broker clause left as-is, no change required
- **3.5** — D-B3-1 — AUTO scope tightened back to SC-025 (Stage C batch 3; done, revertable)
  - closed: True · tier4: False
  - unblock: flip the autoApplies predicate in types/proposed-change.ts if AUTO should apply data-write kinds again
- **3.6** — D-B4-1 — context admission on window-bound lanes (Stage C batch 4; done, revertable)
  - closed: True · tier4: False
  - unblock: have LLMProvider.context_window return None for Ollama to restore silent head truncation

closed = CLOSED/SUPERSEDED marker present in the heading, or the item is explicitly done-and-revertable (§3.5/3.6); tier4 = the item sits in DECISIONS_FOR_OPERATOR.md §1 (reversals) or §2 (Tier-4 blocked/open) sections, or is explicitly framed BLOCKED-FOR-OPERATOR (3.4); §3.1-3.3/3.5-3.6 are non-Tier-4 (autonomous Tier-3 record or accepted-gap notes). All one-line unblocks read verbatim from docs/redesign/DECISIONS_FOR_OPERATOR.md.

## git
- base_tag: `r13-bedrock` — no r15-* tag exists yet as an ancestor of this sha; r13-bedrock is the newest r13-/r15- tag that is (git tag --merged f4444790 --sort=-creatordate, filtered to ^r13-|^r15-).
- commits since base: total 468, first-parent 76
- first-parent merge subjects since base:
  - 6b702305 merge(r15): Stage C batch 9 - 29 certified live (agent runtime identity + budget, research/search/news, fundamentals identity + earnings, market lanes + errors + quant, frontend shell)
  - 68bb7aa4 merge(r15): Stage C batch 8 - 39 certified live (sidecar lifecycle + transport, provider readiness, data error honesty, resolver + exchange lanes, agent runtime + research)
  - e81c9e7c fix(r15): Stage C batch 7 - 55 high/medium entries (50 certified live, 1 needs GUI, 4 open)
  - 5e147317 fix(r15): Stage C batch 6 - 22 delivered high/medium entries (21 certified live, 3 open) + quant-pool leak fix
  - 1574ed8e fix(r15): Stage C batch 5 - 58 high/medium entries (48 certified live, 2 need GUI, 6 open) + LEAD-010 regression fix
  - dcbe7bae fix(r15): Stage C batch 4 - 52 high entries (45 certified live, 2 need GUI, 3 open)
  - c81d879b fix(r15): Stage C batch 3 - 40 critical/high entries (38 certified live, 2 open)
  - 806a90ca fix(r15): Stage C batch 2 - 40 critical/high entries (37 certified live, 3 reopened)
  - a122dbf6 feat(d81): remove trading from the product (Stage C batch 1)
  - 0290aaa0 Merge worktree-agent-rig into 004-r4-experience-rebuild (R15: durable GUI rig, presence safety)
  - 2d99cdab Merge worktree-agent-pushguard into 004-r4-experience-rebuild (R15: pre-push secrets + stray-capture guard)
  (git log --first-parent --merges shown to depth 11 above (head -30 returned only 11 matches for this range); this is the full list within the sampled window, not necessarily every first-parent merge back to r13-bedrock.)

### stage-c dirs
path: `docs/redesign/verification/r15/stage-c/`
- **batch-2**: PLAN.md + VERDICTS.md present — Certified 37 | Not certified 3 (R15-DATA-005, R15-DATA-014, R15-AGENT-001) | needs_gui 0
- **batch-3**: PLAN.md + VERDICTS.md present — Certified 38 | Not certified 2 (R15-DATA-020, R15-RESEARCH-005)
- **batch-4**: PLAN.md + VERDICTS.md present — Certified 45 | needs_gui 2 | open 3 (per CHANGELOG/merge subject; VERDICTS.md line 20 shows Certified 45)
- **batch-5**: PLAN.md + VERDICTS.md present — Certified 48 | Not certified 6 (R15-LEAD-010, R15-DATA-017, R15-CODE-PLATFORM-018, R15-AGENT-052, R15-AGENT-051, R15-CODE-FRONTEND-015) | needs_gui 2 (R15-CODE-AGENT-001, R15-LIFECYCLE-008)
- **batch-6**: PLAN.md + VERDICTS.md present — Certified (21) per VERDICTS.md:64 heading
- **batch-7**: PLAN.md + VERDICTS.md present — 52 claimed (51 delivered + CODE-PLATFORM-018 verify-only); 50 certified, 1 needs GUI (UI-022), 1 not certified (AGENT-045); LEAD-005, AGENT-046, CODE-PLATFORM-021 not delivered, stay open
- **batch-8**: PLAN.md + VERDICTS.md present — 47 planned; 39 certified, 1 needs GUI (LIFECYCLE-001), 7 not certified (3 real residuals DATA-061/UI-053/RESEARCH-027, 1 partial UI-015, 3 not delivered AGENT-046/CODE-AGENT-008/CODE-PLATFORM-021)
- **batch-9**: PLAN.md + VERDICTS.md present — 45 planned; 29 certified, 2 need GUI (UI-083, UI-050), 14 not certified
- **lows-triage**: no PLAN.md/VERDICTS.md present; directory holds different content
- other files: LEAD_FOUND.applied-batch-3.json, LEAD_FOUND.applied-batch-6.json, REMOVAL_PLAN.md

### CHANGELOG.md headings newer than base tag
- R15 Stage C — batch 2: critical + high data/research/workspace fixes (2026-09-23)
- R15 Stage C — batch 3: agent runtime, AUTO gate, LLM adapters, research depth, India witnesses (2026-09-23)
- R15 Stage C — batch 4: context admission, Gemini/xAI lanes, workflows, Delegate output, market-data gate, panels (2026-09-23)
- R15 Stage C — batch 5: India exchange lanes, resolver masters, runtime liveness and memory, workflow control flow, sidecar boundary, screener and earnings (2026-09-24)
- R15 Stage C — batch 6: India Emerge lanes, runtime tool-call identity, research funnel, host-action intents, quant pool, panel bus keys (2026-09-24)
- R15 Stage C — batch 7: exchange-filed India fundamentals, durable delegate runs, unattended workflows, chart/workspace integrity, research funnel, agent-write Undo (2026-09-24)
- R15 Stage C — batch 8: sidecar lifecycle and transport, provider readiness, data-error honesty, resolver and exchange lanes, research runtime (2026-09-24)
- R15 Stage C — batch 9: tool-call identity, research brief contract, search degradation, fundamentals and earnings truth, market lanes and error honesty, keyboard shell (2026-09-24)
- R15 Stage C — trading removed (D81, 2026-09-23)

### DECISIONS.md D-numbers added since base tag: D81, D82, D83, D84, D85, D86, D87, D88, D89, D90, D91, D92

## licence
- LICENSE first heading: `# PolyForm Strict License 1.0.0` (https://polyformproject.org/licenses/strict/1.0.0)
- LICENSE-APACHE present: True
- LICENSING.md present: True
- package.json license: `SEE LICENSE IN LICENSE`
- src-tauri/Cargo.toml: license-file = `../LICENSE` (src-tauri/Cargo.toml:8 (license-file, not a license= string))

## tools
- gitleaks: absent, trufflehog: absent, cargo-license: absent, pip-licenses: absent
- pnpm: 10.32.1, cargo: cargo 1.95.0 (f2d3ce0bd 2026-03-21)
- venvs present: {"sidecar/.venv": true, "sidecar/openbb_mcp_subprocess/.venv": true, "sidecar/sec_edgar_mcp_subprocess/.venv": true}
