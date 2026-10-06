# R15 Stage C — batch-18 plan

Base: `004-r4-experience-rebuild` @ `0890888305bf891ac55a8ed1794f18bb4ae3c2f9`.
Selection: the three open critical/high/medium entries after adjudication — R15-LEAD-030 (high,
agent-chat), R15-LEAD-033 (medium, agent-chat), R15-LEAD-034 (medium, data-smallcaps). No lows
(they belong to the lows waves). Two writer sets, disjoint files.

## W1 — opus — agent-runtime citation guard + history trailer (LEAD-030, LEAD-033)

Why opus: risk-adjacent (the agent runtime's streaming guard and its cross-turn provenance
seeding). LEAD-030 is already root-caused and fixed on the salvage branch; the W1 writer
validates it and adds LEAD-033 on the same seam.

Branch: continue from `origin/worktree-agent-batch-18-W1` @ `ecdd223e` (5 commits on `292ba53a`,
an ancestor of base). Push to that branch.

Owned files: `sidecar/services/agent_runtime.py`, `sidecar/tests/test_agent_runtime.py`,
`sidecar/services/llm/tool_call_rescue.py`, `sidecar/tests/test_tool_call_rescue.py`,
`src/store/chat-history.ts` (+ `chat-history.test.ts`), `src/modules/chat/ChatSidebar.tsx`
(+ `ChatSidebar.test.tsx`), `sidecar/tests/test_b5_runtime_history.py` (read-only unless a
test there is proven wrong), `docs/redesign/verification/r15/stage-c/batch-18/writer-evidence/`.

### R15-LEAD-030 — validate, do not redesign

- Mechanism (from the batch-17 verdict, not the raw title): `_guard_tool_citations` replaced any
  sentence that named an untraced tool beside a cue word, so a true error mention next to an
  ok tool's figure was replaced (probe2 `err-mention-plus-true-figure`), and a camel-cased
  humanised id (`PriceData`) escaped (probe3 `fab-camelcase`).
- Fix (already on the branch): clause-level attribution — one reference regex with id parts
  joined by `[\s_-]?` so snake/spaced/hyphen/Title/camel all canon to the catalog id; a sentence
  parts at clause breaks before the first dump opener; negative wording kept verbatim; a clause
  is replaced only if a non-ok ref is CITED in attribution form, or it carries a figure/dump and
  every ref in it is non-ok; the round's pending calls are subtracted from `ok_tools` and a
  pre-result dump is dropped.
- Writer steps: (1) check out `292ba53a`'s `agent_runtime.py` with the branch's
  `test_agent_runtime.py` and confirm the 3 new tests FAIL; confirm they PASS at `ecdd223e`.
  (2) Run focused suites: `test_agent_runtime.py`, `test_tool_call_rescue.py`,
  `test_llm_ollama.py` (detached, polled). (3) Run the batch-17 verifier probes
  `docs/redesign/verification/r15/stage-c/batch-17/verifier-evidence/b17v_probe.py`,
  `b17v_probe2.py`, `b17v_probe3.py` against the branch code — expected `BAD 0`. Fix only what
  those show; any fix gets a test on a case it was not written against.
- Out of LEAD-030's claim (do not fix here): figures read from the WRONG ROW of an ok result
  stream unchanged (value fidelity, not provenance). Record it in the writer report as an issue.

### R15-LEAD-033 — strip the trailer from the model-visible history, sidecar side

- Mechanism (confirmed in code): `src/store/chat-history.ts` `withTrailer` appends
  `[tool steps: …]` / `[failed: …]` lines into the assistant turn's `content`
  (`historyForSend`). The sidecar's `_coerce_history` passes recent turns VERBATIM to the
  provider, trailer included, so llama3.1:8b quotes the bookkeeping as its own prose. The same
  trailer is the cross-turn provenance channel: `_run_setup` calls
  `_history_tools(history, …)` on the coerced messages to seed `cited_tools` (batch-17/18 tests
  `test_a_citation_of_a_tool_an_earlier_turn_ran_is_kept` and the follow-up test). The folded
  summary of older turns carries the trailer lines as `- [tool steps: …]` / `- [failed: …]`
  (R15-AGENT-040, pinned by `test_b5_runtime_history.py`).
