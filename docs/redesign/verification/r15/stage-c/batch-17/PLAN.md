# R15 Stage C: batch 17 plan (rc1 residual)

Base: `004-r4-experience-rebuild` @ `5d4ca99c325d1a6623231a9c8e6c49c8b6262607`.
Planner: Opus. The queue after adjudication is `{critical:0, high:1, medium:0, low:211}`. The register has one open c/h/m
entry, R15-LEAD-030 (high, agent-chat). R15-LEAD-031 (low, agent-chat) rides along because it shares the streaming surface
(lead note). No other entry is selected, because every other open low belongs to the lows waves. `LOWS_TRIAGE.json` has no
row for LEAD-031, since it was filed after that triage.

| id | sev | operator area | item | writer |
|---|---|---|---|---|
| R15-LEAD-030 | high | agent-chat | A (a)-(d) | W1 |
| R15-LEAD-031 | low | agent-chat | B | W1 |

Nothing is deferred and nothing is proposed as not-a-defect. Both mechanisms were confirmed in the code at the base sha
and against batch-16's `verifier-evidence/` (lead030-1, followup-1, probe.out, b16v_probe2/3, orig-2).

## W1 (opus): one writer set

**Why Opus.** This is the second Opus attempt on LEAD-030. The work sits in the runtime's streaming relay
(`_consume_round`/`_release`, per-round `dump_depth`, per-turn `_TurnState`), which is a state machine that rewrites
every sentence chat, Delegate and MCP invoke stream. An over-replacement there is a trust regression the user can see in
agent-chat, and batch-16 shipped exactly that. Item B changes how both adapters stream text.

**Files (W1 owns every one; no other writer exists, so there are no collisions or mirrors)**
- `sidecar/services/agent_runtime.py`
- `sidecar/services/llm/tool_call_rescue.py`
- `sidecar/services/llm/ollama.py` and `sidecar/services/llm/openai.py`. The only change is the two `hold.feed(...)`
  call sites in each, which move from `shown = …` to `for shown in hold.feed(...)`. The planner added these files beyond
  the lead's list because the re-chunk the lead asks for cannot reach the wire without them.
- `sidecar/tests/test_agent_runtime.py`, `sidecar/tests/test_tool_call_rescue.py`, `sidecar/tests/test_llm_ollama.py`
- `docs/redesign/verification/r15/stage-c/batch-17/writer-evidence/**` (optional)

The change needs no edits to `types/`, the catalog, the schemas, `copilot.json` or any frontend file.

### A. R15-LEAD-030: a fabricated tool-result citation

The spec is batch-16 `VERDICTS.md` §"R15-LEAD-030: not certified" plus its fix shape. Every piece is in
`_guard_tool_citations` (agent_runtime.py ~1961) and its callers.

**(c) First, the per-turn `ok_tools` over-replacement (the regression).**
- *Mechanism.* `turn = _TurnState()` in `invoke_agent` (~2640) starts `ok_tools` empty on every turn. In followup-1 the
  history showed that `fundamentals` returned AAPL's market cap in turn 1. Turn 2 made no tool call, so the true
  "The tool that provided the market cap figure was `fundamentals`, which returned:" was replaced by the false
  "…returned no data for this in this session."
- *History as it arrives.* The client (`src/store/chat-history.ts` `withTrailer`) appends `[tool steps: <s1>; <s2>]` to
  each assistant turn. Each step is the label `readToolLabel` (`src/modules/chat/ChatSidebar.tsx:288`) builds:
  `Using <id with _ → space>`, plus the two fixed labels "Reading what you're looking at" (`get_terminal_state`) and
  "Reading your portfolio" (`get_portfolio`). `_coerce_history` keeps these lines verbatim, including when it folds them
  into the summary message as `- [tool steps: …]`.
- *Fix.*
  1. In `_prepare_run`, after `_coerce_history`, parse every `[tool steps: …]` line of the history messages. Split the
     steps on `;`. Map each step to a tool id: strip `Using `, lowercase it, turn spaces and hyphens into `_`, and keep
     it only if it is a known id. Map the two fixed labels directly.
  2. Carry the parsed set on `_RunSetup` and seed `_TurnState(ok_tools=…)` with it.
  3. Change the replacement text from "…in this session." to "The {T} tool returned no data for this in this turn."
     (and the generic "No tool returned data for this in this turn."). It is then true on every path. That includes
     MCP invoke, Delegate, and history without a trailer, where seeding is impossible.
  4. Update the two existing expectations in `test_a_citation_of_a_tool_that_returned_nothing_ok_is_replaced` (lines
     ~2482 and ~2494) to the new wording. This is a spec change to the text, not a weakened assertion, so log it in the
     report.
  5. Add a `ponytail:` comment naming two ceilings. First, the trailer records tools that were called, not tools that
     returned ok, so a follow-up citing a tool that errored in an earlier turn is kept. Second, `research` has no
     tool-step line (the client renders its ResearchActivity instead), so citing an earlier `research` run is replaced
     with the "this turn" wording, which stays true.
