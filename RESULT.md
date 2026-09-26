# RESULT — writer lows-new-lows

Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
Branch: worktree-agent-lows-NEW-drafted-4c6dfe8
Source: docs/redesign/verification/r15/stage-c/lows/NEW_LOWS_DRAFT.json (drafted; register does not carry these ids yet)

## R15-DOCS-025
- outcome: fixed_untested
- commit: 48314633
- test: doc-only, no test (fix_shape names none)
- files: docs/SAFETY_ARCHITECTURE.md
- note: §2's "no exempt kind" sentence predated R15-AGENT-080/R15-CODE-FRONTEND-008's AUTO_APPLIED_KINDS (panel/chart/watchlist); rewrote to name the actual set and state data-write/settings always wait for review, matching FACTS.md:179.

## R15-CODE-PLATFORM-078
- outcome: fixed_untested
- commit: 79682cda
- test: scripts/sidecar-specs.test.mjs (new it.each asserting every spec builds from requirements.txt with pyinstaller as a pipExtra) — written as source, vitest not run (off-lane).
- files: scripts/sidecar-specs.mjs, scripts/sidecar-specs.test.mjs
- note: 'main' spec pointed at requirements-dev.txt (pulls ruff/pytest/pytest-asyncio into the frozen build venv); repointed to requirements.txt with pyinstaller as a pipExtra, matching the two MCP specs' existing pattern exactly. node --check passed on both files; prettier --write ran clean (no changes).

## R15-CODE-PLATFORM-079
- outcome: fixed_untested
- commit: 31ece664
- test: config-only, no test (fix_shape names none)
- files: .gitignore
- note: added `coverage/` under the existing Build output block. Verified @vitest/coverage-v8 devDependency at package.json:70 and zero `coverage` hits in .gitignore at BASE.

## R15-CODE-FRONTEND-038
- outcome: fixed_untested
- commit: d4bd1c5f
- test: src/lib/export-artifact.test.ts (new; source-scan asserting a static import of sidecar-client is present and no dynamic import of it remains) — written as source, vitest not run (off-lane). The fix_shape's own named check ("pnpm tauri build log has zero [INEFFECTIVE_DYNAMIC_IMPORT] lines") is a build-log assertion that needs an actual build, which the off-lane rule forbids running here; the source-scan test is the closest static regression guard.
- files: src/lib/export-artifact.ts, src/lib/export-artifact.test.ts (new)
- note: confirmed the single dynamic import site (line 51 at BASE) was the only one of 40+ import sites for sidecar-client; made it static. prettier --write ran clean.

## R15-CODE-PLATFORM-080
- outcome: fixed_untested
- commit: 4a0141c8
- test: src-tauri/src/lib.rs `data_dir_override_wins_when_set_to_a_non_blank_value` unit test on the new pure `parse_data_dir_override` helper (env lookup injected as a Result so no real env var is touched) — written as source, cargo never run (off-lane, and Rust changes are untested-by-rule regardless).
- files: src-tauri/src/lib.rs
- note: added `VYSTED_DATA_DIR` env-var override, read before the platform default in BOTH `resolve_data_dir` (sidecar `--data-dir`) and `get_app_data_dir` (the tauri command the frontend export helpers call) — the latter's own doc comment says it must mirror the former, so fixing only one would have made frontend exports land in a different directory than the sidecar's stores under an active override. Rust change, written with care; not cargo-fmt'd (cargo is off-lane).

## R15-DOCS-026 (Tier-4, not touched)
- outcome: tier4
- commit: (none — no work done)
- test: n/a
- files: CLAUDE.md (not touched)
- note: fix needs editing CLAUDE.md, a Tier-1 locked file per the repo's decision-authority tiers; the draft entry itself says this must ride the operator's single pre-authorised CLAUDE.md commit. Recommendation: update CLAUDE.md:325's Quartz match string from `kCGWindowOwnerName == "vysted-terminal"` to `kCGWindowOwnerName == "Vysted Terminal"` (the release bundle's real CGWindow owner name per REHEARSAL.md:70-71), or match by owner PID via the System Events process name instead, and either commit `/tmp/rigcap.py`'s real source under `scripts/rig/` or drop the dead pointer.

## Rules note
Never touched CLAUDE.md, the register, DECISIONS_FOR_OPERATOR.md, or run-state.
Never ran pytest/vitest/cargo/pnpm ci-local/typecheck/tsc/project-wide eslint/rig/app/ollama.
Checks run: `node --check` on touched .mjs files, `prettier --write` on touched .ts/.md files (via the main worktree's node_modules binary — this worktree has none installed), read-only inspection otherwise.
