# P3 lows pre-integration candidate: fresh diff review (extras pass)

Reviewed 07:33-07:40 IST by a fresh read-only Opus reviewer. Status: **untested pending integration**. No pytest, vitest, tsc, eslint, cargo or build was run. This supersedes the 07:00 review at `266ed2ef` (its one blocker, R15-DOCS-010, is fixed at `8295dab8`).

- Branch: `origin/worktree-agent-lows-P3-int-4c6dfe8` @ `6e41bfc1bdd4255b427da84bb999641f7df78998` (fetched 07:33 IST, matches the assembler's return)
- Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Diff: 179 files, +4646/-2001. Delta since the last review (`266ed2ef..6e41bfc1`): 23 files, +583/-59.

## Verdict: needs_fix

One blocking item: an unowned existing test in `sidecar/tests/test_growth_check.py` goes deterministically red under R15-DATA-102 (CN), which the writer did not update and could not run.

## Blocking

| File | Issue | Fix |
|---|---|---|
| `sidecar/tests/test_growth_check.py:252` `test_snapshot_attaches_computed_growth_next_to_provider_values` | R15-DATA-102 makes `growth_check.should_cross_check` return False unless `growth_basis == "mrq_yoy"` is stated (`services/growth_check.py:85`). This test's fixture (`_fund_tool({...})`, lines 266-273) passes `{"symbol": "ICICIBANK.NS", "provider": "yfinance", "revenue_growth": 0.669, "earnings_growth": 0.03}` with no `growth_basis`, and `snapshot_structured` (`services/research/fast.py:369`) passes that dict straight to `should_cross_check`. So `_yoy()` returns None, `fake_yoy` is never called, and `fund["revenue_growth_computed"]` at line 281 raises KeyError. The writer fixed the two gate tests in the same file but not this one. `conftest._no_network_growth_check` skips this module, so no stub masks it. | Add `"growth_basis": "mrq_yoy"` to that fixture dict. This matches production, where `yfinance_provider.get_fundamentals` (`:901-902`) now states `mrq_yoy` whenever Yahoo serves a growth scalar. It is a fixture update that follows the entry's contract ("the producer states the basis") and weakens no assertion. Record it as an R15-DATA-102 fixup on the candidate. Advisory, same file: add the same key to the `test_snapshot_attaches_nothing_when_statements_unavailable` fixture (line 314) too. It still passes, but only vacuously now, because the gate short-circuits before the `none_yoy` path it means to exercise. |

## Checks

(a) **Safety surface.** `git diff --stat base...branch` is empty for `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs` and `types/proposed-change.ts`. It is not empty for `sidecar/services/agent_runtime.py` (+45/-2, R15-LEAD-036 merge `e377d55a`). I read every hunk:
- a new `_carry_fence` after `_units`;
- `_TurnState.fence`;
- the prefix and carry lines in `_consume_round._release`;
- the `_release_point(prefix + text)` hold.

All of these belong to the prose-release streaming guard. None of them touches `_auto_publish_event`, ack/staged narration, the host-action/`INVALID_ARGS_SENTINEL` path, auto_brief dispatch or ProposedChange. The proposed-changes gate itself is untouched, so the merge stands under the P1 precedent. If the lead reads the surface as the whole file, drop merge `e377d55a`; nothing else depends on it.

Also clean: `.github/`, `tauri.conf.json`, `package.json`, `pnpm-lock.yaml`, `Cargo.toml`, `types/plugin.ts`, `CLAUDE.md`, `LICENSE`, `sidecar/agents/`, `services/agent_tools/`.

The R15-DOCS-025 edit to `docs/SAFETY_ARCHITECTURE.md` §2 matches the code. `types/proposed-change.ts:38` declares `AUTO_APPLIED_KINDS = ["panel", "chart", "watchlist"]`, and `data-write` and `settings` are not in it. The doc now describes that correctly (the old text wrongly said every kind auto-applies). No test source-scans SAFETY_ARCHITECTURE.md.

(b) **Claimed tests exist and assert the entry.**
- Every one of the 42 Python `file::test` ids in PREINT.md has exactly one `def` on the branch, and every named whole file exists.
- 29 vitest files are present. The one path that is absent, `src/lib/fuzzy.test.ts`, is the sanctioned deletion (R15-CODE-FRONTEND-024).
- The cargo test `data_dir_override_wins_when_set_to_a_non_blank_value` is at `src-tauri/src/lib.rs:820`.

Extras, read in full:
- **LEAD-036:** three fence tests plus the `_cross_round` and `_fenced_lines` helpers. Every fixture they use (`_RecordingRoundsProvider`, `_ERR`, `_NO_DATA`, `_TCS_PX`) exists at base. The tests assert no fence marker, even fence parity with the note outside the block, and an exact passthrough on an ok result.
- **CN-077:** `test_native_search_oneshot_keeps_the_callers_base_url` asserts `built == [("openai", proxy)]`.
- **CN-102:** the store test (basis None, field_meta provider and as_of), the served-growth test (states `mrq_yoy`) and the b7 overlay test. The flipped gate assertions in `test_growth_check.py` (absent basis True -> False) and the `test_fundamentals.py::test_get_fundamentals` change (`"mrq_yoy"` -> None when no growth is served) reverse a pinned behaviour on purpose, per the entry, and each is paired with a new positive test. I record them as changed, not weakened.
- **NEW-drafted:** the `sidecar-specs.test.mjs` `it.each` holds for all three specs (each is `requirements.txt` plus `pyinstaller==6.20.0`). `export-artifact.test.ts` is a source scan for the static import. The DOCS-010 fixup (`8295dab8`) now uses classList tokens plus `aria-pressed`, and the component sets `aria-pressed` at `NotesToolbar.tsx:100`.

(c) **Conflict resolutions.**
- All four extra tips (`80f8d7a2`, `09d8da83`, `abcee383`, `8315c857`) match origin and are ancestors of the head.
- Every file an extra touches is blob-identical to that extra's tip, except these:
  - `openai.py` (CN-077): its base-to-tip patch reverse-applies cleanly on the head.
  - `models/fundamentals.py`, `growth_check.py`, `yfinance_provider.py`, `test_fundamentals_store.py` and `types/data.ts` (CN-102): the same reverse-apply check is clean.
  - `fundamentals_store.py` (CN-102): the patch fails only because the only difference between tip and head is W3's R15-DATA-103 Quote hunk (`change`/`change_percent` no longer coerced to 0.0; currency falls back to the row currency). Both sides are present.
  - `RESULT.md`: the add/add concatenation. Its content is four writer reports and none of it is product.
- No writer hunk or test was dropped. The nine set merges were verified blob-identical in the 07:00 review.

(d) **Defects, imports, contracts.**
- I found no defect in the delta apart from the blocker.
- An AST scan of all 95 changed .py files finds no duplicated top-level def or class.
- Every `from <sidecar module> import name` in the whole sidecar tree resolves (0 missing).
- The removed symbols have no live referrer left: `_is_rate_limited` in growth_check and yfinance (now `provider_health.is_rate_limit`, which keeps the "Too Many Requests" match), ddg `_TokenBucket`/`_get_bucket`, fuzzy*, `exportNoteMd`, `openCryptoStream`, `register_v0_6_0_nodes`, `price_asian_mc`/`price_barrier_mc` and `StreamErrorFrame`.
- `ruff format --check` on the 95 files and `ruff check` over sidecar/ are clean. `prettier --check` on the 77 changed ts/tsx/mjs/json/md/css files is clean.
- Wire mirrors: the `growth_basis` default change is mirrored by a doc-only change in `types/data.ts` (the type stays `string | null`), and no frontend code reads `growth_basis`.
- Unchanged: the MCP catalog, the agent roster and the register-counted tests.
- Rust (`lib.rs`, PLATFORM-080): `PathBuf` is already imported. `parse_data_dir_override` is pure. Every new line is 100 characters or fewer, and by hand the `use super::{...}` rewrap and the vertical `assert_eq!` layouts agree with rustfmt defaults (fn_call_width 60). I found nothing clippy would obviously flag, but none of this has been run.

## Advisories (integrator: look here first if the chain goes red)

1. **pytest, R15-DATA-102 blast radius.** Beyond the blocker, an unstated basis now turns off the quarterly growth cross-check for any producer that serves growth without stating it: legacy `fundamentals_store` rows written before the `growth_basis` column, and any non-yfinance provider. `research/semantics.py` still labels growth `mrq_yoy (provider-claimed)` without reading the basis (the writer noted this and did not file it). Run the whole `test_growth_check.py`, `test_research_semantics.py`, `test_b7_exchange_financials.py`, `test_fundamentals*.py` and `test_yfinance_provider.py`.
2. **pytest, R15-LEAD-036.** The streaming guard's behaviour changes: an empty fence opener is held across a tool call, and `guarded != text` in that case collapses the provider's chunking into one delta. Run all of `test_agent_runtime.py`, and again after P1 lands. P1 also edits agent_runtime.py (import block, `_resolve_provider_id`, `_research_guard_seconds`, `plan_delegate_run`, `_prepare_run`), which is disjoint, and `git merge-tree` auto-merges it.
3. **cargo fmt, clippy and test, R15-CODE-PLATFORM-080 (`lib.rs`).** None of these was run. `lib.rs` is also the P1 conflict: `git merge-tree` against P1 `dbe5fe4f` reports a CONFLICT in `src-tauri/src/lib.rs`, confirmed at 07:36 IST. The other four P2 conflicts in PREINT.md (`sidecar/main.py`, `fundamentals_store.py`, `StatusChrome.tsx`, `sidecar-client.ts`) stand as recorded.
4. **Venv for the build and tests, R15-CODE-PLATFORM-078.** The CI workflows are unaffected: `lint.yml` pip-installs ruff and `test.yml` installs `requirements-dev.txt` into its own python. A freshly created local `sidecar/.venv` will no longer have pytest or ruff, so run `sidecar/.venv/bin/python -m pip install -r sidecar/requirements-dev.txt` first, as PREINT's recipe says. On an existing venv the dev tools stay installed and PyInstaller bundles by import anyway, so the binary does not change. The copy-metadata targets (fastmcp, mcp, anyio, httpx, starlette, uvicorn) are all runtime or transitive pins, so `ensure` does not die on missing metadata. The recipe edit forces a main sidecar rebuild through the staleness check.
5. **Boot path, R15-CODE-PLATFORM-068** (carried): run the full pytest suite, for order effects such as `test_screener_nodes`, plus `node scripts/smoke-test-sidecars.mjs`.
6. **Vitest, R15-CODE-FRONTEND-038.** `export-artifact.ts` now imports `getSidecarBaseUrl` statically. The two tests that mock `@/lib/sidecar-client` and reach export-artifact (`ScreenerResultsTable.test.tsx`, `csv.test.ts`) also mock `@/lib/export-artifact`, so a factory missing `getSidecarBaseUrl` is not hit. `sidecar-client.ts` does not import export-artifact, so there is no cycle. Verifying the claimed "zero [INEFFECTIVE_DYNAMIC_IMPORT]" still needs a real build.
7. **Repo-root `RESULT.md`** (160 lines, four writer reports). It is prettier-clean, so format:check passes, but it is not product. Move it under `docs/redesign/verification/r15/stage-c/lows/P3/` or drop it before the merge into 004, and record the choice. P1 and P2 carry no root `RESULT.md`, so it will not conflict.
8. Carried from the 07:00 review, still open: the `sidecarRequest` 30 s default timeout and the `AbortSignal.any` WebKit floor (LIFECYCLE-027); the five `test_ddg_backend.py` tests deleted with `_TokenBucket` (RESEARCH-009, sanctioned); the `**_k` fakes (`266ed2ef`) are unrun; the QuantLib wording in the R15-UI-077 "pillar" assertion; `@tiptap/extension-list` missing from local node_modules.
