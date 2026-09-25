# R15 Stage C — batch-21 plan

Base: `004-r4-experience-rebuild` @ `4d9a7324319004e43cdc391d9d719e603d59ef69`. It has no `sidecar/`, `src/` or
`src-tauri/` diff from the batch-20 merge `1abef99b`, so "failing on 1abef99b" and "failing on the base" are the same
test.

**Selection.** After adjudication, two critical/high/medium entries are open: R15-LEAD-030 (high, agent-chat) and
R15-LEAD-035 (medium, agent-chat). R15-LEAD-036 (low, agent-chat) is on the same guard file, so it rides W1 under the
lead note. The lows are not planned here; they belong to the lows waves.

**Writers.** There are exactly two disjoint writer sets. No file is shared between them. The one runtime hunk that
LEAD-035 needs is written out below under "W1 applies for W2".

## W1 — opus — the three named gaps of the figure-grounding guard (R15-LEAD-030, R15-LEAD-036)

**Why opus.** This is risk-adjacent: it touches the agent runtime's streaming guard and the per-turn provenance state
(routing change 5). The root cause is already cracked (batch-20 grounding by provenance). What remains are three
residuals, each named with file and line. Do NOT reopen the mechanism: rules 1, 2 and 3, `figure_grounding.py` and
the unit holder all stay.

**Branch.** `worktree-agent-batch-21-W1`, from `4d9a7324`. Run `git reset --hard 4d9a7324` first, because of the
worktree base hazard. Push every deliverable.

**Owned files.**
- `sidecar/services/agent_runtime.py`
- `sidecar/services/figure_grounding.py`
- `sidecar/tests/test_agent_runtime.py`
- `sidecar/tests/test_figure_grounding.py`
- `sidecar/services/llm/tool_call_rescue.py` and its test, only if the holder needs them. Say so in the report either
  way.

W1 does **not** edit `sidecar/services/symbol_resolver.py`. The unmerged lows branch
`worktree-agent-lows-P3-W3-provenance-data` edits that file. Read the masters through the functions that already exist
(see GAP 2).

**Read first.**
- `batch-20/VERDICTS.md` and `batch-20/PLAN.md`.
- `batch-20/verifier-evidence/`: `b20v_fresh.py` with `fresh.out` (19 offline cases, 6 FAIL lines); `b20v_live.py`
  with `live.out` and `live2.out`, the latter holding the y-neg-estimate-sbin ₹742.35 escape; and `probes.out`.
- `batch-20/writer-evidence/b20w_probe.py`, which gives 18/18 on the merged tree.

### GAP 1 — acknowledgement plus an ungrounded figure (LEAD-030, all-errored and mixed)

**Mechanism.** It is confirmed in code at `agent_runtime.py:2317-2321`. `_judge_clause` computes `prose` and then
returns None as soon as `_NEGATIVE.search(prose)` matches. That runs before `figs`/`ungrounded` are computed and
before rule 1 (`ctx.errored and not ctx.ok_tools`) or rule 2b are reached. So "Although the `price_data` tool failed,
I can tell you that SBIN.NS's latest close was ₹742.35." is one clause: `_CLAUSE_BREAK` needs whitespace before
"although", and at the start of a sentence there is none. That clause streams because "failed" matches.

The same applies to:
- "Since price_data failed, …₹812.40";
- "Although live data is unavailable, … $132 million";
- "I couldn't get a fresh quote, SBIN.NS was at ₹812.40".

**Fix.** Move the negative exemption below the provenance test and gate it on "no ungrounded figure":
1. Compute `figs` and `ungrounded` first. Rule 3 (all figures grounded) still returns None first.
2. Only then apply `if _NEGATIVE.search(prose) and not ungrounded: return None`.
3. A clause that both acknowledges the error and carries an ungrounded figure then falls through to rule 2a, rule 1 or
   rule 2b. It is replaced whole by the honest note, which is itself the acknowledgement.

Do not widen or narrow `_NEGATIVE`. It still exempts figure-free negative reports, for example "The price_data tool
returned an error", or "fundamentals returned an error: {"error": "HTTP 429"}" (429 is grounded by the errored
result).

**Controls.** These stream unchanged:
- an acknowledging clause without a figure;
- an acknowledging clause whose figure is grounded, whether the user's own number ("I couldn't fetch ITC.NS; your 25
  shares at ₹412.75 cost ₹10,318.75") or an ok tool's number.

