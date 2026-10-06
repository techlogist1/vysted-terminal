# RC1 adversarial sample verifier: shard 3 (rc1-vshard-3)

- **Candidate:** `1d6511c89bb27f1785f7af4d2290983b2852d70a`. Worktree `rc1-4097dac-fix-int` was used read-only; `git status` was clean at the end.
- **Own sidecar:** booted from the candidate source on `:52603`, data dir `rc1-data-rc1-vshard-3` (a `cp -R` of `rc1-seed-data`), sleep pid 97375. The shared MCP stack on `:52153` and `:52154` was only read.
- **Frontend and scripts checks:** run in a `git archive` copy of the candidate (`scratchpad/vshard3/cand`), with node_modules and sidecar symlinked read-only and the vitest cacheDir redirected to scratch.
- **Model:** local `llama3.1:8b` via Ollama. `vy.py` refuses non-GET calls outside ports 52100-52399, so the one agent run was a direct `POST /agents/copilot/invoke` on my own `:52603`. It cost nothing.
- **Evidence:** `shard-3-evidence/`. Findings: `../findings/rc1-vshard-3.json`.

| id | verdict | one-line reason |
|---|---|---|
| R15-DOCS-018 | **refuted** (partial) | The asset-class sentence is gone, but §3.3 still never names nse_direct/nse/bse or their ranks. It still calls yfinance "no-key default for equities". |
| R15-LEAD-010 | **refuted** (partial) | The viewer path works. The same listed AAPL FY2023 10-K still 404s via `/sec/filings/{acc}/sections` and the `data.fetch_sec_filing` workflow node. |
| R15-LEAD-013 | holds | The pack matches live Wikipedia exactly (503/503, 0 missing, 0 extra). The delisted names are gone. Residual: new_defect :6. |
| R15-CODE-PLATFORM-014 | holds | `configure()` re-initializes an active plugin with the new secret. A disabled plugin stays stopped. |
| R15-CODE-PLATFORM-013 | **refuted** | The Settings > Modules toggle is still a separate writer of `plugin:<id>`. It diverges from plugins.db and is lost on relaunch. |
| R15-CODE-PLATFORM-023 | holds | New real-data cases (INR: INFY.NS+TTC.BO vs ^NSEI; USD: AAPL+MSFT vs SPY) match an independent Python reference to 1e-9. |
| R15-DATA-059 | **refuted** | The register's own repro reproduces verbatim: `/resolve?q=ONC` and `?q=SIFY` give isin=null and former_name=null. |
| R15-CODE-PLATFORM-024 | holds | BLUEPRINT §3.1 describes the `write_text_atomic`/`write_bytes_atomic` path. CSV exports go through `saveTextArtifact`. |
| R15-CODE-PLATFORM-025 | holds | BLUEPRINT :249 and :322 mark multi-window as a deferred v1.0 item. There is 1 window, no pop-out code, and no other doc claims otherwise. |
| R15-DOCS-017 | **refuted** | The sp500 line is stale again (506, 2026-06-04, "LEAD-013 open"; actual: 503, 2026-09-24). nse-all/bse-all/india-all are still undocumented. |
| R15-CODE-PLATFORM-028 | holds | The 4 scripts test files run under vitest. Mutants (the old allow-list, a removed excludeDirs prune) each turn them red. |
| R15-RELEASE-005 | holds | The extension allow-list is gone. Touching a `.yml` or `.md` data file marks the binary stale; `.pyc` and an excluded MCP dir do not. |
| R15-RELEASE-006 | holds | The ensure scripts, the orchestrator and the smoke gate all read `SIDECAR_SPECS`. An input added to the spec makes both the builder and the gate go stale. |
| R15-LIFECYCLE-024 | holds | All 7 stores go from user_version 0 to 1. A 0.7.5 marker triggers `backups/0.7.5` (keystore mode 600), and a second boot is a no-op. Residual: new_defect :7. |

## Details

### R15-DOCS-018: refuted (partial, low)

**Original repro.** `docs/CURRENT_STATE.md:320-330` now describes preference-order resolution by model key, so the asset-class sentence is gone.

**Variant.** The entry is really about how the doc undersells India coverage, so I checked what §3.3 says about the Indian providers.
- The provider list in §3.3 has no nse_direct/nse/bse entry at all: grep for `nse_direct|NSE|BSE|jugaad` returns 0 hits in the section.
- It still says `yfinance_provider.py` is the "no-key default for equities".
- In the code, `provider_registry.py:161-219` ranks nse_direct 15, nse 20, bse 25 and yfinance 50.
- `/health` on `:52603` reports `"ohlcv":"ccxt (nse_direct, nse, bse, yfinance fallback)"`.

The fix_shape asked for "listing the IN chain and ranks". That part was not done.

### R15-LEAD-010: refuted (partial, medium)