- *Test (`test_agent_runtime.py`).* Extend `_scripted_answer` (or add a sibling) to take `history` and a no-tool round.
  - The history is `[user "AAPL market cap?", assistant "AAPL's market cap is $3.44 T.\n\n[tool steps: Using
    fundamentals]"]`. Turn 2 calls no tool and streams followup-1's shape: `"The tool that provided the market cap
    figure was `fundamentals`, which returned:\n\n"`, `"{\n"`, `' "market_cap": 3440000000000\n'`, `"}"`. The whole
    stream must come through untouched.
  - The case the fix was not written against: history `[tool steps: Using financial statements]` and a turn-2
    "The financial_statements output shows revenue of ₹4,411 cr." are kept. The same sentence with no trailer in the
    history is replaced with the "in this turn" text.

**(a) Humanised tool names.**
- *Mechanism.* `ref` builds its alternation from the literal ids (`re.escape(t)`), so "Price Data", "price data",
  "price-data" and "Financial Statements returned" never match. Live, lead030-1 streamed
  `Price Data: {"ok": true, … "latest_price": 2.11 …}` for a `price_data` tool that was never called. The real price was
  13.41.
- *Fix.* In the id alternation used by the backtick branch and the follower branch
  (`tool|returned|results?|output|data` or `[:=]` then `{`/`[`), each id's `_` becomes `[\s_-]`. The match stays
  case-insensitive, and the matched text normalises back to the id before the `ok_tools` lookup. Keep the bare,
  no-follower branch literal-underscore-only. Plain prose such as "I don't have price data" must stay out of scope.
  Evaluate the claim cue on the sentence with the matched reference blanked, so the "data" inside "price data" does not
  cue the sentence by itself.
- *Test.* The pinned inputs are "Price data returned a close of $2.11." and the live `Price Data: {"ok": true, "symbol":
  "SIFY.US", "latest_price": 2.11}\n\nUnfortunately, I am unable.`, where only `financial_statements` is ok. Both are
  replaced, and neither `2.11` nor `latest_price` streams. The cases the fix was not written against are "The
  Fundamentals Tool shows revenue of $1320 m." and "Per `price data`, the close was $2.11." (both replaced), plus "I don't
  have price data for SIFY yet." (kept).

**(b) The dump on the next line after a replaced `…:`/`…=` citation.**
- *Mechanism.* `_SENTENCE` ends a sentence at `\n\s*`. For "- fundamentals returned:\n{\n …$1320 m…}" the replaced
  sentence holds no bracket, so `depth` is 0 and the dump streams (b16v_probe3, followup-1).
- *Fix.* When a replaced sentence opens no bracket and its `rstrip()` ends in `:` or `=`, leave the round in a
  "dump pending" state rather than depth 0. `dump_depth` is already nonlocal across `_release` calls in
  `_consume_round`, so the state carries across chunks and releases. In that state, whitespace-only text is passed
  through (or dropped, the writer picks). If the first non-whitespace character is `{`/`[`, enter normal depth tracking
  from it and drop until balanced. Any other character clears the state and keeps the text. It still resets every round.
- *Test.* Run `_LIVE_1_DUMP` with the `{` moved onto its own chunk after `"- fundamentals returned:\n"`, with fundamentals
  errored. Neither `$1320` nor `trailing_12m_revenue` streams, and "Revenue is shown above." does. The case the fix was
  not written against is `"The price_data output =\n"`, `"[\n {\"close\": 2.11}\n"`, `"]\n"`, `"Done."` with `price_data`
  never called. It gives the replacement, then "Done.", and no `2.11`. A colon-ended replaced sentence followed by prose
  ("…returned:\n", "Revenue grew.") keeps "Revenue grew.".

**(d) Figure-less pre-call narration.**
- *Mechanism.* "Let me look up the fundamentals data for SIFY." and "Next I'll check the news data for any sentiment."
  match `ref` (`fundamentals data`, `news data`) and `_CITATION_CUE` (`data`), so the guard replaces them before any
  call (probe.out). The same happens to "Let me fetch the `financial_statements` data for SIFY." with any `ok_tools`.
- *Fix.* Keep a sentence that has no currency figure (`_CURRENCY_FIGURE`), no `{`/`[`, no result verb
  (`returned|shows?|showed|reports?|says|according to`) and an intent cue
  (`let me|let's|I'll|I will|I'm going to|I am going to|I need to|we'll|next,? I|going to|about to`).
- *Test.* The two probe.out sentences are kept whether `ok_tools` is empty or holds another tool. The cases the fix was
  not written against are "I'm going to pull the `financial_statements` data for SIFY next." (kept), and "Let me recap:
  `news` data shows revenue of $5 bn." with `news` never called (replaced, because a figure and a result verb are
  present).

