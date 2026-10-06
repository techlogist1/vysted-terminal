# R15 Stage C: Batch 11 Plan (2 high, 24 medium: 20 to fix, 3 deferred, 3 proposed out-of-scope)

- **Base:** branch `004-r4-experience-rebuild` at `30b6414ff63f2fce81acbbf298dcddeecc155f81` (batch 10 merged; the commits after it are docs-only). D81 is merged (`a122dbf6`): nothing here re-adds trading, orders, brokers or a paper account. The option chain in W6 is exchange-published research data, not trading.
- **Author:** the batch planner (Opus). I opened the code each row names at this base. Mechanisms follow the corrected verdicts (the batch-10 "not certified" notes, the refuter corrections, the D81 moot notes), not the raw claims. Line numbers are at base.
- **Queue at base (after the batch-11 adjudication):** 0 critical, 2 high, 24 medium open. Lows are not in this batch. Every one of the 26 is either selected (20), deferred with a reason (3), or proposed out-of-scope (3).
- **Routing (change 5):** Sonnet 5 is the default for sets with a clear spec and a checkable output; Opus 5.5 (default effort) only for root-causing or risk-adjacent sets, with the reason stated per writer. 8 writers: 5 opus, 3 sonnet.
- **Class rule:** a class is a shared root cause, kept whole in one writer.
  - `CODE-PLATFORM-026` + `028` + `RELEASE-005` + `006` (W1): what a sidecar build is made of is encoded in three copied ensure scripts plus a hand-copied gate table, with no tests.
  - `CODE-PLATFORM-027` + `RELEASE-007` (W1): the design-token audit is wired nowhere and walks zero files on Windows (false-clean gate).
  - `LIFECYCLE-026` + `DATA-071` (W4): both live in `provider_registry.py`'s two walkers; the async walker runs sync providers on the loop, the sync walker takes the first non-error result even when it says it is partial.
  - `LEAD-028` + `DATA-059` (W5): the resolver's lookup keys cover only the current ticker and current name (no scrip-code key on data routes, no former-name key).
  - `CODE-PLATFORM-025` + `UI-047` (W8 + proposed): multi-window is unbuilt. The BLUEPRINT promise is corrected (W8); the feature is proposed as v1.0 roadmap for fresh concurrence. Both are decided in this batch, so the class is not split across batches.

---

## 0. The 26 entries

| id | sev | disposition | writer |
|---|---|---|---|
| R15-AGENT-007 | high | fix: eval harness + wire cassettes; live Anthropic/Gemini pass stays operator-attended | W3 |
| R15-AGENT-017 | high | deferred: needs a funded OpenRouter lane (R15-D8) | - |
| R15-AGENT-049 | medium | deferred: fix delivered in batch 9, certification needs a native-search lane | - |
| R15-CODE-AGENT-009 | medium | fix | W2 |
| R15-LIFECYCLE-024 | medium | fix | W2 |
| R15-LIFECYCLE-026 | medium | fix (profile first) | W4 |
| R15-DATA-071 | medium | fix (registry fall-through leg) | W4 |
| R15-CODE-PLATFORM-026 | medium | fix | W1 |
| R15-CODE-PLATFORM-027 | medium | fix | W1 |
| R15-CODE-PLATFORM-028 | medium | fix | W1 |
| R15-RELEASE-005 | medium | fix | W1 |
| R15-RELEASE-006 | medium | fix | W1 |
| R15-RELEASE-007 | medium | fix | W1 |
| R15-LEAD-013 | medium | fix | W5 |
| R15-LEAD-028 | medium | fix | W5 |
| R15-DATA-059 | medium | fix | W5 |
| R15-DATA-079 | medium | fix (spec User Story 2: "checks the options chain in the quant panel") | W6 |
| R15-UI-087 | medium | fix (FR-038 MUST) | W7 |
| R15-UI-085 | medium | fix (W8; one-token swaps in W7's and W8's own files) | W8 (+W7) |
| R15-UI-091 | medium | fix (frontend leg) | W8 |
| R15-CODE-PLATFORM-023 | medium | fix (build the metrics) | W8 |
| R15-CODE-PLATFORM-025 | medium | fix (BLUEPRINT scope correction) | W8 |
| R15-UI-047 | medium | proposed out-of-scope (v1.0 roadmap) | - |
| R15-UI-059 | medium | proposed out-of-scope (no spec/BLUEPRINT promise) | - |
| R15-DATA-080 | medium | proposed out-of-scope (no spec/BLUEPRINT promise) | - |
| R15-UI-088 | medium | deferred: needs an operator call on a new e2e runner and test location | - |

## 1. File ownership: eight disjoint sets

A file belongs to exactly one writer. A needed change in a file you do not own goes to `issues[]` with the exact line; the integrator re-dispatches it to the owner.

