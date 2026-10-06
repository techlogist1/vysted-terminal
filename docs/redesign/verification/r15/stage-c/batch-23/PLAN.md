# R15 Stage C — batch-23 plan

Base: `004-r4-experience-rebuild` @ `014bb7f1cb738d9ab8445668928a2fa98422f4f9`. Its `sidecar/services/planner.py`
is still batch-21's (`2e8593eb`): the closed `_NO_TOOL_CUE` phrase list (planner.py:130-141), searched on
`raw.lower()` in `classify_intent` (:212-215). Batch-22's W2 (`ca609488`) was NOT merged (batch-22 closed W1-only).

**Selection.** Exactly one entry, R15-LEAD-035 (medium, agent-chat), third and FINAL round, per the lead note.
Nothing deferred, nothing proposed as not-a-defect.

## W1 — opus — R15-LEAD-035, the no-tool cue matcher (final round)

**Why opus.** Two Sonnet rounds failed in opposite directions (batch-21 under-matched; batch-22 over-matched and was
blocked as a regression against base `93ba12da`). The gate sits on the agent runtime's tool-surface state: an
over-match strips `price_data` from a data request and the model then fabricates prices narrated as fetched
(batch-22 `live.out` fp-dont-forget, fp-just-from-market). The fail-safe direction must be judged per rule.

**Branch.** `worktree-agent-batch-23-W1`, from `014bb7f1`. Run `git reset --hard 014bb7f1` first (worktree base
hazard). Push every deliverable.

**Owned files (only these).**
- `sidecar/services/planner.py`
- `sidecar/tests/test_b3_runtime_intent_gate.py`
- evidence under `docs/redesign/verification/r15/stage-c/batch-23/writer-evidence/`

`agent_runtime.py` is NOT touched: the batch-21 hunk in `_resolve_tool_surface` (agent_runtime.py:1752-1757,
`"no-tool" in classify_intent(prompt).signals` → `return [], True, retired_tools`) is correct and stays. The
signal and return value `IntentResult("read", 0.95, ["no-tool"], False)` stay. `planner.py` stays free of
catalog/agent-loop imports (its module docstring, :18-19).

**Read first.**
- `git show ca609488` (origin/worktree-agent-batch-22-W2): the coverage it added (normalised apostrophes, per-clause
  scope, verb-less NEG→OBJECT, "except"-guard, 8 no-tool phrasings + 2 controls in the test file).
- `batch-22/VERDICTS.md` §R15-LEAD-035 and `batch-22/verifier-evidence/l035-surface.out` vs
  `l035-surface-base.out`: exactly what over-matched. `b22v_035.py` is the surface probe; `b22v_live.py` the live
  pattern (`scripts/r15/vy.py invoke ...`).
- `batch-21/VERDICTS.md` §R15-LEAD-035 (the batch-21 misses).

### Mechanism (confirmed in code)

- **Base (batch-21) under-matches.** `_NO_TOOL_CUE` is a closed phrase list on `raw.lower()`: "Answer without any
  tools" has no verb, "Do not call a tool" has "a tool", "Don’t use any tools" has U+2019 (`don'?t` is ASCII only).
  Each keeps 55 tools (`l035-surface-base.out`); live, the model called `get_portfolio` / streamed a write.
  "No tools except price_data for TCS.NS" loses every tool on base (`\bno tools\b` has no exception guard).
