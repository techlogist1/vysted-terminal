# P2 lows pre-integration candidate

Assembled 06:57 IST. Untested pending integration (no pytest/vitest/tsc/cargo/build run, per the off-lane rule).

- Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (writers cut from `ebc5ed4194f9362422c3178c27d4cdf946428968`, an ancestor)
- Branch: `worktree-agent-lows-P2-int-4c6dfe8` (pushed, ls-remote verified)
- Head: `7db0b2954bab647e646b324df1c875c9c34f1675` (07:29 IST, after the extra-branch pass below; was `18e5bcb0` at assembly, `d7d0d325` after the fix pass)
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

Extra branches: four, merged last (see "Extra-branch pass" at the end).

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

## Fix pass (07:05-07:06 IST, Opus, one bounded pass)

Candidate `worktree-agent-lows-P2-int-4c6dfe8` moved 18e5bcb0 -> d7d0d325 (pushed, no force; ls-remote = d7d0d3254dfebf89b882c51ea22d9de464048c5e). Tests edited as source only, never run: untested pending integration. Checks run: py_compile + ruff format/check on the .py file, prettier --check and node --check on the touched JS/JSON files.

Applied (blocking):
- 1ebaf89b R15-LIFECYCLE-033: `sidecar/tests/test_provider_health.py::test_system_provider_health_routes` takes `monkeypatch` and sets `VYSTED_RIG_HOOKS=1` before the trip call. Assertions unchanged.
- 09821a53 R15-CODE-PLATFORM-062: in `scripts/smoke-test-sidecars.mjs` the main guard is now `process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href`, so it is portable to Windows and to percent-encoded paths.
- 42b3c679 R15-RELEASE-011: the coverage-threshold pin test in `scripts/smoke-test-sidecars.test.mjs` now runs `process.execPath node_modules/vitest/vitest.mjs ...`, with no .bin shim, and has an explicit 90_000 ms it() timeout. Assertions unchanged.

Applied (advisory, trivial):
- bb945754 R15-RELEASE-011: `coverage/` added to .gitignore and .prettierignore, and `coverage/**` added to the eslint ignores.
- d7d0d325 R15-AGENT-072: the `sidecar/agents/_schema.json` tools description now names `tools` + `effective_tools` in place of `declaredTools`.