- **W1 `scripts-build` (opus)** - `scripts/ensure-sidecar.mjs`, `scripts/ensure-openbb-mcp-sidecar.mjs`, `scripts/ensure-sec-edgar-mcp-sidecar.mjs`, `scripts/ensure-all-sidecars.mjs`, `scripts/smoke-test-sidecars.mjs`, `scripts/sidecar-staleness.mjs`, `scripts/audit-design-tokens.mjs`, new `scripts/sidecar-specs.mjs` (or `build-sidecar.mjs`), new `scripts/*.test.mjs`, `vitest.config.ts`, `package.json` (scripts block only), `docs/redesign/R9_DESIGN_SYSTEM.md`.
- **W2 `runtime-schema` (opus)** - `sidecar/services/agent_runtime.py`, new `sidecar/tests/test_runtime_phases.py`; `sidecar/services/{portfolio_db,agents_store,workflow_store,data_cache,fundamentals_store,runs_store,plugins_store}.py`, new `sidecar/services/schema_version.py`, new `sidecar/tests/test_schema_version.py`, the existing tests of those seven stores, `src/lib/workspace.ts`, `src/lib/workspace.test.ts`.
- **W3 `agent-eval` (opus)** - new `scripts/agent_eval/` (runner, scenarios, grader), new `sidecar/tests/test_agent_eval.py`, `sidecar/tests/test_llm_anthropic.py`, `sidecar/tests/test_llm_gemini.py`, `sidecar/tests/test_gemini_multiround.py`, new `sidecar/tests/fixtures/llm/*` cassettes (add-only), `sidecar/services/llm/anthropic.py`, `sidecar/services/llm/gemini.py` (only if a real-shape cassette exposes a bug).
- **W4 `registry-loop` (opus)** - `sidecar/services/provider_registry.py`, `sidecar/app.py`, `sidecar/services/fundamentals_warm.py`, `sidecar/services/screener.py`, `sidecar/services/nse_symbol_change.py`, `sidecar/services/workflow_scheduler.py`, `sidecar/services/searxng_manager.py`, `sidecar/tests/test_provider_registry*.py`, new `sidecar/tests/test_loop_idle.py`.
- **W5 `data-reference` (sonnet)** - `sidecar/services/symbol_resolver.py`, `sidecar/services/bse_provider.py`, `sidecar/services/resolver_masters/*` (new former-name master + generator), `sidecar/services/screener_universes/{sp500.json,us_fundamentals_seed.json.gz,regenerate_sp500.py}`, `sidecar/tests/test_symbol_resolver*.py`, `sidecar/tests/test_bse_provider.py`, `sidecar/tests/test_sp500_universe.py`, `sidecar/tests/test_fundamentals_seed.py`, `sidecar/tests/test_screener*.py` (only the sp500 count lines).
- **W6 `options-chain` (opus)** - new `sidecar/services/option_chain.py`, `sidecar/models/market.py`, `types/data.ts`, `sidecar/routers/quant.py`, `sidecar/services/agent_tools/catalog.py`, the agent_tools handler module it registers in, `sidecar/agents/copilot.json`, `sidecar/agents/researcher.json`, the tests that assert catalog/MCP counts (`test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_main_stdio.py`, `test_mcp_server.py`, and any other hit of the count grep), new `sidecar/tests/test_option_chain.py` + `sidecar/tests/fixtures/nse/fo_bhavcopy*` (add-only), `src/modules/quant/*`, `src/lib/sidecar-client.ts`.
- **W7 `preferences` (opus)** - `src/store/llm-providers.ts`, `src/store/settings.ts`, `src/components/SettingsPanel.tsx`, `src/modules/chat/ChatSidebar.tsx`, `src/modules/chat/streaming.ts`, `src/components/CommandPalette.tsx`, `src/components/PanelHost.tsx`, and their `*.test.ts(x)`.
- **W8 `frontend-visual` (sonnet)** - `styles/tokens.css` (comments only, if needed), new `src/lib/design-contrast.test.ts`; `src/components/DataTable.tsx`, `src/modules/research/BriefPanel.tsx`, `src/modules/analyst-ratings/IndividualAnalystTable.tsx`, `src/modules/node-editor/node-palette.tsx`, `src/modules/node-editor/NodeEditorPanel.tsx`, `src/modules/chat/ResearchActivity.tsx`, `src/modules/notes/NotesPanel.tsx`, `src/modules/news/NewsFeedPanel.tsx`, `src/modules/equity-overview/EquityOverviewPanel.tsx`; `sidecar/routers/indicators.py`, `sidecar/tests/test_indicators*.py`, `src/modules/chart/indicators.ts`, `src/modules/chart/ChartPanel.tsx`, `src/lib/host-actions.ts` and their tests; `src/modules/portfolio/{metrics.ts,PortfolioPanel.tsx,api.ts}` and their tests; `docs/BLUEPRINT.md` (outside §2).

**Coordination notes (read by every writer):**
- **C1 (UI-085 split):** `text-charcoal-600` → the tertiary text token (`text-charcoal-500`) for readable text. W8 does it in its nine files and in `PortfolioPanel.tsx`. W7 does the same one-token swap in `CommandPalette.tsx` and `ChatSidebar.tsx` (commit: `fix(ui): R15-UI-085 tertiary token in <file>`). W8's source-scan test fails on W8's branch alone until W7 merges; the integrator merges W8 after W7.
- **C2 (vitest include):** W1 widens `vitest.config.ts` include to `scripts/**/*.test.mjs`. Only W1 writes tests under `scripts/`. W3's grader tests go in `sidecar/tests`, not under `scripts/`.
- **C3 (`package.json`):** only W1 edits it, and only the `scripts` block. No writer adds a dependency.
- **C4 (types mirror):** only W6 edits `types/data.ts` and `sidecar/models/market.py`, in the same commit.
- **C5 (catalog):** only W6 adds a capability or bumps a count assertion. Nobody else touches `catalog.py`, `sidecar/agents/*.json` or the count tests.
- **C6 (`workspace.ts`):** only W2 edits it. W7's start-with picker lives in `settings.ts` + `PanelHost.tsx` and calls the existing named-layout loader and `restoreLastSessionOrDefault` without changing them. If W7 needs a new export from `workspace.ts`, that is an `issues[]` line for W2.
- **C7 (`data_cache.py`):** W2 owns it (the upgrade backup hook sits in `ensure_build`). If W4's profile puts the burn in `data_cache.py`, that is an `issues[]` line.
- **C8 (settings store):** W8 reads `useSettingsStore().chartDefaults` and never edits `settings.ts` (W7 owns it).
- **C9 (single live lanes):** only W3 and W4 boot a sidecar (from source, own data-dir copy, W3 on port 52420, W4 on 52410). Before booting, take the lane with `mkdir /tmp/vysted-r15-b11-sidecar.lock` and release it with `rmdir` (max 20 min per hold). If the mkdir fails, run unit work and retry in a later call. Only W3 uses the local model (ollama). Nobody touches the operator's stack or the iso stack.
- **C10 (sidecar binary):** W5 regenerates `sp500.json` and `us_fundamentals_seed.json.gz`, and W1 makes `.json.gz` a staleness input. The integrator rebuilds with `--force` anyway.

