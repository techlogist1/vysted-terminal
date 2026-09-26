# R15 Stage C — batch-24 plan

Base: `004-r4-experience-rebuild` @ `1db862d09e8669f2a7b01938b42b7162bd864faa`. Its `sidecar/services/planner.py`
still carries batch-21's closed `_NO_TOOL_CUE` (`2e8593eb`, planner.py:130-141), searched on `raw.lower()` in
`classify_intent` (:212-215) and consumed only by `agent_runtime._resolve_tool_surface` (agent_runtime.py:1752-1757:
`"no-tool" in classify_intent(prompt).signals` → empty surface). Neither batch-22 W2 (`ca609488`) nor batch-23 W1
(`5a0f1ffe`) is on the base, and neither is revived here (both rejected as regressions).

**Selection.** Exactly one entry, R15-LEAD-035 (medium, agent-chat), with exactly one change: the narrowing-only
closed tail the batch-23 disposition verifier named and said it would certify
(`batch-23/DISPOSITION-CONCURRENCE.md` § "Named fix"; `batch-23/verifier-evidence/disposition/fix-regex.out` and
`dv_fix_regex.py` hold the exact regex and the 67 classified phrasings). Nothing deferred, nothing proposed as
not-a-defect. Low queue untouched this batch (lead note).

## Mechanism (confirmed in code and in the verifier's offline + live evidence)

The four shipping alternatives match their object (`tools?`, `no tool calls`, `answer from what I gave you`) and stop
at `\b`, so a qualifier after the object ("other than price data", "for the math, but do fetch", "you don't need",
"twice", "from the web", "except price_data") and reported speech ("I never said don't use tools") still fire. The
whole tool surface is then emptied on an explicit data request, and llama3.1:8b states invented prices as fetched
(15/21 live runs, up to +353%, `live-OVER.out`). Under-matches (17 phrasings) fail safe (writes staged behind
review, never applied) and are NOT in scope — this change widens nothing.

## W1 — sonnet — R15-LEAD-035, narrowing-only closed tail on `_NO_TOOL_CUE`

**Why sonnet.** The fix is fully specified to the character (the verifier's regex) with a checkable output (67
classified phrasings + a subset invariant). No root-causing remains.

**Branch.** `worktree-agent-batch-24-W1`, from `1db862d0`. Run `git reset --hard 1db862d09e8669f2a7b01938b42b7162bd864faa`
first (worktree base hazard) and confirm `git log -1` shows it. Push every deliverable.

**Owned files (only these).**
- `sidecar/services/planner.py` (the `_NO_TOOL_CUE` block and its comment only)
- `sidecar/tests/test_b3_runtime_intent_gate.py`
- evidence under `docs/redesign/verification/r15/stage-c/batch-24/writer-evidence/`

Do NOT touch `agent_runtime.py`, `figure_grounding.py` or any other file. The `IntentResult("read", 0.95,
["no-tool"], False)` return and the `_resolve_tool_surface` hunk stay as they are.

### SPEC (verbatim from the lead note; implement exactly)

1. Keep the four shipping `_NO_TOOL_CUE` alternatives EXACTLY as they are (planner.py ~136-141).
2. Add a closed-tail lookahead: an alternative fires only when its object is followed by a clause end
   (`$ . , ; : ! ? )` an em or en dash, or `'- '`), or by one of 'please', 'at all', 'whatsoever', 'here', 'now',
   'this time', 'today', 'and', 'just', or by 'for this|that( one| question| turn)?' followed by a clause end.
3. Add a reported-speech guard `(?<!said )(?<!say )` before the cue.
4. The result must be a strict SUBSET of the shipping regex — it may only turn a strip into a keep, never add a strip.
5. PINS in `test_b3_runtime_intent_gate.py` against the gate-off surface (the existing `_agent_tool_ids` helper, the
   real `invoke_agent`): every one of the 67 phrasings in `fix-regex.out` with its want_strip verdict (0
   over-strips, no correct strip lost: assert fixed strips ⊆ shipping strips by also keeping the OLD regex in the
   test as a reference constant), the 7 OVER prompts as keep-surface, the literal register repro and every L38
   phrasing from DISPOSITION-CONCURRENCE.md as 0-tool, the portfolio-add control ('Add 10 TCS at 3,200' keeps the
   surface, staged behind review).
