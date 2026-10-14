# R15 Stage C — batch-22 plan

Base: `004-r4-experience-rebuild` @ `93ba12da01f57307705d39ae80befe2dd4fcf56f`. It has no `sidecar/`, `src/`,
`src-tauri/` or `types/` diff from the batch-21 merge `86ae79c4`, so "failing on 86ae79c4" and "failing on the base"
are the same test.

**Selection.** Two critical/high/medium entries are open after adjudication: R15-LEAD-030 (high, agent-chat, eighth
round) and R15-LEAD-035 (medium, agent-chat, second round). R15-LEAD-036 (low, agent-chat) has the same fence code
as LEAD-030 item 1, so it rides W1. The other 204 lows belong to the lows waves. Nothing is deferred and nothing is
proposed as not-a-defect.

**Writers.** There are exactly two disjoint writer sets and no shared file. W2 needs no runtime hunk: the batch-21
hunk in `_resolve_tool_surface` (agent_runtime.py:1752-1757, `"no-tool" in classify_intent(prompt).signals`) is
already merged and stays as it is. So "W1 applies for W2" is empty this batch.

## W1 — opus — the three residuals of the figure-grounding guard (R15-LEAD-030, R15-LEAD-036)

**Why opus.** The work is risk-adjacent. It changes the agent runtime's streaming guard, its per-turn provenance
state, and the burden of proof in mixed turns (rule 2c). The mechanism stays as it is: grounding by provenance,
rules 1/2/3, the unit holder, the subject alias sets and paragraph inheritance. Batch-22 closes exactly the three
items below.

**Branch.** `worktree-agent-batch-22-W1`, from `93ba12da`. Run `git reset --hard 93ba12da` first, because of the
worktree base hazard. Push every deliverable.

**Owned files.**
- `sidecar/services/agent_runtime.py`
- `sidecar/services/figure_grounding.py`
- `sidecar/tests/test_agent_runtime.py`
- `sidecar/tests/test_figure_grounding.py`
- `sidecar/services/llm/tool_call_rescue.py` and its test, only if the holder needs them. The report says which.

W1 does **not** edit `sidecar/services/symbol_resolver.py`, because the unmerged lows branch P3-W3 edits it. Keep
reading its private readers (`_nse_master`, `_bse_master`, `_us_master`, `_strip_corporate_suffix`,
`_generic_tokens`, `_marquee_aliases`). Add no public accessor now.

**Read first.**
- `batch-21/VERDICTS.md` and `batch-21/PLAN.md`.
- Every file under `batch-21/verifier-evidence/`:
  - `b21v_fresh.py` / `b21v_fresh2.py` with `fresh.out` / `fresh2.out` (the FAIL lines);
  - `b21v_unclosed.py` with `unclosed.out`;
  - `b21v_live*.py` with `live*.out`;
  - `b21v_035.py` with `l035-surface.out`.
- `batch-21/writer-evidence/` (TALLY.md, `b21w_live.py`).

### Item 1 — an unclosed fence at end of stream (regression; LEAD-030 and LEAD-036)

**Mechanism (confirmed in code).**
- `_seg_at` (agent_runtime.py:2125-2136) marks a fence with no closer `closed=False`, with `body_end = n`.
- When the round's stream ends, `_release(held)` judges that unit anyway.
- But `_guard_unit` (:2475) calls `_fence_body(row)`, and `_fence_body` (:2447-2450) always returns `lines[1:-1]`. So
  the last body line is dropped as if it were the closer.
- With a one-line dump (`~~~json\n{"pe": 31.7}\n`), the body is empty and has no figure, so the fence streams.

The tilde form regressed in batch-21: before that, the tilde line was not a fence, so it was judged as a sentence.

**Fix.**
- `_fence_body(text, closed)` drops the last line only when `closed` is true, meaning the stream saw a closer.
- `_guard_unit` passes `seg.closed`.
- An unclosed fence still open when the stream ends is then a complete unit: its last line is body, and no closer is
  consumed. It is judged and replaced exactly like a closed fence, in all-errored and in mixed turns.