- **Batch-22 W2 over-matched** (`ca609488`): NEG accepted `(?:\s+\w+){0,3}` arbitrary filler before the verb
  ("don't **forget to** use the tools"), NEG "not" matched inside questions ("Why did you **not use the tools**"),
  "without using the tools" fired under an outer "Do not answer", and `_NO_TOOL_FROM_GIVEN` used `.*` twice
  ("**just** get the latest price **from** the market for the stocks in **this message**", "**Only** use data
  **from** price_data for **the above** symbols"). All six went 42-55 tools → 0.

### SPEC (lead, verbatim — the writer must meet all of it)

(1) the no-tool cue fires only when a negation is ADJACENT to the verb; between them only a closed filler list
{ever, please, just, even, any, the, a}, so 'don't forget to use the tools' (NEG + 'forget to') never matches;
(2) verbs {use, using, call, calling, invoke, invoking, run, running, rely on, make ... call(s)} x objects {tool(s),
function(s), lookup(s), search(es), tool call(s)} within one clause, either order, curly apostrophes and case
normalised; (3) a DOUBLE NEGATIVE keeps the surface: 'without (using|calling) ...' or 'no tools' counts only when no
other negation {do not, don't, never, not} precedes it in the same clause ('Do not answer without using the tools' =
use them); (4) an INTERROGATIVE clause never fires ('Why did you not use the tools?', 'Did you use the tools?'); (5)
the from-given cue takes a CLOSED object list directly after 'from': {what I gave you, what I told you, what I
pasted, the above, my numbers, this message, the numbers above, the data above, memory}; 'from the market', 'from
price_data', 'from the exchange' keep the surface; never '.*'; (6) any NAMED tool or data source used positively
('use price_data', 'data from price_data', 'use the tools to get ...') keeps the surface, and the named EXCLUSION
('don't use web search, get the price') keeps everything but the named tool, as today; (7) add 'skip the tools|tool
calls', 'zero tool calls', and a bare leading 'No tools:'; (8) PINS in test_b3_runtime_intent_gate.py, each asserting
the exact tool surface (full, full minus the named tool, or empty): the six keep-surface controls from
batch-22/VERDICTS.md ('Don't forget to use the tools to get the latest TCS.NS price.', 'Do not answer without using
the tools: what is TCS.NS trading at?', 'Why did you not use the tools? Get the TCS.NS price now.', 'Why did you not
use the tools', 'Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS', 'Only
use data from price_data for the above symbols: TCS.NS'); every true no-tool phrasing from batch-21 and batch-22
VERDICTS.md ('Answer without any tools', 'Do not call a tool', 'Don't use any tools' with U+2019, 'Avoid calling any
functions ... add them to my holdings', 'Zero tool calls please: I want to add 7 INFY', 'Skip the tools for this
one', 'answer only from what I gave you', 'from memory only'); the portfolio-add control ('Add 10 TCS at 3,200' keeps
the surface and stages behind review); the named exclusion; (9) LIVE BAR on the writer's own :52350 source sidecar
with llama3.1:8b: each of the six keep-surface prompts produces a price_data call, and 'Don't use any tools, add 7
INFY to my holdings' produces no tool call and stages nothing; the bar's transcript goes in writer-evidence.

### Fix shape (planner's reading of the SPEC; Tier-3 choices marked)

Replace `_NO_TOOL_CUE` with one module-level function (e.g. `_no_tool_cue(lowered) -> bool`) that `classify_intent`
calls at :212. Guiding rule for every ambiguity: **when in doubt, keep the surface** — a missed no-tool instruction
still has every write behind the proposed-changes review gate; a false strip makes the model fabricate data.

1. **Normalise.** Fold U+2019/U+2018 to `'`; already lower-cased. Accept `dont` as `don't`.
2. **Clauses.** Split on `. ; : ! ?`, newline, em/en dash and comma, remembering each clause's terminator.
   A match never crosses a clause. A leading "No tools:" is then the whole clause "no tools" (SPEC 7).
3. **Interrogative clause never fires (SPEC 4).** Terminated by `?`, or starting with a wh-word {why, what, how,
   when, where, who, which}, or an auxiliary {did, do, does, can, could, would, will, should, have, has, is, are,
   was, were} directly followed by a subject pronoun {you, i, we, they, it}. "Do not call a tool" is not
   interrogative (aux + "not", not a pronoun).
4. **Verb form (SPEC 1-2).** NEG {don't, do not, never, not, avoid, refrain from} + filler* from EXACTLY
   {ever, please, just, even, any, the, a} + VERB {use, using, call, calling, invoke, invoking, run, running,
   rely on, make} + gap* from {any, a, an, the, your} + OBJECT {tool, tools, function, functions, lookup, lookups,
   search, searches, tool call(s), function call(s)}; for `make` the object must be a `call(s)` form. Reverse order
   = passive: OBJECT (should|must|are to|will)? (not|never) be (used|called|invoked|run). A named tool between verb
   and object ("don't use web search", "without calling the news tool") never matches (the gap list is closed).
5. **Verb-less / without / skip / zero forms (SPEC 3, 7).** `without` + (using|calling|invoking|running)? + gap* +
   OBJECT; `no` + gap* + OBJECT; `zero tool calls`; `skip` + (the|any|all)? + (tools|tool calls).
6. **Double negative, applied to EVERY form (SPEC 3, class fix).** A cue does not fire when another negation
   {do not, don't, never, not} precedes it in the same clause. This also covers the verb form ("Don't reply if you
   do not call the tools") and the from-given form ("not just from memory").
7. **Exception guard (keeps batch-22 W2's fix).** An OBJECT directly followed by {except, other than, besides, but,
   apart from} does not fire ("No tools except price_data for TCS.NS" keeps its tools; base lost them).
8. **From-given (SPEC 5), Tier-3 lead-in.** `from` + one object of EXACTLY {what i gave you, what i told you, what i
   pasted, the above, my numbers, this message, the numbers above, the data above, memory}, AND either a lead-in
   {answer, reply, respond, only, just} whose gap to `from` is only {only, just, me, strictly}, or a trailing
   `only` ("from memory only"). No `.*` anywhere. Why the lead-in: without it "Take the tickers from this message
   and fetch their prices" strips the surface, the batch-22 failure mode again.
9. **Positive naming wins (SPEC 6), whole message.** The cue never fires if the message (a) contains a snake_case
   identifier `[a-z]+(_[a-z]+)+` — every catalog tool id is snake_case, and planner.py must stay catalog-free — or
   (b) has a non-negated, non-interrogative VERB→OBJECT clause ("use the tools to get ..."). Named exclusions
   ("don't use web search, get the price") never match rule 4/5 in the first place, so they keep today's surface.

A one-line comment cites R15-LEAD-035; a `ponytail:` comment names the ceiling (closed lists; phrasings like
"I don't want you to use any tools" are misses by design, and fail safe).

### Tests (`sidecar/tests/test_b3_runtime_intent_gate.py`, through `_agent_tool_ids`)

Pin BEFORE the fix; record the red run on `014bb7f1` and the green run in writer-evidence. "Exact surface" is
asserted against the **gate-off surface**: the same prompt through `_agent_tool_ids` with the planner's no-tool
function monkeypatched to return False (for read-shaped prompts that is the 42-tool read surface, otherwise 55).

- **Keep-surface (== gate-off surface, and `price_data` present):** the six SPEC-8 controls verbatim;
  "No tools except price_data for TCS.NS"; "Answer using the latest data, not just from memory: TCS.NS price"
  (batch-22 control); and class pins the rules were not written against: "Don't reply if you do not call the
  tools: what is INFY.NS at?" (double negative on the verb form), "Did you not call any tools? Get INFY.NS
  price." (interrogative), "No tools for the arithmetic; use the tools to get the TCS.NS price." (positive use
  wins), "Take the tickers from this message and fetch prices: TCS.NS" (from-given without lead-in).
- **Empty surface (== set()):** every SPEC-8 no-tool phrasing, in full sentence form taken from
  `b21v_035.py`/`b22v_035.py`/`b22v_live.py` (curly `Don’t` with U+2019), plus "No tools: what is 5 × 3,100?",
  "Please refrain from using tools, just compute it.", "Don't make any tool calls, restate my 5 TCS at ₹3,100."
  Keep W2's other pinned phrasings only where they meet the SPEC ("Answer only from the numbers in this message"
  does NOT: "the numbers in this message" is not in the closed list — do not pin it either way).
- **Portfolio-add control:** "Add 10 TCS at 3,200 to my portfolio" and "Add 10 TCS at 3,200" == gate-off
  surface, which contains `portfolio_add_position`. Staging behind review is the unchanged proposed-changes gate;
  the live bar proves it (a staged change, `/portfolio/positions` stays `[]`).
- **Named exclusion:** "Don't use web search, get TCS.NS price" and "Without calling the news tool, get TCS.NS
  price" == gate-off surface (see Notes on "full minus the named tool").
- Every existing test in the file stays green; the four existing no-tool tests keep their assertions.

Parametrise; one test function per behaviour (keep-surface, empty, add-control, named exclusion).

### Checks (detached and polled; no call over ~120 s)

- `pytest sidecar/tests/test_b3_runtime_intent_gate.py sidecar/tests/test_planner.py sidecar/tests/test_agent_runtime.py`
  (detached), then `ruff format sidecar/services/planner.py sidecar/tests/test_b3_runtime_intent_gate.py &&
  ruff format --check sidecar && ruff check sidecar`.
- `b22v_035.py` re-run on the fix sha (cwd `<tree>/sidecar`) → `writer-evidence/l035-surface.out`: every line OK
  (the "Skip the tools" line included), BAD 0.
- **Live bar (SPEC 9).** Source sidecar on **127.0.0.1:52350** (never :52152-54, never :52310), llama3.1:8b via
  ollama, autonomy ask, `scripts/r15/vy.py invoke copilot ... --port 52350`. Run the six keep-surface prompts
  (each must show a `price_data` call; send the bare "Why did you not use the tools" as the second turn after a
  "What is TCS.NS trading at?" turn so it has a subject), "Don't use any tools, add 7 INFY to my holdings" (no
  call, nothing staged, `/portfolio/positions` unchanged), "Add 10 TCS at 3,200 to my portfolio" (staged behind
  review, not applied) and "Don't use web search, get TCS.NS price" (price_data called). Check each price against
  `/quotes`. If the model skips a call with the full surface sent, re-run once and report both runs honestly.
  Transcripts + a tally in `writer-evidence/`. Kill the sidecar and its workers at the end.
- **One commit** for the entry (tests + fix), pushed.

## Run order (integrator)

1. Create `worktree-agent-batch-23-int` from `014bb7f1`; merge `origin/worktree-agent-batch-23-W1`, auditing only
   via `origin/`. W1 may touch only `planner.py`, `test_b3_runtime_intent_gate.py` and `batch-23/writer-evidence/`.
2. No `types/data.ts` mirror, no frontend, no Rust change. Run ruff and the full sidecar pytest (detached), then
   `pnpm ci-local` and `node scripts/smoke-test-sidecars.mjs`.
3. Coordination: the unmerged lows branch P1-W2 (runtime-catalog) edits `planner.py` in the PLAN_ACTIONS and prompt
   hunks, not the no-tool cue. Batch-23 merges first; the lows integrator resolves any overlap and re-runs
   `test_b3_runtime_intent_gate`.
4. A fresh-context verifier certifies the Acceptance below.

## Acceptance (verifier)

- `b22v_035.py` on the integration sha: BAD 0 (all 24 lines), and at least 4 fresh verifier phrasings of each kind
  (no-tool and keep-surface), none pinned by the writer, behave per the SPEC.
- Live on llama3.1:8b: every no-tool phrasing makes no call and stages nothing; the six keep-surface prompts call
  `price_data` and state the `/quotes` price; a portfolio add stages behind review; the named exclusion keeps
  `price_data`.
- No regression against base `014bb7f1` on any batch-22 probe line that was OK on base.

## Notes (Tier-3 decisions, for the verifier's concurrence)

- **Named exclusion surface.** SPEC 6 says "keeps everything but the named tool, as today". Today (`014bb7f1`)
  "Don't use web search, get TCS.NS price" sends all 55 tools, `web_search` included — no code strips a named tool.
  The plan pins "as today" (== gate-off surface). Stripping the named tool would be a new phrase→tool-id mechanism
  outside this entry, which is about a no-tool instruction; it goes to issues if wanted.
- **From-given lead-in** (rule 8) and the **snake_case tool-id rule** (rule 9a) are the planner's; both fail safe.
- **Double negative generalised to every cue form** (rule 6) — the class fix for SPEC 3, pinned on the verb form
  and the from-given form, which the lead's examples do not cover.
- **Accepted misses (fail safe, surface kept, writes still review-gated):** "Could you answer without any tools?"
  (interrogative), "I don't want you to use any tools" (non-adjacent), "Answer only from the numbers in this
  message" (not in the closed list).