- Fix (shape 1, sidecar-only, no client/contract change): seed `cited_tools` from the history
  BEFORE the trailer is removed (e.g. `_history_tools` over the unstripped turns), then, in
  `_coerce_history`, drop `[tool steps: …]` lines from the verbatim assistant turns sent to the
  provider (an assistant turn left empty is dropped, as empty content already is). The folded
  summary keeps its trailer record unchanged (it is the runtime's own bookkeeping message and
  AGENT-040 pins it). Shape 2 (a metadata channel mirrored in `types/ai.ts`) is not needed: the
  trailer already reaches the one reader that needs it before the provider sees it, and a new
  wire field would touch the client, the store and the contract for no extra behaviour.
  `[failed: …]` in verbatim turns is not part of the filed claim; leave it (report in issues if
  it is observed echoed).
- Tests (sidecar/tests/test_agent_runtime.py): (a) two-turn history whose assistant turn carries
  `[tool steps: Using fundamentals]` — the provider receives no message containing
  `[tool steps` AND a turn-2 citation of `fundamentals` streams unchanged; (b) a case the fix was
  not written against: a verbatim assistant turn with a two-step trailer
  (`Using price data; Reading your portfolio`) — stripped from the provider messages, both tools
  still seeded (a citation of each is kept). Existing seeding and AGENT-040 tests stay green.
- Live: a two-turn chat (llama3.1:8b) with the client's `historyForSend` history — turn-2
  answer carries no `[tool steps` text; turn-1 citation still streams. Save transcripts under
  `batch-18/writer-evidence/lead033-*`.

## W2 — sonnet — NSE Emerge '-SM' identity in the correctness gate (LEAD-034)

Clear spec, checkable output.

Owned files: `sidecar/services/correctness_gate.py`, `sidecar/tests/test_correctness_gate.py`,
`sidecar/services/yfinance_provider.py`, `sidecar/services/fundamentals_warm.py`,
`sidecar/tests/test_fundamentals_warm.py`.

- Mechanism (confirmed in code): `yfinance_provider._nse_listing` returns `<SYM>-SM.NS` for an
  Emerge name; quotes (`symbol=normalized.upper()`, line ~463), series (~561) and fundamentals
  (`symbol=yahoo`, ~865) echo that form. `correctness_gate._match_key` strips only
  `[.\-](NS|BO|BSE)$`, so `INSPIRE-SM.NS` keys to `INSPIRESM` and a bare `INSPIRE` request
  fails `symbols_match` — every caller of `validate_quote`/`validate_series`/
  `validate_fundamentals`, not only the warm crawler.
- Fix (root, where every caller routes): `_SUFFIX_RE` becomes `(?:-SM)?[.\-](NS|BO|BSE)$`, so the
  Emerge infix is dropped only when it sits right before an Indian exchange suffix (a US ticker
  is untouched; `SMR.NS` unaffected). Update the `_match_key` docstring. No change in the
  crawler or provider unless the reproduction shows another gap.
- Tests (test_correctness_gate.py): REPRODUCE FIRST — `symbols_match("INSPIRE", "INSPIRE-SM.NS")`
  fails on base. Pin: that case True; a case the fix was not written against —
  `validate_quote`/`validate_series` for bare `SUMAX` vs returned `SUMAX-SM.NS` passes; and a
  negative that identity still holds — `symbols_match("INSPIRE", "OTHER-SM.NS")` False.
- Live: on a source-booted sidecar (detached, polled), `GET` fundamentals for one real NSE Emerge
  symbol (bare form, region IN) passes the gate with a plausible value; record the symbol and
  the response shape in the writer report.

## Coordination and run order

- No shared files. W1 is sidecar runtime + (unchanged) client store; W2 is the data gate. No
  `types/data.ts` mirror change in either set (no model shape changes).
- Integrator order: W2 first (small, independent), then W1 (merge the branch's 5 LEAD-030
  commits + the LEAD-033 commit). After both: `ruff format --check sidecar && ruff check
  sidecar`, focused pytest of the five named test files, `pnpm format:check`.
- Verifier (fresh context, once): LEAD-030 — llama3.1:8b on the running app, fresh cases both
  ways (a fabricated citation of an uncalled/errored tool replaced; a true error mention beside
  an ok tool's figure kept; camelCase and Title-case ids; a dump on the next line; a two-turn
  follow-up with the client's history): 0 fabricated streamed AND 0 true citations replaced.
  LEAD-033 — a two-turn chat whose second answer contains no `[tool steps` while turn-1
  citations still stream. LEAD-034 — one `-SM.NS` symbol's fundamentals pass the gate on the
  running sidecar with a plausible value. The wrong-row value-fidelity observation may be filed
  as a candidate entry with evidence; it is not grounds to refuse LEAD-030.