**Order:** (c), then (a), (b), (d). Use one commit per sub-item, or one for A, and push each to
`origin/worktree-agent-batch-17-W1`. Each new test must FAIL on base `5d4ca99c` (or on d64640d2, the batch-16 guard) and
pass after. The report states this per test.

### B. R15-LEAD-031: the partial tool-call marker shows before the hold

- *Mechanism* (batch-16 PLAN item D, reconfirmed in the code). `LeakHold.feed` holds only once `_MARKER` fully matches,
  and the JSON form needs the closing quote after the name. Fed sify-1's chunks `' {"'`, `'name'`, `'":'`, `' "'`,
  `'price'`, `'_data'`, it shows ` {"name": "price_data` before holding. Live orig-2 streamed
  `{"name": "fundamentalsSIFY's …`.
- *Constraint.* `test_llm_ollama.py::test_text_that_is_not_a_rescued_call_streams_whole` pins exact 4-char pass-through
  for `…elsewhere; {"name": "screener_run"} is not mine.` with `write_note` and `price_data` offered. Its chunk `'; {"'`
  ends in a partial marker, so any hold must replay the original chunks as they were.
- *Fix* (`tool_call_rescue.py` plus the adapter call sites).
  1. Change `feed` to return `list[str]`.
  2. While nothing is held, if the text ends in a partial marker whose ident part is still a prefix of an OFFERED name,
     hold back the WHOLE chunks from the one where the partial starts. A partial marker is `{` plus a prefix of
     `"name": "<ident>`, or a trailing `\b<ident>` that is a proper prefix of an offered name.
  3. On the next feed, if the tail no longer matches, return the held chunks as they were plus the new one. If
     `leak_start` now fires, hold from its offset as today, and show whatever comes before it as one piece. `held()`
     already returns `text[_shown:]`, so no text is lost at end of stream.
  4. Change the adapters to `for shown in hold.feed(event.text): yield LLMDeltaEvent(text=shown)` at both sites in
     `ollama.py` and both in `openai.py`.
- *Tests (`test_tool_call_rescue.py`).*
  - With sify-1's JSON chunking, no shown chunk contains `{` or `price`.
  - The call syntax `price`, `_data`, `(symbol="SIFY")` never shows `price_data`. The fix was not written against this
    case.
  - Feeding `"The price"`, `" is up."` gives shown text plus `held()` equal to the input.
  - Unoffered `'; {"'`, `'name'`, `'": "'`, `'scre'` come back as those same four chunks.
  - The existing `test_llm_ollama.py` assertion stays byte-for-byte and must pass unmodified. Never weaken it. If it is
    genuinely wrong, fix it and log why.

## Acceptance for W1 (focused only; writers never re-verify)

Run each file detached and poll it:
`sidecar/.venv/bin/python -m pytest sidecar/tests/test_agent_runtime.py sidecar/tests/test_tool_call_rescue.py
sidecar/tests/test_llm_ollama.py sidecar/tests/test_llm_openai.py -q`.
Keep every tool call under about 120 s. Before each commit, run `ruff format <files>`, `ruff format --check sidecar` and
`ruff check sidecar`. Push every deliverable to `origin/worktree-agent-batch-17-W1`. The branch starts from `5d4ca99c`:
run `git reset --hard 5d4ca99c` in the worktree first, then check `git merge-base`.

## Integrator run order

1. Fetch `origin/worktree-agent-batch-17-W1` and audit that its merge-base is `5d4ca99c`. Then merge it into 004 with
   `--no-ff`.
2. Run `pnpm sidecars:build` (it is staleness-aware; the main sidecar rebuilds). Then run `pnpm ci-local` detached and
   poll it, then `node scripts/smoke-test-sidecars.mjs`.
3. The verifier (fresh context) works on the running sidecar with llama3.1:8b through ollama, autonomy ask. It must:
   - run the lead030-1 prompt ("What is SIFY's TTM revenue in USD? Cite the tool you got it from.") at least 3 times.
     No fabricated `<tool> returned`/dump citation may stream for a tool that was not ok, whether the name is literal or
     humanised.
   - run a two-turn chat where turn 2 cites turn 1's ok tool. The history must be sent as the client sends it
     (`historyForSend`, trailer included), and the true citation must stream untouched.
   - run a humanised-name fabricated dump offline (`_guard_tool_citations` plus the relay). It is replaced and no dump
     streams.
   - run a pre-call narration. It streams untouched.
   - run at least one fresh case of its own that the fix was not written against, in both directions.
   The claim to certify: no fabricated tool-result citation streams, and no true citation is replaced.
   For LEAD-031, re-drive orig-2's shape. No `{"name": "` fragment may reach the client.
