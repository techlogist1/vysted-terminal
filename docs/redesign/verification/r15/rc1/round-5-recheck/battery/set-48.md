# batch-10/unassigned (set-48)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. In-process probes against the candidate's
sidecar venv, or direct source/grep checks where the entry is a doc/wiring claim.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-014 | source check: `src/lib/plugin-runtime.ts` `reloadPlugin`, `src/store/marketplace.ts` `configure()` call site | `reloadPlugin` exists (plugin-runtime.ts:319); `configure()` calls `await runtime.reloadPlugin(row.discovered)` (not `enablePlugin`) after persisting new secrets. Entry was certified only via a vitest test (`plugin-runtime.test.ts` "loadPlugin is idempotent, while reloadPlugin re-runs initialize with fresh secrets") — this shard does not run vitest | ci_pinned (src/lib/plugin-runtime.test.ts: "loadPlugin is idempotent, while reloadPlugin re-runs initialize with fresh secrets") |
| R15-CODE-PLATFORM-024 | source check: `src-tauri/capabilities/default.json`, `Cargo.toml`/`package.json` fs-plugin grep, `lib.rs` command registration, `BLUEPRINT.md` §3.1, `src/lib/csv.ts` -> `export-artifact.ts` wiring | no `fs:*` permission, no `tauri-plugin-fs` dependency; `write_text_atomic`/`write_bytes_atomic` are real registered Tauri commands (lib.rs:391,422,513-514); BLUEPRINT.md:77-81 states the corrected mechanism naming this entry; `csv.ts`'s `downloadCsv` routes through `saveTextArtifact` (the atomic-write commands), Blob download only as the non-Tauri fallback | holds |
| R15-CODE-PLATFORM-030 | in-process: register's literal repro — flat close of 100, buy 10 on bar 2, sell -100 (oversell) on bar 5, capital 100000 | final equity 99998.00 (fees-only, matches expected); one trade `('buy', 10.0, pnl≈-2.0)`; phantom cash from the 90 oversold shares = 0.00 | holds |
| R15-DATA-078 | `grep -rn 'alpha_vantage\|AlphaVantage\|alphavantage' sidecar/ --include='*.py'`; BLUEPRINT.md line 266 | 0 hits anywhere in sidecar source; BLUEPRINT.md:266 now reads "yfinance fallback (no API key needed for basic use; R15-DATA-078 — alpha_vantage was [never built])" | holds |
| R15-DOCS-005 | `cat src/modules/index.ts` (count `vystedModules[]`); grep BLUEPRINT.md module-count lines | `vystedModules[]` has exactly 20 entries; BLUEPRINT.md:20 "20 modules shipped in 0.9 (see §4 for the full ~37-module v1.0 roadmap)"; BLUEPRINT.md:238 "Module Catalog (20 shipped in 0.9.0 ...)" — count matches, scope-drift note recorded | holds |

COVERAGE: 5/5 ids raw; no raw: none.