---

## 2. Per-writer entries (mechanism → fix → test → files)

### W1: `scripts-build` (opus)

Why opus: the build recipe is risk-adjacent. PyInstaller `--onefile` silently drops `--add-data`/`--collect-data`/`--copy-metadata` (CLAUDE.md gotcha), so a refactor that loses one flag ships a broken binary with CI green.

- **R15-CODE-PLATFORM-026 (build-recipe duplication)**
  - Mechanism: `targetTriple`/`run`/`sleepSync`/`copyWithRetry`/the staleness guard/venv bootstrap/copy-sign-tidy tail are copied across `ensure-sidecar.mjs:29-34,36-62,81-100,201-210`, `ensure-openbb-mcp-sidecar.mjs:46-110,178-187` and `ensure-sec-edgar-mcp-sidecar.mjs:36-100,159-171`, and `smoke-test-sidecars.mjs:519-524` has a fourth triple helper.
  - Fix: one module exporting `SIDECAR_SPECS` (name, sourceDir, venvDir, requirements, pyinstallerFlags incl. every `--add-data`/`--collect-data`/`--copy-metadata`, identifier, staleOpts) and `buildSidecar(spec)`. The three ensure scripts become thin spec runners, `ensure-all-sidecars.mjs` keeps its orchestrator role, and the smoke test reads the same spec list.
  - Test: `scripts/sidecar-specs.test.mjs` checks that each spec's PyInstaller argv is byte-identical to the base recipe's flags (capture them from base before refactoring), including the `agents/` and `screener_universes` `--add-data` and the `edgar` `--collect-data`.
- **R15-RELEASE-006 (gate copies builder config)**
  - Mechanism: `smoke-test-sidecars.mjs:870-892` `_assertAllFresh` hand-writes each sidecar's `{dirs, opts}` instead of reading the builders' `STALE_OPTS` (`ensure-sidecar.mjs:78`, `ensure-openbb-mcp-sidecar.mjs:89`, `ensure-sec-edgar-mcp-sidecar.mjs:79`).
  - Fix: `_assertAllFresh` loops over `SIDECAR_SPECS`.
  - Test: assert that the gate and each ensure path resolve the identical `staleOpts` object (same reference or deep-equal from the one table).
- **R15-RELEASE-005 (.json.gz not a build input)**
  - Mechanism: `sidecar-staleness.mjs:41` `SOURCE_EXT = /\.(py|txt|toml|cfg|ini|json|csv)$/i` is an allow-list; `india_fundamentals_seed.json.gz` does not match, so regenerating the seed skips the rebuild while `--add-data` bundles the dir.
  - Fix: invert to a deny-list (`.pyc`, `.pyo`, `.log`, `.DS_Store`, `__pycache__`, the venv/build/dist dirs). Feed each spec's `--add-data` source paths into its `staleOpts` so "what is build input" is encoded once.
  - Test: a tmpdir test where touching a `.gz` under a bundled data dir marks the binary stale.
- **R15-CODE-PLATFORM-028 (scripts untested)**
  - Mechanism: `vitest.config.ts` includes only `src/**` and `plugins/**`; `sidecar-staleness.mjs` (pure) has no test.
  - Fix: add `scripts/**/*.test.mjs` to the include (these files run under `// @vitest-environment node`).
  - Tests: `scripts/sidecar-staleness.test.mjs` (tmpdir) covering isStale true/false, the `excludeDirs` prune, `extraFiles`, and a non-`.py` data file (the RELEASE-005 case).
- **R15-CODE-PLATFORM-027 (audit false-clean on Windows)**
  - Mechanism: `audit-design-tokens.mjs:23` `new URL("..", import.meta.url).pathname` gives `/C:/...` on win32. The `statSync` catch at :75-81 `continue`s, zero files are walked, and :121 prints clean. `SKIP_FILES` (:62) compares against a backslash `relative()` on Windows.
  - Fix: `const ROOT = resolve(import.meta.dirname, "..")`, compare SKIP_FILES on a posix-normalised relative path, and exit non-zero when zero files were scanned.
  - Test: run the script (child_process) against a tmp root with zero matching files → non-zero exit.
- **R15-RELEASE-007 (audit wired nowhere)**
  - Mechanism: `package.json:10` `lint` is `eslint .`; `ci-local` and the workflows never run the audit.
  - Fix: `"lint": "eslint . && node scripts/audit-design-tokens.mjs"`. `ci-local` and any workflow that runs `pnpm lint` then enforce it; do not edit `.github/`. If `lint.yml` calls eslint directly, record that in `issues[]` as the Tier-4 half. Update `R9_DESIGN_SYSTEM.md:40-42,:133` to say where it runs.
  - Test: a fixture file with `gap-1.5`/`text-[12px]` under a tmp scan root makes the audit exit non-zero.
- **Checks:** `pnpm lint` (now including the audit) must be clean at base. Run `node scripts/ensure-all-sidecars.mjs --force` detached and confirm all three binaries build and `node scripts/smoke-test-sidecars.mjs` passes. This is the heavy lane, so run it once, at the end.

### W2: `runtime-schema` (opus)

Why opus: agent-runtime state machine (CODE-AGENT-009) and persistence migration of every store and the workspace blob (LIFECYCLE-024) are both risk-adjacent.

- **R15-CODE-AGENT-009 (god function)**
  - Mechanism: `agent_runtime.py:1743-2230` `invoke_agent` is 487 lines. It owns option popping and publishing (:1792-1893), the round stream consumer (:1946-2088), tool dispatch and read-back (:2128-~2200) and the end-of-turn notices. Batch 10 extracted only the tool surface, native search and planner pre-pass.
  - Fix: extract the per-run option preparation (the pops/ContextVar publishes/scrub into one returned object), one round's stream consumption, one round's tool dispatch (tool-result messages, AUTO read-back) and the end-of-turn notices into named functions. The loop logic is unchanged and every event keeps its order.
  - Acceptance: `invoke_agent` ≤ 150 lines (ast-measured), and each extracted function has a direct unit test in `test_runtime_phases.py` that needs no fake provider. Every existing `test_agent_runtime*`, `test_b3_*`/`test_b4_*`/`test_b5_runtime_*`, `test_tool_loop_e2e`, `test_runtime_prepass`, `test_reasoning_split` passes unmodified.