6. LIVE BAR on the writer's own :52350 source sidecar with llama3.1:8b: the 7 OVER prompts x3 each call price_data
   and state the /quotes price; the literal repro x2 makes no call and stages nothing; transcript in writer-evidence.

One commit, focused tests + ruff clean, pushed.

### The regex (from `dv_fix_regex.py`; copy it, do not re-derive)

```python
_NO_TOOL_CUE = re.compile(
    r"(?<!said )(?<!say )(?:\bwithout (?:calling|using|running|invoking)(?: any)? tools?\b"
    r"|\b(?:don'?t|do not|never) (?:call|use)(?: any)? tools?\b"
    r"|\bno tool(?:s\b|\s*calls?\b)"
    r"|\b(?:just|only) answer from what (?:i )?(?:gave|told) you\b)"
    r"(?=\s*(?:$|[.,;:!?)—–]|-\s|please\b|at all\b|whatsoever\b|here\b|now\b|this time\b|today\b"
    r"|and\b|just\b|for (?:this|that)(?: one| question| turn)?\s*(?:$|[.,;:!?—–])))"
)
```

Split string pieces only as needed for ruff's 100-column limit (E501); the compiled pattern must be byte-identical to
`dv_fix_regex.FIX.pattern` — assert that once offline (scratch, not a committed test). Update the block comment above
it in one or two lines (closed tail + reported-speech guard; narrowing-only, R15-LEAD-035 batch-24). Ruff's selected
rules are E, F, I, UP, B (no RUF), so the literal em/en dash characters are fine.

### Tests (mechanism → pin), all in `sidecar/tests/test_b3_runtime_intent_gate.py`

- `_SHIP_NO_TOOL_CUE`: a module constant, a verbatim copy of the shipping regex at `1db862d0` (planner.py:136-141),
  with a one-line comment that it is the pre-batch-24 reference for the subset invariant.
- `_FIX_REGEX_CASES`: all 67 rows of `fix-regex.out` in file order as `(want_strip, expect_empty, prompt)`, where
  `expect_empty` is the file's `fix=` column (True for the 22 correct strips; False for the 17 fail-safe misses, the
  7 OVER prompts and the other 21 keeps). Keep the prompts byte-exact (curly apostrophes, `₹`, `×`, dashes). Keep
  duplicates (the file lists some L38 phrasings twice) so the count stays 67 and traceable.
- **Test A (surface, parametrised over the 67):** `tool_ids = await _agent_tool_ids(...)`; assert
  `(tool_ids == set()) == expect_empty`; if `expect_empty`, also assert `_SHIP_NO_TOOL_CUE.search(prompt.lower())`
  (subset: never a new strip); if not `want_strip`, assert `tool_ids` is non-empty (0 over-strips).
- **Test B (subset invariant at the regex level, parametrised over the 67 + the held-out class pins below):**
  `planner._NO_TOOL_CUE.search(p.lower())` implies `_SHIP_NO_TOOL_CUE.search(p.lower())`.
- **Test C (OVER keep-surface, the 7 OVER prompts):** `"price_data" in tool_ids`.
- **Class pin on cases the fix was not written against (planner-chosen, verified offline against both regexes):**
  keep-surface (shipping strips, fixed keeps): "Don't use tools unless you must; get the TCS.NS price.",
  "Never call tools on my behalf, get INFY.NS price", "you say don't use tools, but get TCS.NS price" → `price_data`
  present; still-strip (both strip): "No tools at all: I bought 5 ITC at ₹420, what's the total?", "Do not use any
  tools here. I hold 10 SBIN at ₹800; what's my cost?" → surface `set()`. One parametrised test.
- Existing tests stay unchanged and green: the literal t-user-sale repro and "Don't use any tools — I hold 40
  HDFCBANK …" (both still strip under the fix: `,` and ` —` tails), the named-tool exclusion, and the
  "Add 10 TCS at 3,200 to my portfolio" control (`portfolio_add_position` kept). The literal repro and the 7 L38
  phrasings are already in the 67 as `expect_empty=True`; do not duplicate them in new functions.
