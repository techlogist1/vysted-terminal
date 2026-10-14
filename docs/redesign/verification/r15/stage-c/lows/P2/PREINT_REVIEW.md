# P2 lows candidate: fresh diff review

- Reviewer: Opus (claude-opus-5-5[1m]). Read-only, so no worktree, no edits and no push. Written 07:41 IST.
- Candidate: `origin/worktree-agent-lows-P2-int-4c6dfe8` @ `7db0b2954bab647e646b324df1c875c9c34f1675`. Base `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` is an ancestor.
- Diff: `4c6dfe8c...7db0b295`, 156 files, +5517/-2441.
- Nothing was executed except git and static reads. Everything stays untested pending integration.

## Verdict: needs_fix

There are five blocking items. Two were already known: the lockfile, and the Windows backup root the assembler flagged for a decision. Three are new: a vitest break in ScreenerResultsTable, a tsc error in the axe matcher, and a data-access regression in `workspace_store`. All of them are small, local fixes. The merge itself is sound: the safety surface is untouched, every claimed test exists, and no writer hunk was lost.

## (a) Safety surface

`git diff --stat 4c6dfe8c...7db0b295 -- <path>` is empty for each of these:

- `sidecar/models/audit_log.py`
- `sidecar/services/kill_switch.py`
- `src-tauri/src/kill_switch.rs`
- `types/proposed-change.ts`
- `sidecar/services/agent_runtime.py`

There are no blocked hunks.

`src/modules/chat/ProposedChangesReview.tsx` (W8) is safety-adjacent. It only changes tooltip text, which is correct.

## (b) Claimed tests

**pytest:** all 52 claimed nodes exist on the branch as `def test_...`. This includes `test_screener.py::test_result_row_has_no_matched_criteria`, which W4 said was missing and CN-019 later added. It also includes `test_provider_health.py::test_system_provider_health_routes`, which now takes `monkeypatch`. `test_cache_dir.py` has 3 tests.

**vitest:** every named case or describe exists in its claimed file. The spot-read tests assert their entry's behaviour, for example:

- The rig-hooks 404 and 200 pair uses `delenv`/`setenv`.
- The `invoke_tool` envelope tests check the exact strings `provider error: ...` and `unexpected error: ...`.
- The Devanagari workspace tests save the name and then check the byte cap.

## (c) Conflict resolutions and writer hunks

All 13 origin heads match the PREINT table. The per-writer check took every line each writer added (writer base to writer head) and looked for it on the candidate.

**W1, W4, W5, W6, W7, W9:** 0 lines lost.

**Other writers:** every missing line is a documented assembler replacement:

- **W2:** 1 line in `smoke-test-sidecars.mjs`, replaced by the `pathToFileURL` guard (09821a53). 2 lines in `smoke-test-sidecars.test.mjs`, replaced by the `process.execPath` entry (42b3c679).
- **W3:** the `_schema.json` `declaredTools` wording, replaced in d7d0d325.
- **W8 and CN-027:** the separate `sidecar-client` imports in `agents.ts`, folded into one import (e9da8e93). The folded import holds the union of both.
- **CN-019, CN-035, CN-027, DEF-B:** the root `RESULT.md` files, moved to `P2/results/` (4c7b6dde, ed0837b3).

No deleted file came back. The `invoke_tool(wrap_errors=)` resolution (18e5bcb0) reads correctly:

- The agent loop keeps the one-spelling envelope.
- `mcp_server._make_catalog_tool` passes `False` and re-raises as `ToolError`.
- No existing test asserts the old `{"ok": false}` MCP body. I grepped for "not available in this build" and "raised:".

## Blocking

1. **`pnpm-lock.yaml` (DEF-B, R15-UI-071): the lockfile was not updated.** `package.json` adds `eslint-plugin-jsx-a11y ^6.10.2` and `vitest-axe ^0.1.0`, but the lockfile has no entry for either. `pnpm install --frozen-lockfile` fails, and it is step 1 of ci-local and of CI.
   **Fix:** run `pnpm install --lockfile-only` on the rebased branch and commit `pnpm-lock.yaml` before the chain.

