# R15 Stage C — batch-19 plan

Base: `004-r4-experience-rebuild` @ `c5a6ade847ae73743877784b358b460235ba3408` (no `sidecar/` or `src/`
diff from the batch-18 merge head `ebc5ed41`). Selection: the one open critical/high/medium entry after
adjudication, R15-LEAD-030 (high, agent-chat). No lows: 'low' is not among this batch's severities, so
`LOWS_TRIAGE.json` is not applied; the lows belong to the lows waves. One writer set.

## W1 — opus — agent-runtime streaming citation guard (R15-LEAD-030)

Why opus: risk-adjacent. This is the agent runtime's streaming guard, meaning the stream holder in
`_consume_round` and the per-turn provenance state in `_TurnState`. A wrong hold or replace here either
leaks fabricated figures or replaces true answers on every chat.

Branch: `worktree-agent-batch-19-W1`, made from base `c5a6ade8` (run `git reset --hard c5a6ade8` first; see the
agent-worktree base hazard). Push every deliverable.

Owned files: `sidecar/services/agent_runtime.py` and `sidecar/tests/test_agent_runtime.py`. The fix does not need
the adapter's `LeakHold`. The two surviving shapes are judged after the adapter, in the runtime's own holder, so
`sidecar/services/llm/tool_call_rescue.py` and its test are **not** owned or touched. Evidence goes under
`docs/redesign/verification/r15/stage-c/batch-19/writer-evidence/`.

STRATEGY (lead): do **not** extend the attribution regexes (`_tool_reference`, `_ATTRIBUTES`, `_CLAUSE_BREAK`,
`_NEGATIVE`). Every attribution shape holds, and the batch-17 probes are BAD 0. Both surviving shapes are
a result-shaped block that has no ok source.

### Mechanism (confirmed in code at c5a6ade8)

- `_consume_round._release` releases the held text at each `_SENTENCE_BOUNDARY` (`[.!?]\s+|\n`).
  `_guard_tool_citations` then splits the text with `_SENTENCE` (`.*?(?:[.!?]\s+|\n\s*|\Z)`) and judges
  each sentence alone in `_guard_sentence`.
- Shape 1 (`v030-sify-orig`, `probe-d.out` d-sify-i-get-dump and the fresh d-fresh-here-is-what-x-gave for
  WIPRO.NS): the sentence is "After calling the `financial_statements` tool for SIFY's annual revenue, I get:\n\n".
  It names financial_statements, which errored, but it is not *cited*. `_ATTRIBUTES` after the id sees
  " tool for", which is neither a verb nor `:`. It has no figure and no bracket, so the sentence is kept. The
  JSON dump `{"ok": true, "value": {"ttmRevenueUsd": 164600000}}` is the NEXT `_SENTENCE` after the
  blank line. It has no tool reference and `pending` is False, because the call's result has already
  arrived (round 2). The dump therefore streams.
  `DUMP_PENDING` only covers a dump after a *replaced* colon sentence.
- Shape 2 (`v033-infy-t1`, `probe-c.out` c-infy-results-list and the fresh c-results-list-hdfc):
  the text is "Here are the results:\n\n* INFY.NS: ₹1,233.65\n* TCS.NS: ₹3,235.50". No tool is named, so `inside` is empty.
  The generic branch needs `_GENERIC_TOOL_REF` ("tool results"/"the tool returned"), or `pending`. Neither holds,
  so each bullet streams. At that point `turn.ok_tools` is empty and price_data's only call errored with
  invalid args. The turn does not track that errored call: `_dispatch_round` only adds ok names at
  `turn.ok_tools.add`.

### Fix (root cause: a result block is judged apart from what introduces it, and an all-errored turn is not known)

1. **Colon binding.** A sentence whose text ends in `:` after `rstrip()` binds the following paragraph,
   blank lines after the colon included. The paragraph runs up to the next blank line (`\n\s*\n`) or the
   end of the text. Stream holder: in `_consume_round`, a delta's release `cut` never passes the start of
   an open bound unit. An open unit is a colon-terminated sentence whose following paragraph has not yet
   closed. The unit goes to `_release` whole once its paragraph closes, or at the round's end, which is any
   non-heartbeat event or the stream closing. This is what already happens to `held`. Guard: in
   `_guard_tool_citations`, merge that colon sentence and its paragraph's sentences into one unit for
   `_guard_sentence`. In `_guard_sentence`, `cut` = min(first bracket, end of the colon sentence), because the
   bound paragraph belongs to the intro's last clause, as a dump does now. `figure` also counts
   `_result_block(bound paragraph)`. After that, the existing rule decides shape 1 unchanged: every reference in the
   clause is non-ok and the clause has a figure or dump, so the unit is replaced by "The financial_statements tool returned no data
   for this in this turn." A unit whose tools are ok, or seeded from history, streams unchanged.
