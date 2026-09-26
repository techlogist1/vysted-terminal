# P2 lows pre-integration candidate

Assembled 06:57 IST. Untested pending integration (no pytest/vitest/tsc/cargo/build run, per the off-lane rule).

- Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (writers cut from `ebc5ed4194f9362422c3178c27d4cdf946428968`, an ancestor)
- Branch: `worktree-agent-lows-P2-int-4c6dfe8` (pushed, ls-remote verified)
- Head: `18e5bcb077b31d7ee1464ce1e475cc3a2ddb6cfa`
- Worktree: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-preint/P2` (kept)
- Blocked hunks: none (no writer touched audit_log.py, kill_switch.py/.rs, types/proposed-change.ts or the agent_runtime gate)

## Merge order

| # | set | origin head | WRITERS.json head | mismatch | merge sha | conflicts |
|---|---|---|---|---|---|---|
| 1 | W1 `worktree-agent-lows-P2-W1-research-semantics` | `feba1762` | `feba1762` | no | `b1258276` | 0 |
| 2 | W2 `worktree-agent-lows-P2-W2-scripts-gates` | `d9228cc3` | `d9228cc3` | no | `88db406e` | 0 |
| 3 | W3 `worktree-agent-lows-P2-W3-tools-envelope` | `2505d47b` | `2505d47b` | no | `ba6b81e6` | 0 |
| 4 | W4 `worktree-agent-lows-P2-W4-warm-screener` | `1cc7ff1f` | `1cc7ff1f` | no | `1c23f226` | 0 |
| 5 | W5 `worktree-agent-lows-P2-W5-data-resilience` | `eaaef44a` | `eaaef44a` | no | `8a643b4c` | 0 |
| 6 | W6 `worktree-agent-lows-P2-W6-llm-router-mcp` | `d80e01a1` | `d80e01a1` | no | `31dd548f` | 0 |
| 7 | W7 `worktree-agent-lows-P2-W7-mcp-client` | `e581a3be` | `e581a3be` | no | `7d2b8373` | 0 |
| 8 | W8 `worktree-agent-lows-P2-W8-shell-page` | `26c0cb03` | `26c0cb03` | no | `c42259f8` | 0 |
| 9 | W9 `worktree-agent-lows-P2-W9-workspace-persist` | `a7408560` | `a7408560` | no | `fcb10f5d` | 0 |

Extra branches: none.

## Assembler commits

- `b97ffe66` (R15-CODE-AGENT-028; sidecar/tests/test_web_search.py): W3 deleted services/agent_tools/registry_v0_6_0.py (function inlined into services.agent_tools) but test_web_search_in_catalog_and_registered still imported it (ImportError at collection of that test). Repointed to agent_tools.register_v0_6_0_tools(); assertions unchanged. The test existed at the writers base, so W3 would have hit it on a full run.
- `18e5bcb0` (R15-CODE-AGENT-014 x R15-CODE-AGENT-023; sidecar/services/agent_tools/__init__.py, sidecar/services/mcp_server.py): Semantic conflict (textually clean): W3 made invoke_tool convert any handler exception into {ok:false,error:"unexpected error: ..."}, which made W6 mcp_server._make_catalog_tool ToolError branch unreachable for a raising handler, so W6 test_failing_catalog_tool_returns_is_error would get isError false. Added keyword-only invoke_tool(..., wrap_errors=True); default keeps W3 single-spelling envelope for the agent loop (agent_runtime callers unchanged); mcp_server passes wrap_errors=False so a raise still becomes ToolError/isError. Side effect to verify: provider errors from the handlers W3 stripped of per-handler try/except now reach an MCP client as isError ("tool X raised: ...") instead of an ok:false body.

## Conflict map

All nine merges were textually clean. Two post-merge repairs:

- **sidecar/services/agent_tools/__init__.py + sidecar/services/mcp_server.py** (semantic (no textual conflict); R15-CODE-AGENT-014, R15-CODE-AGENT-023). Intents: W3/R15-CODE-AGENT-014: one {ok:false,error} envelope in invoke_tool for every raising handler; W6/R15-CODE-AGENT-023: a raising catalog tool comes back over MCP as isError via ToolError. Resolution: invoke_tool wrap_errors keyword (default True); MCP catalog tool passes False (`18e5bcb0`).
- **sidecar/tests/test_web_search.py** (stale reference to a module W3 deleted (not a writer-vs-writer conflict); R15-CODE-AGENT-028). Intents: W3/R15-CODE-AGENT-028: delete the pass-through registry_v0_6_0 module; test_web_search (pre-existing): web_search is in the catalog and registered by the v0.6.0 registration. Resolution: call the inlined agent_tools.register_v0_6_0_tools(); same assertions (`b97ffe66`).

## Risk map

**multi_writer_files**: none

**cross_partition_files**: none

**writer_files_changed_on_base_since_writer_base**: none

**base_code_drift_since_writer_base**: 
- sidecar/services/agent_runtime.py (638 lines changed; calls agent_tools.invoke_tool at the tool-dispatch site, which W3 now wraps; its own except Exception fallback "tool X raised:" is now only reached by non-handler failures)
- sidecar/services/planner.py
- sidecar/services/figure_grounding.py (new)
- sidecar/tests/test_agent_runtime.py
- sidecar/tests/test_b3_runtime_intent_gate.py
- sidecar/tests/test_figure_grounding.py
- scripts/r15/*

**safety_surface_hunks_left_out**: none

**safety_adjacent_merged**: 
- src/modules/chat/ProposedChangesReview.tsx (W8, R15-CROSS-PLATFORM-009): tooltip text only, Accept/Reject-all titles now render the keybinding via formatBinding; no change to the proposed-changes store, types/proposed-change.ts or the agent_runtime gate

**rust_or_config_changes**: 
- package.json (W2): new probe:exchanges script; ci-local now uses python3 and "vitest run --coverage" instead of "pnpm test"
- vitest.config.ts (W2, R15-RELEASE-011): v8 coverage with thresholds lines 0 + autoUpdate true, which REWRITES vitest.config.ts when coverage rises; coverage/ is not in .gitignore (W2 issue)
- sidecar/agents/_schema.json (W3, R15-AGENT-072): description text only
- No Rust, tauri.conf.json, CI workflow, or types/plugin.ts change

**boot_path**: 
- sidecar/services/fundamentals_warm.py (W4: boot seeding, start/stop task lifecycle)
- sidecar/services/data_cache.py (W5: stale-get eviction, upgrade-backup pruning)
- sidecar/services/searxng_manager.py (W5)
- sidecar/services/mcp_client.py LocalMcpSubprocess now owns openbb/sec-edgar MCP discovery (W7)
- src/app/page.tsx, src/components/PanelHost.tsx (W8: layout restore, plugin-panel restore gating, panel sizing)
- src/lib/workspace.ts (W9: pagehide keepalive autosave flush, import/export)

**deleted_files**: 
- sidecar/services/agent_tools/registry_v0_6_0.py (W3)
- scripts/render_phase_6_e_screenshots.py, scripts/render_phase_6_sc_screenshots.py (W2)
- docs/screenshots/v0.6.0/teammate-e|teammate-sc READMEs + 6 PNGs moved to docs/mockups/ (W2)
- route GET /sec/filings/{accession}/sections (W7); docs/SIDECAR_API.md still documents it (W7 issue)

**new_modules**: 
- src/lib/panel-sizing.ts (W8)
- sidecar/tests/test_agent_tools_lows.py, test_exchange_financials_negcache.py (new test files)
- src/lib/open-panel-literals.test.ts, src/lib/source-guards.test.ts (repo-wide source scans; any later src/ commit adding a hardcoded command-key glyph string, an SSR/static-export claim, or an openPanel literal of an unregistered id fails them)

**wire_contract_changes**: 
- GET /agents (W3, R15-AGENT-072): "tools" is now the declared specialty list and a new "effective_tools" carries the enforced grant; frontend AgentSummary.tools maps row.tools (src/store/agents.ts rowToSummary) and no src/ reader of .tools was found, but external MCP list_agents consumers see the changed meaning
- types/mcp.ts McpToolCallResult gains structuredContent (W7)
- types/brief.ts BriefDerivedMetrics gains 4 optional keys (W1)
- types/research-space.ts (W9)
- openPanel now returns boolean and resolves enabled modules only (W8, src/store/workspace.ts)

**mirrors**: 
- types/brief.ts <-> sidecar research semantics (W1 pinned by test_emitted_keys_subset_of_brief_ts_mirror)
- types/mcp.ts <-> sidecar mcp_client (W7)

**untested_risky**: 
- Everything is untested pending integration; the two assembler commits were never run.
- W3 x W6 resolution (18e5bcb0): run test_mcp_server.py, test_mcp_catalog_parity.py, test_main_stdio.py, test_no_trading_surface.py, test_agent_tools_lows.py together.
- W3 removed per-handler try/except in 7 handler files: any test that calls a handler directly (not via invoke_tool) and expects an ok:false envelope would now see a raise; run the handler test files (test_macro_tools, test_sec_tools, test_news*, test_earnings*, test_analyst*, test_disclosure*, test_price_data*, test_fundamentals_tool) in the full pytest run.
- W7 provider refactor: test_openbb_mcp_provider.py, test_sec_filings_provider.py, test_sec_nodes.py, test_fundamentals.py (W7 ran them green at its own head).
- W8 + W9 both steer workspace restore/persist (PanelHost/page.tsx vs lib/workspace.ts), no shared file, but a full vitest run is the only check of the combination.
- W2 RELEASE-011 test spawns a child vitest --coverage run; slow and writes coverage/.
- Frontend runs need @tiptap/extension-list in node_modules (W8/W9 issue): pnpm install --frozen-lockfile first or NotesPanel/SettingsPanel/modules tests fail to load.
- W4 note: config._DEFAULT_REGION is IN, so test_fundamentals_warm::test_start_is_idempotent can start real IN network lanes before it stops.

**outcomes_needing_verifier**: 
- R15-LEAD-025 not_a_defect_proposed (W4; pin test only, no code)
- R15-CODE-DATA-019 could_not (W4; needs three frontend test fixtures owned elsewhere; jsonl names sidecar/tests/test_screener.py::test_result_row_has_no_matched_criteria which does NOT exist)
- R15-LIFECYCLE-035 could_not (W5; fix regresses test_search_tiers_router.py sticky-error assertion owned elsewhere; reverted)
- R15-CODE-FRONTEND-027 could_not (W8; refreshCustom error detail landed in 26c0cb03, sidecarRequest switch blocked)
- R15-DOCS-012 fixed with no test by design (W2)
- R15-AGENT-072 changes GET /agents field semantics (W3 flags a frontend follow-up)
- W3 jsonl was reconstructed from git log after a resume (W3 issue): spot-check shas
- W1 and W7 jsonl logs were written inside their worktrees, not the main checkout (only W2-W6, W8, W9 jsonl present here)

## Claimed tests (focused commands, run from the repo root unless the command cds)

### pytest

- sidecar/tests/test_research_semantics.py [R15-CODE-RESEARCH-007, R15-CODE-RESEARCH-011, R15-RESEARCH-036]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_research_semantics.py::test_emitted_keys_subset_of_brief_ts_mirror tests/test_research_semantics.py::test_prompt_keys_cover_every_derived_metric tests/test_research_semantics.py::test_every_leg_returns_facts_and_conflicts`
- sidecar/tests/test_research_hosted_lanes.py [R15-CODE-RESEARCH-008]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_research_hosted_lanes.py::test_both_lanes_map_the_same_status_set_incl_402`
- sidecar/tests/test_agent_tools_lows.py [R15-AGENT-068, R15-CODE-AGENT-014, R15-CODE-AGENT-027, R15-CODE-AGENT-028]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_agent_tools_lows.py::test_no_agent_tools_registry_v0_6_0_module tests/test_agent_tools_lows.py::test_reset_for_tests_restores_every_import_time_tool tests/test_agent_tools_lows.py::test_invoke_tool_wraps_provider_error_with_one_spelling tests/test_agent_tools_lows.py::test_news_tool_failure_uses_the_invoke_tool_envelope_not_its_own_prefix tests/test_agent_tools_lows.py::test_earnings_upcoming_bad_days_returns_range_message`
- sidecar/tests/test_web_search.py [R15-CODE-AGENT-028]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_web_search.py::test_web_search_in_catalog_and_registered`
- sidecar/tests/test_sec_tools.py [R15-CODE-AGENT-015]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_sec_tools.py::test_limit_is_clamped_both_ways`
- sidecar/tests/test_compare_symbols.py [R15-AGENT-069]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_compare_symbols.py::test_one_raising_symbol_yields_one_error_row`
- sidecar/tests/test_market_overview.py [R15-AGENT-069, R15-DATA-101]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_market_overview.py::test_one_raising_quote_yields_one_error_row tests/test_market_overview.py::test_global_region_carries_us_proxy_note`
- sidecar/tests/test_agents_router.py [R15-AGENT-072]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_agents_router.py::test_agents_expose_effective_grant_separately_from_specialty_tools`
- sidecar/tests/test_fundamentals_warm.py [R15-LEAD-025, R15-LIFECYCLE-030, R15-LIFECYCLE-031, R15-LIFECYCLE-032]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_fundamentals_warm.py::test_in_boot_seeds_exactly_once tests/test_fundamentals_warm.py::test_start_stop_clean_no_leaked_tasks tests/test_fundamentals_warm.py::test_one_upsert_failure_counts_the_others tests/test_fundamentals_warm.py::test_boot_window_openbb_call_budget`
- sidecar/tests/test_screener_router.py [R15-CODE-DATA-020]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_screener_router.py::test_internal_error_is_500_formula_error_is_400`
- sidecar/tests/test_screener_india.py [R15-DATA-107, R15-DATA-108, R15-LEAD-029]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_screener_india.py::test_india_symbol_meta_fields_by_name tests/test_screener_india.py::test_sector_master_parsed_once tests/test_screener_india.py::test_nse_lookup_docstring_count_matches_india_all_length`
- sidecar/tests/test_corporate_disclosures.py [R15-CODE-DATA-007, R15-LEAD-017]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_corporate_disclosures.py::test_lane_keyerror_degrades_to_partial_merge tests/test_corporate_disclosures.py::test_shareholding_lane_keyerror_falls_through_to_next_lane tests/test_corporate_disclosures.py::test_duplicate_quarter_rows_collapse_to_one`
- sidecar/tests/test_provider_registry.py [R15-CODE-DATA-008]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_provider_registry.py::test_resolve_sync_keyerror_falls_through_to_next_candidate tests/test_provider_registry.py::test_resolve_async_keyerror_falls_through_to_next_candidate`
- sidecar/tests/test_data_cache.py [R15-CODE-DATA-010, R15-CODE-PLATFORM-077]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_data_cache.py::test_stale_get_evicts_row tests/test_data_cache.py::test_old_upgrade_backups_are_pruned_after_a_successful_backup`
- sidecar/tests/test_exchange_financials_negcache.py [R15-LEAD-020]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_exchange_financials_negcache.py::test_failed_then_succeeded_lookup_stays_stable_within_ttl tests/test_exchange_financials_negcache.py::test_negative_cache_expires_and_serves_the_now_available_filing`
- sidecar/tests/test_earnings_provider.py [R15-DATA-104]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_earnings_provider.py::test_get_upcoming_caps_concurrent_calendar_fetches tests/test_earnings_provider.py::test_get_upcoming_skips_fetch_when_yahoo_circuit_is_open`
- sidecar/tests/test_system_router.py [R15-LIFECYCLE-033]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_system_router.py::test_provider_health_mutations_404_without_rig_hooks_flag tests/test_system_router.py::test_provider_health_mutations_work_with_rig_hooks_flag`
- sidecar/tests/test_searxng_manager.py [R15-LIFECYCLE-034]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_searxng_manager.py::test_setup_write_settings_oserror_reports_error_with_reason`
- sidecar/tests/test_llm_router.py [R15-CODE-AGENT-019, R15-CODE-AGENT-021]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_llm_router.py::test_validate_transport_failure_is_humanized tests/test_llm_router.py::test_no_llm_route_echoes_the_key`
- sidecar/tests/test_mcp_server.py [R15-CODE-AGENT-022, R15-CODE-AGENT-023]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_mcp_server.py::test_status_protocol_version_matches_initialize_handshake tests/test_mcp_server.py::test_failing_catalog_tool_returns_is_error`
- sidecar/tests/test_mcp_client.py [R15-CODE-AGENT-024, R15-CODE-AGENT-025]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_mcp_client.py::test_call_tool_passes_structured_content_through tests/test_mcp_client.py::test_local_mcp_subprocess_resolves_and_decodes_once`
- sidecar/tests/test_sec_filings_router.py [R15-CODE-DATA-013]: `cd sidecar && .venv/bin/python -m pytest -q tests/test_sec_filings_router.py::test_sections_route_is_gone`

