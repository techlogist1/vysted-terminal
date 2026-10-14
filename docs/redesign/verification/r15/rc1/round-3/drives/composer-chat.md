# composer-chat — owner-drive, RC1 gate round 3

Label `rc1-drive-composer-chat`. Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own
sidecar `127.0.0.1:52320` (source: `rc1-round-3-cand/sidecar`, data:
`rc1-round-3-data-composer-chat/` cp'd from `rc1-round-3-seed-data`), shared MCP
`:52153/:52154` (read-only). Local lane `llama3.1:8b` via the Ollama lock. Full transcripts
under `docs/redesign/verification/r15/surface/composer-chat/rc1/round-3/`.

Method: re-drove the census's exact 6-turn conversation (`cc-t1..t6.jsonl`, history threaded)
plus the no-key error-frame probe, then cross-checked every OTHER census-found defect in this
group against the register's now-`fixed` entries via the repo's own dedicated regression tests
(faster and no less rigorous than a fresh live LLM re-drive for deterministic code paths, and
keeps Ollama contention down for the other roles sharing the lane) — `pytest` for sidecar-side
fixes, `vitest` for the 19 frontend unit-test files this group's rows map to (190/190 pass).

## Scored table — census → rc1 round 3

| # | Interaction | Census (2026-09-23) | RC1 round 3 | Evidence |
|---|---|---|---|---|
| 1 | Turn 1 — ask price/P/E/mcap | partial (growth% read as a fraction) | **ok** | `cc-t1.jsonl` — clean fundamentals answer, price/mcap/P/E all correct; no growth% figure emitted this run so the fraction-unit bug (LEAD-039/DATA-113 class, fixed separately) wasn't re-exercised |
| 2 | Turn 2 — compare valuation | partial (invented ticker, tool silently 502'd) | **partial → improved** | `cc-t2.jsonl` — model still invents a wrong ticker (`MDSL.NS`, known llama3.1:8b resolver-hallucination limitation, out of this round's fix-class per the lead note); but `compare_symbols` now returns a **clean** `"unresolved name: ... is not a known ticker"` instead of a raw 502 — DATA-061-class fix holding |
| 3 | Turn 3 — add both to watchlist | **broken (half)** — `tool_call_id: ""`, both acks impossible | **fixed** | `cc-t3.jsonl` — two DISTINCT real ids (`call_bfa9…`, `call_5c0d…`), both `tool_result ok:true`. R15-AGENT-046 confirmed live (matches `agent_runtime.py:2894 f"call_{uuid.uuid4().hex}"`) and by `test_tool_call_identity.py` (3/3 pass) |
| 4 | Turn 4 — write a note | **broken** — `write_note` stripped by the intent gate, model typed the call as leaked JSON prose | **fixed** | `cc-t4.jsonl` — genuine `tool_use write_note` event, `tool_result ok:true`. R15-AGENT-019 confirmed live (planner.py `_EDIT_SIGNALS` now has `\bnotes?\b`/`\bwrite\b`) and by `test_planner.py` (25/25 pass) |
| 5 | Turn 5 — `/screener` expansion | **broken** — `write_screener_filters` stripped (same intent-gate bug), `screener_run` got JSON-string criteria and validation-errored | **fixed** | `cc-t5.jsonl` — first `screener_run` attempt sent empty args and got a **clean** sentinel rejection (R15-AGENT-047-class), then `write_screener_filters` succeeded with a properly nested criteria array (R15-AGENT-093's deep `_coerce` + R15-AGENT-019's intent gate both confirmed live together) |
| 6 | Turn 6 — arrange side-by-side | partial (ack skipped, apply not headlessly provable) | **ok** | `cc-t6.jsonl` — `arrange_layout` called with the correct pattern/symbols, `tool_result ok:true` |
| 7 | No-key error frame (OpenAI) | ok-ish — humanized to `"Something went wrong with the AI provider."` / code `unknown` | **REGRESSION** | `cc-20-err-nokey-openai.jsonl` — now `"The terminal hit an internal error... restart Vysted"` / code `internal`. New finding, see below. |

Delegate lifecycle, stop-mid-stream, budget-clear (turns 8-11 of the census's original drive)
re-verified via the repo's own regression tests rather than a fresh paid/local re-drive:

| Census finding | Register id | RC1 verification | Result |
|---|---|---|---|
| Stop doesn't stop (tool keeps running after SSE close) | R15-AGENT-002 | `pytest sidecar/tests/test_b3_runtime_cancel.py` | **1/1 pass** — `agent_runtime.py`'s `_dispatch_tool_with_progress` finally-block now does `task.cancel()` |
| Budget-clear box removes the ceiling entirely | R15-AGENT-034 | code-read `BudgetConfig.tsx` (onBlur restores default) + `models/run.py` (`gt=0`, `DEFAULT_RUN_BUDGET`, `_with_floor` at launch AND resume) | **fixed, both client and server** |
| Delegate cancel/pause act on any status, resume re-executes a done run | R15-CODE-AGENT-010 | `pytest sidecar/tests/test_run_manager.py` | **27/27 pass**; `cancel_run`'s docstring: "A finished run is never rewritten: the store raises RunStateError" |
| `pause_run`/answer control plane has no caller | R15-CODE-AGENT-011 | same suite, `test_ask_user_pauses_the_run_and_the_answer_resumes_it` | **pass** — a live `ask_user` catalog tool now parks the run and `answer_run` resumes it |
| Resume drops the user's provider/model | R15-LIFECYCLE-013 / R15-AGENT-035 | same suite, `test_resume_reuses_the_launch_provider_model_and_adds_to_the_cost` | **pass** |
| Halted run still persists undispatched host_actions | R15-AGENT-092 | same suite, `-k halt` | **2/2 pass** |
| Tab-switch mid-stream drops the reply | R15-CODE-FRONTEND-002 | `vitest src/store/agent-spaces.test.ts` | **8/8 pass** |

## New finding this round

**Missing/invalid API key on OpenAI or Groq now surfaces a misleading "internal error /
restart Vysted" frame instead of the humanized "check your key in Settings" message**, on
BOTH `/agents/{id}/invoke` and `/llm/chat`. Root cause: `services/llm/openai.py` (and
`groq.py`) construct their SDK client (`self._client(api_key)`) BEFORE the `try:` block in
`stream_chat`; OpenAI's/Groq's SDK constructors raise immediately on a missing key, so that
exception never reaches the adapter's own `humanize()` and instead falls all the way to
`routers/agents.py:106-110` / `routers/llm.py:167-170`'s last-resort guard, which — per
R15-AGENT-030's (fixed) design — now ALWAYS emits the generic `error_frame()` unconditionally
rather than trying `humanize(provider_id, exc)` first. R15-AGENT-030's own fix was correct for
a genuine internal fault (its test: a `RuntimeError` from a closed DB connection should say
"internal"); the regression is that it also swallows a legitimate, provider-classifiable
exception for the 5 providers (openai, groq, openrouter, xai, deepseek — all sharing
`OpenAIProvider`'s eager-validating client) whose SDK fails BEFORE entering the adapter's own
try/except. Anthropic and Gemini are not currently exposed (their SDKs defer key validation to
request time, inside the try), confirmed by a live A/B on the identical `/llm/chat` route
(Anthropic: humanized correctly; OpenAI/Groq: "internal error"). Filed as
`findings/rc1-drive-composer-chat.json:1`, severity medium (reachable whenever a resumed
Delegate run or a direct API caller hits one of the 5 affected providers with a stale/missing
key — the interactive composer itself still blocks sending before this point per
`ChatSidebar.tsx:786-792`, unchanged from census).

## Spend / lane

Local only (llama3.1:8b via the Ollama lock, ~7 calls) + one free-lane style `--no-key` probe
(zero cost). No paid OpenAI-direct spend this drive.

## Sidecar

Started detached on `:52320`, sleep pid 73681, worker pid 73682, log
`$SCRATCH/composer-chat-sidecar.log`. Stopped at the end of this drive (see log for the kill
timestamp).