2. **All-errored turn.** Add `errored_tools: set[str]` to `_TurnState` and fill it where `outcome.ok` is
   False in `_dispatch_round`. Invalid-args calls already get an ok:false `tool_result`. Pass it to the
   guard. New branch in `_guard_sentence`: if `not inside`, `ok_tools` (after the pending subtraction) is empty,
   `errored_tools` is non-empty, and the clause is result-shaped, replace it with
   "The {sorted errored tools joined} tool(s) returned no data for this in this turn". Result-shaped means it
   contains a `{`/`[` dump, or its bound paragraph is a `_result_block`. This rule never fires while any ok
   tool exists (the existing clause rules apply then) and never on prose figures without a result shape.
   Value fidelity is out of LEAD-030's claim.
3. `_result_block(text)` is one small predicate: at least 2 lines that each carry a name then a figure. Each
   line has an optional bullet or number, a symbol or metric name that starts with a letter (≤~40 chars), a
   `:`/`=`/dash separator, then a number with an optional currency mark, `%` or unit. Brackets are already
   counted by the existing `cut`.
   `ponytail:` a label-less bare list with no colon intro is not bound, so it streams line by line. Add
   binding when one is seen live.

### Tests (sidecar/tests/test_agent_runtime.py, via `_scripted_answer`)

These must FAIL on `ebc5ed41` (the same guard as c5a6ade8) and PASS after the fix. Record both runs.

- Pin `v030-sify-orig`: financial_statements returns `{"ok": false, "error": "invalid arguments ... 'ttm' ..."}`.
  Stream the transcript's text chunked mid-word and with the blank line split across chunks. The answer has no
  `ttmRevenueUsd`/`164600000` and carries the financial_statements note. The opening "It looks like I made an error ...
  correct arguments." sentence streams unchanged.
- Pin `v033-infy-t1`: price_data errors on invalid args. The answer has no `1,233.65`/`3,235.50` and carries a price_data
  note. "To fetch the latest prices, I need to call `price_data` again ..." and the closing prose stream unchanged.
- Class cases not written against: (a) compare_symbols errored, with "Checking `compare_symbols` for INFY and TCS, here's the
  output:\n\n- INFY P/E: 24.1\n- TCS P/E: 29.8". (b) price_data errored, with "I got:\n1. RELIANCE.NS = 2,950.10\n2.
  HDFCBANK.NS = 1,610.40", chunked mid-line. (c) A tool never called while another is ok: "Running the `price_data`
  tool, I got back:\n\n{\"close\": 2.11}" with only fundamentals ok. All three are replaced.
- Controls that must stream unchanged: the same generic list with price_data **ok**; the same list with price_data
  seeded from a `[tool steps: Using price data]` history trailer; the same list with **no** tool call at all;
  "Here is the plan:\n- fetch INFY\n- fetch TCS" after an errored call (no figures); prose "You said you bought at
  ₹1,500." after an errored call.
- Every existing LEAD-030/031/033 and AGENT-090 test stays green, with no deletion and no weakening. If a pinned
  expectation must change, the commit states why.

### Checks (detached and polled; no single call over ~120 s)

- Focused runs: `test_agent_runtime.py`, `test_b5_runtime_history.py`, `test_tool_call_rescue.py`, `test_llm_ollama.py`.
  Also `ruff format --check sidecar && ruff check sidecar`.
- Offline probes, run with cwd `<tree>/sidecar`: `batch-17/verifier-evidence/b17v_probe.py`, `b17v_probe2.py`,
  `b17v_probe3.py` (expected BAD 0), plus `batch-18/verifier-evidence/b18v_probe.py`, `b18v_probe_b.py`, `b18v_probe_c.py`,
  `b18v_probe_d.py` (expected BAD 0 on c and d).
- Live bar: sidecar from source on **:52350** (the lows waves hold :52320/:52330/:52340, and :52152–:52154 is the
  running app; touch none of them). Use llama3.1:8b through ollama with autonomy ask; `batch-18/verifier-evidence/b18v_live.py` is the
  pattern. Run at least 8 prompts. They must include SIFY's TTM revenue in USD (the entry's own prompt), the WIPRO.NS fundamentals case,
  and a two-turn INFY/TCS price run with price_data forced to error. Add at least 3 true-citation controls that must stream unchanged:
  a real ok tool's figures, a Reuters/Morgan-Stanley style plain-English lead-in, and a user-supplied figure restated. Save
  transcripts and a tally under `batch-19/writer-evidence/`.

## Run order (integrator)

1. Merge `origin/worktree-agent-batch-19-W1` into a `worktree-agent-batch-19-int` made from `c5a6ade8`. Audit only through
   `origin/`. The diff must touch only the two owned files plus `batch-19/writer-evidence/`.
2. Run `ruff format --check sidecar`, `ruff check sidecar` and the full sidecar pytest (detached). No frontend or Rust file changes,
   so vitest and cargo are unaffected.
3. Fresh-context verifier. On a running app with llama3.1:8b, the entry's own prompt plus two fresh error-shaped prompts stream 0
   fabricated result blocks. At least 3 true controls stream unchanged (0 true replaced). The batch-17 probes show BAD 0.

## Deferred / not-a-defect

None. No other c/h/m entry is open.