All claimed pytest files: `cd sidecar && .venv/bin/python -m pytest -q tests/test_agent_tools_lows.py tests/test_agents_router.py tests/test_compare_symbols.py tests/test_corporate_disclosures.py tests/test_data_cache.py tests/test_earnings_provider.py tests/test_exchange_financials_negcache.py tests/test_fundamentals_warm.py tests/test_llm_router.py tests/test_market_overview.py tests/test_mcp_client.py tests/test_mcp_server.py tests/test_provider_registry.py tests/test_research_hosted_lanes.py tests/test_research_semantics.py tests/test_screener_india.py tests/test_screener_router.py tests/test_searxng_manager.py tests/test_sec_filings_router.py tests/test_sec_tools.py tests/test_system_router.py tests/test_web_search.py`

Collateral (touched-path neighbours, run before the verifier): `cd sidecar && .venv/bin/python -m pytest -q tests/test_mcp_catalog_parity.py tests/test_main_stdio.py tests/test_no_trading_surface.py tests/test_capability_catalog.py tests/test_openbb_mcp_provider.py tests/test_sec_filings_provider.py tests/test_sec_nodes.py tests/test_fundamentals.py tests/test_search_tiers_router.py tests/test_r9_integration_seams.py tests/test_b7_exchange_financials.py tests/test_agent_runtime.py tests/test_macro_tools.py tests/test_fundamentals_tool.py tests/test_research_fast.py tests/test_screener.py`