**Original repro holds.**
- `GET /sec/filings?symbol=AAPL&form_type=10-K` lists 10 10-Ks.
- `GET /sec/filings/0000320193-25-000079?identifier=AAPL&form_type=10-K` returns 200 with Apple Inc. 10-K sections. `-24-000123` also returns 200.
- Older 10-Ks with the hint also return 200: 19-000119 and 16-020309.
- llama3.1:8b chose `sec_filing_content {accession: 0000320193-23-000106, form_type: "10-K"}` and summarized Business correctly.

**Variant: the same listed filing through the callers that send no hint.**
- `GET /sec/filings/0000320193-23-000106/sections?identifier=AAPL` returns **404** `not_found`.
- `GET /sec/filings/0000320193-23-000106?identifier=AAPL` (no `form_type`) returns **404**.
- In-process, `sec_nodes.fetch_sec_filing({}, {accession: "0000320193-23-000106", identifier: "AAPL"})` raises `ProviderError: filing metadata unavailable`. For comparison, 25-000079 returns OK through the same node.

**Cause.** `sec_filings_provider.get_filing_sections` (:661) and `workflow_nodes/sec_nodes.py:50` call `get_filing` without `form_type`. With no hint, the lookup is still the unfiltered 40/100-row window this entry was about. The fix patched the viewer's and the agent tool's inputs rather than the lookup, so the defect class survives on those two sibling callers.

### R15-LEAD-013: holds

**Original repro.** On 2026-09-25 I diffed the pack against Wikipedia's live constituents table: 503 vs 503, nothing missing and nothing extra. BXP, NVR and UDR are present. None of the 14 known-delisted names remain. `test_sp500_universe.py` pins the list with a 180-day staleness limit.

**Variant: a cold keyless sp500 screen while Yahoo v7 was returning 429.**
- Result: 498/503 screened.
- The 5 skips are **BXP, ECHO, NVR, UDR, VMRK, all `rate_limited`**. These are exactly the names the regenerated `us_fundamentals_seed.json.gz` (498 rows) does not carry.
- BXP itself quotes fine: `/quotes/BXP` returns 200 from yfinance.

The pack is correct, but the seed pack regenerated in the same batch leaves out the names this entry pinned. Logged as new_defect :6 (low).

### R15-CODE-PLATFORM-014: holds

**Original.** `plugin-runtime.test.ts` and `marketplace.test.ts` pass in the archived copy (8 files, 114 tests).

**Variants (scratch vitest, not committed).**
- `configure("vysted-news")` twice on an active plugin: `initialize` is called 2 times, and the second call receives `secrets` keys `plugin-secret:vysted-news:newsapi_key`. The module count is unchanged.
- `configure()` on an installed but disabled plugin: `initialize` is not called and the state stays `stopped`.

### R15-CODE-PLATFORM-013: refuted (low)

The pinned case holds: an older blob with `plugin:x=false` no longer hides a plugin that was re-enabled since. The Plugin Manager now goes through the marketplace store.

**Variant.** The Settings > Modules `ToggleRow` (`SettingsPanel.tsx:1940`) calls `setModuleEnabled(module.id, false)` for every row, and the plugin modules are listed there too.

Scratch run on `vysted-example`, after toggling it off there:
- The module map says `enabled=false`.
- The marketplace says `{enabled: true, runtimeState: "active"}`.
- plugins.db says `enabled=true`.
- `serializeWorkspace` drops the flag.
- After a relaunch over the same plugins.db, the module is `enabled=true` again.

So "is this plugin on?" still has two writers, and this toggle's choice is now silently thrown away.

### R15-CODE-PLATFORM-023: holds

I pulled new real 1y closes from `:52603` and ran them through `computeCurrencyRisk` (a copy of `metrics.ts` under node strip-types), then through an independent Python `statistics` implementation.

| Case | Days | Vol | Sharpe | Sortino | MaxDD | Calmar | VaR95 | Beta | Corr |
|---|---|---|---|---|---|---|---|---|---|
| INR: INFY.NS 0.6 + TTC.BO 0.4 vs ^NSEI | 192 | 0.375548 | -1.463296 | -1.953978 | -0.470546 | -1.167873 | 0.044357 | 0.659308 | 0.072844 |
| USD: AAPL + MSFT vs SPY | 250 | 0.215903 | 0.802328 | 1.219971 | -0.214374 | 0.808052 | 0.020155 | 0.814079 | n/a |

Every metric agrees with the reference to within 1e-9.

The data came from mixed providers: nse_direct stamps `00:00Z`, yfinance `^NSEI` stamps `+05:30`, and bse stamps `Z`. `timestamp.slice(0,10)` still aligns them on the trading date.

### R15-DATA-059: refuted (medium)

**Original repro, verbatim.**
- `GET /resolve?q=ONC` gives `isin: null, former_name: null, board: null`.
- `GET /resolve?q=SIFY` gives `isin: null, former_name: null`.
- The bundled `former_names.json` does carry `ONC: ["BeiGene, Ltd."]` and `SIFY: ["SIFY LTD", "SATYAM INFOWAY LTD"]`. It is used only to match name queries, never to fill identity on a ticker resolve.
- `?q=ETERNAL`, an NSE ticker, does return `former_name: "ZOMATO"`, which shows the gap is US-specific.
- `us_instruments.json` rows are still `[ticker, name]`, so no US name has an ISIN or CUSIP. The fix_shape asked to "add ISIN/CUSIP to the US master".

