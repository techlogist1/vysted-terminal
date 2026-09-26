# P1 lows pre-integration candidate

Assembled 06:50-06:54 IST. Untested pending integration: no pytest, vitest, cargo, tsc or eslint was run on the candidate. Only py_compile, ruff and prettier ran.

- Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (writer branches were cut from `ebc5ed41`, which is an ancestor of the base)
- Branch: `worktree-agent-lows-P1-int-4c6dfe8`, pushed; `git ls-remote` shows `70fe85c9af801387dc503e4a4bc97552f7a532d8`
- Head: `70fe85c9af801387dc503e4a4bc97552f7a532d8`. The candidate differs from the base in 91 files (+3156/-764).
- Worktree: `scratchpad/lows-preint/P1`. It is kept, not removed.

## Merge order

Each branch was merged with `git merge --no-ff --no-edit origin/<branch>`.

| # | Set | Branch | origin head | WRITERS.json head | Merge sha | Result |
|---|---|---|---|---|---|---|
| 1 | W1 backtest | worktree-agent-lows-P1-W1-backtest | 6cb980bf | match | fec16399 | clean |
| 2 | W2 runtime-catalog | worktree-agent-lows-P1-W2-runtime-catalog | 31e61ce5 | match | 1aacf748 | clean |
| 3 | W3 actions-research | worktree-agent-lows-P1-W3-actions-research | dd1ceed2 | match | 886acf46 | clean |
| 4 | W4 chat-composer | worktree-agent-lows-P1-W4-chat-composer | 57d0e546 | match | 5b41e737 | clean |
| 5 | W5 portfolio | worktree-agent-lows-P1-W5-portfolio | 95a94e16 | match | 2ab2b0f1 | clean |
| 6 | W6 runs-stores | worktree-agent-lows-P1-W6-runs-stores | 104d96a5 | match | f24f73be | clean |
| 7 | W7 rust-core | worktree-agent-lows-P1-W7-rust-core | 8d07e2f6 | match | f592a3d3 | clean |
| 8 | W8 tokens-market | worktree-agent-lows-P1-W8-tokens-market | 2a2f0564 | match | bae0c204 | clean |
| 9 | W9 docs-truth | worktree-agent-lows-P1-W9-docs-truth | dd10d2e0 | match | 21175c2e | clean |
| - | style | (assembler) | - | - | 70fe85c9 | ruff I001 on 3 W1 files, prettier on 2 W9 docs |

- Head mismatches: none. Extra branches: none.

## Conflict map

There were no textual conflicts, and no writer hunk was dropped. No file is touched by more than one P1 writer.

The base moved `ebc5ed41..4c6dfe8c` on three W2 files: `sidecar/services/agent_runtime.py`, `sidecar/services/planner.py` and `sidecar/tests/test_agent_runtime.py`. The base-side commits are R15-LEAD-030/035/036: the figure/citation guard rewrite and the "no-tool" intent signal in `_resolve_tool_surface`. Git auto-merged these files. I checked the result by reading it:
- Both `_resolve_model` call sites use the new 3-arg form (`agent_runtime.py:1852`, `:2623`).
- `PLAN_ACTIONS` is exported and imported.
- The base's `classify_intent(prompt).signals` "no-tool" branch sits beside W2's hunks and does not overlap them.

## Style commit (70fe85c9)

- **W1 ruff I001:** `ruff check sidecar` (the CI form) failed with I001 on `sidecar/routers/backtest.py`, `sidecar/tests/test_backtest_engine.py` and `sidecar/tests/test_backtest_lows.py`. W1 had put `from models...` in the third-party group. The fix is `ruff check --fix --select I`, which only reorders imports. W1 reported ruff clean, most likely because it ran ruff without `sidecar/ruff.toml` as the project root.
- **W9 prettier:** `prettier --check` failed on `docs/CURRENT_STATE.md` (W9 R15-DOCS-014/019 tables) and `docs/redesign/R4_STALE_CODE_REGISTER.md` (W9 R15-AGENT-087). The fix is `prettier --write`, which only aligns tables. At base both files passed prettier. `docs/BLUEPRINT.md` is prettier-ignored.
- **After the fixes:** `ruff format --check sidecar` reports 445 formatted. `ruff check sidecar` passes. prettier is clean on all 52 changed ts/tsx/js/mjs/json/md/css files. py_compile passes on all 35 changed .py files.

## Risk map

**Safety surface.** No blocked hunks. No hunk touches `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs` or `types/proposed-change.ts`.

