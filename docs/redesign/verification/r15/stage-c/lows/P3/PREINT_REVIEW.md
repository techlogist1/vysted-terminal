# P3 lows pre-integration candidate: fresh diff review

Reviewed 07:00 IST by a fresh read-only Opus reviewer. Status: **untested pending integration**. I ran no pytest, vitest, tsc, eslint, cargo or build.

- Branch: `origin/worktree-agent-lows-P3-int-4c6dfe8` @ `266ed2ef75a399b8e8602fce3b1f786edd60db30`
- Base: `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`. Diff: 161 files, +4065/-1944.

## Verdict: needs_fix

There is one blocking item. The R15-DOCS-010 test (W7, never run by its writer) is deterministically red.

## Blocking

| File | Issue | Fix |
|---|---|---|
| `src/modules/notes/NotesToolbar.test.tsx` (describe "NotesToolbar — R15-DOCS-010") | The test checks `className` as a substring. `expect(boldButton.className).not.toContain("bg-charcoal-800")` runs against the inactive class string from `NotesToolbar.tsx:109`, which is `"text-charcoal-400 hover:bg-charcoal-800 hover:text-charcoal-100"`. That string contains the substring `bg-charcoal-800` via `hover:bg-charcoal-800`, so the first assertion always fails. The later `waitFor(... toContain("bg-charcoal-800"))` would always pass, so the test also cannot tell active from inactive. | Assert on class tokens: `expect(boldButton.classList.contains("bg-charcoal-800")).toBe(false)` before the click and `.toBe(true)` in the `waitFor`. Alternatively assert `aria-pressed` false then true together with the token check. This keeps the entry's behaviour, the fill class on the active button. Do not weaken it. This is a writer (W7) branch fix, or a recorded assembler fixup on the candidate. |

## Checks

(a) **Safety surface untouched.** `git diff --stat base...branch` is empty for `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs`, `types/proposed-change.ts` and `sidecar/services/agent_runtime.py`. Nothing touches `src-tauri/`, `.github/`, `package.json`, `pnpm-lock` or Cargo either. The FE change in `ChatSidebar.tsx` (R15-CODE-FRONTEND-032) only *adds* `rejectAllChanges()` on `/clear` and on a space switch, which tightens the proposal gate. Nothing auto-applies.

(b) **Claimed tests exist as source.** I found every Python test id named in PREINT.md with a `def` on the branch: 32 ids, and each is present once. The whole-file claims (`test_brave_backend`, `test_mojeek_backend`, `test_earnings_quality`, `test_growth_check`, `test_range_check`) are unchanged regression files for refactors, which is legitimate. Every vitest claim has its entry marker or assertion on the branch except R15-UI-069. `ScreenerPanel.test.tsx` is unchanged and has no UI-069 case, and WRITERS says test "None", so that claim rests on existing coverage. Spot-read assertions: `test_workflow_router` (dangling edge gives run-start + one run-error; `resume-from` returns 400, `resumeFrom` returns 422), `test_quant_router::test_duplicate_pillar_is_400`, `test_quant_yield_curve::test_grid_distinct_and_within_max_tenor`, `test_symbol_resolver` (garbled master gives 200; autocomplete exact band binds), `test_ddg_backend::test_one_search_with_lite_fallback_takes_one_pacing_slot`, `brief-layout.test.tsx`. Each asserts its entry's behaviour. The exception is the DOCS-010 case under Blocking.

(c) **Conflict resolution.** There were no conflicts. I verified this independently: the nine writer diffs against `ebc5ed41` cover 159 files with zero overlap between writers, and every writer tip is an ancestor of the candidate. Every one of those 159 files is blob-identical on the candidate to its writer tip (0 mismatches), so no writer hunk was dropped. The candidate's remaining 2 files are the assembler commit `266ed2ef`.

(d) **Defects, imports, contracts.** Apart from the blocking item I found none. What I checked:
- Deleted modules have no importer left: `services/quant/monte_carlo.py`, `services/workflow_nodes/registry_v0_6_0.py` (`agent_tools.registry_v0_6_0` is a different module and still exists), `src/lib/fuzzy.ts`, `exportNoteMd`, `openCryptoStream` and `StreamErrorFrame`. `needs_disambiguation` was removed from `Resolution`. The only remaining uses are wire dict keys, and the tests moved to `decide(r)` with equivalent assertions. Every `_instrument_nse/_bse/_us` call now passes a band.
- Wire mirrors are changed together:
  - `Quote.change`/`change_percent` became nullable on both sides. The TS consumers are guarded (`EquityOverviewPanel` null-checks, `WatchlistPanel ??`, `brief-blocks typeof`). The Python consumers either pass the value through or guard for None, and `company_narrative._fmt` handles None.
  - `Freshness` gains `"unknown"` on both sides. There is no exhaustive `Record<Freshness,…>`, and `DataBadges` handles the new value.
  - The `CompanyNarrative` FR-124 fields are added in Python (with defaults) and in TS (required). The two TS object literals (`EquityOverviewPanel.tsx:726`, `EquityOverviewPanel.test.tsx:165`) set every field.
  - `FieldMeta.status` became a Literal. All producers use ok/flagged/withheld/unavailable.
  - `WorkflowRunRequest` drops `resume_from` on both sides. No TS caller used `resumeFrom`.
  - The `LLMUsage.served_model` field is normalized to `servedModel` in `streaming.ts`.
  - The `types/ai.ts` error member gains optional fields, which is additive.