### vitest

- `pnpm exec vitest run scripts/sidecar-staleness.test.mjs`
  - survives a source file deleted between readdir and stat (TOCTOU, R15-CODE-PLATFORM-061) [R15-CODE-PLATFORM-061]
- `pnpm exec vitest run scripts/smoke-test-sidecars.test.mjs`
  - _httpGetOk (R15-CODE-PLATFORM-062) > a 404 and an offline host (ENOTFOUND-shaped failure) yield different shapes [R15-CODE-PLATFORM-062]
  - _scopedOrphanPreflight (R15-LIFECYCLE-039) [R15-LIFECYCLE-039]
  - _shouldProbeExchanges (R15-RELEASE-008) [R15-RELEASE-008]
  - ci-local's pip installs (R15-CROSS-PLATFORM-010) [R15-CROSS-PLATFORM-010]
  - coverage gate (R15-RELEASE-011) [R15-RELEASE-011]
  - dead Phase-6 screenshot generators stay deleted (R15-CODE-PLATFORM-064) [R15-CODE-PLATFORM-064]
- `pnpm exec vitest run src/store/workflow.test.ts`
  - append a, take, append b -> b still pending [R15-CODE-FRONTEND-026]
- `pnpm exec vitest run src/components/CommandPalette.test.tsx`
  - agent row selection uses agentSummary.id [R15-CODE-FRONTEND-022]
  - custom agent added while open appears [R15-CODE-FRONTEND-029]
