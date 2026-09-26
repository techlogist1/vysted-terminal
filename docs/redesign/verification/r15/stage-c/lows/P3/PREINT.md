# P3 lows pre-integration candidate

Assembled 06:50-06:53 IST. Status: **untested pending integration** (no pytest, vitest, tsc, eslint, cargo or build was run; the rc1 gate owns those lanes).

- Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (writer branches were cut from `ebc5ed4194f9362422c3178c27d4cdf946428968`; base drift since then touches no P3 file)
- Branch: `worktree-agent-lows-P3-int-4c6dfe8` (pushed, `git ls-remote` verified)
- Head: `266ed2ef75a399b8e8602fce3b1f786edd60db30`
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

No head mismatches. No extra (second-attempt) branches.

Assembler commit on top:

- `266ed2ef75a3` (R15-AGENT-077): get_provider fakes widened to accept **_k (lambda _p -> lambda _p, **_k; lambda *_a -> lambda *_a, **_k). Signature only, no assertion change. W2 left 077 could_not because these two unowned fakes raise TypeError once oneshot passes base_url=. Files: `sidecar/tests/test_research_metering.py`, `sidecar/tests/test_b5_runtime_synthesis.py`.

## Conflict map

None. All nine merges were clean (`git merge --no-ff --no-edit`); no set shares a file with another P3 set, with a P1/P2 lows branch, or with the base drift since the writer base.

## Blocked hunks (order-safety surface)

None. No P3 branch touches `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs`, `types/proposed-change.ts` or `sidecar/services/agent_runtime.py`.

## Risk map

- Files touched by more than one P3 writer: none.
- Files touched by P3 and a P1/P2 lows branch: none.
- Rust / CI / Tauri / dependency config: none: no src-tauri/, .github/, tauri.conf.json, package.json, pnpm-lock, Cargo, pyproject or PyInstaller spec change.
- Boot path: sidecar/app.py + sidecar/main.py (W5, R15-CODE-PLATFORM-068): create_app now calls workflow_nodes.register_all() for every node type; main.py no longer calls it nor the deleted services/workflow_nodes/registry_v0_6_0.register_v0_6_0_nodes. The removed main.py docstring said node handlers were kept OUT of create_app so TestClient builds would not see them because workflow-engine tests reset the registry and register their own; that premise is reversed, so the FULL pytest suite (order effects, e.g. test_screener_nodes) and the sidecar smoke-test both matter here. agent_tools.register_v0_6_0_tools is a different module and is still referenced.
- Deleted files: sidecar/services/quant/monte_carlo.py (R15-CODE-PLATFORM-040, no importer); sidecar/services/workflow_nodes/registry_v0_6_0.py (R15-CODE-PLATFORM-068); src/lib/fuzzy.ts + src/lib/fuzzy.test.ts (R15-CODE-FRONTEND-024; PARTITION.md sanctions removing the test because its module is the dead code).
- New modules: sidecar/routers/_cached.py (imported statically by routers/earnings.py, routers/fundamentals.py); sidecar/services/search/html_serp.py (imported by brave.py, mojeek.py); src/lib/date-defaults.ts; src/lib/safe-filename.ts; src/modules/analyst-ratings/format.ts; scripts/search-live-smoke.mjs.
- Wire mirrors changed together: sidecar/models/llm.py <-> types/ai.ts (W2); types/data.ts <-> sidecar/models/market.py + fundamentals.py (W3); sidecar/models/quant.py <-> types/quant.ts (W4); sidecar/models/workflow.py <-> types/workflow.ts (W5).
- Untested / risky:
  - R15-AGENT-077 fixup commit 266ed2ef is unrun; the two fakes previously failed per W2.
  - W7 R15-DOCS-010 NotesToolbar test was never executed by the writer (tiptap extension-list missing from the shared node_modules top-level symlinks); first real run is at integration.
  - test_screener_nodes.py order dependence after the workflow_nodes registry deletion (W5 issue).
  - R15-DATA-102 could_not: partial producer change landed (858ed56e), Fundamentals.growth_basis default still mrq_yoy.
  - W5 PLATFORM-069: node-registry filter only; NodeEditorPanel/VystedNode do not pass the server node list yet (UI behaviour unchanged until wired).
  - Writer-reported pre-existing tsc TS2307 for @tiptap/extension-list in src/modules/notes (node_modules state, not this diff).
  - docs/redesign/verification/r15/stage-c/lows/P3/writers/W1.jsonl arrives via the W1 branch (not present in the main worktree); a later main-worktree write of the same path would conflict.
  - docs/.../P3/writers/W2.jsonl line 6 (R15-RESEARCH-031) is not valid JSON; WRITERS.json carries the entry.