W2 edits `sidecar/services/agent_runtime.py`. I reviewed every hunk against SAFETY_ARCHITECTURE §2-4 (`_build_local_tools` narration, `_auto_publish_event`, the read-intent strip) and none of them edits the proposed-changes gate:
- `_STAGEABLE_PLAN_ACTIONS` is now derived as `PLAN_ACTIONS ∩ HOST_ACTION_TOOLS`, so the set gains close_panel and focus_panel. This set is only the advisory `staged` flag on plan-pre-pass steps (`:1731`). `_READ_SAFE_PANEL_ACTIONS` is unchanged.
- The preamble tool list is generated.
- `_resolve_model`
- `_tool_timeout_seconds`

The integrator's verifier should confirm this reading (entries R15-AGENT-089 and R15-CODE-AGENT-018).

**Frontend gate plumbing.** Not on the read-only list, but next to the gate:
- W3 R15-CODE-FRONTEND-034 changes `src/store/proposed-changes.ts` `accept()` to ack with `ApplyResult.status` instead of `publishAckStatus(label)`. `ok` is now `status !== "failed"`.
- `src/lib/host-actions.ts`: write_note is re-routed through the notes store (R15-CODE-FRONTEND-035).

**Rust.** W7 changes `src-tauri/src/lib.rs` (+380/-83), `keychain.rs`, `openbb_mcp.rs` and `sec_edgar_mcp.rs`:
- write_atomic with fsync and a PermissionDenied retry.
- A single app_data_dir.
- MCP ports go through `Command::envs`, and `set_var` is removed.
- The main-sidecar wait now requires `/health` 200 with `service=vysted-sidecar`. `sidecar/routers/health.py:29` does emit this.
- The discovery file is cleared at boot, at sidecar termination and on exit.
- The dev-keystore migration emits a `waiting` event.

None of this is cargo-verified on the candidate: cargo fmt, clippy and test were not run.

**Config and keychain.** Tauri config, CI workflows, Cargo.toml, package.json, `types/plugin.ts`, licensing and CLAUDE.md are all untouched. W7 R15-CROSS-PLATFORM-011 moves the onboarding flags from the keychain to a data-dir `app-meta.json` through new commands `app_meta_get` / `app_meta_set`. Both commands are registered in the invoke handler (`lib.rs:627-628`). Like `keychain_*`, they need no entry in `capabilities/default.json`.

**W8 R15-UI-076 ripple (high).** `DEFAULT_SYMBOLS` and `DEFAULT_CHART_SYMBOL` now derive from `DEFAULT_REGION = "IN"` (`^NSEI` / RELIANCE.NS / TCS.NS / HDFCBANK.NS, chart `^NSEI`). W8 reports that four test files outside P1 assert US symbols. Each of them imports DEFAULT_SYMBOLS:
- `src/modules/watchlist/WatchlistPanel.test.tsx`
- `src/modules/news/NewsFeedPanel.test.tsx`
- `src/modules/panel-context-publishers.test.tsx`
- `src/modules/notes/NotesPanel.test.tsx`

`src/lib/workspace.ts:339` and `src/store/settings.ts:119` consume `DEFAULT_CHART_SYMBOL`. Their tests may assert "SPY". Expect fixture updates at integration. The fix is to update the fixtures; never weaken the tests.

**W6 R15-CODE-AGENT-032.**
- `list_runs` is newest-first with `LIMIT 100`, and terminal rows older than 30 days are pruned at first connect.
- A paused or planned run with more than 100 newer runs drops out of `GET /runs`.
- W6 restamped two migration fixtures in `test_runs_store` / `test_runs_router` from epoch-1 to now.

**W6 R15-CODE-AGENT-029.** Four `_ensure_schema` functions are deleted. The idempotency tests were converted to call `_connect()` twice, not deleted.

**W2 prompt budget.** The copilot prompt was cut from 8906 to 4382 bytes, and every agent prompt is capped at 4608 bytes by `test_agent_system_prompts_within_byte_budget`. Any agent JSON added after the rc1 tag must fit under that cap. The A/B check was a single sample on qwen2.5:7b.

**W2 R15-AGENT-066/067.** The MCP exposed set is pinned by name (31 ids), and run_custom_backtest is now internal-only. A capability added upstream after the tag will fail `test_mcp_projection_is_explicit_per_entry` until it is named there.

**W3 R15-RESEARCH-042.** Adds a `structured.source_floor` leg and a "N sources (below 3)" markdown marker. The frontend (`types/brief.ts` / `brief-blocks.tsx`) does not render the leg yet. The Sonar and Perplexity lanes are not floor-stamped.