- `pnpm exec vitest run src/lib/open-panel-literals.test.ts`
  - resolves to a registered panel [R15-UI-065]
- `pnpm exec vitest run src/store/workspace.test.ts`
  - disabled portfolio: openPanel returns false, no panel added [R15-UI-081]
- `pnpm exec vitest run src/lib/layout-templates.test.ts`
  - equals a registered PanelSpec [R15-CODE-FRONTEND-036]
  - applyLayoutTemplate/applyCustomLayout apply without a rAF flush [R15-AGENT-078]
- `pnpm exec vitest run src/components/PanelHost.test.tsx`
  - fromJSON with a sub-minimum panel grows it [R15-CODE-FRONTEND-025]
  - saved layout with a plugin panel restores intact when the plugin registers after bootstrap [R15-LIFECYCLE-029]
- `pnpm exec vitest run src/lib/source-guards.test.ts`
  - outside src/store/keybindings.ts [R15-CROSS-PLATFORM-009]
  - outside the shrinking allowlist [R15-DOCS-006]
- `pnpm exec vitest run src/store/command-palette.test.ts`
  - no two empty-query rows share a panelId [R15-LEAD-027]
- `pnpm exec vitest run src/store/agents.test.ts`
  - refreshCustom 404 -> customStatus error [R15-CODE-FRONTEND-027]