**Name-query variants work.**
- `BeiGene` returns ONC and BEIGF candidates.
- `Satyam Infoway` resolves to SIFY.
- `Facebook` resolves to META.
- `Square Inc` returns XYZ as a candidate.
- `Toss the Coin Private Limited` resolves to TTC on BSE.

### R15-CODE-PLATFORM-024: holds

- `capabilities/default.json` has no `fs:*` permission, and `tauri-plugin-fs` is absent.
- `lib.rs:513-514` registers `write_text_atomic` and `write_bytes_atomic`.
- `downloadCsv` calls `saveTextArtifact`, which invokes `write_text_atomic`. The Blob download runs only as the non-Tauri fallback.
- BLUEPRINT §3.1 (:77-81) now describes exactly this.

### R15-CODE-PLATFORM-025: holds

- `tauri.conf.json` declares 1 window.
- There is no `WebviewWindowBuilder`, `addPopoutGroup` or pop-out anywhere in `src/` or `src-tauri/src`.
- BLUEPRINT :249 and :322 scope multi-window to the deferred v1.0 roadmap.
- `git grep` across README, docs/*.md, specs and .specify finds no other multi-window claim.

### R15-DOCS-017: refuted (medium)

**What §3.3 of the candidate says now (`docs/CURRENT_STATE.md:358-365`):**
- sp500 is "506 symbols, a static snapshot dated 2026-06-04 that has drifted ... R15-LEAD-013 open". This was written by f7f58adf to match the batch-10 revert.
- The shipped pack is actually 503 symbols with snapshot_date 2026-09-24, and LEAD-013 is fixed, so the line is wrong again.

**What is still missing:** `nse-all`, `bse-all` and `india-all` appear nowhere in CURRENT_STATE.md. They exist in `screener_universe_india.py` and `fundamentals_warm.py`, and the fix_shape named them explicitly.

The nested AND/OR claim was corrected and holds.

### R15-CODE-PLATFORM-028: holds

`vitest.config.ts` includes `scripts/**/*.test.mjs`, and the 4 files run (18 tests, all green).

**Mutation check in the scratch copy:**
- Restoring the old `(py|txt|toml|cfg|ini|json|csv)` allow-list fails the `.json.gz` test.
- Removing the `excludeDirs` prune fails 2 tests.

### R15-RELEASE-005: holds

The `SOURCE_EXT` allow-list is replaced by a deny-list (`.pyc`, `.pyo`, `.log`, `.DS_Store`).

**New tmp-tree cases:**
- Touching a `.yml` under resolver_masters makes the binary stale.
- Touching an `agents/*.md` makes it stale (the real `agents/README.md` is bundled via `--add-data`).
- Touching a `.pyc` does not.
- Touching the excluded `openbb_mcp_subprocess` dir does not.

Against the real candidate binaries, `assertAllFresh` passes and none of the 3 binaries is stale.

### R15-RELEASE-006: holds

- The three `ensure-*` scripts and `ensure-all-sidecars` read `SIDECAR_SPECS`. The smoke test imports `assertAllFresh` from `sidecar-specs.mjs`. No private staleness config is left anywhere.
- `tauri.conf.json` `beforeBuildCommand` and the CI workflows go through `ensure-all-sidecars` and the smoke test.

**Variant:** I pushed a fresh file into the main spec's `stale.opts.extraFiles`. The builder's `isStale` returned true and `assertAllFresh` threw `STALE SIDECAR`.

### R15-LIFECYCLE-024: holds

**Original repro.** My boot on the seed copy moved data_cache, fundamentals_cache and workflows to user_version 1. Touching `/portfolio/positions`, `/plugins`, `/custom-agents` and `/runs` moved the other four to 1, so all 7 stores end at 1.

**Variant, in-process on a seed copy with `meta.build` set to `0.7.5`:**
- `ensure_build("0.8.0")` created `backups/0.7.5` with every DB (quick_check ok), notes, workspaces, searxng and `dev-keystore.json` at mode `-rw-------`.
- A second call returned `cleared False` and made no new backup.
- Oddity: the backed-up `data_cache.db` is already at user_version 1, because `_connect` migrates it before `ensure_build` copies the data dir. This does no harm, since that cache is cleared on a build change anyway.

**Residual (new_defect :7, low).** The operator's real profile is marked `0.8.0`, and so is this candidate. It was migrated 0 to 1 with no backup, because the backup keys on the version string while the migrations key on user_version.

## Not checked or not applicable

- No ci-local or smoke run: out of this shard's scope. The shared stack was not written to.
- `vy.py` refused port 52603 (its guard allows only 52100-52399). The only model run was the ollama `llama3.1:8b` call above, made directly. No OpenRouter or OpenAI spend.
