# R15 Stage C — batch 16 plan (RC1 round 2, residual batch)

Base: `004-r4-experience-rebuild` @ `f7ea77b807616ab91a1fbc9cecda6ae00e2f69f2`. The batch-15 merge
`74ee3468` is its ancestor. Only docs commits follow it (the register and the run-state).
Planner: Opus. Lows are not planned, except R15-LEAD-031 (item D, lead note).
Queue after adjudication: `{critical:16, high:116, medium:288, low:226}`. Status `open` c/h/m in the
register: 2 high, 1 medium.

## Selection

| id | sev | operator area | item | writer |
|---|---|---|---|---|
| R15-AGENT-090 | high | agent-chat, research-search | A | W1 |
| R15-LEAD-030 | high | agent-chat | B | W1 |
| R15-LEAD-032 | medium | agent-chat | C | W1 |
| R15-LEAD-031 | low | agent-chat | D (≤10 lines, see below) | W1 |

Nothing is deferred or proposed as not-a-defect. Every entry was confirmed in the code at the base
sha: the mechanism was reproduced on the sidecar venv, not read from the title.

## W1 (opus): one writer set

**Why opus.** Items A, B and D sit in the agent runtime's streaming relay (`_consume_round` /
`_release`). That relay rewrites every sentence that chat, Delegate runs and MCP invoke stream, and it
holds per-turn state (`_TurnState`), which makes it a runtime state machine. The work is in the
agent-chat named area and next to §6.5, so an over-replacement shows up as a trust regression the user
can see. No other writer exists, so there are no file collisions and no mirrors.

**Files (W1 owns all of them)**
- `sidecar/services/agent_runtime.py`
- `sidecar/services/adr_ratio.py`
- `sidecar/services/agent_tools/fundamentals.py` (touch only if C needs it; see C)
- `sidecar/services/llm/tool_call_rescue.py` (item D; see the mechanism correction)
- `sidecar/tests/test_agent_runtime.py`, `sidecar/tests/test_adr_ratio.py`,
  `sidecar/tests/test_fundamentals_tool.py`, `sidecar/tests/test_tool_call_rescue.py`
- `docs/redesign/verification/r15/stage-c/batch-16/writer-evidence/**`

No `types/data.ts` mirror is needed. No catalog, schema, roster, `copilot.json` or `types/plugin.ts`
change is needed.

### A. R15-AGENT-090 residual: the class-qualifier escape in `_MARKED`

**Mechanism (reproduced at the base).** `_MARKED`'s plural-noun branch
(`\b{_NUM}\s+(?-i:(?:[a-z]+\s+)?(?!(?:shares?|…)\b)[a-z]+(?:s|es)\b)`, `agent_runtime.py` ~1849)
takes any lower-case word that ends in s/es as the counted noun. A qualifier in front of "shares" is
therefore taken as the counted noun, and the claimed number is blanked. The four escapes the verifier
found all return `_share_counts == set()` and stream unchanged. The same happens to the unseen
`3 series C shares`, `8 bonus class A shares` and `4 class A preferred shares`.
`5 founder shares` and `2 deferred shares` are already guarded, because the qualifier does not end
in s. The bug has a second side. `_sourced_counts` uses the same marker, so a source statement written
in lower case ("each representing six class A ordinary shares") yields no count, and the TRUE claim
gets replaced.