- `pnpm exec vitest run src/store/settings.test.ts`
  - R15-CODE-FRONTEND-030 [R15-CODE-FRONTEND-030]
- `pnpm exec vitest run src/lib/workspace.test.ts`
  - R15-CODE-FRONTEND-037 [R15-CODE-FRONTEND-037]
  - R15-LIFECYCLE-028 [R15-LIFECYCLE-028]
  - R15-CODE-FRONTEND-028 [R15-CODE-FRONTEND-028]
- `pnpm exec vitest run src/modules/platform/WorkspaceDialog.test.tsx`
  - exports a saved workspace to a .vysted-workspace file and imports it back under a chosen name [R15-UI-070]
- `pnpm exec vitest run src/store/research-spaces.test.ts`
  - R15-CODE-FRONTEND-028 [R15-CODE-FRONTEND-028]

All claimed vitest files: `pnpm exec vitest run scripts/sidecar-staleness.test.mjs scripts/smoke-test-sidecars.test.mjs src/store/workflow.test.ts src/components/CommandPalette.test.tsx src/lib/open-panel-literals.test.ts src/store/workspace.test.ts src/lib/layout-templates.test.ts src/components/PanelHost.test.tsx src/lib/source-guards.test.ts src/store/command-palette.test.ts src/store/agents.test.ts src/store/settings.test.ts src/lib/workspace.test.ts src/modules/platform/WorkspaceDialog.test.tsx src/store/research-spaces.test.ts`