- Outcomes for the verifier: R15-CODE-PLATFORM-045, R15-CODE-PLATFORM-046: not_a_defect_proposed; R15-AGENT-077: could_not in WRITERS.json; the assembler fixup may let it be judged fixed; R15-DATA-102: could_not.

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

All Python in one call:

```sh
cd sidecar && .venv/bin/python -m pytest -q tests/test_b5_runtime_synthesis.py tests/test_brave_backend.py tests/test_budget_guard.py tests/test_company_narrative.py tests/test_ddg_backend.py tests/test_earnings_quality.py tests/test_fundamentals_models.py tests/test_fundamentals_store.py tests/test_growth_check.py tests/test_history.py tests/test_india_sector_map.py tests/test_keyless_backend.py tests/test_llm_lows.py tests/test_llm_ollama.py tests/test_llm_openai.py tests/test_macro_providers.py tests/test_mojeek_backend.py tests/test_provider_health.py tests/test_quant_greeks.py tests/test_quant_options.py tests/test_quant_router.py tests/test_quant_yield_curve.py tests/test_range_check.py tests/test_research_metering.py tests/test_research_relevance.py tests/test_resolver_rename.py tests/test_router_cached_helper.py tests/test_run_manager.py tests/test_symbol_resolver.py tests/test_workflow_builtin_nodes.py tests/test_workflow_router.py
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

```sh
node_modules/.bin/vitest run src/components/DataBadges.test.tsx src/components/EmptyState.test.tsx src/components/StatusChrome.test.tsx src/lib/date-defaults.test.ts src/lib/dead-surface.test.ts src/lib/plugin-bootstrap.test.ts src/lib/plugin-runtime.test.ts src/lib/safe-filename.test.ts src/lib/search-headers.test.ts src/lib/sidecar-client.test.ts src/modules/analyst-ratings/format.test.ts src/modules/backtest/BacktestPanel.test.tsx src/modules/chart/ChartPanel.test.tsx src/modules/chat/ChatSidebar.test.tsx src/modules/chat/ModelControl.test.tsx src/modules/chat/streaming.test.ts src/modules/earnings/EarningsCalendarPanel.test.tsx src/modules/node-editor/node-registry.test.ts src/modules/notes/NotesToolbar.test.tsx src/modules/quant/BondPricerPanel.test.tsx src/modules/quant/GreeksDashboard.test.tsx src/modules/quant/OptionPricerPanel.test.tsx src/modules/quant/YieldCurvePanel.test.tsx src/modules/research/BriefPanel.test.tsx src/modules/research/brief-layout.test.tsx src/modules/screener/ScreenerPanel.test.tsx src/modules/sec/SecFilingsPanel.test.tsx
```

Claims that are not a test id:

- R15-CODE-PLATFORM-045: None
- R15-CODE-PLATFORM-046: None
- R15-LEAD-006: grep: one def _row_value
- R15-CODE-PLATFORM-040: n/a (deletion; confirmed no importer via repo grep)

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
# run the chain (pnpm ci-local) + the focused commands above + node scripts/smoke-test-sidecars.mjs (boot path changed)
git -C $WT push origin worktree-agent-lows-P3-int-rc1          # new name, never force
# one fresh verifier on origin/worktree-agent-lows-P3-int-rc1, then on 004-r4-experience-rebuild:
git merge --no-ff origin/worktree-agent-lows-P3-int-rc1
```

`--onto r15-rc1 4c6dfe8c` replays only the nine merges plus the assembler commit onto the tag. If `git merge-base --is-ancestor 4c6dfe8c r15-rc1` is false, the tag does not contain the base; stop and ask the lead.