**Cross-partition overlap.** None found: no P1 file appears in any P2 or P3 writer diff from `ebc5ed41`.

**Could-not entries (not fixed, no code).**
- R15-CODE-RESEARCH-005: needs `services/research/citecheck.py` plus five non-owned tests.
- R15-CODE-AGENT-031: needs `sidecar/tests/test_run_manager.py:758,760`, owned by P3 W2. The CLAUDE.md "GET /runs emits BOTH" gotcha stays as it is.

**Handed to the lead.**
- W9 R15-DOCS-009: the DECISIONS.md line recording the hand-rolled orchestration.
- W8 R15-CODE-PLATFORM-049: the exa orphan-secret one-shot migration was skipped because no source ever wrote that key.
- W9: spec.md has stale "four-mode" mentions outside FR-003, US3 and SC-029.

## Claimed tests

These are the writers' own claims, all untested on the candidate.

### pytest (sidecar)

| File | Entry | Test |
|---|---|---|
| test_backtest_lows.py | R15-AGENT-079 | test_uppercase_and_or_parse_like_lowercase |
| test_backtest_lows.py | R15-CODE-PLATFORM-036 | test_each_rule_compiled_once |
| test_backtest_lows.py | R15-CODE-PLATFORM-034 | test_each_bar_in_exactly_one_slice |
| test_backtest_lows.py | R15-CODE-PLATFORM-035 | test_no_dead_backtest_scaffolding |
| test_backtest_engine.py | R15-UI-060 | test_event_sequence_has_progress_between_start_and_complete |
| test_agent_runtime.py | R15-AGENT-070 | test_timeout_from_args_flag_not_name_selects_guard |
| test_agent_runtime.py | R15-AGENT-071 | test_every_tool_named_in_prompts_resolves_in_catalog |
| test_agent_runtime.py | R15-AGENT-073 | test_provider_override_without_model_uses_provider_default |
| test_agent_runtime.py | R15-CODE-PLATFORM-076 | test_agent_system_prompts_within_byte_budget |
| test_planner.py | R15-AGENT-089 | test_coerce_steps_keeps_close_and_focus_panel_and_plan_marks_staged |
| test_toolbelt_integrity.py | R15-CODE-AGENT-018 | test_stageable_and_read_safe_relation_is_pinned |
| test_mcp_catalog_parity.py | R15-AGENT-066 | test_run_custom_backtest_not_read_only_on_mcp |
| test_mcp_catalog_parity.py | R15-AGENT-067 | test_mcp_projection_is_explicit_per_entry |
| test_mcp_catalog_parity.py | R15-CODE-AGENT-026 | test_toolkind_has_no_unprojected_mcp_endpoint |
| test_research_iter.py | R15-RESEARCH-041 | test_structured_only_sources_are_not_web_available |
| test_research_iter.py | R15-RESEARCH-035 | test_over_cap_report_keeps_facts_established |
| test_research_depth.py | R15-CODE-RESEARCH-006 | test_panel_threshold_single_source |
| test_research_fast.py | R15-RESEARCH-042 | test_below_floor_marker |
| test_agents_store.py | R15-CODE-AGENT-017 | test_unparseable_row_is_skipped_and_logged |
| test_agents_store.py / test_plugins.py / test_portfolio.py / test_schema_version.py | R15-CODE-AGENT-029 | test_connect_is_idempotent (x3) + schema_version openers |
| test_runs_store.py | R15-CODE-AGENT-032 | test_list_runs_is_bounded_and_prunes_old_terminal_rows |
| test_workspace.py | R15-CROSS-PLATFORM-007 | test_replace_retries_permission_error_then_succeeds |

Every named def was grep-confirmed present on the candidate.