**Checks.** No other change is expected. Rows or a list the stream ends in the middle of are already judged per row
at the flush, but pin them anyway (see the tests).

### Item 2 — short-name aliases (LEAD-030, errored AND ok subjects)

**Mechanism (confirmed).** Today `figure_grounding.aliases` gives:
- SBIN → {sbin, state, state bank, state bank of india};
- BHARTIARTL → {bharti, bharti airtel};
- LT → {larsen, larsen &, larsen & toubro}.

So rule 2b never sees "SBI", "Airtel" or "L&T" (fresh.out w-mixed-sbi-abbrev, fresh2.out n-BHARTIARTL.NS and
n-LT.NS).

**Fix.** Extend `aliases(base, user_text, names=())`, keeping every alias it gives today, with:
- **(a) The symbol base**, as today. `mentions` allows the exchange suffix.
- **(b) Each master name, and each extra name,** lower-cased with the corporate suffix stripped. This is as today,
  applied to the names in (e) and (f) too.
- **(c) The initialism.** Take the first character of each word of the stripped name, keeping `&` as its own token.
  - Always skip `of`, `the` and `and`.
  - Emit two forms: one keeping {limited, ltd, india, industries, corporation, company} and one skipping them.
    Examples: State Bank of India → SBI (and SB); Larsen & Toubro → L&T; Housing Development Finance Corporation →
    HDFC (and HDF); Tata Consultancy Services → TCS.
  - Only names of two or more words, and only initialisms of three or more characters (`&` counts). Two-letter forms
    like SB and BA are dropped.
  - Store the initialism upper-case and match it **case-sensitively** (see the notes: "it", "us" and "and" are
    English words). Symbol bases and name aliases stay case-insensitive.
- **(d) Every distinctive name token,** at least 4 letters and not in `_generic_tokens()` (the existing
  `_distinctive`). Today only the first token counts; now every token does. Bharti Airtel → bharti and airtel;
  Reliance Industries → reliance.
- **(e) Payload names.** Take every `name`, `longName` or `shortName` string in the call's own result JSON, ok or
  error, at any depth (walk it like `payload_numbers`). Feed these through (b)-(d).
- **(f) The user's own wording.**
  - Keep the existing rule: a distinctive name token that the user's text contains.
  - Add the marquee family keys (`_marquee_aliases`) whose `primary` is the base. For example, "l&t" and "larsen" →
    LT.
  - Add the `query` of any `resolve_symbol` call this turn whose result resolved to the base, meaning the noun phrase
    the resolver matched. Record it in `_dispatch_round` on a per-turn `{base: names}` map, and pass it as `names` to
    later `aliases()` calls.
  - A `resolve_symbol` call itself adds nothing to `ok_subjects` or `errored_subjects`. Its input has no `symbol`, and
    it must not be allowed to, because an ok resolve would otherwise shield a fabricated price.

**Matching.** Whole-word, and punctuation-tolerant: in `mention_end`, `&` matches `\s*&\s*`, so "L&T", "L & T" and
"Larsen&Toubro" all match.

A `ponytail:` comment records two ceilings: the private master reads, and a two-letter initialism floor.

### Item 3 — FAIL-SAFE rule 2c (Tier-3, recorded here)

**Rule.** In a turn with at least one errored call, an **ungrounded** figure is replaced by the honest note naming
the errored tool(s) (`_errored_note(ctx.errored)`) unless its clause or row attaches to an **ok subject**. A clause
attaches by ticker or alias: its own, or inherited from the paragraph (`ctx.subject`) or the colon intro (`context`).

This flips the burden to the ok side, so an alias form nobody foresaw fails safe. In `_judge_clause`, after rule 2b:

```python
if ungrounded and ctx.errored:
    attached = own if own is not None else inherited
    if attached is None or attached not in ctx.ok_subjects:
        return _errored_note(ctx.errored)
```

- Grounded figures stream anywhere (rule 3 returns first).
- An ungrounded figure attached to an ok subject streams. Derived values such as "TCS is up 1.2%" with TCS ok are the
  accepted concession.
- A negative clause with no ungrounded figure still streams (the batch-21 order is unchanged).

