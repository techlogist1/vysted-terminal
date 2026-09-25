# R15 Stage C — batch 14 plan (RC1 round 2, final c/h/m batch)

Base: `004-r4-experience-rebuild` @ `4cfd283e631d5b4c1ea22d2cf079488f25fa3532`.
Planner: Opus. Lows are not planned this batch (lead note).

## Selection

Open entries in the register with severity critical/high/medium: exactly two. Everything else
at c/h/m is fixed, `blocked_tier4`, `needs_gui`, `removed_with_feature` or `not_a_defect`.

| id | sev | operator area | writer |
|---|---|---|---|
| R15-AGENT-090 | high | agent-chat, research-search | W1 |
| R15-CODE-AGENT-033 | medium | agent-chat | W1 |

Both entries touch `sidecar/services/agent_runtime.py` (`_consume_round` / `_dispatch_round`)
and `sidecar/tests/test_agent_runtime.py`, so they cannot be split. There is ONE writer set.

## W1 (opus): agent-runtime ratio guard class + tool_result stream event

**Why opus.** This is the agent-chat named area. The guard rewrites every sentence the agent
relays, on chat, Delegate runs and MCP invoke. A too-wide claim class silently replaces true
prose, and a too-narrow one lets a fabrication through. The event change adds a new kind to
the agent runtime's stream state machine, next to the §6.5 host-action review path in
`_dispatch_round`.

**Files (W1 owns all of them):**
- `sidecar/services/agent_runtime.py`
- `sidecar/models/llm.py`
- `sidecar/services/llm/base.py`
- `scripts/agent_eval/grader.py`
- `sidecar/tests/test_runtime_phases.py`
- `sidecar/tests/test_agent_runtime.py`
- `sidecar/tests/test_agent_eval.py`
- `src/modules/chat/streaming.ts`
- `src/modules/chat/streaming.test.ts`
- `types/ai.ts`

### (A) R15-AGENT-090: the depositary-ratio claim class

**Mechanism (confirmed in code, per the batch-13 verifier note, not the raw claim).**
- `_ratio_claim_traced` (`agent_runtime.py:1827-1846`) counts a sentence as a claim only when
  `_CLAIM_NUMBERS` (`:1803`) matches. That pattern accepts only two forms:
  - a number directly before `(ordinary|equity|underlying|common) shares`, or
  - `N:M` / `N-for-M` / `N to M` between two bare operands, gated by `_RATIO_CUE`.
- Three fresh phrasings escape with `claimed == set()` and return True, so they are "traced":
  - `American Depositary Shares each represent six underlying equity shares`: two words sit
    between the number and `shares`.
  - `Each ADR is equivalent to 2 shares of common stock`: `shares of common stock` is not
    `common shares`.
  - `1 ADR : 6 shares`: the operand is followed by a word, not by `:`.
- The class defect: the claim is recognised by the shape of the number's neighbours, so every
  new wording is a new escape.

**Fix: redefine the claim class. Replace the operand-shape pattern.**
A sentence is a depositary-ratio claim when all three of these hold:
1. **Depositary term.** It carries the existing `_CLAIM_TERM`: `ADRs?|ADSs?|American Depositary|depositary|conversion ratio`.
2. **Ratio cue.** One of:
   - a cue word: `ratio`, `represent(s|ing)?`, `equivalent`, `equals?`, `each`, `converts?|convertible`, `corresponds?`, `for every`, `-for-`;
   - or the batch-13 share-count form `N (ordinary|equity|underlying|common) shares?`, kept as a cue so "backed by 6 ordinary shares" is still caught.
3. **Quantity.** It carries at least one: a digit number, a number word from one to TWENTY
   (extend `_NUMBER_WORDS`), or the operands of an N:M form.
   - A number attached to money or percent is NOT a quantity: preceded by `$`, `₹`, `Rs`, `USD` or `INR`, or followed by `%`, `percent`, `dollars`, `cents`, `rupees` or `cr`.
   - This keeps "Each ADR closed at $12.50" from becoming a claim.

**What must be traced.** Take the sentence's quantities, normalise number words to digits, and
drop the unit side `1` unless every quantity is `1`. So `1 ADR : 6 shares` claims {6}, and the
1:1 fabrication still claims {1}.

