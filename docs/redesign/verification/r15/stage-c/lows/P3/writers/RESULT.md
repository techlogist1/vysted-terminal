# R15-AGENT-077 second attempt (CN, base 4c6dfe8c)

- Entry: R15-AGENT-077 (tool-arg repair round and native-search oneshot rebuilt the adapter without the configured base_url)
- Outcome: fixed_untested
- Stamped: 06:50 IST

## Commits

- e7c9adc0: cherry-pick -x of 0e5e72e5 (prior W2 branch): base_url kwarg on oneshot.complete / complete_with_usage and native_search_oneshot, threaded into get_provider; openai.py repair round passes self.\_base_url; acceptance test test_llm_openai.py::test_repair_round_keeps_configured_base_url.
- ef9e04cd: the two get_provider fakes that pinned a narrower signature than the real get_provider now accept `**_k` (tests/test_research_metering.py:114 `lambda _p`, tests/test_b5_runtime_synthesis.py:55 `lambda *_a`), assertions unchanged; new test_native_search.py::test_native_search_oneshot_keeps_the_callers_base_url.

## Files

sidecar/services/llm/oneshot.py, sidecar/services/llm/native_search.py, sidecar/services/llm/openai.py, sidecar/tests/test_llm_openai.py, sidecar/tests/test_research_metering.py, sidecar/tests/test_b5_runtime_synthesis.py, sidecar/tests/test_native_search.py

## Verification done

py_compile, ruff format --check, ruff check on all touched files: clean. Sequential merge simulation (base + origin/worktree-agent-lows-P3-W2-llm-chat, then this branch) via git merge-tree: clean.

## Untested pending integration

No test was run (off-lane rule). Audit of every get_provider fake patched on the oneshot module or services.llm package: all others already take `**kwargs` or base_url=None. complete_with_usage fakes in test_llm_openai.py take `**_k` or base_url; the one in test_research_metering.py:89 is reached only from deep_research, which passes no base_url.

## Risks

Latent-only per the refuter: no shipped surface sets a custom base_url on the agent path (agent_runtime and deep_research call without one), so behaviour is unchanged today. The native_search_oneshot base_url has no production caller yet.

---

# R15-DATA-102 second attempt (CN) - RESULT

- entry: R15-DATA-102 (partition P3, prior set W3, prior outcome could_not)
- outcome: fixed_untested
- branch: worktree-agent-lows-CN-r15-data-102-4c6dfe8 (base 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2)
- stamped: 06:57 IST

## Commits

- a84cb868 cherry-pick -x of 858ed56e (prior W3 store part: growth_basis column,
  per-tier field_meta in row_to_pair, yfinance states mrq_yoy). Carried WITHOUT its
  sidecar/tests/test_fundamentals_store.py hunk: that hunk is textually entangled with
  the R15-DATA-103 test from 22d4a619 and conflicts when this branch merges after the
  prior branch. The test reaches the candidate verbatim via the prior branch.
- 94185b4d model default flip + consumers + the tests that pinned the inherited default.
- 975cc181 legacy-row store test (appended at file end; merges clean).

## Files

- sidecar/models/fundamentals.py: growth_basis default "mrq_yoy" -> None; producer states it.
- sidecar/services/correctness_gate.py: overlay_filed_periods serves filed MRQ-YoY growth
  over a stated mrq_yoy OR an unstated basis (was: only the inherited default), and states
  growth_basis="mrq_yoy" when it serves. Without this the flip would silently drop filed
  growth on an Indian listing Yahoo served none for. annual_yoy is still never overlaid.
- sidecar/services/growth_check.py: should_cross_check requires a STATED mrq_yoy.
- types/data.ts: growth_basis doc (no shape change).
- (cherry-picked) sidecar/services/fundamentals_store.py, sidecar/services/yfinance_provider.py.

## Tests written (source only, none run: off-lane rule)

- test_b7_exchange_financials.py::test_filed_growth_states_mrq_yoy_and_never_overrides_an_annual_basis (acceptance, new)
- test_fundamentals.py::test_served_growth_states_its_mrq_yoy_basis (new)
- test_fundamentals.py::test_get_fundamentals: fixed; asserted "mrq_yoy" on a fake that serves
  no growth (the inherited claim); now asserts no basis stated.
- test_fundamentals_tool.py::test_tool_result_carries_growth_basis: fixed; fake producer states the basis.
- test_growth_check.py: two gate tests fixed; the absent-basis case flips True -> False.
- test_fundamentals_store.py::test_row_to_pair_growth_without_a_recorded_basis_states_none (new)
- via prior branch: test_fundamentals_store.py::test_row_to_pair_null_growth_row_states_no_basis_and_derives_field_meta

## Untested pending integration

All of the above. Only py_compile + ruff format/check (touched Python) and prettier --check
(types/data.ts) were run. Simulated candidate merge (base + prior W3 branch, then this branch)
is conflict-free (git merge-tree exit 0) and the merged Python files compile.

## Risks

- Any unseen fixture that builds Fundamentals with growth and relies on the default basis
  now gets None (grep of sidecar/tests found only the three fixed above).
- Legacy store rows (growth, NULL basis column) now state no basis until the next .info refresh.
- Adjacent, not changed here: research/semantics.py and company_narrative.py label growth
  "quarterly YoY (MRQ)" unconditionally and never read growth_basis, so a yfinance
  annual_yoy fallback figure is labelled MRQ there. Unfiled; independent of the default.
- field_meta stays Optional on the contract (openbb-mcp / v7 rows still emit none of their own);
  the entry's fix_shape scopes field_meta to row_to_pair only.

---

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

---

# R15-LEAD-036 lows writer result (06:54 IST)

- Outcome: fixed_untested (untested pending integration; no test was run, off-lane rule).
- Not the signed-off local-model class: this is guard replacement formatting (defect_class guard-replacement-formatting), not a figure stated with no ok tool call.
- Base 4c6dfe8c; branch worktree-agent-lows-LEAD-036-4c6dfe8; fix commit 500cd050.
- Open shape fixed: batch-22/23 cross-round fence (b22v_crossround.py): a fence opened in round 1 before a tool call stayed open when round 2's note streamed.
- Root cause: \_consume_round judged each release with no knowledge of a fence an earlier release (often an earlier round) left open.
- Fix (sidecar/services/agent_runtime.py): \_TurnState.fence carries (prefix, closer) of the fence released prose left open; \_release judges the next release with the opener line prefixed (the hold point too); new \_carry_fence strips the already-streamed prefix from kept output, prepends the closer before a replacing note, and holds back an opener whose body is still blank so a replaced block leaves no fence at all.
- Tests as source (sidecar/tests/test_agent_runtime.py, end of file): test_a_fence_opened_before_a_tool_call_leaves_no_marker_when_replaced (` ``` ` and `~~~`, the b22v_crossround shape), test_a_streamed_fence_is_closed_before_the_next_rounds_note (` ``` ` and `~~~`), control test_a_fence_continued_on_an_ok_result_streams_as_written.
- Checks run: python3 -m py_compile, ruff format, ruff check on the two touched files.
- Risk for the verifier: the held empty opener now makes round 2's rows a fenced block judged by the fence path (\_judge_clause on the body) instead of row by row; an empty unclosed fence at turn end is now dropped instead of streamed.