- **R15-LIFECYCLE-024 (no schema version, no upgrade backup)**
  - Mechanism: all seven surviving SQLite stores are `CREATE IF NOT EXISTS` plus hand-rolled "add nullable column" guards (`fundamentals_store.py:172-182`, `runs_store.py:94-102`, `plugins_store.py:53-67`; none in `portfolio_db.py:26-35`, `agents_store.py:23`, `workflow_store.py:26-34`, `data_cache.py:59-65`). `PRAGMA user_version` is 0 everywhere. `workspace.ts:174` versions only the model overrides. Nothing backs up the data dir before a new build.
  - Fix:
    - `schema_version.migrate(conn, steps)` keyed on `PRAGMA user_version`: forward-only, each step runs in a transaction, and step 1 is the store's current schema plus its existing additive guards. All seven stores use it.
    - A `user_version` newer than the code knows is logged and left untouched (no downgrade migration, no crash).
    - `data_cache.ensure_build`, before it clears, copies the data dir once to `<data>/backups/<old-build>/` (excluding `backups/` and `logs/`) when a different previous build is recorded; there is no backup on a first boot.
    - `SerializedWorkspace.schemaVersion` plus a migrate chain in `deserializeWorkspace` (an older blob without it = version 0 → migrated).
  - Tests:
    - A store DB at user_version 0 with the old schema migrates to N, and a second open is a no-op.
    - A future user_version is left alone.
    - A build change produces exactly one backup and the same build produces none.
    - A v0 workspace blob deserializes and re-serializes with `schemaVersion`.
- **Decision:** D-B11-4 (§6).

### W3: `agent-eval` (opus)

Why opus: designing a grader over a live agent end state and root-causing any wire-shape break it finds in an adapter is judgement work on the agent-chat path.

- **R15-AGENT-007 (no eval loop)**
  - Mechanism: every agent test runs against hand-authored fakes (`test_research_fast.py:3`). The Anthropic SSE path is now tested on the real frame shape (`test_llm_anthropic.py` `_sse`, `anthropic.py:271` emits on `content_block_stop`), but there is no scenario set, grader or pass^k per lane, and the Gemini stream fixtures have not been checked against the documented wire shape. The refuter narrowed the scope: Ollama, OpenRouter, OpenAI and DeepSeek have had ad-hoc live runs, while Anthropic and Gemini have had no live tool loop.
  - Fix:
    - Write `scripts/agent_eval/` holding 12-20 fixed real-data scenarios as JSON: tool-arg asks (price_data/fundamentals on RELIANCE, AAPL), a research brief, host actions (watchlist add, chart indicator, portfolio add, staged under ASK), macro, SEC filing, disclosures and a missing-parameter ask.
    - The grader is deterministic over the vy.py event stream plus the end state: expected tool names/args predicates, an expected `research_step`/publish, a staged host action, a non-empty answer, and no forbidden text. It computes pass^k per lane (a scenario passes only if all k trials pass).
    - The runner (`python scripts/agent_eval/run.py --lane ollama|openrouter-free|openai --k 3`) reuses `scripts/r15/vy.py` for the key-safe drive and its budget guard, and writes a JSON report to the scratchpad.
    - Add real-shape cassettes for the Gemini stream (functionCall with args object, multi-part) and fix any adapter bug a cassette exposes.
  - Tests: `sidecar/tests/test_agent_eval.py` grades recorded event streams, one pass and one per failure mode (the grader must fail a tool call with `{}` args, the Anthropic COD-llm-adapters-2-1 shape), plus the pass^k arithmetic. The cassette tests go in `test_llm_gemini.py`/`test_gemini_multiround.py`.
  - Live proof: take the C9 lane, run the full set at k=3 on ollama llama3.1:8b and on one OpenRouter `:free` tool model, and report the pass^k numbers. An OpenAI run is allowed only within vy.py's guard. The Anthropic/Gemini live pass is operator-attended (no key here, D35); state that in the report.
  - The release-gate wiring into CLAUDE.md's gate list is a Stage D note, not this writer's job.

### W4: `registry-loop` (opus)

Why opus: LIFECYCLE-026's root cause is unknown (no profiler was attached in the census), so it has to be root-caused before the fix shape is known.

- **R15-LIFECYCLE-026 (idle loop CPU burn)**
  - Mechanism, known part: `provider_registry._resolve_async:444-446` calls sync accessors (yfinance fundamentals/statements/analyst) inline on the event loop (`fn(*args)` then `await` only if awaitable).
  - Mechanism, unknown part: the ~100 s of CPU between requests in the L6 soak (99% on the loop thread). Candidates are the background loops started in `app.py:124-141`: screener warm, `fundamentals_warm` (:199,:301,:373), the `nse_symbol_change` refresh, `workflow_scheduler`, SearXNG `warm_detect`.
  - Fix:
    - Profile first. Boot the source sidecar (C9 lock, port 52410, a copy of an iso data dir, region IN, keyless) and drive a light soak (8 cheap GETs/min). During an idle gap take `sample <pid> 10` (or `py-spy dump` if installed) and attribute the loop-thread CPU.
    - Then move the hot path off the loop: `asyncio.to_thread` for non-coroutine accessors in `_resolve_async`, plus whatever spinning or re-scheduling loop the profile names.
    - Record the attribution in the commit body.
  - Tests:
    - `test_provider_registry.py`: a sync accessor in `_resolve_async` runs off the event-loop thread.
    - `test_loop_idle.py`: the fixed background loop's idle wake-ups are bounded (fake clock or counter), on the loop the profile named.
    - A live before/after soak number: idle-gap loop CPU < 5% over 5 min.