- One test function per behaviour; no scratch scripts committed as tests.

### Checks (detached and polled; no single call over ~120 s)

- `cd sidecar && .venv/bin/python -m pytest tests/test_b3_runtime_intent_gate.py tests/test_planner.py
  tests/test_agent_runtime.py` (detached, log polled) → `writer-evidence/focused.out`.
- `ruff format sidecar/services/planner.py sidecar/tests/test_b3_runtime_intent_gate.py && ruff format --check
  sidecar && ruff check sidecar`.
- Re-run `batch-23/verifier-evidence/disposition/dv_fix_regex.py` logic against the COMMITTED `planner._NO_TOOL_CUE`
  (scratch copy importing `services.planner`, cwd `<tree>/sidecar`) → `writer-evidence/fix-regex-committed.out`:
  N=67, correct/over-strip/miss = 50/0/17, no assertion failure.
- **Live bar (SPEC 6).** Source sidecar from the writer tree on **127.0.0.1:52350** (never :52152-54, never :52310),
  llama3.1:8b via ollama, keyless, agent mode, autonomy ask; reuse the pattern of batch-23 W1's `b23w_live.py`
  (`git show origin/worktree-agent-batch-23-W1:docs/redesign/verification/r15/stage-c/batch-23/writer-evidence/b23w_live.py`)
  with `scripts/r15/vy.py invoke copilot ... --port 52350`. Record `/quotes` for RELIANCE, TCS, ITC, HDFCBANK,
  WIPRO and `/portfolio/positions` first. Run the 7 OVER prompts ×3 (each must call `price_data` and state the
  `/quotes` price) and the literal repro ("I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my
  sale price and my total proceeds.") ×2 (no `tool_use`, no staged proposal, `/portfolio/positions` unchanged).
  Report every run honestly, including a run where the model skips the call with the full surface sent (that is the
  LEAD-030/037 residual, not this gate — note it, do not re-run to hide it). Transcripts (`live/<tag>.r<n>.jsonl`)
  plus a tally in `writer-evidence/`. Boot the sidecar detached, poll `/health`, kill it and its workers at the end.
- **One commit** (fix + tests; evidence may ride the same commit), conventional message, pushed.

## Coordination / mirrors

No `types/data.ts` mirror, no frontend, no Rust, no catalog change. `planner.py` stays free of catalog/agent-loop
imports. The unmerged lows branch P1-W2 (runtime-catalog) edits `planner.py` in the PLAN_ACTIONS / prompt hunks,
not `_NO_TOOL_CUE`; if the lows integrator later merges it, it resolves any overlap and re-runs
`test_b3_runtime_intent_gate`.

## Run order (integrator)

1. Create `worktree-agent-batch-24-int` from `1db862d0`; merge `origin/worktree-agent-batch-24-W1`, auditing only via
   `origin/`. Confirm W1's diff touches only `planner.py` (the `_NO_TOOL_CUE` block + comment),
   `test_b3_runtime_intent_gate.py` and `batch-24/writer-evidence/`.
2. Ruff, the full sidecar pytest (detached), then `pnpm ci-local` and `node scripts/smoke-test-sidecars.mjs`.
3. A fresh-context verifier certifies the Acceptance below.

## Acceptance (verifier)

- The committed `_NO_TOOL_CUE` pattern equals `dv_fix_regex.FIX.pattern`; on the 67 phrasings: 50 correct / 0
  over-strip / 17 miss, and no phrasing is stripped that the shipping regex keeps (subset).
- Fresh verifier phrasings (≥4 of each kind, none pinned by the writer): qualified negations keep `price_data`;
  plain no-tool instructions with a clause-end or closed tail still empty the surface.
- Live on llama3.1:8b: the 7 OVER prompts call `price_data` and state the `/quotes` price; the literal repro makes no
  call and stages nothing; "Add 10 TCS at 3,200 to my portfolio" stages behind review, not applied.
- With this merged, the over-match clause of the LEAD-035 operator-briefing sentence drops out (DISPOSITION-
  CONCURRENCE.md); the 17 misses remain the accepted staged-behind-review state.