**When a claim counts as traced.** Unchanged: some tool result of the run names `_SOURCE_TERM`
(which includes `Repr`) and carries every claimed number. An untraced claim sentence becomes
`RATIO_UNAVAILABLE`, as today.

**Where the change lands.**
- `_CLAIM_NUMBERS`, `_RATIO_CUE` and `_ratio_claim_traced` are rewritten in place.
- `_guard_ratio_claims`, the sentence buffering in `_consume_round` and the preamble rule are
  unchanged.
- The ponytail note is updated: a claim split over sentences still slips past; a number
  adjacent to a form name (for example `20-F`) is conservatively treated as claimed.

**Tests (`test_agent_runtime.py`). Batch-13 tests stay green unmodified:**
- `test_an_untraced_adr_ratio_claim_is_replaced`
- `test_an_adr_ratio_a_tool_result_carries_is_kept`
- `test_an_adr_price_range_or_time_is_not_a_ratio_claim`

**New tests (one parametrized test for replaced claims, one for kept sentences).**

Replaced, against the `_SIFY_FUNDAMENTALS` result (no depositary term):
- `SIFY American Depositary Shares each represent six underlying equity shares.`
- `Each ADR is equivalent to 2 shares of common stock.`
- `The ADR-to-share ratio is 1 ADR : 6 shares.`
- a writer-invented spelled-out case, for example `One ADS equals fifteen ordinary shares.`
  (covers the one..twenty extension)
- a writer-invented case that no batch-13 form matches, for example
  `Every SIFY ADS corresponds to 3 shares.`

Kept byte-identical:
- `The ADR traded between 10 and 12 dollars.` (price range; required)
- `Each ADR closed at $12.50 on volume of 40,000 shares.` (money quantity plus volume)
- `Revenue represents 12% of the total.` (cue, no depositary term)
- `The PE ratio is 22.4.` (cue, no depositary term)

Traced and kept:
- `The ADR-to-share ratio is 1 ADR : 6 shares.` against the web_search result
  `Sify Technologies Ltd ADS (Each Repr 6 Ords)`. This pins the unit-side rule.

**Live bar (the writer, on its own isolated sidecar started detached; `llama3.1:8b` is
installed in the local ollama).**
- Run the original repro prompt 5 times via `scripts/r15/vy.py invoke` with provider ollama,
  model llama3.1:8b and autonomy ask. The prompt is: "How many ordinary shares does one SIFY
  ADR represent, and what is SIFY's TTM revenue in USD?"
- Record each final text in the writer note.
- Bar: 0/5 state an untraced ratio. Sourced "6" and the unavailable statement both pass.
- If ollama is unreachable, record could-not with the error and do not claim the bar.

### (B) R15-CODE-AGENT-033: the tool_result stream event and the grader

**Mechanism (confirmed).**
- The `models/llm.py` stream kinds have no tool-result kind.
- `_dispatch_round` (`agent_runtime.py` ~2275-2380) appends `result_str` only to the model's
  messages and to `turn.tool_results`.
- `grader.grade` (`scripts/agent_eval/grader.py:~85`) sees only `tool_use` inputs, so an
  option_chain `nearest` call that returned 422, with `expect: {}`, grades `[]` (a pass).
- `vy.py` writes every SSE frame raw to `--out` (`vy.py:190-193`), so vy and `run.py` need no
  change.

**Fix: apply the batch-13 writer's patch.** It is at
`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/code-agent-033.patch`.
- `git apply --check` on 4cfd283e succeeds for 9 of its 10 files. `agent_runtime.py` applies at
  an offset of 6 lines.
- Only the `test_agent_runtime.py` tail hunk fails, because batch 13 appended
  `test_an_adr_price_range_or_time_is_not_a_ratio_claim` after its context. Apply that hunk by
  hand: append `test_each_dispatched_call_streams_its_tool_result` at the end of the file.

The patch contains:
- `LLMToolResultEvent(kind="tool_result", tool_call_id, name, ok, error≤200)` in `models/llm.py`,
  added to the `LLMStreamEvent` union in `services/llm/base.py`.
