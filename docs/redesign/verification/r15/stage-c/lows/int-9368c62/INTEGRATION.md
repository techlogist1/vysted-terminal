# lows-int integration (base 9368c626, branch worktree-agent-lows-int-9368c62)

Integrator: Sonnet 5.5. Status: RED (real cross-partition test failures; none edited, skipped or weakened).

## Merge log (first-parent)

| sha | what |
|---|---|
| d6f4ef89 | merge R15-LEAD-116 fix (3acd24dc), clean |
| 8712f3e5 | merge P1 (dbe5fe4f), 4 conflicts |
| 94b82a94 | merge P3 (f9da207a), 7 conflicts |
| b29fff2e | merge P2 (78220d0c), 9 conflicts |
| 1a409a45 | fix: imports both partitions orphaned in routers/fundamentals.py; ruff format tests/test_run_manager.py |
| b016ac26 | fix: sidecarRequestInit no default deadline, sidecarRequest applies the 30 s budget |
| 73ab5881 | fix: brave/mojeek parse hook late-bound |

## Conflicts and resolutions

P1: sidecar/services/research/deep.py (Findings type from P1, hosts docstring); src/lib/host-actions.test.ts (kept undoPreImage import, publishAckStatus is gone); src/modules/watchlist/WatchlistPanel.test.tsx (settings store + defaultSymbolsForRegion; DEFAULT_SYMBOLS unused); src/store/symbols.ts (both region imports).

P3: routers/fundamentals.py (import union, later orphaned, removed); services/search/brave.py + mojeek.py (P3 html_serp refactor kept; 004 challenge-page detection R15-RESEARCH-022 ported into html_serp.py via new challenge_label config field, error text unchanged "Brave: blocked (challenge page)"); tests test_research_relevance / test_run_manager / test_symbol_resolver (both sides' tests kept); src-tauri/src/lib.rs (004 pub(crate) app_data_dir helper with P3's VYSTED_DATA_DIR override folded in; get_app_data_dir stays on the helper).