- MCP surface and register-counted tests: no change to `agent_tools/catalog.py`, the MCP server, or the agent JSON roster.
- Formatting: I re-ran `ruff format --check` and `ruff check` on 86 changed .py files (clean) and `prettier --check` on 70 changed FE/doc files (clean), in the assembler worktree at `266ed2ef`.

## Advisories (integrator: look here first if the chain goes red)

1. **Boot path (W5, PLATFORM-068).** `create_app` now registers every node type, including the 12 core built-ins, which were previously only registered in `main.py`. Tests that reset the registry do so in their own fixtures, so this is probably benign. `test_screener_nodes::test_register_adds_screener_query_to_workflow_engine` still depends on test order, but that was already true: the old `create_app` also registered the domain nodes. Its comment still names the deleted `register_v0_6_0_nodes`. Run the full pytest suite and `node scripts/smoke-test-sidecars.mjs`.
2. **Global 30 s default timeout in `sidecarRequest` (W1, LIFECYCLE-027).** Every REST call that does not supply its own `signal` now aborts at 30 s. The long-running flows I found are safe: SearXNG setup runs as a background task with status polling, and delegate runs are detached. Any slow synchronous GET/POST, such as a cold fundamentals or financials fetch behind a throttled Yahoo, now fails at 30 s instead of waiting. `AbortSignal.any` (used when the caller passes a signal) needs WebKit 17.4+ / WebKitGTK 2.44+. `tauri.conf.json` sets no `minimumSystemVersion`, so an older macOS or Linux webview would throw on every signal-carrying request. Consider feature-detecting it. jsdom 29 has it, so vitest is fine.
3. **Five tests deleted from `sidecar/tests/test_ddg_backend.py`** (`test_token_bucket_*` x3, `test_module_bucket_is_lazy_and_process_global`, `test_limiter_does_not_delay_a_single_search`). They go with the deleted `_TokenBucket`, which is R15-CODE-RESEARCH-009's partition-sanctioned fix ("delete ddg.py's _TokenBucket"). They are replaced by `test_no_internal_pacing_symbols_survive_on_the_module`, `test_lite_fallback_makes_exactly_two_requests_no_pacing_wait` and `test_one_search_with_lite_fallback_takes_one_pacing_slot`. PREINT.md records only the fuzzy.test.ts deletion; the verifier should record this one too.
4. **Changed existing assertions** (not weakened, recorded for the verifier):
   - `test_quant_options::test_mc_rejects_too_few_paths` now goes through `options.price()` and matches the `validate_domain` message. The floor moved there (PLATFORM-041), and the engine-level checks for fewer than 3 steps or fewer than 100 paths were removed.
   - `test_llm_openai` fake signature widened.
   - Assembler `266ed2ef` widened the fakes in `test_research_metering.py` and `test_b5_runtime_synthesis.py` with `**_k`, without running them. The other oneshot `get_provider` fakes on the branch already take `**k` or `base_url`.
5. **Behaviour changes that may surprise a non-P3 test:**
   - `transform.code` `round()` now rejects digits outside [0, 15] (a negative ndigits used to work). No test on the branch uses a negative value.
   - The code node evaluates in `asyncio.to_thread` with a 5 s `wait_for`.
   - The `/workflow/run` stream now wraps a `WorkflowEngineError` raised before run-start as run-start + run-error.
   - LLM adapters collapse the per-SDK except clauses into one `except Exception`, and `validate_key` no longer re-raises through an explicit clause (still propagates).
   - The quant floors are now enforced only in `validate_domain`. A direct engine call that bypasses the dispatcher is no longer floored.
6. **`@tiptap/extension-list` is in `package.json` and `pnpm-lock.yaml`** but is missing from the main worktree's `node_modules/@tiptap`. `ci-local`'s `pnpm install --frozen-lockfile` should restore it. If tsc still reports TS2307 for it in `src/modules/notes`, the cause is the environment, not this diff.
7. **R15-UI-077 duplicate-pillar test** asserts that `"pillar"` appears in QuantLib's RuntimeError text. That depends on the QuantLib version's message wording, so check it first if it goes red.
8. **Stale doc reference:** `docs/SIDECAR_API.md:94` still mentions `openCryptoStream()`, which R15-DATA-109 removed. This is docs only and outside the chain.
9. **Carried from PREINT:** R15-DATA-102 is could_not. PLATFORM-045/046 are not_a_defect_proposed. W2.jsonl line 6 is not valid JSON. W1.jsonl arrives only via the W1 branch.