- `_tool_result_event` in `agent_runtime.py`, yielded once per dispatched call right after
  `turn.tool_results.append`. That covers the cap and invalid-args synthetic results.
- The TS mirror variant in `types/ai.ts`, and the `normalizeEvent` branch in `streaming.ts`.
  Unknown kinds already fall through to `return null` (`streaming.ts:503`).
- The grader: the LAST `tool_result` per tool name with `ok: false` fails the trial as
  `"<name> errored: <error>"`. `__autobrief` ids are skipped. Streams without the frames grade as
  before.
- Tests in `test_agent_eval.py`: the errored trial fails; an errored call followed by a
  successful retry passes. In `streaming.test.ts`: an unknown kind is dropped with no onError;
  `tool_result` normalises to camelCase.

**The phase test must stay honest (`test_runtime_phases.py:209`).**
- `out == []` becomes an explicit assertion of the two `tool_result` events:
  `[("tool_result","call_s",False), ("tool_result","call_n",True)]`.
- The writer additionally asserts that `call_s`'s `error` carries `web-search cap reached`. That
  is the cap result's `message`, and the event must surface it.
- Never loosen the assertion to "anything" or to a length.

**Consumers checked (no change needed).**
- `routers/agents.py` encodes any event via `model_dump`.
- `run_manager.py:283-305`, `workflow_nodes/builtin.py:187-200` and `mcp_server.py:230-240`
  branch on known kinds and ignore the rest.
- ChatSidebar's `onEvent` is an if/else chain with no `never` exhaustiveness check. The only
  `never` switch (`workflow-run-overlay.tsx:116`) is over workflow events, not `LLMStreamEvent`.

**Payload.** The event carries the outcome plus the tool's own error/message string, which the
model already sees. No result payload and no credentials: the tools' BYOK keys ride headers and
never appear in results.

### Commit discipline (W1)
1. **Commit 1, R15-CODE-AGENT-033.** One commit holding the event model, the mirror and the
   consumers: `models/llm.py`, `services/llm/base.py`, `types/ai.ts`, `streaming.ts`,
   `streaming.test.ts`, `agent_runtime.py` (event), `grader.py`, `test_agent_eval.py`,
   `test_runtime_phases.py`, `test_agent_runtime.py` (event test).
2. **Commit 2, R15-AGENT-090.** `agent_runtime.py` (guard) + `test_agent_runtime.py` (class
   tests).
3. Push after each commit.

### Gates (W1, each detached where >~60 s)
- `ruff format <files> && ruff format --check sidecar && ruff check sidecar`
- pytest, run detached and polled: `sidecar/tests/test_agent_runtime.py`, `test_runtime_phases.py`,
  `test_agent_eval.py`, `test_capability_catalog.py`, `test_mcp_server.py`, `test_run_manager.py`, `test_runs_router.py`
 
- `pnpm vitest run src/modules/chat/streaming.test.ts`
- `pnpm typecheck`, `pnpm lint`, `pnpm format:check`

## Integrator run order
1. Merge W1 (one set). Check with `git show --stat` that commit 1 carries `models/llm.py`,
   `services/llm/base.py`, `types/ai.ts` and `streaming.ts` together (the mirror rule).
2. No build recipe changes, so no sidecar rebuild is required for ci-local. The verifier's live
   runs use a source sidecar.
3. Run `pnpm ci-local` detached and poll it.
4. Verifier (one fresh-context pass):
   - **AGENT-090.**
     - Run 5 live llama3.1:8b trials itself.
     - Feed `_guard_ratio_claims` fresh phrasings the writer did not pin. Suggested:
       - `Each American depositary receipt is worth four ordinary shares.`
       - `The depositary ratio stands at 1-for-6.`
       - a kept `SIFY ADR volume was 120,000 shares today.`
     - Confirm the batch-13 tests are unmodified (`git diff a217a529 -- sidecar/tests/test_agent_runtime.py` shows only additions).
   - **CODE-AGENT-033.**
     - Re-grade a recorded option_chain `nearest` stream with a synthetic `tool_result ok:false`
       appended. It must now fail.
     - Run one live `vy.py invoke` and confirm `tool_result` frames appear after each `tool_use`.

## Deferred
None.

## Proposed not-a-defect
None.