P2: sidecar/main.py (CACHE_DIR_ENV added, unused workflow_nodes import dropped); services/fundamentals_store.py (get_cache_dir + FieldMeta); services/workspace_store.py (004 replace-retry constants + P2 byte cap / unsafe chars; _MAX_STEM_LENGTH dropped, unused); src-tauri/src/lib.rs (--cache-dir arg and mcp_port_env envs on the one spawn; resolve_cache_dir also honours VYSTED_DATA_DIR so an isolated profile never writes real local app data); src/components/StatusChrome.tsx (bg-caution per R15-UI-073, LEAD-021 comment kept); src/lib/sidecar-client.ts (P2 withDeadline/timeoutMs; 004 default 30 s budget applied in sidecarRequest, sidecarRequestInit stays deadline-free as P2's test pins); CommandPalette.test.tsx, test_corporate_disclosures.py, test_screener.py (both sides kept).

No lockfile conflict; pnpm install --frozen-lockfile clean.

## Safety diff (git diff --stat 9368c626 HEAD -- audit_log.py kill_switch.py kill_switch.rs test_safety_end_to_end.py SAFETY_ARCHITECTURE.md plugin.ts)

    docs/SAFETY_ARCHITECTURE.md | 9 +++++----
    1 file changed, 5 insertions(+), 4 deletions(-)

Only the R15-DOCS-025 AUTO-autonomy sentence (commit 48314633, one sentence replaced). Every other safety path empty.

## ci-local stages (final run, logs/lows-int-ci.log; attempt 1 died on PEP 668 pip install into system python, rerun with the sidecar venv first on PATH)

| stage | result |
|---|---|
| pnpm install --frozen-lockfile | ok |
| ensure-all-sidecars (3 built) | ok |
| eslint + design-token audit | ok |
| prettier --check | ok |
| tsc --noEmit | ok |
| cargo fmt --check | ok |
| cargo clippy -D warnings | ok |
| ruff check / ruff format --check sidecar | ok (453 files formatted) |
| vitest run --coverage | FAIL, EXIT 1: 3 failed, 2028 passed (2031), 166/169 files |
| cargo test (run separately, chain stops at vitest) | ok, 31 passed |
| pytest (run separately) | FAIL, EXIT 1: 16 failed, 3905 passed, 1 skipped |

CI_EXIT=1. Smoke (scripts/smoke-test-sidecars.mjs): SMOKE_EXIT=0, all three sidecars booted cleanly.

## Failing ids and cause

Vitest (3):
- src/modules/quant/OptionPricerPanel.test.tsx R15-CODE-PLATFORM-041 steps-below-floor and src/modules/quant/YieldCurvePanel.test.tsx R15-UI-077 duplicate pillar: P3 added them asserting vi.mocked(fetch), P2 moved the file's mocks to sidecarRequest (R15-CODE-FRONTEND-027). Stale transport in the P3 assertion. P2 x P3.
- src/modules/agent-builder/agent-builder.test.tsx "POSTs the payload and refreshes the list on save": P2's agents store now awaits sidecarRequestInit before fetch, so the panel's tool-ids fetch consumes the test's mockImplementationOnce([]) and no tool buttons render. P2 store x existing test (P1 touched the panel, R15-UI-003).

Pytest (16):
- test_corporate_disclosures (6: test_explicit_bo_pin_on_a_different_company_takes_the_bse_company_in_every_lane x5, test_bo_pin_keeps_same_company_and_bare_behaviour), test_disclosure_tools::test_class_case_deals_and_actions_gate_the_same_way_amal_bo_still_served: `_instrument_nse() missing 'band'`. LEAD-116 fix tests vs P3 R15-CODE-DATA-017 (band now required).
- test_symbol_resolver (test_current_name_beats_an_identical_former_name_kpit, test_former_name_coincidence_binds_the_current_name_holder): `Resolution.needs_disambiguation` gone. P3 resolver change vs existing tests.
- test_research_deep (3 test_run_researcher_drops_*): `deep._run_researcher` no longer exists. P1 research refactor vs P3-era tests.
- test_research_module_boundary: sonar.py imports `perplexity._domain_of` (private) after P2 R15 Sonar lane collapse (feba1762), plus one more ResearchLane import.
- test_search_registry::test_resolve_ddg_is_unconditional_keyless_floor: P3 registry change (7d6be0f4, duplicate ddg pacing removed) wraps the backend in _PacedBackend.
- test_tests_encoding: read_text()/write_text() without encoding= in test_agents_router.py:84 (P2), test_backtest_lows.py:146 (P1), test_india_sector_map.py:130/148 (P3), test_llm_lows.py:34 (P3), test_provider_health.py:135 (P2). Guard test vs new tests from three partitions.
- test_workspace::test_any_name_round_trips[a%41]: P2 R15-UI-082 encodes % but the load path unquotes to "aA"; workspace_store x existing test (c10c274a).

Fixed during integration (mechanical): test_b7_research_result_limit brave/mojeek (2 ids) went green after late-binding the parse hook.

## Round 2

- Merges (--no-ff, in order): fix-A 3af0502c (840d5ea9), fix-B 1e924996 (0f5ac5db), fix-C 0f1c0074 (8597d991). No conflicts.
- Encoding pass: test_tests_encoding.py named new test files; explicit encoding= added (3ecb019d). ruff format on sidecar/tests/test_agents_router.py (92fb7d40).
- Safety diff vs 9368c626: docs/SAFETY_ARCHITECTURE.md (R15-DOCS-025 AUTO_APPLIED_KINDS sentence only, 5+/4-) and src/store/proposed-changes.ts (R15-CODE-FRONTEND-034, lead-ruled equivalent ack-status refactor, 3+/4-). types/proposed-change.ts, test_no_trading_surface.py, types/plugin.ts: empty.
- Chain: single pnpm ci-local invocation, EXIT=0. Stages: install, ensure-all-sidecars, lint+token audit, prettier (453 files formatted), tsc, cargo fmt, clippy, ruff (all checks passed), vitest 169 files / 2031 tests passed, cargo test 31 passed, pytest 3921 passed 1 skipped.
- Smoke: node scripts/smoke-test-sidecars.mjs EXIT=0 (3 sidecars, /agents roster 13, mcp toolCount 39).
- Logs: logs/round-2/. Status green.