Collateral: `pnpm exec vitest run src/store/modules.test.ts src/components/SettingsPanel.test.tsx src/lib/host-actions.test.ts src/store/agent-spaces.test.ts src/modules/chat`

Non-test claims:
- R15-DOCS-012 (W2): doc hygiene, no pin by design
- R15-CODE-DATA-019 (W4) could_not: no test; claimed node sidecar/tests/test_screener.py::test_result_row_has_no_matched_criteria does not exist
- R15-LIFECYCLE-035 (W5) could_not: no test

## Sanity (touched files only)

- py_compile: OK on all 53 changed .py (before the 18e5bcb0 edit; the two files it touched re-compiled OK after)
- ruff_format_check: 53 files already formatted (sidecar/.venv/bin/ruff); 2 files re-checked after 18e5bcb0: unchanged
- ruff_check: All checks passed
- prettier_check: All matched files use Prettier code style (48 ts/tsx/mjs/json/md files)
- style_commit: none needed

## Integration recipe (after the r15-rc1 tag)

```sh
export GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20"
git fetch --prune origin --tags
git worktree add <scratch>/lows-int-P2 -b lows-P2-int-rc1 origin/worktree-agent-lows-P2-int-4c6dfe8
cd <scratch>/lows-int-P2
git merge-base --is-ancestor 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 r15-rc1   # must succeed
git -c core.hooksPath=/dev/null rebase --rebase-merges --onto r15-rc1 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2   # replays the 9 --no-ff merges + 2 assembler commits; conflicts only if rc1 touched a P2 file after 4c6dfe8 (re-check: git diff --name-only 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 r15-rc1 against the risk_map file list)
# fallback if --rebase-merges is awkward: git switch -c lows-P2-int-rc1b r15-rc1 && git merge --no-ff origin/worktree-agent-lows-P2-int-4c6dfe8
pnpm install --frozen-lockfile   # @tiptap/extension-list missing from node_modules per W8/W9
<run claimed_tests.pytest_all + pytest_collateral, then vitest_all + vitest_collateral, then the chain>
git push origin lows-P2-int-rc1   # then one fresh verifier, then merge --no-ff into 004-r4-experience-rebuild
```
