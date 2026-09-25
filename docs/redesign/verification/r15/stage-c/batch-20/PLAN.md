# R15 Stage C — batch-20 plan

Base: `004-r4-experience-rebuild` @ `d685a4be3a9f3fd670079aeefd2839349be8073a`. It has no `sidecar/`, `src/` or
`src-tauri/` diff from the batch-19 merge `ec7f7cd6`, so "failing on ec7f7cd6" and "failing on the base" are the same
test. Selection: the open critical/high/medium entries after adjudication are R15-LEAD-030 (high, agent-chat) and
R15-LEAD-035 (medium, agent-chat). R15-LEAD-036 (low, agent-chat) was filed from the batch-19 residuals on the same
streaming guard, so it rides W1 under the lead note (same file, same writer). LEAD-035 is deferred (see below). The
lows are not triaged here; they belong to the lows waves. There is one writer set.

## W1 — fable — figure grounding for the streaming citation guard (R15-LEAD-030, R15-LEAD-036)

Why fable (the lead's routing, change 5): this is a root cause that five Opus writers failed to fix with five
shape-based rules. Each time, a fresh verifier found a new shape that leaked. It is also risk-adjacent: it is the
runtime's stream holder and the per-turn provenance state. Run one strongest-tier agent at a time, at high effort.

Branch: `worktree-agent-batch-20-W1`, made from `d685a4be`. Run `git reset --hard d685a4be` first, because of the
agent-worktree base hazard. Push every deliverable.

Owned files (exact):
- `sidecar/services/agent_runtime.py`
- `sidecar/tests/test_agent_runtime.py`
- `sidecar/services/figure_grounding.py` (NEW): figure extraction, normalisation, the grounded-value set and
  precision matching, as pure functions. agent_runtime.py is already 3006 lines, so the numeric parsing lives here.
- `sidecar/tests/test_figure_grounding.py` (NEW)
- `sidecar/services/llm/tool_call_rescue.py` and `sidecar/tests/test_tool_call_rescue.py`: touch these ONLY if the live
  bar proves the stray `}` seen in batch-19's t-rel-list came from the adapter's `LeakHold`. The offline replay shows no
  `}` (`batch-19/verifier-evidence/probe-fresh3.out`), so it is likely the runtime's DUMP_PENDING drop, which this
  rewrite removes. If W1 does not touch them, say so in the report.

Evidence: `docs/redesign/verification/r15/stage-c/batch-20/writer-evidence/`.

### Mechanism (confirmed in code at d685a4be, not taken from the titles)

- `_consume_round` (agent_runtime.py ~2539) holds delta text and releases it at `_SENTENCE_BOUNDARY`. It also holds a
  colon sentence until a blank line closes its paragraph (`_open_bound`, ~2105). `_release` runs `_guard_ratio_claims`,
  then `_guard_tool_citations(text, ok_tools - pending, tool_ids, depth, pending, errored_tools)` (~2117). That splits
  the text by `_SENTENCE` and judges each sentence, plus a bound paragraph, in `_guard_sentence` (~2180).
- `_guard_sentence` decides by SHAPE:
  - `figure` = `_CURRENCY_FIGURE` or a bracket, `_result_block` (≥2 `_RESULT_LINE` lines) or a `{`/`[` bound paragraph;
  - the all-errored branch fires only on `_result_block`/`_DUMP_OPEN`.

  The batch-19 escapes follow directly from this:
  - A fenced dump (```` ``` ```` first) is not `{`/`[`-led, so it is never result-shaped: f-uncalled-colon-fenced and
    f-mixed-errored-named-fenced stream.
  - A markdown table row (`| SBIN.NS | ₹812.40 |`) and an annotated bullet (`* INFY.NS: ₹1,233.65 (up 1.2%)`) fail
    `_RESULT_LINE`'s `$`-anchored figure tail: f-allerr-table and f-allerr-bullets-annotated stream.
  - `_result_block` also matches the user's own figure list, so t-err-user-figures-list and
    t-err-user-position-summary are over-replaced.
  - A tool id inside a JSON string (llama narrating its own call, t-live-rel-list-replay) counts as a reference, and the
    bracket makes `figure` true, so the note is false.
  - b18v_probe_b x-news-data-shows: "The news data shows AAPL rose 3% to $190." matches `news` + " data shows" as a
    citation of the `news` tool, which was never called. web_search ran ok and its snippet carries 3% and $190. The
    guard has no notion of what the model could know, so it cannot see that the sentence is true. The humanised name
    and the round are not the cause.
- The turn state it needs is partly there. `_TurnState.ok_tools` is seeded with `run.cited_tools` (history trailers)
  and `errored_tools` is filled in `_dispatch_round` (~2851). There is no record of values or of call subjects.
  History carries only user/assistant text (`_coerce_history`, ~571): no tool payloads, and trailers name tools only.

### Fix (root cause: judge a figure by whether anything the model was given carries it, not by the text's shape)

1. **GROUNDED, per turn** (`figure_grounding.py` + `_TurnState`):
   - Seed at turn start from `run.messages` (in `invoke_agent`, where `_TurnState(ok_tools=set(run.cited_tools))` is
     built), taking every message except assistant turns and except the agent's own `spec.system_prompt` (static
     instructions whose example figures must not ground a fabrication). That covers the user's messages, the folded
     summary, the session preamble, the terminal/context preamble (PRIOR STATED VALUES included) and the
     earlier-tools note.
   - Extend in `_dispatch_round` with every tool result: walk the parsed payload recursively (numeric leaves, e-notation
     included, plus numbers inside string leaves with their scale words), and also scan the model-facing content (the
     display strings `_model_facing_content` gives, such as "₹12.1 lakh cr").
   - Errored results ground too (Tier-3, recorded): the numbers are what the tool literally sent ("HTTP 429"), so a
     restatement is true.
   - Keep the user/context values in a separate set, used for derivations (step 2).
2. **FIGURE** = a number with a currency sign or code, a `%`, a decimal point, thousands separators (`1,233.65`,
   `2,30,000`), or ≥3 digits, optionally followed by a scale word (k, lakh, crore/cr, mn/million/m after a currency,
   bn/billion, tn/trillion, lakh crore). It is normalised to a decimal with its precision (decimal places of the written
   mantissa).
   - Not figures: bare years 1900–2099, dates and times (`2026-09-25`, `10:30`), list numbering (`1.` at line start),
     bare integers <100 without a currency or `%`, and digits inside a symbol or tool id (`500325.BO`, `20-F`, `Q3`,
     `FY24`).
   - **Grounded** when some grounded value g matches at the figure's own precision: |figure − g| ≤ ½·10^(−dp), tested
     on the mantissa and on the scaled value. So 812.4 grounds "₹812.40"; 2300000000000 grounds "2.3 trillion" and
     "₹2.3 lakh crore"; 44110000000 grounds "₹4,411 cr"; and 0.012 or 1.2 both ground "1.2%".
   - A figure is also grounded when it equals, at its precision, a sum, difference, product, quotient or percent change
     of TWO user/context values. For example, "That is ₹15,000 in total" after the user gave 10 at ₹1,500.
   - `ponytail:` derivations use user/context values only. Tool values ground by direct match, because pairwise
     combinations of hundreds of payload numbers would ground almost any fabricated figure.
3. **RULE 1 — all-errored turn** (≥1 errored call and `ok_tools`, seeded ones included, empty after the pending
   subtraction):
   - Every unit that contains an ungrounded figure is replaced by the note naming the errored tool(s). A unit is a
     prose clause/sentence, a list item, a table row, a fenced block or a JSON block.
   - The wording stays exactly as the probes and tests expect: "The X tool returned no data for this in this turn."
     (plural form as now).
   - There is one note per block, never one per line. Consecutive replaced units in one block or paragraph collapse to
     that one note, and a block that is already replaced emits nothing more.
   - Everything else streams unchanged. The class is shape-agnostic by construction.
4. **RULE 2 — any other turn.** A unit is replaced when either condition holds:
   - (a) It CITES a tool (existing `_tool_reference` + `_ATTRIBUTES`/lead-in) that errored or was never called and is
     not seeded, and it carries an ungrounded figure or a payload. The payload branch is the existing attribution guard
     for figure-free text. A tool id that only appears as a JSON string value is a mention, not a citation.
   - (b) It carries an ungrounded figure attached to a SUBJECT of an errored call. The subject is the call's
     `symbol`/`symbols` argument, matched case-insensitively as a word with or without the exchange suffix
     (SBIN ≡ SBIN.NS ≡ sbin). It counts in the same clause, list item or table row, or in the colon-intro sentence that
     binds the paragraph (batch-19's binding stays). A subject that also has an ok call this turn is an ok subject.

   Figures attached to an ok subject, and grounded figures anywhere, stream.

   Keep the existing "no tool at all + generic 'the tool returned $X'" branch and the `pending` bare-dump/"Returned:"
   branch, but gate their figure test on UNGROUNDED figures.
5. **RULE 3 — never replace** a unit whose figures are all grounded. A figure-free unit only goes through the
   attribution guard (4a without a figure). This fixes both x-news-data-shows and t-live-rel-list-replay.
6. **BLOCKS in the stream holder.** `_open_bound` generalises to "where the first still-open block starts". These are
   each held as ONE unit:
   - a fenced block (```` ``` ```` to ```` ``` ````);
   - a markdown table (contiguous lines starting with `|`);
   - a list (contiguous `-`, `*`, `•` or `N.`/`N)` lines);
   - a multi-line JSON object/array (bracket depth > 0);
   - a colon-intro sentence and its following paragraph/block.

   Blocks are released whole when they close, or at the round's end as now. Prose clause holds stay as they are, so
   latency is added only while a block is open.

   Tables and lists are judged per row (a table's header and separator rows follow their rows): rows that are ok or
   grounded stay, the others go, with one note per block. If every figure row goes, one note replaces the whole block
   and its colon intro. A replaced fenced block loses its fence markers too, so the note renders as prose
   (**R15-LEAD-036**).

   Result-shape detection (`_result_block`, `_DUMP_OPEN`) stays only as a secondary trigger for figure-free payloads
   under 4a. `DUMP_PENDING`/bracket-depth dropping becomes unnecessary once JSON blocks are held whole. Delete it if the
   holder covers every case its tests pin, and keep those tests green.
7. **No new prose-shape regex.** The only new patterns are the number/figure grammar in `figure_grounding.py` and
   block-boundary detection. None of the attribution regexes grow (`_tool_reference`, `_ATTRIBUTES`, `_CLAUSE_BREAK`,
   `_NEGATIVE`, `_RESULT_LINE`).

### Tests — pin BEFORE the fix (fail on d685a4be/ec7f7cd6, pass after; record both runs)

In `sidecar/tests/test_agent_runtime.py`, run through the full `invoke_agent` relay with a scripted provider, the same
path the b19v probes use (`_scripted_answer` style). Add an optional `prompt=` parameter to `_scripted_answer`, with the
default unchanged, and let calls take per-call `input`. Cases are parametrised, one test per behaviour.

1. **Every batch-19 FAIL line, as written in the probes.** The FAB lines must be replaced and the TRUE lines unchanged:
   - FAB: f-uncalled-colon-fenced, f-mixed-errored-named-fenced, f-allerr-table, f-allerr-bullets-annotated.
   - TRUE: t-live-rel-list-replay (round 1 narrates the call JSON, round 2 lists ok prices; no "returned no data").
   - TRUE: b18v_probe_b x-news-data-shows.
2. **The user-figure TRUE lines, with their premise made true.** t-err-user-figures-list and
   t-err-user-position-summary are pinned with the user's prompt carrying the figures ("I bought 10 at ₹1,500", "I hold
   40 HDFCBANK.NS at ₹1,640 average") and must stream unchanged, "That is ₹15,000 in total." included. See Notes: the
   probes' own prompt is "q?".
3. **R15-LEAD-036.** In f-named-colon-fenced-json (all errored), the output has no ```` ``` ```` and carries the
   fundamentals note as prose.
4. **Controls from the lead:**
   - rounding: ok price_data 812.4 → "₹812.40" streams;
   - scale word: ok fundamentals marketCap 2300000000000 → "₹2.3 lakh crore" streams;
   - a user restatement after an error streams ("You told me: - Buy price: ₹1,500", with ₹1,500 in the prompt);
   - one table with TCS ok and SBIN errored: the TCS row streams and the SBIN row is replaced;
   - a derived percent from two ok values on an ok subject streams;
   - a fenced dump for an errored tool while another tool is ok is replaced;
   - an all-errored annotated bullet list is replaced by exactly ONE note;
   - an all-errored inline dump is replaced.
5. **Class cases the fix is not written against (≥3, W1's own invention).** For example:
   - all-errored plain prose with no tool named ("SBIN closed at ₹812.40 today.") is replaced;
   - an all-errored em-dash "key — value" list;
   - a mixed-turn prose clause "WIPRO.NS trades at ₹248.15" with WIPRO.NS errored and TCS ok is replaced, while the
     TCS clause in the same sentence streams;
   - "the S&P 500" streaming when the user's prompt names it.
6. **`test_figure_grounding.py`.** The figure/not-figure grammar (years, dates, times, list numbers, small ints, symbol
   digits, Indian grouping, lakh crore, bn, %) and the precision matcher, one parametrised test each.
7. **Every existing LEAD-030/031/033 and AGENT-090 test stays green, with no deletion and no weakening.** One known
   fixture must change: `test_a_result_list_with_a_source_or_no_result_shape_streams` pins "You said you bought at
   ₹1,500." after an errored call, under `_scripted_answer`'s prompt "SIFY ADR ratio?". There the user said no such
   thing, so under grounding the figure is ungrounded.
   - Correct the FIXTURE: pass `prompt=` carrying ₹1,500. Keep the expectation: it streams unchanged.
   - Log the rationale in the commit.
   - Any other flip gets the same treatment only if its premise was false. Never flip an expectation from "streams" to
     "replaced" for a true statement.

### Checks (detached and polled; no single call over ~120 s)

- Focused tests: `test_agent_runtime.py`, `test_figure_grounding.py`, `test_b5_runtime_history.py`,
  `test_tool_call_rescue.py`, `test_llm_ollama.py`, and `ruff format --check sidecar && ruff check sidecar`.
  Then run the full sidecar pytest detached.
- Offline probes, with cwd `<tree>/sidecar`, on the fix sha: `batch-17/verifier-evidence/b17v_probe.py`,
  `b17v_probe2.py`, `b17v_probe3.py`; `batch-18/verifier-evidence/b18v_probe.py`, `_b.py`, `_c.py`, `_d.py`; and
  `batch-19/verifier-evidence/b19v_probe.py` (no arg, `2`, `3`). Expected: BAD 0 on every line, with one exception.
  The two user-figure TRUE lines in `b19v_probe.py` run under prompt "q?", so they are expected flips. Run a copy,
  `writer-evidence/b20w_probe.py`, with a per-case prompt that carries the user's figures; it must PASS. Report both.
- Live bar: a sidecar from source on **127.0.0.1:52350**. Never use :52152–:52154 (the app) or :52310 (the verifier).
  Use llama3.1:8b through ollama with autonomy ask, following the pattern in `batch-18/verifier-evidence/b18v_live.py`
  (`--options` for history). Run at least 8 prompts:
  - "What is SIFY's TTM revenue in USD?";
  - the WIPRO.NS fundamentals case;
  - a two-turn INFY/TCS price run with price_data forced to error (a "call price_data with no arguments" turn);
  - an all-errored multi-symbol price ask;
  - ≥3 true controls, which must stream unchanged: an ok tool's figures with rounding (e.g. MSFT price), a
    Reuters/Morgan-Stanley plain-English lead-in, and a user-supplied figure restated after an error.

  Save the transcripts and a tally under `writer-evidence/`.

### Acceptance (what the verifier certifies)

On the running app with llama3.1:8b, all of the following must hold:
- The entry's own prompt, plus at least two fresh error-shaped prompts of the verifier's own invention, stream 0
  fabricated figures in ANY shape.
- ≥3 true controls stream unchanged. These include a user-figure restatement and an ok-tool figure with rounding.
- The b17/b18/b19 offline probes report BAD 0 on the FAB and TRUE lines, with the user-figure pair judged on their
  premise-true form.
- At least one fresh shape that W1 did not pin is tried.

LEAD-036 is certified by the fenced case rendering the note as prose with no fence.

## Run order (integrator)

1. Merge `origin/worktree-agent-batch-20-W1` into `worktree-agent-batch-20-int`, made from `d685a4be`. Audit only
   through `origin/`. The diff may touch only the owned files above plus `batch-20/writer-evidence/`.
2. Run `ruff format --check sidecar`, `ruff check sidecar` and the full sidecar pytest (detached). There are no
   frontend/Rust/types changes, so vitest and cargo are unaffected, and there is no `types/data.ts` mirror.
3. Fresh-context verifier per the Acceptance above.
4. Coordination: the lows P1/W2 branch `worktree-agent-lows-P1-W2-runtime-catalog` is pushed but NOT merged into 004.
   It also edits `agent_runtime.py` (the constants ~73–160, `_resolve_model` ~720, the research timeout ~800) and
   `test_agent_runtime.py`, in hunks apart from the guard (~1870–2320), the holder (~2539–2690), `_dispatch_round`
   (~2751–2912) and the turn seed in `invoke_agent`. Whichever merges second resolves; expect conflicts only where both
   append tests at the test file's end. Re-run the focused runtime tests after both are in.

## Deferred

- **R15-LEAD-035** (medium, agent-chat). llama3.1:8b staged `portfolio_update_position` after "without calling any
  tool". It is a real gap, not model noise to wave away: the product already has a deterministic intent gate
  (`planner.classify_intent` → `_resolve_tool_surface` strips writes on a positive read cue), and an explicit "without
  calling/using any tool" or "don't call any tools" is exactly such a cue, yet it is not one.
  - Deferred because the lead restricts batch-20 to one writer, W1, on the streaming guard ("nothing else in this
    batch").
  - The fix's file, `sidecar/services/planner.py`, is owned by the unmerged lows P1/W2 branch.
  - Next batch, after the lows merge: add the no-tool cue as a positive read signal so the turn is read-only (data
    writes stripped server-side). Pin it in `test_b3_runtime_intent_gate.py`: the prompt of case t-user-sale gets no
    write tool in its allow-list.
  - The staged write awaited review, so nothing was applied in the observed case.

## Proposed not-a-defect

None.

## Notes (Tier-3 decisions, for the verifier's attention)

- **The user-figure TRUE probe lines have a false premise.** `b19v_probe.py` runs every case with prompt "q?", so in
  t-err-user-figures-list and t-err-user-position-summary the "user's figures" were never given by the user. Under
  grounding, an all-errored turn correctly replaces them.
  - The lead's "BAD 0 on every TRUE line" is met only on the premise-true form (pinned, plus `b20w_probe.py`).
  - Honouring the original lines would need a "you told me" shape exemption, which is exactly the kind of prose-shape
    rule that leaks ("You told me SBIN is ₹812.40").
  - Verifier concurrence is needed.
- **History grounds no values.** The request carries no tool payloads from earlier turns, only trailers naming tools.
  Seeded tools count as ok for turn classification and citation, which keeps history-seed tests green. Assistant turns
  never ground.
- **Errored results ground (their own numbers).** The agent system prompt does not.
- **Derivations** come from user/context values only (see `ponytail:` above).
- **If LEAD-030 is not certified a sixth time,** the run-state rule applies: no seventh shape round. File a Tier-4 note
  in DECISIONS_FOR_OPERATOR.md, and the entry's disposition needs a fresh verifier's concurrence.