2. **`src/components/SettingsPanel.test.tsx:919` (DEF-B, R15-UI-071): `pnpm typecheck` fails with TS2339.** `expect(results).toHaveNoViolations()` has no type. The test only calls `expect.extend(axeMatchers)` at runtime.
   - `vitest-axe@0.1.0`'s `extend-expect.d.ts` augments the legacy global `namespace Vi { interface Assertion }`, which Vitest 4 no longer reads. The test does not import it anyway.
   - `tsconfig.json` includes `**/*.tsx`, so test files are typechecked.

   **Fix:** add a declaration file, for example `src/types/vitest-axe.d.ts` or `vitest-axe.d.ts` at the root, containing:
   ```ts
   import "vitest";
   import type { AxeMatchers } from "vitest-axe/matchers";
   declare module "vitest" { interface Assertion<T = any> extends AxeMatchers {} interface AsymmetricMatchersContaining extends AxeMatchers {} }
   ```
   Check that it passes `@typescript-eslint/no-empty-object-type` and `no-explicit-any` in `pnpm lint`. If it does not, use an explicit `toHaveNoViolations(): void` member. The assertion stays unchanged.

3. **`src/modules/screener/ScreenerResultsTable.test.tsx:191,198,308` (DEF-B, R15-UI-068 x the existing R15-UI-006 tests): the vitest cases break.**
   - DEF-B moved the sort `onClick` from the `<th data-testid="column-...">` to a child `<button>`.
   - These tests still call `fireEvent.click(screen.getByTestId("column-pe_ratio"))` and `column-price`.
   - A click dispatched on the `<th>` never reaches the button inside it, so the sort handler does not run: `sortBy` stays `market_cap` and the row-order assertions fail.
   - DEF-B retargeted only `DataTable.test.tsx`. Its RESULT.md says the screener files were left alone.
   - No other test clicks a `column-*` header by test id. I grepped all `*.test.tsx`.

   **Fix:** retarget the three clicks to `within(screen.getByTestId("column-pe_ratio")).getByRole("button")` (and the same for `column-price`). All assertions stay unchanged.

4. **`sidecar/services/data_cache.py` `_backup_data_dir` (DEF-B R15-CROSS-PLATFORM-012 x R15-LIFECYCLE-024 / W5 R15-CODE-PLATFORM-077): the pre-upgrade backup copies the wrong directory on Windows.**
   - `data_dir = _db_path.parent` is now `get_cache_dir()`. On Windows that is LocalAppData, while the user data is in Roaming.
   - So the pre-upgrade undo copy, and W5's pruning, cover the regenerable cache dir. They no longer cover `portfolio.db`, `workspaces/`, `runs.db` or the audit DB.
   - On the first upgrade onto this build, `data_cache.db` is new in the cache dir and has no `build` row. So `ensure_build` skips the backup entirely for that upgrade.
   - macOS and Linux are unaffected, because `app_local_data_dir == app_data_dir` there.

   **Fix:** make `_backup_data_dir` copy `config.get_data_dir()` into `get_data_dir()/backups/<old_build>`, and keep the `_BACKUP_EXCLUDES` comparison against that dir. Optionally make it also run when the cache DB is freshly created but `get_data_dir()/data_cache.db` exists, meaning a legacy build. Check that `test_data_cache.py` backup tests still point both dirs at the same `tmp_path`.

5. **`sidecar/services/workspace_store.py` `_filename_stem` (DEF-B, R15-UI-082): existing workspaces become unreachable, and names containing `%XX` no longer round-trip.**
   - The old stem was `quote(name, safe=" ")`, which percent-encoded everything except letters, digits, space and `_.-~`. The new stem keeps every character raw except `/\:*?"<>|`, control characters and `.`.
   - A workspace saved before the upgrade with a name like `Q1 (draft)`, `R&D`, `P/E, 5y` or any non-ASCII name is stored as `Q1 %28draft%29.vysted-workspace`. `list_workspaces` still shows it, because it unquotes the name, but `load_workspace` and `delete_workspace` now look for `Q1 (draft).vysted-workspace` and return a 404. The user's saved layout disappears.
   - `%` is no longer escaped, so a new save named `a%41` is listed back as `aA`, and loading `aA` misses.

   **Fix:**
   - Add `%` to `_UNSAFE_CHARS`.
   - In `_path_for`, fall back to the legacy stem `quote(cleaned, safe=" ").replace(".", "%2E")` when the new path does not exist. Or rename the legacy file on first access.
   - Add one pin test: a file written under the legacy stem loads and deletes by its plain name, and `a%41` round-trips.

## Advisories