```
cd sidecar && .venv/bin/python -m pytest -q \
  "tests/test_backtest_lows.py::test_uppercase_and_or_parse_like_lowercase" \
  "tests/test_backtest_lows.py::test_each_rule_compiled_once" \
  "tests/test_backtest_lows.py::test_each_bar_in_exactly_one_slice" \
  "tests/test_backtest_lows.py::test_no_dead_backtest_scaffolding" \
  "tests/test_backtest_engine.py::test_event_sequence_has_progress_between_start_and_complete" \
  "tests/test_agent_runtime.py::test_timeout_from_args_flag_not_name_selects_guard" \
  "tests/test_agent_runtime.py::test_every_tool_named_in_prompts_resolves_in_catalog" \
  "tests/test_agent_runtime.py::test_provider_override_without_model_uses_provider_default" \
  "tests/test_agent_runtime.py::test_agent_system_prompts_within_byte_budget" \
  "tests/test_planner.py::test_coerce_steps_keeps_close_and_focus_panel_and_plan_marks_staged" \
  "tests/test_toolbelt_integrity.py::test_stageable_and_read_safe_relation_is_pinned" \
  "tests/test_mcp_catalog_parity.py::test_run_custom_backtest_not_read_only_on_mcp" \
  "tests/test_mcp_catalog_parity.py::test_mcp_projection_is_explicit_per_entry" \
  "tests/test_mcp_catalog_parity.py::test_toolkind_has_no_unprojected_mcp_endpoint" \
  "tests/test_research_iter.py::test_structured_only_sources_are_not_web_available" \
  "tests/test_research_iter.py::test_over_cap_report_keeps_facts_established" \
  "tests/test_research_depth.py::test_panel_threshold_single_source" \
  "tests/test_research_fast.py::test_below_floor_marker" \
  "tests/test_agents_store.py::test_unparseable_row_is_skipped_and_logged" \
  "tests/test_agents_store.py::test_connect_is_idempotent" \
  "tests/test_plugins.py::test_connect_is_idempotent" \
  "tests/test_portfolio.py::test_connect_is_idempotent" \
  "tests/test_runs_store.py::test_list_runs_is_bounded_and_prunes_old_terminal_rows" \
  "tests/test_workspace.py::test_replace_retries_permission_error_then_succeeds"
# then the whole touched-file set plus the neighbours the writers ran:
cd sidecar && .venv/bin/python -m pytest -q tests/test_backtest_lows.py tests/test_backtest_engine.py tests/test_backtest_custom.py tests/test_bar_loader.py tests/test_backtest_agent_parity.py tests/test_backtest_store.py tests/test_backtest_strategies.py tests/test_strategy_critic_e2e.py tests/test_agent_runtime.py tests/test_planner.py tests/test_toolbelt_integrity.py tests/test_mcp_catalog_parity.py tests/test_capability_completeness.py tests/test_capability_catalog.py tests/test_b3_runtime_intent_gate.py tests/test_research_fast.py tests/test_research_iter.py tests/test_research_deep.py tests/test_research_depth.py tests/test_research_model_lane.py tests/test_research_tools.py tests/test_sonar_lane.py tests/test_perplexity_backend.py tests/test_agents_store.py tests/test_plugins.py tests/test_portfolio.py tests/test_schema_version.py tests/test_runs_store.py tests/test_runs_router.py tests/test_run_manager.py tests/test_workspace.py tests/test_mcp_server.py tests/test_agents_router.py
```

### vitest

| File | Entry | Case (-t pattern) |
|---|---|---|
| src/modules/backtest/BacktestResultView.test.tsx | R15-UI-061 | whole file |
| src/store/proposed-changes.test.ts | R15-CODE-FRONTEND-034 | a reworded Kept label still acks kept_previous |
| src/lib/host-actions.test.ts | R15-CODE-FRONTEND-035, R15-RESEARCH-041 | write_note append with a trailing-whitespace addendum equals appendSymbolNote; webAvailable false |
| src/modules/chat/DepthControl.test.tsx | R15-RESEARCH-040 | Tier B + ULTRA renders an estimate before dispatch |
| src/modules/chat/mentions.test.ts | R15-UI-093 | a quoted candidate renders description |
| src/store/portfolios.test.ts | R15-UI-078, R15-CODE-PLATFORM-052 | validateHolding rejects blank cost; whole file |
| src/modules/portfolio/metrics.test.ts | R15-CODE-PLATFORM-050 | rows carry the real holding id |
| src/modules/portfolio/PortfolioPanel.test.tsx | R15-CODE-PLATFORM-051 | whole file (existing suite) |
| src/lib/csv.test.ts | R15-UI-079 | R15-UI-079 (the actual title reads "prefixes a formula-trigger leading char so no text cell opens a live formula", not the claimed "...with a quote") |
| src/modules/chat/context-provider.test.ts | R15-AGENT-091 | get_portfolio holdings carry a currency field |
| src/lib/delegate-runs.test.ts | R15-CODE-AGENT-032 | skips a poll while one is in flight |
| src/lib/keychain.test.ts | R15-CODE-PLATFORM-057 | keychain-migrate:waiting |
| src/store/onboarding.test.ts | R15-CROSS-PLATFORM-011 | rejecting keychain keeps seen:true once markSeen ran |
| scripts/audit-design-tokens.test.mjs | R15-UI-075, R15-CODE-PLATFORM-070 | body font-feature-settings enables zero; a mismatched fallback fails the audit |
| src/store/symbols.test.ts, src/store/chart-drawings.test.ts | R15-UI-076 | whole files |
| src/store/marketplace.test.ts | R15-CODE-PLATFORM-049 | deletes each granted secret |
| src/modules/marketplace/MarketplacePanel.test.tsx | R15-UI-089 | whole file |
| src/store/agent-mode.test.ts | R15-AGENT-087 | whole file |