Left (advisory):
- thresholds.autoUpdate ratchet rewriting vitest.config.ts on every run: this is an operator decision (commit the ratchet, or have ci-local pass autoUpdate=false).
- ci-local vs test.yml drift (`--coverage`, python3 Store stub on Windows): check this on the ROG box, not here.
- Rig impact of R15-LIFECYCLE-033: the rig sidecar and scripts/r15/route_fuzz.py need `VYSTED_RIG_HOOKS=1`. Notify the rig owner. No code change here.
- W3 x W6 isError CHANGELOG line: CHANGELOG is written at integration, so it is left for the integrator.
- R15-AGENT-068, R15-LIFECYCLE-030, R15-CODE-DATA-008, R15-CODE-DATA-010: these are intended behavior changes. Nothing to fix.
- W7 SIDECAR_API.md stale sections route: at d7d0d325 no `accession` or `sections` route appears in docs/SIDECAR_API.md, so there is nothing to remove.
- types/*.ts effective_tools mirror: this is a contract addition, left for the integrator or operator.
- source-guards / open-panel-literals cross-partition risk: integrate P2 last or re-check on the combined tree.
- Collateral: add tests/test_provider_health.py to pytest_collateral, and run pnpm install --frozen-lockfile before vitest.

## Extra-branch pass (07:25-07:29 IST, Opus)

Continued from the pushed candidate `d7d0d325` (worktree state reused). `git fetch --prune`: all nine set heads on origin still equal WRITERS.json `head_sha_origin` (no mismatch). Candidate moved `d7d0d325` -> `7db0b295`, pushed without force, ls-remote = `7db0b2954bab647e646b324df1c875c9c34f1675`. Nothing run beyond py_compile, ruff and prettier: untested pending integration.

| # | branch | entries | origin head | merge sha | conflicts |
|---|---|---|---|---|---|
| 10 | `worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` (after W4) | R15-CODE-DATA-019 | `31aa053b` | `260074ef` | 0 |
| 11 | `worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` (after W5) | R15-LIFECYCLE-035 | `954ffa89` | `d145842b` | 0 |
| 12 | `worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` (after W8) | R15-CODE-FRONTEND-027 | `cba8df9f` | `552ab6f0` | 0 |
| 13 | `worktree-agent-lows-DEF-B-4c6dfe8` | R15-CROSS-PLATFORM-012, R15-UI-068, R15-UI-071, R15-UI-073, R15-UI-082 | `af933bcc` | `4e6eee82` | 0 |

Blocked hunks: none (no extra branch touches audit_log.py, kill_switch.py/.rs, types/proposed-change.ts or agent_runtime.py).

### Assembler commits

- `4c7b6dde`, `ed0837b3`: each extra branch adds its own `RESULT.md` at the repo root (a four-way add/add, and a report does not belong in the product root). Moved byte-identical to `docs/redesign/verification/r15/stage-c/lows/P2/results/<entry>.md` right after each merge.
- `e9da8e93` (R15-CODE-FRONTEND-027): folded the CN writer's second `@/lib/sidecar-client` import in `src/store/agents.ts` into one, as its RESULT asked once both landed; RESULT.md moved.
- `7db0b295` (R15-UI-073): `src/lib/warning-token-scope.test.ts` scans every src .ts/.tsx including itself, and its own comments and regex contain `text-warning`/`bg-warning`/`border-warning` while it is not allowlisted, so the offenders assertion always lists the test itself (fails at the DEF-B head alone). One filter skips its own path; assertions unchanged. DEF-B RESULT.md moved.

### Conflict map (all textually clean; read for semantics)

- `sidecar/services/searxng_manager.py` (W5 R15-LIFECYCLE-034, CN R15-LIFECYCLE-035, DEF-B R15-CROSS-PLATFORM-012). W5's catch-all setup error goes through `_set()`, which now also records `last_error`; `setup()` clears `last_error` before W5's try. DEF-B only moves `settings_dir`. Composable, no edit.
- `src/store/agents.ts` + `agents.test.ts` (W8 partial, CN full R15-CODE-FRONTEND-027): CN's 72daa055 is a `-x` cherry-pick of W8 26c0cb03, so git merged it identically; `refreshAll` stays removed (W8) with no remaining reference.
- `src/store/workflow.ts` + `workflow.test.ts` (W8 R15-CODE-FRONTEND-026 `takeNotifications`, CN R15-CODE-FRONTEND-027 shared transport): both kept, both writers' tests present.
- `sidecar/services/data_cache.py` (W5 R15-CODE-DATA-010/R15-CODE-PLATFORM-077, DEF-B cache dir): no edit; see risks.
- `package.json` (W2 scripts, DEF-B devDeps), `eslint.config.mjs` (bb945754 ignores, DEF-B jsx-a11y), `SettingsPanel.tsx`/`PluginManagerPanel.tsx` (earlier sets, DEF-B `text-caution`): no edit.

### Risks the extras add (integrator: read first)

1. **Blocking for the chain: lockfile.** DEF-B adds `eslint-plugin-jsx-a11y` and `vitest-axe` to package.json devDependencies but `pnpm-lock.yaml` has no entry for either, so `pnpm install --frozen-lockfile` (ci-local step 1, CI) fails. Run `pnpm install --lockfile-only` on the rebased branch and commit the lockfile before the chain (package install is off-lane here).
2. **Upgrade backup root (DEF-B x W5).** `data_cache._backup_data_dir` takes `_db_path.parent` as the data dir. With `--cache-dir` set, the pre-upgrade backup (and W5's pruning) copies the cache dir, not the user data dir (portfolio, notes, workspaces, audit DB). Diverges only where `app_local_data_dir != app_data_dir` (Windows). Needs a decision: back up `get_data_dir()` explicitly.
3. **Cross-partition conflicts introduced by the extras.** `git merge-tree` of the new head: vs P1 candidate `dbe5fe4f` conflicts in `sidecar/services/workspace_store.py` and `src-tauri/src/lib.rs`; vs P3 candidate `6e41bfc1` conflicts in `sidecar/main.py`, `sidecar/services/fundamentals_store.py`, `src/components/StatusChrome.tsx`, `src/lib/sidecar-client.ts`; vs `worktree-agent-lows-CN-r15-data-102-4c6dfe8` in `fundamentals_store.py`. The pre-extras head `d7d0d325` merged clean with both P1 and P3. `sidecar-client.ts` is a semantic duplicate: P3 R15-LIFECYCLE-027 bounds every request with a timeout, and CN-027 adds `timeoutMs` + `SIDECAR_REQUEST_TIMEOUT_MS`. Collapse them into one deadline mechanism when the second one lands.
4. **Rust untested.** `src-tauri/src/lib.rs` `resolve_cache_dir` + `--cache-dir` was never compiled, and rustfmt/clippy were not run.
5. **Lint gate widened.** The `jsx-a11y/label-has-associated-control` rule (error level, all .ts/.tsx) was audited only on SettingsPanel inputs. `pnpm lint` over src is unverified.
6. **SearXNG settings moved to the cache dir** with no migration. An existing Windows container keeps its old mount.
7. **Writer-changed tests (recorded, not weakened by the assembler):**
   - CN-019 dropped the `[0, 1, 2]` matched_criteria assertion in test_screener (the field is deleted).
   - CN-027 moved the quant store and panel tests to mock `sidecarRequest`, and quant.test's error case now expects the server sentence.
   - DEF-B retargeted the DataTable sort test from the `<th>` to its new button.
8. CN-027's `AbortSignal.any` path needs Safari 17.4+ in WKWebView; no current caller hits it.
9. CN-035: polls in error state and the throttled hot path now run docker CLI probes; `last_error` has no frontend reader.

### Outcomes superseded

- R15-CODE-DATA-019: W4 could_not -> CN fixed_untested (a1539309).
- R15-LIFECYCLE-035: W5 could_not -> CN fixed_untested (3da1e972).
- R15-CODE-FRONTEND-027: W8 partial -> CN fixed_untested (72daa055 + f8d6594f).
- DEF-B: R15-CROSS-PLATFORM-012, R15-UI-073 and R15-UI-082 are fixed_untested. R15-UI-071 is fixed as a gate. R15-UI-068 is split: the primitive is fixed_untested and the table porting is deferred_feature.

### Additional claimed tests (focused commands; the full lists are in PREINT.json claimed_tests)

- `cd sidecar && .venv/bin/python -m pytest -q tests/test_screener.py::test_result_row_has_no_matched_criteria` [R15-CODE-DATA-019]
- `cd sidecar && .venv/bin/python -m pytest -q tests/test_searxng_manager.py::test_hand_fixed_container_supersedes_a_sticky_error tests/test_searxng_manager.py::test_error_stays_sticky_while_the_container_is_not_serving tests/test_searxng_manager.py::test_hot_path_reprobes_a_sticky_error_on_a_throttle` [R15-LIFECYCLE-035] (collateral: `tests/test_search_tiers_router.py::test_setup_failure_is_observable_through_the_status_poll`)
- `cd sidecar && .venv/bin/python -m pytest -q tests/test_cache_dir.py` [R15-CROSS-PLATFORM-012]
- `cd sidecar && .venv/bin/python -m pytest -q tests/test_workspace.py::test_a_32_char_devanagari_name_saves tests/test_workspace.py::test_a_name_whose_encoded_bytes_exceed_the_cap_is_still_rejected` [R15-UI-082]
- `pnpm exec vitest run src/lib/sidecar-client.test.ts src/store/workflow.test.ts src/modules/node-editor/schedule-control.test.tsx src/store/agents.test.ts src/store/quant.test.ts src/modules/quant src/modules/node-editor/NodeEditorPanel.test.tsx` [R15-CODE-FRONTEND-027]
- `pnpm exec vitest run src/modules/screener/ScreenerPanel.test.tsx src/modules/screener/ScreenerResultsTable.test.tsx src/store/screener.test.ts` [R15-CODE-DATA-019 fixture edits]
- `pnpm exec vitest run src/components/DataTable.test.tsx` [R15-UI-068]
- `pnpm exec vitest run src/components/SettingsPanel.test.tsx` [R15-UI-071 axe smoke] + `pnpm lint` [R15-UI-071 rule]
- `pnpm exec vitest run src/lib/warning-token-scope.test.ts` [R15-UI-073]
- `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test` (manifest src-tauri) [R15-CROSS-PLATFORM-012 lib.rs]

### Sanity (the 50 files the extras and new assembler commits touch)

- py_compile: OK on 12 .py
- ruff format --check: 12 files already formatted
- ruff check: all passed
- prettier --check: 37 ts/tsx/json/md/css files clean
- No style commit needed. lib.rs was not checked (cargo is off-lane).

### Integration recipe delta

The recipe is the same as above except for these points:

- Worktree from `origin/worktree-agent-lows-P2-int-4c6dfe8` @ `7db0b295`.
- `--rebase-merges` now replays 13 merges plus 11 assembler/fix commits.
- Before `pnpm install --frozen-lockfile`, run `pnpm install --lockfile-only` and commit `pnpm-lock.yaml`.
- If P1 or P3 lands first, expect the conflicts in risk 3.
- Add `pnpm lint` and the cargo trio to the focused runs.
