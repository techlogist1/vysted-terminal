# Lows P1 pre-integration review

- Reviewer: Opus (claude-opus-5-5[1m]), read-only, fresh context
- Candidate: `worktree-agent-lows-P1-int-4c6dfe8` @ dbe5fe4f15f1aca12273038a9ef61c66497513ec (fetched; matches the assembler's ls-remote)
- Base: 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 (writers W1-W9 cut from ebc5ed41; CN research-005, CN agent-031 and DEF-A cut from the base)
- Diff: 113 files, +3588 / -1033
- Stamp: 07:36 IST
- Status: untested pending integration. No pytest, vitest, cargo, tsc or eslint was run (off-lane rule). Only py_compile and ruff ran, on a `git archive` extract of the candidate in scratchpad.
- Supersedes the 07:07 IST review of 70fe85c9. Its one blocker, the R15-UI-076 fixture ripple, is fixed in a642caac. The fixture suites now seed `defaultSymbolsForRegion("US")` / `defaultChartSymbolForRegion("US")`, and settings/workspace expect `^NSEI`.

## Verdict: ready

## Blocking

None.

## Checks

**(a) Safety surface.** `git diff --stat base...candidate` shows no change for any of these four files:
- `sidecar/models/audit_log.py`
- `sidecar/services/kill_switch.py`
- `src-tauri/src/kill_switch.rs`
- `types/proposed-change.ts`

W2 does change `sidecar/services/agent_runtime.py`. I read every hunk:
- the `_STAGEABLE_PLAN_ACTIONS` derivation
- the generated preamble tool list
- the 3-arg `_resolve_model`
- `_tool_timeout_seconds` via `timeout_from_args`

None of them edits the proposed-changes gate. `_STAGEABLE_PLAN_ACTIONS` is read in one place only, `:1731`, and that is the advisory `staged` flag on plan-pre-pass steps. `_READ_SAFE_PANEL_ACTIONS` is unchanged. The preamble still carries the no-brokerage rule ("you cannot place, stage or simulate trades", `agent_runtime.py:166`), so dropping that sentence from copilot.json loses nothing. No blocked hunks.

**(b) Claimed tests.** Every test in PREINT.md exists as source on the candidate:
- pytest: all 28 named defs grep-confirmed (`^(async )?def <name>(`), plus the new `test_research_module_boundary.py` with both of its tests.
- cargo: all 10 named fns present (8 in `lib.rs`, 2 in `keychain.rs`).
- vitest: all 16 claimed titles or strings found; the 5 whole-file suites exist.

Spot-checked that the assertions test what each entry says:
- `test_provider_override_without_model_uses_provider_default` (R15-AGENT-073)
- `test_every_tool_named_in_prompts_resolves_in_catalog` (R15-AGENT-071)
- `test_agent_system_prompts_within_byte_budget` (R15-CODE-PLATFORM-076)
- `test_runs_rows_carry_only_snake_case_keys` and `test_launch_rejects_a_camel_case_budget` (R15-CODE-AGENT-031)
- `test_shared_round_helpers_are_public_deep_exports` (R15-CODE-RESEARCH-005)
- the DEF-A `arrange_layout pattern=focus resolves a panel ALIAS` test, whose "Focused on Screener" matches `host-actions.ts:1626`

I also re-ran two of those checks by hand, statically, without running the tests:
- The snake_case-name regex over all 13 agent JSONs against the 56 catalog ids finds no unknown names. Every prompt is at or under 4608 bytes; copilot is 4382.
- The 33 read_handler capabilities minus `{backtest_summary, run_custom_backtest}` give exactly the 31 ids pinned in `_MCP_EXPOSED`.

**(c) Conflict resolutions.** There were no textual code conflicts. The only collision was the root `RESULT.md` add/add, and leaving it out drops no code. For each file two writers touched, I checked that every non-blank line the writer added is present in the candidate:

| Writer | Files | Lines missing |
|---|---|---|
| W3 `dd1ceed2` (vs ebc5ed41) | deep.py, iter.py, test_research_deep.py, test_research_depth.py, host-actions.test.ts | 0 |
| CN research-005 `113ab130` (vs base) | deep.py, iter.py, test_research_deep.py, test_research_depth.py | 0 |
| W6 `104d96a5` | delegate-runs.ts, delegate-runs.test.ts | 0 |
| CN agent-031 `695e934a` | delegate-runs.ts, delegate-runs.test.ts | 0 |
| DEF-A `8113ddc1` | host-actions.test.ts | 2 |

The 2 DEF-A lines are the `expect(...)` wrap that dbe5fe4f re-flowed with prettier. The expectation is identical. Writer origin heads match ls-remote: W3 dd1ceed2, W6 104d96a5, CN 113ab130 and 695e934a, DEF-A 8113ddc1.

**(d) Defects, imports and contracts.**
- **Research rename.** No old private name (`_safe_llm`, `_emit_step`, ...) remains anywhere under `sidecar/`, in code or in monkeypatch strings. I checked by AST that every `from services.research.deep import X` and every `deep.X` / `"services.research.deep.X"` resolves to a module-level name in `deep.py`. The `setattr(deep_research, ...)` targets (`_run_loop`, `_run_native`, `run_deep_brief`, `_LOCAL_LLM_CALL_TIMEOUT_SECS`) live in `agent_tools/deep_research.py` and all still exist.
- **Runs wire.** It is consistent end to end:
  - `runs_store` builds the models with snake kwargs and already persisted `model_dump()` without aliases, so old rows still validate under `extra="forbid"`.
  - The frontend launch body (`delegate-runs.ts:158-176`) is snake_case, and `RunWire` / `RunOutputWire` are snake-only.
  - No other sidecar or `src/` reader of the runs camelCase keys remains. The remaining `runId` hits belong to the backtest and workflow models.
  - There is no `types/*.ts` mirror of the run models. The module docstring now says so.
- **Backtest events.** `BacktestRunEvent` drops the `trade` kind and `equity`. `types/backtest.ts` is updated in the same change, and no src or test reader of either remains.
- **`_resolve_model`.** The ValueError is unreachable today: all 8 `LLMProviderId` values have a `default_model` in `config/model_registry.json`. Both call sites use the 3-arg form.
- **`proposed-changes.ts`.** The ack now uses `ApplyResult.status`. `ok = status !== "failed"` is equivalent to the old `label !== null`, because `fail()` is the only constructor that returns `label: null`. `publishAckStatus` has no remaining importer.
- **Rust.**
  - `app_meta_get` / `app_meta_set` are registered (`lib.rs:627-628`).
  - `write_text_atomic` / `write_bytes_atomic` stay registered as thin wrappers over `write_atomic`.
  - The MCP port env is now `""` when a child is unavailable. Both Python providers treat an empty value as "not running" (`if not port`).
  - `no_env_mutation_in_src` reads `src-tauri/src` without recursing. It holds only flat `.rs` files today.
  - `sidecar_healthy` matches `"service":"vysted-sidecar"`, which Starlette's compact JSON does emit (`routers/health.py:29`).
- **Structure.** No top-level name is duplicated in any changed ts/tsx/mjs file. The four deleted `_ensure_schema` functions have no remaining callers. `_dual_case` and the two renamed runs tests are referenced nowhere.
- **Sanity.** py_compile passes on all 49 changed .py files. `ruff check sidecar` passes and `ruff format --check sidecar` reports 446 formatted, both run from the extract with `sidecar/ruff.toml`.

## Advisories (integrator: where to look first if the chain goes red)

1. **cargo fmt / clippy / test (W7, highest uncompiled surface).** `lib.rs` is +380/-83, and `keychain.rs`, `openbb_mcp.rs` and `sec_edgar_mcp.rs` also changed. Nothing here has been compiled.
   - Run clippy with `-D warnings` first.
   - Watch the `spawn_boot` generic signature change: `A`/`B` now return `(Option<u16>, S*)` and `M` takes two ports. Its call site and any test that builds a `spawn_boot` must match.
   - Watch the `while let Err(err) = rename` retry loop for `clippy::significant_drop_in_scrutinee`, which the W7 clippy line enables with `-W`.
2. **pytest, model resolution (R15-AGENT-073).** A run that overrides only the provider now uses that provider's registry default. Before, it used copilot's `qwen2.5:7b`. Any test that runs copilot with `provider="anthropic"|"openai"|...` and `model=None`, and then asserts on the model name, native-search gating or spend pricing, will see a different model. I found none by grep; `test_runtime_phases` builds its own setup with ollama. This is still the first place to look if an agent-runtime test flips.
3. **Runs contract is now snake_case only (CN agent-031).**
   - A camelCase launch body now returns 422, and FastAPI's default 422 body echoes the offending `input`. An `apiKey` sent camelCase would come back in the response on loopback. This class of leak already existed for any unknown key under `extra="forbid"`; the only caller sends `api_key`.
   - Fix if wanted: a `RequestValidationError` handler that strips `input` from the error body.
   - The test inversion `test_launch_accepts_snake_case_run_budget` -> `test_launch_rejects_a_camel_case_budget` matches the entry's intent ("one spelling; never a silently dropped limit"). It is a real behavioural pin, not a weakened test.
   - Lead: the CLAUDE.md gotcha "`GET /runs` emits BOTH camelCase + snake_case" is now false. That file is Tier-1, so the lead edits it.
4. **Exact-set pins will fail on upstream additions.** Integrating onto a tag that adds any of the following will fail its pin. That failure is the intended signal, not a regression; name the new entry explicitly.
   - a read_handler capability: `test_mcp_projection_is_explicit_per_entry` (31 ids)
   - a run-model field: `_SUMMARY_KEYS` / `_DETAIL_KEYS` in `test_runs_router`
   - an agent JSON prompt over 4608 bytes: `test_agent_system_prompts_within_byte_budget`
   - an agent prompt naming a non-catalog snake_case word: `test_every_tool_named_in_prompts_resolves_in_catalog`

   P2 and P3 should be checked against these pins after the three-way merge.
5. **Copilot prompt trim (R15-CODE-PLATFORM-076 / R15-AGENT-071).** The trim drops explicit routing prose for these tools:
   - `write_screener_filters`: stage vs `screener_run`
   - `add_chart_drawing`
   - `arrange_layout(pattern='custom')`
   - close / focus panel
   - the compare layout

   The generated preamble list and the tool descriptions now carry that routing. The A/B check was a single qwen2.5:7b sample. This is a behavioural risk for the rc1 scenario battery, not for ci-local.
6. **vitest, R15-UI-076 default region.** The six suites seeded in a642caac are the known ripple. Other `"SPY"` hits I sampled seed their own state explicitly: command-palette, ChatSidebar, notes, backtest, context-provider, chart-command and BacktestPanel. If a vitest failure names `^NSEI` / `RELIANCE.NS`, fix the fixture seed; never loosen the assertion.
7. **Portfolio restore (W5 `validateHolding`).**
   - `normalizeHolding` now drops, on restore, any persisted holding with quantity above `1e12`. A very large meme-coin lot could plausibly exceed that.
   - It also drops a persisted blank `costBasis`, which was coerced to 0 before.
   - Both drops are silent. Consider logging a dropped-on-restore count.
8. **Dead alias.** `deep.py:497` `_Findings = Findings` exists only for the annotation at `:332`. Replacing that annotation with `Findings` would let the alias go. Cosmetic.
9. **Untested frontend gate plumbing.** `proposed-changes.ts` ack (R15-CODE-FRONTEND-034) and the `host-actions.ts` write_note re-route (R15-CODE-FRONTEND-035) sit next to the order-safety gate. Both read correct to me. Neither is on the read-only list, but the verifier should include them in its diff pass.

## Integration order suggestion

Run the focused commands in PREINT.md in this order, then `pnpm ci-local`:

1. cargo: fmt, clippy, test
2. pytest: `test_runs_router`, `test_run_manager`, `test_agent_runtime`, `test_mcp_catalog_parity`, `test_research_module_boundary`, `test_research_*`
3. vitest: the ripple set, delegate-runs, host-actions