- **R15-DATA-071 (registry fall-through leg)**
  - Mechanism: batch 10 added `OHLCVSeries.partial`/`coverage_start` (`bse_provider.py:505-518`), but `_resolve_sync:378-388` returns the first non-error result, so a partial BSE range still ends the walk before yfinance. D-B10-8's "under 50% → ProviderError" was not delivered.
  - Fix: give `_resolve_sync` the same `accept` gate `_resolve_async` has, and have `get_history` pass `accept=lambda s: not s.partial`. A partial result is kept as the fallback, the next lane is tried, and the ranked-first partial is served, still flagged, only when no lane is complete. This supersedes D-B10-8 (D-B11-3).
  - Tests: a fake ranked-first partial and a complete second lane serve the second; a partial first with an erroring second serves the partial flagged. Class case the fix was not written against: two partial lanes serve the higher-ranked one, and a quote (no `accept`) is unchanged.

### W5: `data-reference` (sonnet)

- **R15-LEAD-028 (BSE scrip code 404s)**
  - Mechanism: `symbol_resolver.is_bse_symbol`/`bse_scrip_code` (:586-595) key `_bse_master()` by ticker only. `bse_provider._require_bse` (:454-463) rejects `506597.BO`, and the numeric index `_bse_scrip_index` (:397) is used only by `/resolve`.
  - Fix: map an all-digit bare BSE symbol through `_bse_scrip_index` in `is_bse_symbol`/`bse_scrip_code`, and have `_require_bse` return the canonical ticker, so every BSE data path accepts the code.
  - Tests: resolve the same listing by code and by ticker (quote and history on fakes), then a second code the fix was not written against; an unknown code still raises not-found.
- **R15-DATA-059 (former names; US identity)**
  - Mechanism: `_enrich_instrument` (:1235) returns early for non-NSE/BSE instruments; `_us_master` (:440) holds only `[ticker, name]`; there is no former-name index; `private` is not in `_CORP_SUFFIXES` (`_canonical_name` maps pvt⟺private but keeps the word).
  - Fix:
    - A bundled `former_names.json` master generated offline by a new `resolver_masters/regenerate_former_names.py`. The US side comes from SEC EDGAR submissions `formerNames` for the US master's CIKs, with a fair-access UA at ≤10 req/s, detached. The IN side comes from NSE's company name-change file.
    - The name scan matches a former name as a bound or disambiguate candidate carrying `former_name`.
    - Add `private`/`pvt` to the suffix strip.
    - US ISIN stays null by decision (D-B11-5); board/listing_date are product-wide schema gaps, which go to `issues[]`.
  - Tests: `BeiGene` → ONC with `former_name` 'BeiGene, Ltd.'; `Toss the Coin Private Limited` → TTC; the class case is an Indian rename from the NSE file.
- **R15-LEAD-013 (stale sp500 pack)**
  - Mechanism: `sp500.json` is a 2026-06-04 snapshot. Batch 10's regeneration (`fde0ad3c`, `ccd5b0da`) was reverted (`d5370601`) because `us_fundamentals_seed.json.gz` covered 463 of 503 new names, below `test_shipped_us_pack_covers_sp500_whole`'s 95% floor (`test_fundamentals_seed.py:56-76`).
  - Fix:
    - Re-apply `fde0ad3c` and `ccd5b0da` (cherry-pick).
    - Then crawl the newly added constituents paced and detached, and regenerate or extend the US seed pack (rows carry a per-row `seed_as_of`), so the pack is a subset of the universe and covers ≥95%.
    - If Yahoo stays rate-limited, report the achieved coverage and stop; never lower the floor.
  - Tests: `test_sp500_universe.py` (known-current present, known-delisted absent, age ≤180 days) and `test_shipped_us_pack_covers_sp500_whole`, both green.

### W6: `options-chain` (opus)

Why opus: a new data capability that crosses the catalog (the one source of truth), the MCP projection, the types mirror and a new exchange parser. It is risk-adjacent to the D81 line: research data only.

- **R15-DATA-079 (no OI / option chain)**
  - Mechanism: no `open_interest` symbol exists outside quant tests; Greeks are model-computed only (`catalog.py` `price_option`/`compute_greeks`). Spec User Story 2 has the user "check the options chain in the quant panel".
  - Fix:
    - `services/option_chain.py`. IN uses the NSE F&O UDiFF bhavcopy (`nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip`, walked back over holidays like `nse_bhavcopy.py`): per-contract expiry, strike, CE/PE, OI, change in OI, close/settle, volume, as_of. US uses yfinance `option_chain` (OI, IV).
    - `OptionChain`/`OptionContract` models are mirrored in `types/data.ts` and served as `GET /quant/option/chain/{symbol}?expiry=`, with provenance and `as_of`, and EOD labelled.
    - A `read_handler` catalog capability `option_chain` (auto-projects to the MCP surface), added to `copilot.json`/`researcher.json`, with the count assertions bumped.
    - A chain view in the quant panel (strike rows, CE/PE OI and change in OI).
  - Tests: parse a committed trimmed F&O bhavcopy fixture (NIFTY and one stock) into the chain with OI; the US leg on a stubbed yfinance frame; route 404/`not_found` for a non-F&O symbol; catalog parity green; a vitest test that the chain view renders OI.
  - Decision: D-B11-6.

### W7: `preferences` (opus)

Why opus: a provider fallback inside the chat send path (agent-chat state machine) and a launch-restore branch (workspace persistence) are both risk-adjacent.

