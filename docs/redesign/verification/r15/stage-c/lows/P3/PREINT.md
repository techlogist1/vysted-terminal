# P3 lows pre-integration candidate

Assembled 06:50-06:53 IST (nine sets); fix pass 07:02 IST; extras pass 07:25-07:31 IST (four second-attempt branches merged last). Status: **untested pending integration** (no pytest, vitest, tsc, eslint, cargo or build was run; the rc1 gate owns those lanes).

- Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (writer branches were cut from `ebc5ed4194f9362422c3178c27d4cdf946428968`; base drift since then touches no P3 file)
- Branch: `worktree-agent-lows-P3-int-4c6dfe8` (pushed, `git ls-remote` verified)
- Head: `6e41bfc1bdd4255b427da84bb999641f7df78998` (previous heads: `266ed2ef` nine sets + assembler fixup; `aa1690ee` fix pass)
- Worktree: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-preint/P3` (kept)

## Merge order

| # | Set | Branch | origin head = WRITERS.json | Merge sha | Conflicts |
|---|---|---|---|---|---|
| 1 | W1 | `worktree-agent-lows-P3-W1-client-plugins` | `9d0a9129b273` yes | `e6a8687dc48f` | 0 |
| 2 | W2 | `worktree-agent-lows-P3-W2-llm-chat` | `69ce59998999` yes | `358a7c078484` | 0 |
| 3 | W3 | `worktree-agent-lows-P3-W3-provenance-data` | `d7059b24a27e` yes | `f7196d73b614` | 0 |
| 4 | W4 | `worktree-agent-lows-P3-W4-quant-macro` | `c60f921f4a64` yes | `de8db722dd49` | 0 |
| 5 | W5 | `worktree-agent-lows-P3-W5-workflow-backend` | `d9c8da22eb20` yes | `30244a88f3f7` | 0 |
| 6 | W6 | `worktree-agent-lows-P3-W6-data-hygiene` | `9eaab2ac7382` yes | `bdb286b349ee` | 0 |
| 7 | W7 | `worktree-agent-lows-P3-W7-notes-datatable` | `f714efe50aa3` yes | `df0a6d71b303` | 0 |
| 8 | W8 | `worktree-agent-lows-P3-W8-panels-polish` | `e4a77aca0f96` yes | `9a0108df5359` | 0 |
| 9 | W9 | `worktree-agent-lows-P3-W9-search-backends` | `95b60cc1e7b4` yes | `7b7fa49476ab` | 0 |
| 10 | extra (R15-AGENT-077, after W2) | `worktree-agent-lows-CN-r15-agent-077-4c6dfe8` | `80f8d7a244f7` = task list | `c58f04f3` | 0 |
| 11 | extra (R15-DATA-102, after W3) | `worktree-agent-lows-CN-r15-data-102-4c6dfe8` | `09d8da83a20c` = task list | `19835106` | 1 (RESULT.md) |
| 12 | extra (NEW drafted lows) | `worktree-agent-lows-NEW-drafted-4c6dfe8` | `abcee383b1c1` = task list | `e9a0b8b9` | 1 (RESULT.md) |
| 13 | extra (R15-LEAD-036) | `worktree-agent-lows-LEAD-036-4c6dfe8` | `8315c8579d1d` = task list | `e377d55a` | 1 (RESULT.md) |

No head mismatches (the nine set heads re-checked on origin at 07:25 IST). The four extra branches are cut from `4c6dfe8c` and merged last, after every set branch, so each CN branch lands after the set that carried its entry's first partial attempt (W2 for 077, W3 for 102). Every extra tip is an ancestor of the head. Every file an extra touches is blob-identical to that extra's tip, or its hunks reverse-apply cleanly on the head, with one exception: `fundamentals_store.py`, whose only delta from the CN-102 tip is W3's R15-DATA-103 quote hunk, so both are present.

Assembler commit on top:

- `266ed2ef75a3` (R15-AGENT-077, 06:53): get_provider fakes widened to accept **_k (lambda _p -> lambda _p, **_k; lambda *_a -> lambda *_a, **_k). Signature only, no assertion change. W2 left 077 could_not because these two unowned fakes raise TypeError once oneshot passes base_url=. Files: `sidecar/tests/test_research_metering.py`, `sidecar/tests/test_b5_runtime_synthesis.py`. The CN-077 branch (ef9e04cd) later made byte-identical hunks, so merge 10 was clean.
- `6e41bfc1bdd4` (extras pass): `style: ruff/prettier on the P3 candidate`. It runs prettier --write on the combined root `RESULT.md`. None of the four writer copies was prettier-clean. Prettier oscillated on the bare `**_k` and dropped two backticks from the triple-backtick and `~~~` fence mentions, so those tokens were wrapped as inline code first. After that the output is idempotent (checked by a second --write) and keeps every word.

## Conflict map

The nine set merges were clean. The extras produced one conflict kind, three times:

| File | Merges | The two intents | Resolution | Entry ids |
|---|---|---|---|---|
| `RESULT.md` (repo root, add/add) | 11 `19835106`, 12 `e9a0b8b9`, 13 `e377d55a` | Each second-attempt writer adds its own root report | Concatenate ours, `---`, theirs at each merge. All four reports are kept verbatim in merge order (CN-077, CN-102, NEW-drafted, LEAD-036), then prettier-formatted in `6e41bfc1` | R15-AGENT-077, R15-DATA-102, R15-DOCS-025, R15-CODE-PLATFORM-078/079/080, R15-CODE-FRONTEND-038, R15-DOCS-026, R15-LEAD-036 |

`RESULT.md` is a writer report, not product. The integrator may move it under `docs/redesign/verification/r15/stage-c/lows/P3/` or drop it, with a recorded decision. No code file conflicted: CN-077's code and test hunks were already on the candidate via W2 plus `266ed2ef`, and CN-102's auto-merged over W3.

## Blocked hunks (order-safety surface)

None blocked. No branch touches `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs` or `types/proposed-change.ts`.

The one exception is R15-LEAD-036, which touches `sidecar/services/agent_runtime.py` (5 hunks, +45/-2), and it **was merged after review**. The surface entry is that file's proposed-changes gate: `_auto_publish_event` (~:1251 at base), the ack and staged narration (~:1320-1690) and the auto_brief dispatch (~:3168). The LEAD-036 hunks are `_carry_fence` (new, after `_units`), a `_TurnState.fence` field, and three lines in `_consume_round._release` / the `_release_point` hold. All of that is the figure/citation prose-release guard, the same area as the base-side LEAD-030/035/036 guard commits. No gate, dispatch, ack or ProposedChange code is touched. P1's PREINT set the precedent: its W2 agent_runtime hunks were reviewed and merged. A verifier who reads the surface as the whole file should drop merge 13 (`e377d55a`); nothing else depends on it.

## Risk map

- Files touched by more than one P3 writer (all resolved without loss):
  - W2 + CN-077 (+ `266ed2ef`): `sidecar/services/llm/{openai,oneshot,native_search}.py`, `tests/test_llm_openai.py`, `tests/test_research_metering.py`, `tests/test_b5_runtime_synthesis.py`. The hunks are identical (R15-AGENT-077).
  - W3 + CN-102: `sidecar/models/fundamentals.py`, `services/fundamentals_store.py`, `services/yfinance_provider.py`, `services/growth_check.py`, `tests/test_fundamentals_store.py`, `tests/test_growth_check.py`, `types/data.ts`. These carry R15-DATA-102 alongside W3's R15-DATA-103 and R15-LEAD-006.
  - `RESULT.md`: all four extras.
- **Files touched by P3 and another partition: the candidates moved since 06:53, and there are now conflicts.** I simulated the merges at 07:29 IST with `git merge-tree` against origin `P1-int` `dbe5fe4f` and `P2-int` `7db0b295`. Stacking P3 on P1+P2 conflicts in five files:
  - `src-tauri/src/lib.rs`: P3 R15-CODE-PLATFORM-080 (NEW-drafted) against P1's R15-CODE-PLATFORM-054/055/058/059, R15-CROSS-PLATFORM-007/008/011, R15-LIFECYCLE-037/038 and R15-RELEASE-009.
  - `sidecar/main.py`: P3 R15-CODE-PLATFORM-068 (W5) against P2 R15-CROSS-PLATFORM-012.
  - `sidecar/services/fundamentals_store.py`: P3 R15-DATA-102/103 against P2 R15-CROSS-PLATFORM-012.
  - `src/components/StatusChrome.tsx`: P3 R15-LEAD-021 (W8) against P2 R15-UI-073.
  - `src/lib/sidecar-client.ts`: P3 R15-CODE-PLATFORM-039, R15-DATA-109 and R15-LIFECYCLE-027 (W1) against P2 R15-CODE-FRONTEND-027.
  - These auto-merge: `docs/SIDECAR_API.md`, `agent_runtime.py`, `test_agent_runtime.py`, `research/relevance.py`, `test_run_manager.py` and `ChartPanel.test.tsx` (with P1); `.gitignore`, `test_provider_health.py`, `DataTable.tsx`, `sidecar-client.test.ts`, `ModelControl.tsx`, the four quant panel tests and `ScreenerPanel.tsx` (with P2).
- Rust / build config:
  - `src-tauri/src/lib.rs` (R15-CODE-PLATFORM-080): a `VYSTED_DATA_DIR` override is read before `app_data_dir` in both `resolve_data_dir` and `get_app_data_dir`, with a new pure `parse_data_dir_override` and a unit test. cargo fmt, clippy and test were never run, and the writer did not rustfmt it. `tauri.conf.json` is untouched.
  - `scripts/sidecar-specs.mjs` (R15-CODE-PLATFORM-078): the main spec now builds `sidecar/.venv` from `requirements.txt` plus the pip extra `pyinstaller==6.20.0`. `requirements-dev.txt` is `-r requirements.txt` plus pyinstaller, ruff, pytest, pytest-asyncio and httpx, and httpx is also a runtime pin, so the runtime set does not change. **But `sidecar/.venv` is the same venv the focused pytest commands and `sidecar/.venv/bin/ruff` use.** A freshly created venv no longer has pytest, pytest-asyncio or ruff. On an existing venv pip never uninstalls, so the change has no effect there. Editing the recipe makes sidecar-staleness force a main rebuild. ci-local installs `requirements-dev.txt` into its own python before pytest, so the chain is unaffected.
  - `.gitignore` gains `coverage/` (R15-CODE-PLATFORM-079).
  - No .github/, tauri.conf.json, package.json, pnpm-lock, Cargo.toml or pyproject change.
- Safety doc: `docs/SAFETY_ARCHITECTURE.md` §2 (R15-DOCS-025). The claim that every kind auto-applies under AUTO now names `AUTO_APPLIED_KINDS` (panel, chart, watchlist) and says data-write and settings always wait. This is doc-only and describes existing behaviour. A verifier should confirm it against the frontend `AUTO_APPLIED_KINDS`.
- Boot path: sidecar/app.py + sidecar/main.py (W5, R15-CODE-PLATFORM-068): create_app now calls workflow_nodes.register_all() for every node type; main.py no longer calls it nor the deleted services/workflow_nodes/registry_v0_6_0.register_v0_6_0_nodes. The removed main.py docstring said node handlers were kept OUT of create_app so TestClient builds would not see them because workflow-engine tests reset the registry and register their own; that premise is reversed, so the FULL pytest suite (order effects, e.g. test_screener_nodes) and the sidecar smoke-test both matter here. agent_tools.register_v0_6_0_tools is a different module and is still referenced.
- Deleted files: sidecar/services/quant/monte_carlo.py (R15-CODE-PLATFORM-040, no importer); sidecar/services/workflow_nodes/registry_v0_6_0.py (R15-CODE-PLATFORM-068); src/lib/fuzzy.ts + src/lib/fuzzy.test.ts (R15-CODE-FRONTEND-024; PARTITION.md sanctions removing the test because its module is the dead code).
- New modules: sidecar/routers/_cached.py (imported statically by routers/earnings.py, routers/fundamentals.py); sidecar/services/search/html_serp.py (imported by brave.py, mojeek.py); src/lib/date-defaults.ts; src/lib/safe-filename.ts; src/modules/analyst-ratings/format.ts; scripts/search-live-smoke.mjs.
- Wire mirrors changed together: sidecar/models/llm.py <-> types/ai.ts (W2); types/data.ts <-> sidecar/models/market.py + fundamentals.py (W3); sidecar/models/quant.py <-> types/quant.ts (W4); sidecar/models/workflow.py <-> types/workflow.ts (W5).
- Untested / risky:
  - R15-AGENT-077: the `**_k` fakes (266ed2ef = CN ef9e04cd) are unrun; the two fakes previously failed per W2.
  - R15-DATA-102 (CN): the default for `Fundamentals.growth_basis` is now None, so anything that relied on the inherited 'mrq_yoy' now sees None. The writer found and fixed three tests. `correctness_gate.overlay_filed_periods` now serves filed growth over an unstated basis and stamps 'mrq_yoy'. `growth_check.should_cross_check` flips True->False for an absent basis. `research/semantics.py` and `company_narrative.py` still label growth MRQ unconditionally (the writer noted this and did not file it).
  - R15-LEAD-036: the streaming guard behaves differently. A held empty fence opener turns round 2's rows into a fenced block judged by `_judge_clause`, and an empty unclosed fence at turn end is dropped. Run the whole `test_agent_runtime.py`, again after the P1 merge (P1 also edits agent_runtime).
  - R15-CODE-FRONTEND-038: the claimed build-log check (zero `[INEFFECTIVE_DYNAMIC_IMPORT]`) needs a real `pnpm tauri build`.
  - The R15-CODE-PLATFORM-080 Rust test and its rustfmt layout are unverified.
  - W7 R15-DOCS-010 NotesToolbar test was never executed by the writer (tiptap extension-list missing from the shared node_modules top-level symlinks); first real run is at integration.
  - test_screener_nodes.py order dependence after the workflow_nodes registry deletion (W5 issue).
  - W5 PLATFORM-069: node-registry filter only; NodeEditorPanel/VystedNode do not pass the server node list yet (UI behaviour unchanged until wired).
  - Writer-reported pre-existing tsc TS2307 for @tiptap/extension-list in src/modules/notes (node_modules state, not this diff).
  - docs/redesign/verification/r15/stage-c/lows/P3/writers/W1.jsonl arrives via the W1 branch (not present in the main worktree); a later main-worktree write of the same path would conflict.
  - docs/.../P3/writers/W2.jsonl line 6 (R15-RESEARCH-031) is not valid JSON; WRITERS.json carries the entry.
- Outcomes for the verifier:
  - R15-CODE-PLATFORM-045 and R15-CODE-PLATFORM-046: not_a_defect_proposed.
  - R15-AGENT-077: fixed_untested (CN second attempt; WRITERS.json still says could_not).
  - R15-DATA-102: fixed_untested (CN second attempt; WRITERS.json still says could_not).
  - NEW drafted (register does not carry these ids yet): R15-DOCS-025, R15-CODE-PLATFORM-078/079/080 and R15-CODE-FRONTEND-038 are fixed_untested. R15-DOCS-026 is tier4 and was not touched (CLAUDE.md).

## Claimed tests (focused commands for the integrator)

Python, from the repo root:

```sh
cd sidecar && .venv/bin/python -m pytest -q tests/test_b5_runtime_synthesis.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_brave_backend.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_budget_guard.py::test_prices_with_served_model
cd sidecar && .venv/bin/python -m pytest -q tests/test_company_narrative.py::test_five_section_fixture_parses_all_fields
cd sidecar && .venv/bin/python -m pytest -q tests/test_ddg_backend.py::test_403_then_429_reports_rate_limited tests/test_ddg_backend.py::test_one_search_with_lite_fallback_takes_one_pacing_slot
cd sidecar && .venv/bin/python -m pytest -q tests/test_earnings_quality.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_fundamentals_models.py::test_field_meta_status_rejects_unknown
cd sidecar && .venv/bin/python -m pytest -q tests/test_fundamentals_store.py::test_null_change_row_keeps_change_unset_and_row_currency tests/test_fundamentals_store.py::test_row_to_pair_null_growth_row_states_no_basis_and_derives_field_meta
cd sidecar && .venv/bin/python -m pytest -q tests/test_growth_check.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_history.py::test_freshness_label_failure_yields_unknown
cd sidecar && .venv/bin/python -m pytest -q tests/test_india_sector_map.py::test_enrichment_writes_canonical_seven_keys
cd sidecar && .venv/bin/python -m pytest -q tests/test_keyless_backend.py::test_canary_engine_error_counts_a_failure_with_its_own_note tests/test_keyless_backend.py::test_canary_real_results_record_success tests/test_keyless_backend.py::test_nonempty_page_zero_rows_counts_parser_drift_failure
cd sidecar && .venv/bin/python -m pytest -q tests/test_llm_lows.py::test_get_provider_groq_gemini_honour_or_reject_base_url tests/test_llm_lows.py::test_stream_chat_abc_is_not_a_coroutine_function tests/test_llm_lows.py::test_validate_key_has_no_reraise_only_clause
cd sidecar && .venv/bin/python -m pytest -q tests/test_llm_ollama.py::test_tools_construction_error_logs_and_emits_notice
cd sidecar && .venv/bin/python -m pytest -q tests/test_llm_openai.py::test_repair_round_keeps_configured_base_url
cd sidecar && .venv/bin/python -m pytest -q tests/test_macro_providers.py::test_fred_sa_bw_map_to_other tests/test_macro_providers.py::test_provider_constants_are_macro_provider_values
cd sidecar && .venv/bin/python -m pytest -q tests/test_mojeek_backend.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_provider_health.py::test_is_rate_limit_union
cd sidecar && .venv/bin/python -m pytest -q tests/test_quant_greeks.py::test_compute_greeks_equals_price_european_bs
cd sidecar && .venv/bin/python -m pytest -q tests/test_quant_options.py::test_validate_domain_rejects_steps_2_and_low_paths
cd sidecar && .venv/bin/python -m pytest -q tests/test_quant_router.py::test_duplicate_pillar_is_400
cd sidecar && .venv/bin/python -m pytest -q tests/test_quant_yield_curve.py::test_grid_distinct_and_within_max_tenor
cd sidecar && .venv/bin/python -m pytest -q tests/test_range_check.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_research_metering.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_research_relevance.py::test_junk_filter_host_match_delegates_to_finance
cd sidecar && .venv/bin/python -m pytest -q tests/test_resolver_rename.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_router_cached_helper.py::test_corrupt_cache_entry_refetches_for_all_rating_routes
cd sidecar && .venv/bin/python -m pytest -q tests/test_run_manager.py::test_crashed_run_detail_is_humanized
cd sidecar && .venv/bin/python -m pytest -q tests/test_symbol_resolver.py
cd sidecar && .venv/bin/python -m pytest -q tests/test_workflow_builtin_nodes.py::test_create_app_registers_every_builtin_node tests/test_workflow_builtin_nodes.py::test_huge_pow_and_repeat_rejected_fast tests/test_workflow_builtin_nodes.py::test_zero_input_not_replaced_by_config_and_unknown_provider_errors
cd sidecar && .venv/bin/python -m pytest -q tests/test_workflow_router.py::test_dangling_edge_yields_one_run_error_frame tests/test_workflow_router.py::test_resume_from_is_rejected_not_silently_rerun
```

Extra branches (from each RESULT.md). Where a file is already listed above, these are added cases:

```sh
# R15-AGENT-077 (CN)
cd sidecar && .venv/bin/python -m pytest -q tests/test_llm_openai.py::test_repair_round_keeps_configured_base_url tests/test_native_search.py::test_native_search_oneshot_keeps_the_callers_base_url tests/test_research_metering.py tests/test_b5_runtime_synthesis.py
# R15-DATA-102 (CN)
cd sidecar && .venv/bin/python -m pytest -q tests/test_b7_exchange_financials.py::test_filed_growth_states_mrq_yoy_and_never_overrides_an_annual_basis tests/test_fundamentals.py::test_served_growth_states_its_mrq_yoy_basis tests/test_fundamentals.py::test_get_fundamentals tests/test_fundamentals_tool.py::test_tool_result_carries_growth_basis tests/test_growth_check.py tests/test_fundamentals_store.py::test_row_to_pair_growth_without_a_recorded_basis_states_none tests/test_fundamentals_store.py::test_row_to_pair_null_growth_row_states_no_basis_and_derives_field_meta
# R15-LEAD-036
cd sidecar && .venv/bin/python -m pytest -q tests/test_agent_runtime.py::test_a_fence_opened_before_a_tool_call_leaves_no_marker_when_replaced tests/test_agent_runtime.py::test_a_streamed_fence_is_closed_before_the_next_rounds_note tests/test_agent_runtime.py::test_a_fence_continued_on_an_ok_result_streams_as_written
# NEW drafted: R15-CODE-PLATFORM-078, R15-CODE-FRONTEND-038 (vitest), R15-CODE-PLATFORM-080 (cargo)
node_modules/.bin/vitest run scripts/sidecar-specs.test.mjs src/lib/export-artifact.test.ts
cargo test --manifest-path src-tauri/Cargo.toml data_dir_override_wins_when_set_to_a_non_blank_value
```

If `sidecar/.venv` was rebuilt after R15-CODE-PLATFORM-078, first run `sidecar/.venv/bin/python -m pip install -r sidecar/requirements-dev.txt`, because that venv no longer gets pytest.

All Python in one call:

```sh
cd sidecar && .venv/bin/python -m pytest -q tests/test_agent_runtime.py tests/test_b5_runtime_synthesis.py tests/test_b7_exchange_financials.py tests/test_brave_backend.py tests/test_budget_guard.py tests/test_company_narrative.py tests/test_ddg_backend.py tests/test_earnings_quality.py tests/test_fundamentals.py tests/test_fundamentals_models.py tests/test_fundamentals_store.py tests/test_fundamentals_tool.py tests/test_growth_check.py tests/test_history.py tests/test_india_sector_map.py tests/test_keyless_backend.py tests/test_llm_lows.py tests/test_llm_ollama.py tests/test_llm_openai.py tests/test_macro_providers.py tests/test_mojeek_backend.py tests/test_native_search.py tests/test_provider_health.py tests/test_quant_greeks.py tests/test_quant_options.py tests/test_quant_router.py tests/test_quant_yield_curve.py tests/test_range_check.py tests/test_research_metering.py tests/test_research_relevance.py tests/test_resolver_rename.py tests/test_router_cached_helper.py tests/test_run_manager.py tests/test_symbol_resolver.py tests/test_workflow_builtin_nodes.py tests/test_workflow_router.py
```

TypeScript (vitest), from the repo root; named cases per file:

- `src/components/DataBadges.test.tsx`: R15-UI-067: dates EOD in the viewer's local calendar across IST midnight (R15-UI-067)
- `src/components/EmptyState.test.tsx`: R15-UI-066: R15-UI-066: variant error renders role=alert and a distinct icon
- `src/components/StatusChrome.test.tsx`: R15-LEAD-021: an error status with a reason renders the reason in the chip title
- `src/lib/date-defaults.test.ts`: R15-UI-063: None
- `src/lib/dead-surface.test.ts`: R15-CODE-FRONTEND-024: R15-CODE-FRONTEND-024: no live source references a deleted dead-code symbol > finds zero references to fuzzyRank/fuzzyScore/exportNoteMd under src/
- `src/lib/plugin-bootstrap.test.ts`: R15-LIFECYCLE-027: persistence.load is called exactly once per catalog plugin
- `src/lib/plugin-runtime.test.ts`: R15-CODE-PLATFORM-047: disable during a pending healthCheck stays stopped, not reverted to active | R15-CODE-PLATFORM-048: '<0.9.0' is rejected as unsupported...
- `src/lib/safe-filename.test.ts`: R15-CROSS-PLATFORM-006: safeFilename > maps %s to a Windows-legal name (table: NSE:RELIANCE, CON, a?b, x.)
- `src/lib/search-headers.test.ts`: R15-CODE-PLATFORM-039: includeKey:false omits the key and never reads the keychain, tier/models still ride (R15-CODE-PLATFORM-039)
- `src/lib/sidecar-client.test.ts`: R15-DATA-109: openCryptoStream is not exported | R15-LIFECYCLE-027: request timeouts (3 tests)
- `src/modules/analyst-ratings/format.test.ts`: R15-CODE-DATA-016: fmtDate parses a YYYY-MM-DD date as a local calendar date, never UTC midnight
- `src/modules/backtest/BacktestPanel.test.tsx`: R15-UI-062: None
- `src/modules/chart/ChartPanel.test.tsx`: R15-CODE-FRONTEND-023: N crosshair moves on a lone chart cause 0 ChartPanel re-renders (R15-CODE-FRONTEND-023) | R15-UI-064: a % comparison overlay gets sorted, de-duplicated points on a VISIBLE left scale (R15-UI-064)
- `src/modules/chat/ChatSidebar.test.tsx`: R15-CODE-FRONTEND-021: ContextBadge hidden with no bus events, shown with one panel event (asserted on kind) (R15-CODE-FRONTEND-021) | R15-CODE-FRONTEND-032: /clear rejects a pending write_note and acks it failed (R15-CODE-FRONTEND-032)
- `src/modules/chat/ModelControl.test.tsx`: R15-UI-072: R15-UI-072: the trigger contains a chevron icon
- `src/modules/chat/streaming.test.ts`: R15-RESEARCH-031: multi-line query research:begin fires beginRun with the full query
- `src/modules/earnings/EarningsCalendarPanel.test.tsx`: R15-CODE-DATA-015: R15-CODE-DATA-015: skeleton and loaded colgroups share widths
- `src/modules/node-editor/node-registry.test.ts`: R15-CODE-PLATFORM-069: plugin node absent from the server list is not runnable
- `src/modules/notes/NotesToolbar.test.tsx`: R15-DOCS-010: NotesToolbar — R15-DOCS-010 > the active toolbar button carries the fill class
- `src/modules/quant/BondPricerPanel.test.tsx`: R15-UI-063: panel date-default describe block
- `src/modules/quant/GreeksDashboard.test.tsx`: R15-UI-063: panel date-default describe block
- `src/modules/quant/OptionPricerPanel.test.tsx`: R15-UI-063: panel date-default describe block
- `src/modules/quant/YieldCurvePanel.test.tsx`: R15-UI-063: panel date-default describe block ; R15-UI-077: duplicate-pillar test
- `src/modules/research/BriefPanel.test.tsx`: R15-UI-080: a vysted:// source renders a provenance chip, no external link, and no favicon lookup
- `src/modules/research/brief-layout.test.tsx`: R15-UI-074: caps heading, prose and list blocks at max-w-prose but lets a table use the panel width
- `src/modules/screener/ScreenerPanel.test.tsx`: R15-UI-069: None
- `src/modules/sec/SecFilingsPanel.test.tsx`: R15-CODE-DATA-014: R15-CODE-DATA-014: a filingsByIdentifier update after mount re-renders the row count
- `scripts/sidecar-specs.test.mjs`: R15-CODE-PLATFORM-078: %s builds from requirements.txt, not requirements-dev.txt (it.each over SIDECAR_SPECS)
- `src/lib/export-artifact.test.ts`: R15-CODE-FRONTEND-038: export-artifact.ts sidecar-client import > imports sidecar-client statically

```sh
node_modules/.bin/vitest run scripts/sidecar-specs.test.mjs src/components/DataBadges.test.tsx src/components/EmptyState.test.tsx src/components/StatusChrome.test.tsx src/lib/date-defaults.test.ts src/lib/dead-surface.test.ts src/lib/export-artifact.test.ts src/lib/plugin-bootstrap.test.ts src/lib/plugin-runtime.test.ts src/lib/safe-filename.test.ts src/lib/search-headers.test.ts src/lib/sidecar-client.test.ts src/modules/analyst-ratings/format.test.ts src/modules/backtest/BacktestPanel.test.tsx src/modules/chart/ChartPanel.test.tsx src/modules/chat/ChatSidebar.test.tsx src/modules/chat/ModelControl.test.tsx src/modules/chat/streaming.test.ts src/modules/earnings/EarningsCalendarPanel.test.tsx src/modules/node-editor/node-registry.test.ts src/modules/notes/NotesToolbar.test.tsx src/modules/quant/BondPricerPanel.test.tsx src/modules/quant/GreeksDashboard.test.tsx src/modules/quant/OptionPricerPanel.test.tsx src/modules/quant/YieldCurvePanel.test.tsx src/modules/research/BriefPanel.test.tsx src/modules/research/brief-layout.test.tsx src/modules/screener/ScreenerPanel.test.tsx src/modules/sec/SecFilingsPanel.test.tsx
```

Claims that are not a test id:

- R15-CODE-PLATFORM-045: None
- R15-CODE-PLATFORM-046: None
- R15-LEAD-006: grep: one def _row_value
- R15-CODE-PLATFORM-040: n/a (deletion; confirmed no importer via repo grep)
- R15-DOCS-025: doc-only, no test
- R15-CODE-PLATFORM-079: config-only (.gitignore), no test
- R15-CODE-FRONTEND-038: build-log check (zero `[INEFFECTIVE_DYNAMIC_IMPORT]` in `pnpm tauri build`), needs a build
- R15-DOCS-026: tier4, no work

Watch, not claimed by a writer:

- `sidecar/tests/test_screener_nodes.py::test_register_adds_screener_query_to_workflow_engine`: W5 reports it is test-order dependent (import-time registration); its comment names the deleted workflow_nodes register_v0_6_0_nodes. Run: cd sidecar && .venv/bin/python -m pytest -q tests/test_screener_nodes.py, and also inside the full suite.

## Integration recipe (after the r15-rc1 tag)

```sh
export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20"
git fetch --prune origin --tags
WT=/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-preint/P3
git -C $WT checkout -b worktree-agent-lows-P3-int-rc1 origin/worktree-agent-lows-P3-int-4c6dfe8
git -C $WT rebase --rebase-merges --onto r15-rc1 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2
# expected clean: no P3 file differs between 4c6dfe8c and the writer base; if the tag moved a P3 file, resolve and record
# --rebase-merges re-runs merges 11-13: RESULT.md add/add again -> take the concatenation (ours, '---', theirs)
# if the P1 and/or P2 candidates landed first: resolve lib.rs, main.py, fundamentals_store.py, StatusChrome.tsx, sidecar-client.ts (risk map), keeping both entries' behaviour and tests
sidecar/.venv/bin/python -m pip install -r sidecar/requirements-dev.txt   # R15-CODE-PLATFORM-078: a rebuilt sidecar/.venv lacks pytest/ruff
# run the chain (pnpm ci-local) + the focused commands above + pnpm sidecars:build --force + node scripts/smoke-test-sidecars.mjs (boot path R15-CODE-PLATFORM-068, build input R15-CODE-PLATFORM-078)
git -C $WT push origin worktree-agent-lows-P3-int-rc1          # new name, never force
# one fresh verifier on origin/worktree-agent-lows-P3-int-rc1, then on 004-r4-experience-rebuild:
git merge --no-ff origin/worktree-agent-lows-P3-int-rc1
```

`--onto r15-rc1 4c6dfe8c` replays only the 13 merges, `266ed2ef`, the fix pass (`8295dab8`, `38d454be`, `aa1690ee`) and `6e41bfc1` onto the tag. If `git merge-base --is-ancestor 4c6dfe8c r15-rc1` is false, the tag does not contain the base; stop and ask the lead.

## Fix pass (07:02 IST, Opus, one bounded pass)

Candidate `worktree-agent-lows-P3-int-4c6dfe8` moved 266ed2ef -> aa1690ee (pushed, not forced; ls-remote confirms aa1690eeb868fcf4f3ce04debd885f95c6f531e7). Everything is untested pending integration; no test lane was run.

Applied:

- **R15-DOCS-010 (blocking), 8295dab8.** `src/modules/notes/NotesToolbar.test.tsx`: the before/after checks now use `boldButton.classList.contains("bg-charcoal-800")` (false before the click, true inside the waitFor) and also assert `aria-pressed` "false" then "true". The inactive string at `NotesToolbar.tsx:109` carries `hover:bg-charcoal-800`, so the old substring check was red before the click and could pass without one. This makes the assertion stricter, not weaker. Prettier clean.
- **Advisory, R15-PLATFORM-068, 38d454be.** `sidecar/tests/test_screener_nodes.py:56`: the comment named the deleted `register_v0_6_0_nodes`. It now names `create_app` -> `workflow_nodes.register_all`. Comment only; py_compile and ruff are clean.
- **Advisory, R15-DATA-109, aa1690ee.** `docs/SIDECAR_API.md:94` no longer points at the removed `openCryptoStream()`. It now says no frontend client opens `/crypto/stream` and the watchlist polls REST. Prettier clean.

Left, with reasons:

- Boot path (W5, PLATFORM-068) full pytest plus `smoke-test-sidecars.mjs`: this lane is barred from running them. Hand to the integration gate.
- sidecarRequest global 30 s timeout and the `AbortSignal.any` WebKit floor (W1, LIFECYCLE-027): this is a behaviour and design choice, not a trivial fix. Record it for the integration verifier or the lead (feature-detect `AbortSignal.any`, or set a minimum OS version, which is Tier-1 `tauri.conf.json`).
- The five deleted `test_ddg_backend.py` tests (R15-CODE-RESEARCH-009): these deletions are sanctioned by the partition and replaced by three pacing tests. The verifier should list them next to the `fuzzy.test.ts` deletion. No code change.
- The `**_k` fakes in assembler commit 266ed2ef (`test_research_metering.py`, `test_b5_runtime_synthesis.py`) are still unrun, pending integration.
- Behaviour changes that may break non-P3 tests (round() digits bound, code-node to_thread plus 5 s wait_for, /workflow/run pre-start error events, collapsed LLM except clauses, quant floors in validate_domain): nothing to change. Watch for them at the integration run.
- `@tiptap/extension-list` missing from the main worktree's node_modules: environmental. A frozen-lockfile install restores it.
- The QuantLib-version-dependent 'pillar' assertion (R15-UI-077): nothing to change. Check it first if it goes red.
- R15-UI-069 has no new test and rests on the existing ScreenerPanel coverage. It stays recorded as is.

## Extras pass (07:25-07:31 IST, Opus)

I merged the four second-attempt branches last, in the given order (merges 10-13 above). The only conflict was `RESULT.md`, three times, and each was concatenated. I then made one style commit, `6e41bfc1`, and pushed `aa1690ee..6e41bfc1` (no force; `git ls-remote` confirms `6e41bfc1bdd4255b427da84bb999641f7df78998`).

Checks on the whole candidate against the base: `py_compile` passes on 95 changed .py files, `ruff format --check` and `ruff check` are clean, and `prettier --check` is clean on 77 changed ts/tsx/js/mjs/json/md/css files. No tsc, eslint, vitest, pytest, cargo or build was run. Everything is untested pending integration.

## Fix pass (07:41 IST)

Worktree: scratchpad/lows-preint/P3 (the existing assembler worktree), branch worktree-agent-lows-P3-int-4c6dfe8. Head 6e41bfc1 -> f9da207a, pushed without force; ls-remote shows f9da207a. Untested pending integration: only py_compile, ruff and prettier were run.

Applied:
- 0d7f0d38 R15-DATA-102 fixup (blocking). In sidecar/tests/test_growth_check.py, added "growth_basis": "mrq_yoy" to the test_snapshot_attaches_computed_growth_next_to_provider_values fixture. Root cause: should_cross_check (services/growth_check.py:85) now needs an explicitly stated mrq_yoy basis, so the old fixture never ran the cross-check and the computed-key lookup raised KeyError. Advisory folded in: the same key was added to the test_snapshot_attaches_nothing_when_statements_unavailable fixture, which now reaches the None-yoy path and no longer passes vacuously. No assertion was changed or removed. py_compile passes, ruff format leaves the file unchanged, and ruff check is clean.
- f9da207a (advisory). Moved repo-root RESULT.md (the four writer reports) to docs/redesign/verification/r15/stage-c/lows/P3/writers/RESULT.md as a pure rename with no content change, prettier --check clean. Nothing referenced the old path.

Left (not trivial, or outside this lane):
- LEAD-036 merge e377d55a is kept under the P1 precedent (fence guard only; no proposed-changes gate hunk). Dropping it is the lead's call.
- R15-DATA-102 blast radius (legacy fundamentals_store rows and non-yfinance producers lose the cross-check; semantics.py still labels growth 'mrq_yoy (provider-claimed)' unconditionally). This is a behaviour and design question, not a trivial fix. It needs the listed suites run at integration: test_growth_check, test_research_semantics, test_b7_exchange_financials, test_fundamentals*, test_yfinance_provider.
- LEAD-036 guard behaviour: run test_agent_runtime.py now and again after P1 lands (gate lane).
- PLATFORM-080 lib.rs: cargo fmt/clippy/test are off-lane. The lib.rs conflict with P1 dbe5fe4f and the P2 conflicts stand for the lead's integration.
- PLATFORM-078: pip install -r sidecar/requirements-dev.txt on a fresh venv is an operator/gate step with no code change.
- FRONTEND-038 INEFFECTIVE_DYNAMIC_IMPORT needs a real build (off-lane).
- R15-DOCS-025, the conflict audit and the static checks are informational; no action.
- Items carried from 07:00 (sidecarRequest timeout / AbortSignal.any WebKit floor, test_ddg_backend deletions, unrun **_k fakes, the QuantLib wording in UI-077, the PLATFORM-068 boot pytest plus smoke) remain open for the gate.