### GAP 2 — errored subject named by company name, and subject inheritance (LEAD-030, mixed turn)

**Mechanism.** Rule 2b (`agent_runtime.py:2338-2343`) iterates `ctx.errored_subjects`. That map is filled at
`_dispatch_round` ~3055-3059 from `figure_grounding.subjects(tool_call.input)`, which gives only the symbol base
(`INFY`), and it is matched by `figure_grounding.mentions` (the symbol, with an optional exchange suffix). So in
"Infosys last traded at ₹1,233.65." with INFY.NS errored and TCS.NS ok, no subject matches, and the clause streams.
v-mixed-errored-alias-name and v-mixed-alias-fund run under prompt "q?", so the user never wrote "Infosys". The name
has to come from the sidecar's own data.

**Fix (the alias set).** Each call's subject set becomes its aliases. Build it for both errored and ok calls, so the
existing `subject not in ctx.ok_subjects` collision rule keeps working on names. The aliases are:
- **(a) The symbol base,** as today. `mentions` already allows the suffix.
- **(b) The company name.** Look up the base in the resolver masters that already exist:
  `symbol_resolver._nse_master()` (INFY → "Infosys Limited"), `_bse_master()` and `_us_master()` (SIFY → "SIFY
  TECHNOLOGIES LTD"). Lower-case it and strip the corporate suffix with `symbol_resolver._strip_corporate_suffix`, which
  gives "infosys", "tata consultancy services" and "state bank of india".
- **(c) Short forms.** These are:
  - the name's first two tokens when the name has three or more ("state bank", "tata consultancy");
  - the name's first token when it is distinctive, meaning not in `symbol_resolver._generic_tokens()` and at least 4
    letters ("infosys", "wipro", "reliance", "sify"; "tata" is generic, so it is excluded);
  - every distinctive name token that the user's own messages this run contain as a whole word. For example, if the
    user wrote "Infosys" or "Consultancy", that word is an alias for this turn. Store the user text on `_TurnState` at
    the grounding-seed loop, from `role == "user"` messages only.

Match case-insensitively, on whole words, as phrases (`mentions` already does this; an alias with spaces works).
Possessives work too ("Infosys's", "Wipro's").

A `ponytail:` comment records a trade-off. The private-master reads avoid a conflict with the unmerged P3-W3
`symbol_resolver.py` edits. A first-token alias that is also a common word ("state") can over-replace an **ungrounded**
figure only when that symbol's call errored, which fails safe.

**Fix (paragraph inheritance).** A clause that has an ungrounded figure and names no subject of its own (no alias of
any ok or errored subject in its clause, row or colon intro) inherits the nearest preceding subject mention in the
same paragraph. That mention can be from an earlier unit or from its colon-intro.
- If that subject is errored and not ok, the clause is replaced (rule 2b).
- If it is an ok subject, the clause streams.

The paragraph resets at a blank line. Carry the last-mentioned subject across releases the same way `last_note` is
carried: `_guard_tool_citations` receives and returns it, and it is reset where `_BLANK_LINE` closes the paragraph.

Example: "Infosys (INFY.NS) could not be refreshed. It last traded at ₹1,233.65." → the second sentence is replaced.

**Controls.** These stream unchanged:
- a company-name clause on an ok subject ("TCS last traded at ₹2,082.00" with TCS.NS ok, or "Tata Consultancy
  Services closed at ₹3,235.50");
- in one list, an ok-subject row ("- TCS: ₹3,235.50") beside an errored-subject row ("- Infosys: ₹1,233.65"). The
  TCS row keeps its figure and only the Infosys row becomes the note.

### GAP 3 — tilde fences (LEAD-036)

**Mechanism.** `_FENCE_OPEN = [ \t]*```` ` and `_FENCE_CLOSE = \n[ \t]*```[^\n]*` (`agent_runtime.py:2084-2085`) are
backtick-only. In `_seg_at` (~2123), a `~~~json` line is never a fence segment. Its lines are cut as a sentence, the
JSON and a trailing `~~~`, so the replacement leaves an orphan `~~~` that swallows the prose after it
(v036-tilde-fence).

**Fix.** Recognise CommonMark fences:
- The opener is at least three backticks or at least three tildes, with an optional info string.
- The closer is the SAME character, at least as long as the opener.

Build the closer from the opener's run: `_FENCE_OPEN` captures the run, and `_seg_at` searches for
`\n[ \t]*{char}{{{n},}}[^\n]*`. `_fence_body` is unchanged. There are no other fence regexes in `agent_runtime.py`
(grepped).

### Tests W1 pins BEFORE the fix (failing on 1abef99b/4d9a7324, passing after; record both runs)

Put these in `sidecar/tests/test_agent_runtime.py`, through the full `invoke_agent` relay (`_scripted_answer` with
`prompt=`, and per-call `input`). Parametrise, with one test per behaviour.

1. **Every FAIL line of `batch-20/verifier-evidence/fresh.out`, as the probe writes it.** The fabrications must be
   replaced (the listed figure absent, the note present):
   - v-mixed-errored-alias-name
   - v-mixed-alias-fund
   - v-allerr-negative-since
   - v-allerr-negative-although
   - v-allerr-negative-couldnt
   - v036-tilde-fence: no `~~~` in the output, and "Hope that helps." survives as prose.
2. **The live ₹742.35 transcript replayed.** Round 1 calls `price_data` with invalid args (the ERR_ARGS result).
   Round 2 streams "Although the `price_data` tool failed, I can tell you that SBIN.NS's latest close was ₹742.35.".
   The output carries no "742.35" and does carry the price_data note.
3. **The Infosys mixed turn.** The user prompt is "What are the latest prices of Infosys and TCS?", `price_data` errors
   for INFY.NS and returns ok for TCS.NS (2082.0), and the model streams "Infosys last traded at ₹1,233.65, and TCS
   closed at ₹2,082.00.". The Infosys clause is replaced and the TCS clause streams.
4. **A tilde fence (fresh; not the probe's text).** In an all-errored `~~~~text` block of four tildes with a `~~~~`
   closer, the note renders as prose and no tilde run remains.
5. **Class cases the fix is not written against (W1's own invention, ≥3).** Examples:
   - an all-errored "Price data wasn't available, but my estimate is ₹905." (a "but" split, and the negative clause has
     no figure);
   - a mixed-turn "State Bank of India's P/E is 9.8" with SBIN.NS errored;
   - an inherited "Infosys could not be refreshed. It last traded at ₹1,233.65.";
   - a backtick fence of four backticks.
6. **Controls, each streaming unchanged:**
   - an acknowledgement without a figure;
   - an acknowledgement with the user's own figure;
   - an acknowledgement with an ok tool's figure in a mixed turn;
   - "TCS last traded at ₹2,082.00" with TCS ok;
   - an ok row beside an errored row in one list;
   - a sentence after a blank line with an ok subject.
7. **`test_figure_grounding.py`.** One parametrised test of the alias set:
   - INFY → contains "infosys";
   - SBIN → contains "state bank of india" and "state bank";
   - TCS → contains "tata consultancy services" and not "tata";
   - SIFY → contains "sify";
   - a user-text token becomes an alias.
8. **Every existing LEAD-030/031/033/036 and AGENT-090 test, and `test_figure_grounding`, stay green.** No deletion,
   no weakening. If a pinned expectation has to change, its fixture premise must have been false (for example, a
   negative clause whose "true" figure nothing in the turn carries). Change the fixture, and put the rationale in the
   commit. Never flip a true statement to "replaced".

### Checks (detached and polled; no single call over ~120 s)

- **Focused tests.** `test_agent_runtime`, `test_figure_grounding`, `test_b5_runtime_history`,
  `test_tool_call_rescue`, `test_llm_ollama` and `test_b3_runtime_intent_gate`. Then run
  `ruff format --check sidecar && ruff check sidecar`, and the full sidecar pytest (detached).
- **Offline probes, with cwd `<tree>/sidecar`, on the fix sha.** Expect BAD 0 on every FAB and TRUE line:
  - `batch-17/verifier-evidence/b17v_probe{,2,3}.py`
  - `batch-18/verifier-evidence/b18v_probe{,_b,_c,_d}.py`
  - `batch-19/verifier-evidence/b19v_probe.py` 3
  - `batch-20/writer-evidence/b20w_probe.py`
  - `batch-20/verifier-evidence/b20v_fresh.py`, which must be 19/19

  The two false-premise "q?" lines of `b19v_probe.py` (no arg, and `2`) stay judged on their premise-true form in
  `b20w_probe`, per the batch-20 concurrence. Save the outputs under `batch-21/writer-evidence/`.
- **Live bar.** Run a source sidecar on **127.0.0.1:52350**. Never use :52152–:52154 (the app) or :52310 (the
  verifier). Use llama3.1:8b through ollama with autonomy ask, following the pattern of
  `batch-20/verifier-evidence/b20v_live.py`. Run at least 8 prompts:
  - "What is SIFY's TTM revenue in USD?";
  - an all-errored SBIN.NS price ask that invites an acknowledgement ("Call price_data once with no arguments. Even if
    the tool fails, tell me what you know about SBIN.NS's latest close.");
  - a two-turn INFY/TCS run with price_data forced to error for INFY only, where the user writes "Infosys";
  - a prompt that invites a tilde fence ("show the raw fundamentals for TATAMOTORS.NS in a ~~~ fenced block");
  - at least 3 true controls:
    - an ok tool's figures with rounding (MSFT price);
    - a company-name clause on an ok subject (TCS by "Tata Consultancy Services");
    - a user-supplied figure restated after an error.

  Put the transcripts and a tally in `batch-21/writer-evidence/`, each true control checked against the app's own
  /quotes or /fundamentals.
- **LEAD-035 hunk.** Apply the "W1 applies for W2" hunk below as its own commit. Run `test_b3_runtime_intent_gate`
  after it, and report that it is inert without W2's planner change.

## W2 — sonnet — an explicit no-tool instruction is honoured server-side (R15-LEAD-035)

**Why sonnet.** The spec is clear and the output is checkable: one planner cue and one intent-gate test file.

**Branch.** `worktree-agent-batch-21-W2`, from `4d9a7324`. Run `git reset --hard 4d9a7324` first.

**Owned files.**
- `sidecar/services/planner.py`
- `sidecar/tests/test_b3_runtime_intent_gate.py`

**Mechanism.** It is confirmed in code:
- `planner.classify_intent` (planner.py:185-232) lets any research, build or edit signal win over read.
- The prompt "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total
  proceeds." has no read cue for "without calling any tool", and it may hit an edit cue.
- So `_resolve_tool_surface` (agent_runtime.py:1742-1790) keeps the full set, and llama3.1:8b stages
  `portfolio_update_position` (batch-19 live.out:42-50).
- Batch-20 c-reuters shows the same instruction ignored with a READ tool (`web_search`). So stripping only the writes
  would not meet the acceptance ("no staged write and no tool call").

**Fix.** In `planner.py`, add a module-level `_NO_TOOL_CUE` pattern with a one-line comment citing R15-LEAD-035. It
matches an explicit instruction not to use tools at all, including:
- "without calling/using/running/invoking any tool(s)" (also without "any");
- "don't/do not/never call/use any tool(s)";
- "no tool calls" / "no tools";
- "just/only answer from what I gave/told you".

It must not match an instruction to skip one specific tool ("without calling the fundamentals tool, use price_data").

In `classify_intent`, check it first, after the empty-text return. On a match, return
`IntentResult("read", 0.95, ["no-tool"], False)`. This is a POSITIVE read cue that overrides action cues, so the
write-strip in `_resolve_tool_surface` fires even on the agent path alone. The runtime hunk below then empties the
surface.

**Tests W2 pins in `test_b3_runtime_intent_gate.py`.** Each runs through the existing `_agent_tool_ids` path.
1. The t-user-sale prompt, verbatim, gives `tool_ids == set()`.
2. One fresh phrasing gives `tool_ids == set()`, for example: "Don't use any tools — I hold 40 HDFCBANK at ₹1,640;
   just tell me my cost basis."
3. A specific-tool exclusion keeps the surface: "Without calling the news tool, get TCS.NS price" keeps `price_data`.
4. A control: "Add 10 TCS at 3,200 to my portfolio" still carries `portfolio_add_position`.

Every existing test in the file stays green.

**Running the tests.** Tests 1 and 2 need W1's hunk. To run them, apply the hunk locally uncommitted, run the test,
then `git checkout -- sidecar/services/agent_runtime.py` before committing. Record in the report that tests 1 and 2
pass only on the merged tree.

Also run `ruff format --check sidecar && ruff check sidecar`.

### W1 applies for W2 (the exact hunk in `sidecar/services/agent_runtime.py` `_resolve_tool_surface`)

The hunk goes right after `tool_ids, retired_tools = catalog.resolve_tool_ids(spec.tools)`, and applies in every mode:

```python
    # R15-LEAD-035: an explicit no-tool instruction in the user's turn
    # ("without calling any tool") is honoured server-side in every mode: the
    # provider is sent no tools, so the model can make no call, a write or a
    # read (planner.classify_intent tags it with the "no-tool" signal).
    if "no-tool" in classify_intent(prompt).signals:
        return [], True, retired_tools
```

`classify_intent` is already imported (agent_runtime.py:69). The hunk is inert until W2's planner change lands.

It is safe for three reasons, all confirmed in code:
- With empty `tool_ids`, the ollama adapter sends no `tools=` (ollama.py:162).
- It rescues text-JSON calls only for names it offered (`offered`, ~178), so nothing can be rescued.
- The runtime dispatches only calls the adapter emits.

## Run order (integrator)

1. Create `worktree-agent-batch-21-int` from `4d9a7324`. Merge `origin/worktree-agent-batch-21-W1`, then
   `origin/worktree-agent-batch-21-W2`, auditing only via `origin/`.
   - W1's diff may touch only W1's owned files plus `batch-21/writer-evidence/`.
   - W2's diff may touch only `planner.py` and `test_b3_runtime_intent_gate.py`.
   - Confirm that the W1 hunk above is present verbatim.
2. Run ruff and the full sidecar pytest (detached). `test_b3_runtime_intent_gate` tests 1 and 2 pass only now. There
   is no frontend, Rust or `types/` change, so vitest and cargo are unaffected and there is no `types/data.ts` mirror.
   Run `pnpm ci-local` and the smoke test as usual.
3. Coordination with the unmerged lows branches:
   - `worktree-agent-lows-P1-W2-runtime-catalog` edits `planner.py` in the PLAN_ACTIONS/prompt hunks (~241-310). It
     also edits `agent_runtime.py` in the constants, `_resolve_model` and research-timeout hunks. None of these are
     the hunks W1 or W2 touch.
   - `worktree-agent-lows-P3-W3-provenance-data` edits `symbol_resolver.py`, which W1 only reads.

   Batch-21 merges first. The later lows integrator resolves any overlap and re-runs `test_agent_runtime`,
   `test_figure_grounding` and `test_b3_runtime_intent_gate`.
4. A fresh-context verifier checks the Acceptance below.

## Acceptance (what the verifier certifies)

- **LEAD-030.** On the running app with llama3.1:8b, the following stream 0 fabricated figures in ANY shape:
  - the entry's own prompt;
  - at least three fresh error-shaped prompts of the verifier's own invention: at least one inviting an error
    acknowledgement, at least one naming the subject by company name, and at least one all-errored multi-symbol ask.

  Also required:
  - At least 3 true controls stream unchanged: a user-figure restatement, an ok-tool figure with rounding, and a
    company-name clause on an ok subject.
  - The b17, b18, b19 and b20 offline probes (with b20v_fresh) report BAD 0 on the FAB and TRUE lines.
  - At least one fresh shape or phrasing that the writer did not pin is tried.
- **LEAD-035.** The t-user-sale prompt and one fresh no-tool phrasing produce no staged write and no tool call. A
  normal "add 10 TCS at 3,200 to my portfolio" still stages the write behind review.
- **LEAD-036.** Backtick and tilde fences both render the note as prose, with no orphan marker.

## Deferred

None. Both open c/h/m entries and LEAD-036 are planned.

## Proposed not-a-defect

None.

## Notes (Tier-3 decisions, for the verifier's attention)

- **LEAD-035 empties the whole tool surface, not only the writes.** The entry's fix_shape says "refuse any tool call
  the model attempts". The acceptance says "no tool call", and batch-20 c-reuters shows a read tool called against the
  instruction. Emptying the surface is the only deterministic way to meet both. It is the user's own instruction, it
  touches no §6.5 safeguard, and it only removes capability.
- **Resolver names are read through private master functions** (`_nse_master`, `_bse_master`, `_us_master`,
  `_strip_corporate_suffix`, `_generic_tokens`). This avoids a file collision with the unmerged lows P3-W3
  `symbol_resolver.py` edits. A public accessor can replace them once that branch lands.
- **If LEAD-030 is not certified a seventh time,** the run-state rule stands: there is no further shape round, and the
  lead files the Tier-4 note.