- **R15-UI-087 (FR-038 preference depth)**
  - Mechanism: `llm-providers.ts:127-136` has a single default pick. `settings.ts` dropped `providerPreferenceOrder`/`palette*`/`starterCockpitPanelIds` in R9 because nothing consumed them. The `ChatSidebar.tsx:1062-1090` send path has no fallback. `restoreLastSessionOrDefault` is the only launch path (`PanelHost.tsx:239`).
  - Fix:
    - **Provider order:** an ordered provider list in `llm-providers.ts`, reorderable in Settings (drag plus up/down buttons for keyboard use).
    - **Fallback:** on a classified provider failure (error frame `code` auth/402/quota/network/unreachable, per `streaming.ts:36-60`) BEFORE any answer text streamed, the send retries once on each next configured provider (a key present, or keyless) with its effective model. A notice chip says who failed and who answered. There is no fallback on content errors, after partial output, or when the user aborted.
    - **Start with:** a picker (last session | a named layout) read in `PanelHost` that calls the existing loaders (C6).
    - **Palette behaviour:** two options that parameterise behaviour `CommandPalette` already hard-codes (e.g. recents-first ordering and the instrument-search scope), each consumed by the palette.
    - Plus the C1 swaps in `CommandPalette.tsx`/`ChatSidebar.tsx`.
  - Tests:
    - A store/send test where a first-provider auth failure routes to the second and the notice names both.
    - A failure after a delta does NOT fall back.
    - A start-with named layout loads that layout, and a missing layout falls back to the last session.
    - Each palette option changes the palette's result order or scope.
  - Decision: D-B11-7.

### W8: `frontend-visual` (sonnet)