- **Cross-partition conflicts (re-verified with `git merge-tree`):**
  - vs P1 `dbe5fe4f`: `sidecar/services/workspace_store.py` (P1 adds a `_replace` retry next to DEF-B's constants; adjacent hunks, easy to resolve) and `src-tauri/src/lib.rs`.
  - vs P3 `6e41bfc1`: `sidecar/main.py`, `fundamentals_store.py`, `StatusChrome.tsx` and `sidecar-client.ts`. In `sidecar-client.ts`, P3's R15-LIFECYCLE-027 timeout and CN-027's `timeoutMs` are two deadline mechanisms for one intent: collapse them into one.
- **`src-tauri/src/lib.rs` `resolve_cache_dir`:** it mirrors `resolve_data_dir` line for line (the same `diag_eprintln!` shape, `app.path().app_local_data_dir()`). It looks like it compiles, but it has never been through `cargo fmt`, clippy or `cargo test`.
- **`sidecar/config.py` `get_cache_dir` docstring:** it says "XDG cache on Linux". In Tauri 2, `app_local_data_dir` on Linux is the XDG *data* dir, and `lib.rs`'s own comment says it is a no-op there. The docstring is wrong; the code is fine.
- **Windows upgrade orphans:** the old `data_cache.db`, `fundamentals_cache.db` and `searxng/` in Roaming are left behind (wasted disk, no migration). An existing SearXNG container keeps its old mount.
- **`jsx-a11y/label-has-associated-control` (error, all .ts/.tsx):**
  - 49 `<label>` elements under `src/` have no `htmlFor`.
  - The ones I sampled pass the rule's heuristics: a nested native `<input>`, or `{expr}` children, which the rule treats as a possible control.
  - I could not lint project-wide, because that is off-lane and the plugin is not installed. Run `pnpm lint` early in the chain.
- **`vitest.config.ts` `thresholds.autoUpdate: true`:** it rewrites the file on every passing `vitest run --coverage` in ci-local, after `format:check` has run, which leaves the tree dirty. Committing the ratchet or passing `autoUpdate=false` is the operator's call.
- **ci-local drift from CI:** ci-local now runs `vitest run --coverage` and `python3`, but `.github/workflows` is unchanged (Tier-1). The CLAUDE.md claim that ci-local mirrors CI byte-for-byte no longer holds.
- **W3 x W6 behaviour change:** an MCP client now gets `isError` with "tool X raised: ..." where it used to get an `ok:false` body. `wrap_errors=False` also lets a `KeyError` raised *inside* a handler be reported as "not available in this build". Record this in CHANGELOG at integration.
- **GET /agents (W3, R15-AGENT-072):**
  - `tools` now means the declared list (re-read from `agents/<id>.json`), and there is a new `effective_tools` field.
  - Neither `types/` nor `src/store/agents.ts` mirrors `effective_tools`.
  - `status: Literal[*action_ledger.KNOWN_STATUSES]` is valid in 3.13 (with `from __future__ import annotations`, pydantic evaluates the string), and `KNOWN_STATUSES` is a tuple.
- **Other contracts (clean):**
  - `types/screener.ts` and `sidecar/models/screener.py` both drop `matched_criteria`. No reader of it remains in `src/`, `plugins/` or `sidecar/`.
  - The removed route `GET /sec/filings/{accession}/sections` has no caller left in `src/` and no entry in `docs/SIDECAR_API.md`.
  - No `refreshAll`, `drainNotifications`, `_safeText` or `agent_tools.registry_v0_6_0` reference remains, except prose in `workflow_nodes/registry_v0_6_0.py:3` and `docs/archive`.
  - No catalog, MCP-surface or agent-roster count change.
- **Repo-wide source-scan tests, simulated statically on the candidate:**
  - `warning-token-scope`: 0 offenders, and all 10 allowlist files still use the token.
  - `source-guards` SSR ratchet: the matching set equals the allowlist exactly.
  - The `⌘` guard: every hit outside `keybindings.ts` is in a comment, which the AST walk skips.
  - These scans are fragile against whatever lands after P2, so re-run them on the combined tree.
- **Runtime dependencies to watch:**
  - CN-027 uses `AbortSignal.any`/`AbortSignal.timeout`, which needs Safari 17.4+ in WKWebView. jsdom 29 has both.
  - `quant.ts` errors now carry the server `detail` sentence without the old `POST ... failed (N):` prefix. `quant.test` was updated.
- **Where to look first in the chain:**
  1. The install (blocking item 1).
  2. `pnpm lint`: the jsx-a11y rule and the new `.d.ts`.
  3. `pnpm typecheck` (blocking item 2).
  4. `vitest`: ScreenerResultsTable (blocking item 3), SettingsPanel axe, then the source-scan tests.
  5. `cargo fmt/clippy/test` on `lib.rs`.
  6. pytest: `test_mcp_server`, `test_mcp_catalog_parity`, `test_agent_tools_lows`, the handler files W3 stripped of try/except, `test_data_cache`, `test_workspace`, `test_searxng_manager` + `test_search_tiers_router`.