```
pnpm exec vitest run src/modules/backtest/ src/store/backtest.test.ts src/store/proposed-changes.test.ts src/lib/host-actions.test.ts src/modules/chat/DepthControl.test.tsx src/store/search-settings.test.ts src/modules/chat/mentions.test.ts src/store/portfolios.test.ts src/modules/portfolio/metrics.test.ts src/modules/portfolio/PortfolioPanel.test.tsx src/lib/csv.test.ts src/modules/chat/context-provider.test.ts src/lib/delegate-runs.test.ts src/lib/keychain.test.ts src/store/onboarding.test.ts src/components/KeyEntryDialog.test.tsx scripts/audit-design-tokens.test.mjs src/store/symbols.test.ts src/store/chart-drawings.test.ts src/store/marketplace.test.ts src/modules/marketplace/MarketplacePanel.test.tsx src/store/agent-mode.test.ts
# W8 ripple (expected to need fixture updates, outside P1):
pnpm exec vitest run src/modules/watchlist/WatchlistPanel.test.tsx src/modules/news/NewsFeedPanel.test.tsx src/modules/panel-context-publishers.test.tsx src/modules/notes/NotesPanel.test.tsx src/lib/workspace.test.ts src/store/settings.test.ts
```

### cargo (W7)

Claimed tests:
- lib.rs `tests::write_atomic_text_and_bytes` (R15-CODE-PLATFORM-055)
- lib.rs `tests::write_atomic_round_trip_leaves_no_tmp` (-054)
- lib.rs `tests::rename_failure_removes_tmp` (R15-CROSS-PLATFORM-007)
- lib.rs `tests::no_env_mutation_in_src` and `tests::sidecar_command_env_carries_mcp_ports` (R15-CROSS-PLATFORM-008)
- lib.rs `tests::clear_mcp_endpoint_file_removes_existing` (R15-LIFECYCLE-037, R15-CODE-PLATFORM-074)
- lib.rs `tests::plain_tcp_listener_is_not_healthy` (R15-LIFECYCLE-038)
- lib.rs `tests::smoke_bind_budget_matches_supervisor` (R15-RELEASE-009)
- keychain.rs `tests::dev::migrate_with_erroring_reader_leaves_unmigrated_and_retries` (-056)
- keychain.rs `tests::dev::on_wait_called_before_sleep` (-057)
- R15-CODE-PLATFORM-058: the whole cargo test --lib run
- R15-CODE-PLATFORM-059: the clippy line below

Every named fn was grep-confirmed present on the candidate.

```
cargo test --manifest-path src-tauri/Cargo.toml --lib
cargo fmt --manifest-path src-tauri/Cargo.toml --check
cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings -W clippy::significant_drop_in_scrutinee
```

### docs-only (W9)

The acceptance checks are greps. They were already run on the candidate:
- `grep -i langgraph docs/BLUEPRINT.md` returns nothing.
- `grep -ic "system tray" docs/BLUEPRINT.md` returns 0.

Entries: R15-DOCS-007/009/014/019/020/021/022/023, R15-CODE-PLATFORM-060, R15-RELEASE-010. These have no runnable test.

## Integration recipe (after the r15-rc1 tag)

```
git fetch origin
git worktree add <scratch>/P1-int origin/worktree-agent-lows-P1-int-4c6dfe8 -b lows-P1-int-on-tag
cd <scratch>/P1-int
git rebase --rebase-merges --onto r15-rc1 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
#  if the tag is not a descendant of 4c6dfe8c, or the rebase conflicts, replay instead:
#  git reset --hard r15-rc1 && for b in W1-backtest W2-runtime-catalog W3-actions-research W4-chat-composer W5-portfolio W6-runs-stores W7-rust-core W8-tokens-market W9-docs-truth; do git merge --no-ff --no-edit origin/worktree-agent-lows-P1-$b || break; done && git cherry-pick 70fe85c9
pnpm ci-local   # full chain: lint, format:check, typecheck, clippy, ruff, vitest, cargo test, pytest
#  plus the focused commands above; fix the W8 ripple fixtures in their owning files
#  then one fresh verifier over the diff r15-rc1..HEAD
git checkout 004-r4-experience-rebuild && git merge --no-ff lows-P1-int-on-tag
```