**The cost, accepted and documented.**
- A general-knowledge figure with no subject, in a turn where some call errored, is replaced. For example, "The Nifty
  fell 0.8% today." with price_data errored and no index tool ok.
- The same sentence in a turn with no errored call streams unchanged.
- One verifier TRUE line flips for this reason and only this reason: batch-21 `b21v_fresh.py` t-inherit-reset-blank,
  "The index rose 0.8% today." in a mixed INFY-errored turn. No tool carries that 0.8%, and it names no ok subject.
- W1 lists every probe TRUE line that flips, each with this justification. A flip for any other reason is a defect in
  the fix.

### Tests W1 pins BEFORE the fix

Each test fails on 93ba12da and passes after it. Record both runs in `batch-22/writer-evidence/`. Tests go in
`test_agent_runtime.py`, through the full `invoke_agent` relay (`_scripted_answer` with `prompt=` and a per-call
`input`), parametrised with one test per behaviour.

1. **Every FAIL line of `batch-21/verifier-evidence/fresh.out`, `fresh2.out` and `unclosed.out`.** A FAB line is
   replaced (the figure is absent and the note is present):
   - w-mixed-sbi-abbrev, n-BHARTIARTL.NS, n-LT.NS, f036-unclosed-tilde;
   - u-tilde-unclosed, u-backtick-unclosed, u-backtick-unclosed-prose.

   The TRUE lines stay unchanged, except t-inherit-reset-blank (see rule 2c).
2. **Unclosed fences at end of stream.**
   - ```` ```json ```` and `~~~json` dumps, all-errored → one note, with no orphan marker.
   - Mixed, on an errored subject → replaced.
   - Mixed, on an ok subject with grounded figures → the fence streams intact.
   - The stream ends mid-table (`| SBI | ₹812.40`, no newline) and mid-list, in an errored turn → replaced.
3. **Short names.**
   - Mixed turns where the user or model writes SBI, Airtel or L & T for an errored call → replaced.
   - "SBI is up 1.2%" with SBIN.NS ok (the 1.2% is derived) → streams.
   - "HDFC Bank closed at ₹1,712.90, up 0.4%" with HDFCBANK.NS ok → streams.
4. **Rule 2c.**
   - "The Nifty fell 0.8% today." with price_data errored → replaced.
   - The same sentence with no errored call → unchanged.
   - An alias form not in any list (for example "Big Blue" for errored IBM) → replaced. This is a case the fix is not
     written against.
5. **`test_figure_grounding.py`.** One parametrised test of the alias set:
   - SBIN ∋ SBI;
   - LT ∋ L&T;
   - BHARTIARTL ∋ airtel;
   - TCS ∋ TCS;
   - HDFCBANK ∋ hdfc bank;
   - a payload `longName` becomes an alias;
   - "it", "us" and "and" never match an initialism case-insensitively.
6. **Every existing test stays green.** That covers the LEAD-030/031/033/036 and AGENT-090 tests and all of
   `test_figure_grounding`. Nothing is deleted or weakened. Change a pinned expectation only when its premise was
   false, and put the rationale in the commit. The batch-20 "q?" false-premise lines stay as batch-20 accepted them.

### Checks (detached and polled; no call over ~120 s)

- **Focused tests.** `test_agent_runtime`, `test_figure_grounding`, `test_b5_runtime_history`,
  `test_tool_call_rescue`, `test_llm_ollama` and `test_b3_runtime_intent_gate`. Then run
  `ruff format --check sidecar && ruff check sidecar`, and the full sidecar pytest (detached).
- **Offline probes, with cwd `<tree>/sidecar`, on the fix sha.** Expect BAD 0 on FAB and TRUE lines, except the two
  accepted "q?" lines and the documented 2c flip(s):
  - `batch-17/verifier-evidence/b17v_probe{,2,3}.py`
  - `batch-18/verifier-evidence/b18v_probe{,_b,_c,_d}.py`
  - `batch-19/verifier-evidence/b19v_probe.py` (no arg, `2` and `3`)
  - `batch-20/writer-evidence/b20w_probe.py`
  - `batch-20/verifier-evidence/b20v_fresh.py`
  - `batch-21/verifier-evidence/b21v_fresh.py`, `b21v_fresh2.py` and `b21v_unclosed.py`

  Outputs go to `batch-22/writer-evidence/`.
- **Live bar.** Run a source sidecar on **127.0.0.1:52350**. Never use :52152-54 (the app) or :52310 (the verifier).
  Use llama3.1:8b through ollama with autonomy ask, following the pattern of `b21v_live.py`. Run at least 8 prompts:
  - the entry's SIFY TTM prompt;
  - a mixed turn where the user writes "SBI" and "Airtel", with price_data forced to error for one of them;
  - an all-errored multi-symbol ask phrased to invite a code block;
  - "reply with raw JSON only", which invites an unfinished dump;
  - at least 3 true controls: an ok figure with rounding, a short-name clause on an ok subject, and a user figure
    restated after an error.

  Put the transcripts and a tally in `batch-22/writer-evidence/`, each control checked against /quotes or
  /fundamentals.

## W2 — sonnet — a normalised no-tool matcher (R15-LEAD-035, second round)

**Why sonnet.** The spec is clear and the output is checkable: one planner pattern and one test file.

**Branch.** `worktree-agent-batch-22-W2`, from `93ba12da`. Run `git reset --hard 93ba12da` first.

**Owned files.**
- `sidecar/services/planner.py`
- `sidecar/tests/test_b3_runtime_intent_gate.py`

**Mechanism (confirmed).** `_NO_TOOL_CUE` (planner.py:136-141) is a closed phrase list, searched on `raw.lower()`
(:209-215):
- "Answer without any tools" has no verb;
- "Do not call a tool" does not match "a tool";
- "Don’t use any tools" has U+2019, and `don'?t` accepts only an ASCII apostrophe.