- **R15-UI-085 (contrast floor)**
  - Mechanism: `text-charcoal-600` (#484848, ~1.98:1 on #161616) is used as readable text in 20 places. `tokens.css:40` defines it as a border/disabled fg.
  - Fix: swap to `text-charcoal-500` (tertiary, 5.7:1) in W8's nine files and `PortfolioPanel.tsx`; W7 does two files (C1). Keep charcoal-600 only as a `disabled:`/border use.
  - Tests: `src/lib/design-contrast.test.ts` does two things.
    - It parses `styles/tokens.css` and computes WCAG contrast of each text token (charcoal-100..500, sage-500) against charcoal-900 and charcoal-950. The floors are from `R4_DESIGN_LANGUAGE.md:271-277`: body ≥4.5, labels ≥3.
    - It source-scans `src/**/*.tsx` (non-test) for an unprefixed `text-charcoal-600`/`-700`. That is the class pin, since it catches any future file.
- **R15-UI-091 (chart indicator defaults, frontend leg)**
  - Mechanism: the sidecar side is done (`fast.py:108` `_suggested_indicators(timeframe, asset_class)`; `indicators.py` parses `ema:9`/`vwap:week`). But `indicators.ts:418` `indicatorByKey` matches exact keys only, so `host-actions.ts:574` drops `ema:9`. No frontend consumer of the suggested set exists, and a fresh chart takes `settings.chartDefaults.indicators` (`ChartPanel.tsx:289`).
  - Fix:
    - Add `GET /indicators/suggested?timeframe=&asset_class=` (declared before `/{symbol:path}`) returning `_suggested_indicators`, the one source.
    - `indicatorByKey` resolves `base:param` to the base def and keeps the full spec as the series key and label ("EMA 9"); `splitIndicatorKeys` keeps the raw spec.
    - A chart whose indicator set is untouched (no persisted view, no user "Make default") seeds the suggested set for its (asset class, timeframe) on open and on a timeframe/symbol change. A user edit stops reseeding.
  - Tests:
    - Sidecar: (equity, 5m) → ema:9, ema:21 and (crypto, 1d) → ema:50, ema:200, vwap:week.
    - Vitest: a fresh 5m equity chart requests `ema:9,ema:21`; `set_chart_indicators ['ema:9']` is not dropped; after a user toggle, a timeframe change does not reseed.
  - Decision: D-B11-8.
- **R15-CODE-PLATFORM-023 (portfolio risk metrics)**
  - Mechanism: Sharpe/Sortino/Calmar/max drawdown exist only in `backtest_engine.py:236-282`, and VaR/Beta/correlation exist nowhere. BLUEPRINT lists them under Portfolio & Risk.
  - Fix:
    - Pure functions in `metrics.ts` over daily closes (via the existing `/history` client, 1y), per currency bucket (never cross-currency, D57): daily returns, annualised vol (√252), Sharpe (rf = 0, labelled), Sortino, max drawdown, Calmar, 1-day historical VaR 95%, Beta vs the bucket's benchmark (INR ^NSEI, USD SPY) and a holdings correlation matrix.
    - A Risk section in `PortfolioPanel` with loading/insufficient-history states. Metrics are null, never fabricated, under 30 overlapping days.
  - Tests: every metric on a hand-computed fixed series (asserted to 1e-9), a mixed-currency portfolio that yields per-bucket metrics only, and an insufficient history that yields null.
  - Decision: D-B11-9.
- **R15-CODE-PLATFORM-025 (BLUEPRINT multi-window)**
  - Fix: in `BLUEPRINT.md` §4 item 5, say "multi-tab (dockview, shipped); multi-window (v1.0 roadmap)", and in §5.2 mark "pop-out to second window" v1.0 roadmap (§2 untouched).
  - Test: none (docs); the verifier greps it.

---

## 3. Integrator run order and gates

**Stall rule (all roles):**
- No single tool call runs longer than ~120 s.
- `pnpm ci-local`, full pytest/vitest, cargo, PyInstaller builds, sidecar boots and soaks start detached and are polled with separate short calls.
- Never an `until`/`sleep` loop inside one call.
- Emit a tool call at least every 2 minutes.

1. Work in a scratch worktree (`git worktree add <scratchpad>/b11-int 004-r4-experience-rebuild`), never the main repo (it holds the uncommitted `CLAUDE.md` hunk, the ledger and the register edits).
2. Audit each branch through `origin/worktree-agent-batch-11-<Wn>-<name>`:
   - `git merge-base --is-ancestor 30b6414f origin/<branch>` (a stale base means re-dispatch).
   - `git diff --stat 30b6414f..origin/<branch>` touches only that writer's §1 files.
3. Merge `--no-ff` in this order, running that writer's tests detached after each:
   1. **W1:** `pnpm vitest run scripts`, `pnpm lint` (the audit is now in it).
   2. **W4:** `test_provider_registry.py`, `test_loop_idle.py`, `test_bse_provider.py`, `test_history*.py`, `test_fundamentals*.py`, `test_screener*.py`.
   3. **W2:** `test_runtime_phases.py`, `test_agent_runtime*.py`, `test_b3_*`, `test_b4_*`, `test_b5_runtime_*`, `test_tool_loop_e2e.py`, `test_runtime_prepass.py`, `test_schema_version.py`, the seven stores' tests, and the workspace vitest.
   4. **W5:** `test_symbol_resolver*.py`, `test_bse_provider.py`, `test_sp500_universe.py`, `test_fundamentals_seed.py`, `test_screener*.py`.
   5. **W6:** `test_option_chain.py`, `test_capability_catalog.py`, `test_mcp_catalog_parity.py`, `test_mcp_server.py`, `test_main_stdio.py`, `test_agents_router.py`, `test_quant*.py`, quant vitest, `pnpm typecheck`.
   6. **W3:** `test_agent_eval.py`, `test_llm_*.py`, `test_gemini_multiround.py`.
   7. **W7:** settings/llm-providers/ChatSidebar/CommandPalette/PanelHost vitest.
   8. **W8** last, after W7 (C1): `design-contrast.test.ts`, chart/host-actions/portfolio vitest, `test_indicators*.py`, then the full vitest.
   - No integrator code edits. A cross-writer seam break is re-dispatched to its owner.
4. Gates after all eight (export `PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH` first; run everything long detached):
   - `ruff format --check sidecar && ruff check sidecar`.
   - `pnpm format:check`, `pnpm lint`, `pnpm typecheck`.
   - `node scripts/ensure-all-sidecars.mjs --force`. W5's `sp500.json`/US seed and the new `former_names.json` must be inside the main binary (they ride the existing `--add-data`).
   - `pnpm ci-local` with the exit code recorded.
   - `node scripts/smoke-test-sidecars.mjs`.
5. Grep checks:
   - `audit-design-tokens.mjs` has no `import.meta.url).pathname`.
   - `sidecar-staleness.mjs` has no extension allow-list regex.
   - `smoke-test-sidecars.mjs` has no literal `extraFiles: [join(ROOT, "scripts", "ensure-`.
   - `invoke_agent` is ≤ 150 lines.
   - `_resolve_async` has no bare `fn(*args)` on the loop for a sync accessor.
   - `host-actions.ts` keeps `ema:9`.
   - `grep -rn "text-charcoal-600" src --include=*.tsx` hits only `disabled:`/border uses.
   - `BLUEPRINT.md` §5.2 marks pop-out as roadmap.
6. Record §6 decisions D-B11-1..10 in `docs/redesign/DECISIONS.md` and `CHANGELOG.md` at merge. D-B11-3 supersedes the D-B10-8 row's mechanism (say so in that row's text).
7. Tell the Stage D docs wave to run `mode: refresh` after this merge. The BLUEPRINT edit and the new capabilities, routes and settings change what the CURRENT_STATE/BLOCKERS drafts derive. Add a handover item for the AGENT-007 release gate (the eval run per lane) and the operator-attended Anthropic/Gemini pass.
8. Certification notes (one fresh verifier, Opus):
   - **AGENT-007:** re-run the harness at k=3 on ollama and one `:free` lane; the grader fails a doctored `{}`-args stream.
   - **CODE-AGENT-009:** the ast line count.
   - **LIFECYCLE-026:** a fresh idle-gap CPU sample on a source sidecar (< 5%).
   - **DATA-071:** a cold `/history/<BSE-only small-cap>?range=1y` either serves a complete lane or `partial:true` with `coverage_start`.
   - **LEAD-028:** live `/quotes/506597.BO` and `/history/544774.BO` → 200.
   - **DATA-059:** live `/resolve?q=BeiGene` → ONC with former_name.
   - **LEAD-013:** pack age and seed coverage.
   - **DATA-079:** live `/quant/option/chain/NIFTY` carries OI and as_of; an agent run on ollama calls `option_chain`.
   - **LIFECYCLE-024:** copy a 0.8.0-era data dir, boot, and confirm the user_version values and one backup dir.
   - **UI-087, UI-085, UI-091, PLATFORM-023:** vitest-certified. GUI feel is recorded as needs-GUI.
   - **PLATFORM-026/027/028, RELEASE-005/006/007:** the tests plus the forced build and smoke.
   - Concur or refuse each §5 proposal.

## 4. Deferred (with reason)

- **R15-AGENT-017 (high):** the shipped OpenRouter default (`model_registry.json:61`, `OnboardingFlow.tsx:60`) can only be replaced by a model proven on the portfolio-write scenario. That proof needs a funded OpenRouter lane, and R15-D8 records it as exhausted (DeepSeek-direct is at $0). W3's harness ships that scenario, so the swap becomes an operator-attended run at top-up. Swapping blind would repeat the default-not-proven class.
- **R15-AGENT-049:** the fix is in (batch 9, 6b70230). Certifying it needs a native-search lane: the OpenAI `*-search-preview` models 404 upstream, OpenRouter paid is unfunded, and there is no Gemini or Anthropic key. It is operator-attended.
- **R15-UI-088:** a Playwright harness needs three things:
  - a new e2e runner and test location, which the batch rule (tests only in `sidecar/tests`, `src/**/*.test.ts(x)`, `src-tauri`) does not allow without an operator call;
  - a browser download;
  - CI wiring, which is Tier-4 (`.github/`).
  
  Chromium also would not exercise the WKWebView path that `dragDropEnabled:false` guards. It needs an operator decision on the runner; the GUI lane is off in Stage C.

