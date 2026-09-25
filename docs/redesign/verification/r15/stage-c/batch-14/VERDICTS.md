# R15 Stage C batch 14: verifier verdicts

- **Merge target:** `worktree-agent-batch-14-int@11e23ace` (base `4cfd283e`).
- **Stack:** I ran the main sidecar from the source of a scratch worktree at 11e23ace on `127.0.0.1:52310`, with a copy of the vysted-iso data dir. The MCP subprocesses were on :52153/:52154, and `/health` returned ok. The local model was llama3.1:8b on ollama, under autonomy ask. The sidecar was stopped and the worktree removed afterwards.
- **Chain:**
  - The integrator's `pnpm ci-local` passed at c27e07c0 with CI_EXIT=0 (pytest 3214 passed, 1 skipped). The smoke test passed with SMOKE_EXIT=0.
  - 11e23ace changes only `grader.py` (1 line added, 3 removed).
  - At 11e23ace I re-ran `test_agent_eval`, `test_runtime_phases`, `test_agent_runtime`, `test_run_manager`, `test_mcp_server` and `test_capability_catalog`: 196 passed. `ruff check` and `ruff format --check` on sidecar are clean. `vitest streaming.test.ts` passed 23 of 23.
- **Verdict: approve.**
  - CODE-AGENT-033 certifies and is not a regression.
  - AGENT-090 is not certified. Its guard now catches more fabrication wordings but replaces some true ADR price sentences (see below). That is a real regression. It hides a fact and never states a false one, so on balance it does not make the branch worse than base for a high-severity fabrication.

| id | verdict |
|---|---|
| R15-CODE-AGENT-033 | certified |
| R15-AGENT-090 | not certified (class still wording-bound, both directions) |

## R15-CODE-AGENT-033: certified

**Live stream.** All 12 live invokes carried a `tool_result` frame immediately after each `tool_use`. The event kinds seen were `heartbeat`, `tool_use`, `tool_result`, `delta` and `done`.

**Original repro, live.** I asked llama3.1:8b to call `option_chain` for AAPL with expiry `nearest` (`verifier-evidence/live-5.jsonl`). The stream carried:
- `tool_use option_chain`
- then `tool_result option_chain ok=false error="invalid argument: Invalid isoformat string: 'nearest'"`

`grader.grade({'expect': {}}, events)` returns `["option_chain errored: invalid argument: Invalid isoformat string: 'nearest'"]`. That is a fail. Before this batch the same case graded `[]`.

**Fresh cases, other tools and error shapes, live.** Both fail with the `<tool> errored:` reason:
- `sify-5.jsonl`: `fundamentals` returned provider error "yfinance has no instrument data for 'SIFY.A'", and `price_data` hit the "correctness gate: empty series" error.
- `sify-2.jsonl`: `financial_statements` returned invalid-args ok:false.

**Controls.**
- An errored call followed by an ok retry of the same tool grades `[]`.
- A legacy stream with no `tool_result` frames grades `[]`, the same as before.
- A clean live run (`sify-1`) grades `[]`.

**Mirror and consumers.**
- Commit e85f8b01 carries `models/llm.py`, `services/llm/base.py`, `types/ai.ts` and `streaming.ts` together.
- In `ChatSidebar`, the `onEvent` if/else chain ignores the new kind. The `produced` flag was already set by the preceding `tool_use`.
- The `__autobrief` publish is yielded only as a `tool_use` (`_auto_publish_event`) and never gets a `tool_result`, so dropping its filter in 11e23ace is correct.
- `test_runtime_phases` asserts the two exact events and the cap message. The assertion was not loosened.

## R15-AGENT-090: not certified

**Batch-13 tests unmodified.** `git diff a217a529 -- sidecar/tests/test_agent_runtime.py` shows only additions (0 removed lines).

**Live bar (original repro prompt, 5 llama3.1:8b runs).**

| run | ratio part | notes |
|---|---|---|
| 1 | guard fired ("not available from this session's sources") | revenue ₹4,651 cr, in INR and not converted |
| 2 | guard fired, then **"For SIFY, one ordinary share represents 1 share."** | untraced 1:1, split from the ADR sentence, so it escapes. Also "TTM revenue for SIFY in USD is ₹4,411 cr" after both financial_statements calls errored |
| 3 | guard fired | revenue honestly unavailable |
| 4 | guard fired | — |
| 5 | no ratio stated | both tools errored, yet the model stated price ₹34.15 and revenue ₹13.38 B |

Result: 1 of 5 runs states an untraced ratio. The bar is 0 of 5.

**Planner's fresh cases.** All behave correctly:
- `Each American depositary receipt is worth four ordinary shares.` is replaced, also live in `live-4`.
- `The depositary ratio stands at 1-for-6.` is replaced when untraced. It is kept against the `Each Repr 6 Ords` result.
- `SIFY ADR volume was 120,000 shares today.` is kept.

**My fresh cases, not in any test** (`verifier-evidence/guard.py`, run against the worktree's `_guard_ratio_claims` with a SIFY fundamentals result that has no depositary term).

These pass through untouched:
- `1 ADR = 6 shares.` This also happened live: llama emitted it verbatim and it streamed unguarded (`live-2.jsonl`).
- `One ADR is worth 10 shares of Sify.`
- `A single SIFY ADR gives you 2 shares.`

These are replaced, although they are true or unrelated prose:
- `Each ADR closed at 5.20 USD on Friday.`
- `Each ADS's 52-week high was 12.4.`
- `SIFY's ADSs each gained 3 points in 2024.`
- `SIFY files a 20-F each year for its ADSs.` The ponytail note accepts this one.

The base guard at 4cfd283e keeps all four of those sentences, so they are new over-replacements.

These are correctly caught:
- `According to fundamentals data, the ADR ratio is 1:1.`
- `SIFY ADRs trade at a 1:2 ratio to ordinary shares.`
- `The ADS-to-ordinary ratio is 1 to 10.`
- `Holders receive 3 ordinary shares per ADS.`
- `One SIFY ADS is backed by ten equity shares.`

**Why not certified.**
- The title claim still holds in 1 of 5 live runs.
- The class is still recognised by cue words. `=`, `worth` and `gives` escape.
- The bare `each` cue now swallows true ADR price and return sentences. Before this batch they survived.
- The fix_shape asks for the model not to cite a field the tool results lack. The guard enforces that only for sentences that carry a depositary term.

## Issues found (outside the two entries)

1. **Hallucinated figures after errored tools.** In `sify-2` and `sify-5`, llama3.1:8b stated revenue and price figures although every tool call in the run had errored: ₹4,411 cr, ₹34.15 and ₹13.38 B. This is the same hallucinated-field class as AGENT-090, but for revenue and price rather than the ratio.
2. **Raw tool-call JSON in the answer text.** A raw fragment such as `{"name": "financial_statements` / `{"name": "price_data` leaked into the delta text (`sify-2`, `sify-5`).
3. **Revenue asked in USD, answered in INR.** "TTM revenue ... in USD" was answered in INR without a conversion in runs 1, 2 and 5. Run 2 labelled a rupee figure "in USD".