So `l035-surface.out` shows 55 tools, and the live runs made a `get_portfolio` call and a text-JSON write. The
runtime hunk is correct and is merged.

**Fix.** Replace `_NO_TOOL_CUE` with a normalised matcher, keeping the signal and return
`IntentResult("read", 0.95, ["no-tool"], False)`:

1. **Normalise.** `lowered.replace("’", "'").replace("‘", "'")` before the match.
2. **The clause.** No `.;!?` and no newline between the parts.
3. **NEG → VERB → OBJECT.**
   - NEG is one of {no, not, without, don't, do not, never, avoid, skip, please don't, refrain from}.
   - Then at most 3 filler words.
   - Then VERB, one of {call, calls, calling, use, uses, using, invoke, invoking, run, running, rely on, look up,
     lookup, fetch, search}.
   - Then only determiners {any, a, an, the, your, external}.
   - Then OBJECT, one of {tool, tools, function, functions, external data, lookups, searches}.
4. **NEG → OBJECT, without a verb.** {no, without, zero}, then determiners, then {tools, tool calls, tool use,
   function calls, external data, lookups, searches}.
5. **OBJECT → VERB-noun.** "(no|without|zero) (any )?(tool|function) (calls?|use|usage)", "tool-free" and "tool free".
6. **Standalone cues.**
   - (answer|just|only) … from (what I gave you|what I told you|the above|my numbers|this message);
   - from memory only;
   - without looking anything up.