## 5. proposed_not_defect (out of the 0.9 release scope; each needs the verifier's fresh concurrence, all three are in the operator's named areas)

- **R15-UI-047 (ui-panels): panels cannot pop out to a second window.**
  - Multi-window is v1.0 roadmap: BLUEPRINT §4 is relabelled "20 shipped in 0.9.0; the rest is the v1.0 roadmap" (D-B10-4), and W8 now marks §5.2's pop-out as roadmap (CODE-PLATFORM-025, the same class).
  - Building it needs one of two paths, and neither is a 0.9 fix:
    - dockview's `addPopoutGroup` uses `window.open`, which needs a new-window handler on the main window. The main window is built from Tier-1 `tauri.conf.json`, so it would have to be built in code.
    - A separate runtime `WebviewWindow` has its own JS runtime and stores, with no cross-window state sync.
  - Only a GUI can verify either path.
- **R15-UI-059 (data-smallcaps, ui-panels, research-search): no composite score/scorecard.**
  - A competitive-parity feature from the world comparison (WLD-T-11, Trendlyne DVM/Tickertape).
  - No spec FR or BLUEPRINT module promises a score.
  - Choosing its inputs and bands is a product decision, not a defect fix. Record it as roadmap.
- **R15-DATA-080 (research-search, data-smallcaps): no segment/operational-metric data.**
  - A competitive-parity feature from the world comparison (WLD-T-13, Tijori/screener.in).
  - No spec FR or BLUEPRINT module promises it.
  - The refuter notes the data sits in Reg 33 results XBRL, a separate parser from the shareholding one, with per-filer taxonomy variance. Record it as roadmap.

## 6. Tier-3 decisions (the integrator records them; none is Tier-4)

- **D-B11-1:** `scripts/**/*.test.mjs` is a kept vitest location (node environment), per R15-CODE-PLATFORM-028's fix shape.
- **D-B11-2:** the design-token audit rides `pnpm lint`, so ci-local and any workflow running `pnpm lint` enforce it. Wiring a workflow that calls eslint directly is Tier-4 (`.github/`).
- **D-B11-3:** a `partial` OHLCV series is an incomplete result. The registry tries the next lane and serves the ranked-first partial, flagged, only when no lane is complete. This supersedes D-B10-8's "under 50% is a ProviderError".
- **D-B11-4:** every persistent SQLite store carries `PRAGMA user_version` with a forward-only migrate chain. A newer version than the code knows is logged and left untouched. The data dir is copied once to `backups/<old-build>/` when the build changes. The workspace blob carries `schemaVersion`.
- **D-B11-5:** former names come from SEC EDGAR submissions (US) and NSE name-change records (IN), shipped as a bundled master. US ISIN stays null (CUSIP-derived identifiers are CGS-licensed; SEC data carries none).
- **D-B11-6:** the option chain is EOD and exchange-published: the NSE F&O UDiFF bhavcopy for IN and yfinance for US, served at `/quant/option/chain` and as the `option_chain` capability. It is research data; D81 stands.
- **D-B11-7:** provider fallback fires only on a classified provider failure before any answer text, never on a content error, after partial output or on a user abort. The turn states which provider answered.
- **D-B11-8:** an untouched chart indicator set seeds FR-092's (asset class, timeframe) set from the sidecar's one table. A user edit or a "Make default" chart default wins.
- **D-B11-9:** portfolio risk metrics are per currency bucket, on daily closes, with √252 annualisation, rf = 0 (labelled), a 1-day historical VaR 95%, and Beta vs ^NSEI (INR) or SPY (USD). They are null under 30 overlapping days.
- **D-B11-10:** the agent eval harness lives in `scripts/agent_eval/`, and pass^k counts a scenario only when all k trials pass. The Anthropic/Gemini live pass is operator-attended.

## 7. Writer ground rules

1. **Worktree.**
   - Work in your own isolated worktree and branch `worktree-agent-batch-11-<Wn>-<name>`.
   - First run `git reset --hard 30b6414ff63f2fce81acbbf298dcddeecc155f81` and confirm with `git log -1`.
   - Never the main worktree.
   - Push after each concrete deliverable. On a restart, read your branch log and continue.
2. **Stall rule.** No tool call longer than ~120 s. Long runs (pytest suites, builds, crawls, sidecar boots, soaks) are detached and polled in separate short calls.
3. **Commits.** One focused commit per entry or root-cause group, conventional, no emojis, ending with the session's attribution trailer.
4. **Tests.**
   - Tests go only in `sidecar/tests`, `src/**/*.test.ts(x)`, or (W1 only, D-B11-1) `scripts/*.test.mjs`.
   - Pin the class case named above; it is the one the fix was not written against.
   - Never delete, skip or weaken a test to get green. A test that encodes the defect is fixed with the reason in the commit.
   - Never special-case code to satisfy a test.
   - Live captures become add-only fixtures, never live calls in a test.
5. **Checks before committing.**
   - Export the PATH line from §3.
   - Python: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`.
   - TypeScript: `pnpm format:check`, `pnpm typecheck`, `pnpm lint` and your vitest files.
6. **Scope.**
   - Touch only your §1 files and honour C1-C10 exactly.
   - A needed change elsewhere goes to `issues[]` with the exact line, as do pre-existing oddities.
   - No refactoring beyond the entry.
7. **Docs.** Only W1 (`R9_DESIGN_SYSTEM.md`) and W8 (`BLUEPRINT.md` outside §2) edit docs, and only those files. Nobody edits DECISIONS.md, CHANGELOG.md or the register.
8. **Hard limits.**
   - Never re-add trading.
   - Never touch `CLAUDE.md`, `src-tauri/tauri.conf.json`, `.github/`, `LICENSE*`, `types/plugin.ts` or `r15-fanout.js`.
   - Read no `R15_BRIEF*.md` and nothing under `r15/local/`.
   - No GUI.
   - Never print, log or commit a secret. `vy.py` reads keys in-process; never echo one.