**Fix (the verifier's shape, applied to the whole noun span).** Put a negative lookahead right after
`{_NUM}\s+`, inside the case-sensitive group. The span the branch would blank (one or two lower-case
words) does not count as a non-share noun when an optional capital class letter, an optional
`(ordinary|equity|common|preferred) `, and then `shares?` follow it directly:
`(?!(?:[a-z]+\s+){1,2}(?:[A-Z]\s+)?(?:(?:ordinary|equity|common|preferred)\s+)?shares?\b)`.
The planner prototyped this lookahead on the venv:
- All nine sentences above are replaced.
- `3 analyst ratings`, `two possible matches` and `SIFY's ADSs each gained 3 points in 2024` stay kept.
- The lower-case source statement now traces its 6.

Do not add a word list (class/series/bonus): the lookahead is structural. The ceiling goes in a
`ponytail:` comment: a number two words before "shares" in a depositary sentence
("3 analysts covering shares") now reads as a share count.

**Tests (`test_agent_runtime.py`, one parametrised test each).**
- Guarded, against a fundamentals result with no depositary term: the four escaped sentences plus
  `Each ADS represents 3 series C shares.`, `Each ADR equals 8 bonus class A shares.`,
  `Each ADS represents 4 class A preferred shares.`, `Each ADR represents 5 founder shares.` and
  `Each ADS represents 2 deferred shares.`. The fix was not written against the last five.
- Traced and kept: `Each ADS represents 6 class A ordinary shares.` against an `ads_ratio.statement`
  written in lower case ("each representing six class A ordinary shares").
- Every batch-13/14/15 GUARDED, KEPT and TRACED test stays green unchanged.

### B. R15-LEAD-030: a fabricated tool-result citation

**Mechanism (read from `verifier-evidence/live-1.jsonl` and the code).** In live-1, llama3.1:8b emits
the `fundamentals` tool_use (with `SIFY.NS`) and then, in the SAME round and before the tool runs,
streams `- fundamentals returned: {` and a multi-line dump carrying `'$1320 m'` / `'₹331 cr'`. The
result then errors. `_release` runs only `_guard_ratio_claims`. `turn.tool_results` is a list of bare
strings with no tool name and no ok flag, so nothing can check "did this tool return ok". The dump
continuation lines contain no tool name, so a sentence-only check would still let them through.

**Fix.**
1. Add `ok_tools: set[str]` to `_TurnState`. `_dispatch_round` computes `_tool_result_event(tool_call,
   result_str)` once, adds `tool_call.name` to the set when `.ok` is true, and yields that same event.
   Reuse it; do not add a second ok parser.
2. Add a sibling guard `_guard_tool_citations(...)` and run it in `_release` on the output of
   `_guard_ratio_claims`, sentence by sentence (`_SENTENCE`).
   - A **tool reference** is a known tool id (the capability catalog ids ∪ `run.tool_ids`) written in
     one of these forms: backticked (`` `fundamentals` ``); the bare id when it contains an
     underscore (`financial_statements`); or the id followed by `tool|returned|result(s)|output|data`,
     or by `:`/`=` and then `{`/`[` (a dump).
   - Keep single-word ids in plain prose ("the news", "its fundamentals show") out of scope.
   - A sentence is **untraced** when it references tool T and T ∉ `ok_tools`, AND it either carries a
     claim cue (`returned|returns|result|output|data|according to|shows?|reports?|says`, or a `{`/`[`
     dump) or carries a currency-marked figure: `[$₹€£]|Rs|USD|INR|US$` before a number, or a number
     followed by `cr|crore|m|mn|bn|billion|million|USD|INR`.
   - A generic `tool result(s)|tool output|the tool returned` that names no tool is untraced only when
     `ok_tools` is empty.
   - The untraced sentence becomes `The {T} tool returned no data for this in this session.`
     (generic: `No tool returned data for this in this session.`). Keep its leading and trailing
     whitespace, as the ratio guard does.
3. When a replaced sentence opens an unbalanced `{`/`[`, drop the text that follows until the brackets
   balance. Keep the depth counter in a local variable of `_consume_round` (like `held`), so it resets
   every round.
4. Do not generalise to bare numbers. Derived arithmetic and a figure the user supplied are
   legitimate. A bare `₹4,411 cr` with no tool reference (batch-14 sify-2) is outside this guard; put
   that ceiling in a `ponytail:` comment, and it is recorded in the notes for the verifier.

**Tests (scripted provider, `test_agent_runtime.py`).**
- Errored `fundamentals` plus the live-1 shaped text (`- fundamentals returned: {\n "trailing_12m_revenue":
  {"display": "$1320 m"}\n}\n`) → the stream contains the replacement and neither `$1320` nor
  `trailing_12m_revenue`.
- The same text with an ok `fundamentals` result carrying `$1320 m` → kept verbatim.
- `You mentioned revenue of $1.3 bn.` with an errored tool → kept.
- The class case the fix was not written against: `According to the \`financial_statements\` tool,
  revenue was ₹4,411 cr.` when `financial_statements` was never called → replaced.
- `I'll call \`price_data\` next.` → kept.

### C. R15-LEAD-032: adr_ratio exception miss and timeout

**Mechanism (confirmed, `adr_ratio.py:131-147`).** The `except` branch returns before
`data_cache.set(f"{key}:miss", {})`, so an exception is never cached. `_TIMEOUT = 60.0` is httpx's
per-operation timeout on each of two sequential requests, and `_load_company_tickers` adds its own
30 s. A stalled EDGAR therefore blocks every fundamentals/financial_statements call for a foreign
reporter for minutes, because both tools await `_ads_ratio`.

**Fix.**
- Set `_TIMEOUT = 8.0`.
- In `lookup`, bound the whole fetch: `await asyncio.wait_for(_fetch(symbol), _TIMEOUT)`.
- On any exception, including `TimeoutError`, cache the miss (`data_cache.set(f"{key}:miss", {})`)
  before returning `None`. `_MISS_TTL` stays 24 h.
- Ceiling for a `ponytail:` comment: a cold fetch that takes longer than 8 s caches a 24 h miss. The
  answer is an honest absence, and the ratio guard still defends. Add background completion only if
  the live bar shows it.
- `fundamentals.py` needs no change unless the test shows one.

**Tests.**
- `test_adr_ratio.py`: `_fetch` raises; a second `lookup` for the same symbol does not call `_fetch`
  again.
- `test_fundamentals_tool.py` (or `test_adr_ratio.py`, next to the existing `_serve` helper):
  - `_fetch` hangs (`asyncio.sleep(3600)`) with `adr_ratio._TIMEOUT` monkeypatched to 0.2, and
    `_fundamentals({"symbol": "SIFY"})` runs for a foreign reporter.
  - The result must return in under 2 s with `ok: True` and no `ads_ratio` key.
  - A second call must not invoke `_fetch`.
  - Also assert `adr_ratio._TIMEOUT <= 8`.

### D. R15-LEAD-031: the leaked tool-call fragment (low, ≤10 lines)

**Mechanism correction (reproduced on the venv; the register's root cause is wrong).** The splice does
not happen in `_release`. `LeakHold.feed` (`services/llm/tool_call_rescue.py`) holds text only once
`_MARKER` matches, and the JSON marker needs the closing quote after the name. Fed sify-1's chunks
(`' {"'`, `'name'`, `'":'`, `' "'`, `'price'`, `'_data'`), it SHOWS ` {"name": "price_data` and holds
only from `",` onwards. The adapter rescues the call and emits a tool_use. The runtime releases the
leaked prefix at the round end. The next round's first sentence (here RATIO_UNAVAILABLE) is then
appended to it on the client. The replacement only made the splice visible.

**Fix (root cause, 5–8 lines, one shared place for both LeakHold users: ollama and openai).** In
`LeakHold.feed`, while nothing is held yet, hold back a trailing partial marker:
- a `{` optionally followed by a prefix of `"name": "<ident>` that runs to the end of the text, or
- a trailing identifier that is a prefix of an offered tool name (the `name(` call syntax).

The held-back text is released on the next feed once the tail no longer matches. At end of stream,
`held()` still returns it, so no text is lost.

**Tests (`test_tool_call_rescue.py`).**
- The JSON leak fed in sify-1's chunking: no shown chunk contains `{` or `price`.
- The call-syntax leak `price`, `_data`, `(symbol="SIFY")`: `price_data` is never shown. The fix was
  not written against this case.
- Prose that starts like a tool name (`"The price"`, `" is up."`): the text shown plus `held()` equals
  the input.

If the fix exceeds 10 lines, W1 leaves D open for the lows and says so.

## Acceptance for W1 (focused only; writers never re-verify)

Run each test file in the background and poll it:
`sidecar/.venv/bin/python -m pytest sidecar/tests/test_agent_runtime.py sidecar/tests/test_adr_ratio.py
sidecar/tests/test_fundamentals_tool.py sidecar/tests/test_tool_call_rescue.py -q`.
Before committing, run `ruff format` and `ruff check` on the touched files. Make one commit per item
(A, B, C, D) and push each one to `worktree-agent-batch-16-W1`.

## Integrator run order

1. Fetch `origin/worktree-agent-batch-16-W1`. Audit its merge-base against `f7ea77b8`, then merge it
   into 004 with `--no-ff`.
2. Build the sidecars (`pnpm sidecars:build`; staleness-aware). Then run `pnpm ci-local` detached and
   poll it, then `node scripts/smoke-test-sidecars.mjs`.
3. Verifier (fresh context), on the running sidecar with llama3.1:8b/ollama, autonomy ask:
   - The AGENT-090 live bar: 5 original-repro runs, plus 3 fresh phrasings, at least one of them
     class-qualifier wording ("…class A shares"). The bar is 0 untraced ratio claims.
   - The LEAD-030 bar: the original SIFY TTM-revenue prompt, and 0 fabricated
     "<tool> returned"/dump citations for a tool that errored.
   - Spot-check that ok-tool citations still stream (no over-replacement in agent-chat).