7. **Not a match.**
   - An OBJECT followed by `except`, `other than`, `besides` or `but`, as in "no tools except price_data".
   - A named tool between VERB and OBJECT ("without calling the news tool", "don't use web search", "don't search the
     web"). This follows from the determiner-only gap and from "web" not being an OBJECT.

A one-line comment cites R15-LEAD-035.

### Acceptance tests (`test_b3_runtime_intent_gate.py`, through `_agent_tool_ids`)

**Parametrised → `set()`:**
- The three batch-21 verifier phrasings, verbatim from `b21v_035.py`:
  - "Answer without any tools: I sold 5 TCS shares at ₹3,100 each; …";
  - "Do not call a tool. I sold 5 TCS …";
  - "Don’t use any tools. …" with U+2019.
- The t-user-sale prompt, which is already pinned.
- At least 4 fresh phrasings. For example:
  - "Please refrain from using tools, just compute it";
  - "No tool calls — what is 5 × 3,100?";
  - "Answer only from the numbers in this message";
  - "Never invoke any functions for this";
  - "Give me a tool-free answer".

**Negative controls, where the surface is kept:**
- "Add 10 TCS at 3,200 to my portfolio" keeps `portfolio_add_position`.
- "Use the price tool for TCS.NS" keeps `price_data`.
- "What tools do you have?" keeps a non-empty surface.
- "Don't use web search, get TCS.NS price" keeps `price_data`.
- "Without calling the news tool, get TCS.NS price" keeps `price_data`. This one is already pinned.
- "No tools except price_data for TCS.NS" keeps `price_data`.

Every existing test in the file stays green. Also run `ruff format --check sidecar && ruff check sidecar`.

**W1 applies for W2.** Nothing this batch.

## Run order (integrator)

1. Create `worktree-agent-batch-22-int` from `93ba12da`. Merge `origin/worktree-agent-batch-22-W1`, then
   `origin/worktree-agent-batch-22-W2`, auditing only via `origin/`.
   - W1 may touch only its owned files plus `batch-22/writer-evidence/`.
   - W2 may touch only `planner.py` and `test_b3_runtime_intent_gate.py`.
2. There is no `types/data.ts` mirror, no frontend change and no Rust change. Run ruff and the full sidecar pytest
   (detached), then `pnpm ci-local` and `node scripts/smoke-test-sidecars.mjs`.
3. Coordination with the unmerged lows branches:
   - P1-W2 (runtime-catalog) edits `planner.py` in the PLAN_ACTIONS and prompt hunks, and edits
     `agent_runtime.py` and `test_agent_runtime.py`.
   - P3-W3 edits `symbol_resolver.py`, which W1 only reads.

   Batch-22 merges first. The lows integrators resolve any overlap and re-run `test_agent_runtime`,
   `test_figure_grounding` and `test_b3_runtime_intent_gate`.
4. A fresh-context verifier checks the Acceptance below.

## Acceptance (what the verifier certifies)

- **LEAD-030.** On the running app with llama3.1:8b, the following stream 0 fabricated figures in any shape:
  - the entry's own prompt;
  - at least 3 fresh error-shaped prompts of the verifier's own: one naming a subject by a short name or an
    initialism, one inviting an unfinished code block, and one all-errored multi-symbol ask.

  Also required:
  - At least 3 true controls stream unchanged: a user-figure restatement, an ok-tool figure with rounding, and a
    short-name clause on an ok subject.
  - The b17-b21 offline probes report BAD 0 on FAB and TRUE lines. The two accepted "q?" lines are excepted, and so
    are the 2c flips W1 documented, which the verifier concurs with or rejects.
  - At least one fresh phrasing the writer did not pin is tried.
- **LEAD-035.** Every no-tool phrasing the verifier invents (at least 4, including the three from batch-21) produces
  no tool call and no staged write, live. A normal portfolio add still stages the write behind review. A named-tool
  exclusion keeps the other tools.
- **LEAD-036.** Closed and unclosed fences of both forms render the note as prose, with no orphan marker.

## Notes (Tier-3 decisions)

- **Rule 2c.** An ungrounded figure attached to no ok subject is replaced in any turn with an errored call. It is
  fail-safe by design. Its cost: general-knowledge figures with no subject in such a turn are replaced
  (t-inherit-reset-blank flips).
- **Initialisms match case-sensitively in upper case.** The lead note said case-insensitive. Under 2c, an ok-side
  initialism that is also an English word ("it", "us", "and") would attach any ungrounded figure to an ok subject and
  leak it. The model writes initialisms upper-case. There is also a floor of three characters.
- **`resolve_symbol` never adds a subject.** It only contributes its `query` as a name, so an ok resolve cannot
  shield a fabricated price.
- **Known residual, out of scope.** When one subject is ok on one tool and errored on another (TCS price ok,
  fundamentals errored), an ungrounded TCS P/E counts as attached to an ok subject and streams. This comes from
  per-subject rather than per-(tool, subject) grounding, and has been the case since batch-20.
