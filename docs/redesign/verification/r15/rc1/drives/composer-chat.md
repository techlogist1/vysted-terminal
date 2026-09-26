# RC1 drive: composer-chat

Candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` (`rc1-cand` worktree, read-only). Own
sidecar started from `rc1-cand/sidecar` on `:52320` with a copy of `rc1-seed-data`
(`rc1-data-rc1-drive-composer-chat`), MCP env pointed at the shared `:52153`/`:52154`. Stopped
by killing its own sleep pid (67607) at the end of this drive. Writes went to my own sidecar
only; all reads that didn't need a write ran against the shared `:52152`. Evidence under
`docs/redesign/verification/r15/surface/composer-chat/rc1/`.

## Scope and method

The census (`surface/composer-chat/EVIDENCE.md`, `COVERAGE.json`, 24 rows) drove this group
in full on 23 Sep and the refuter admitted all 11 raw findings it produced
(`census/refute/surf-composer-chat.json`). Every one of those 11 maps to a register entry
(`vysted-r15-register.json`), every one is `status: "fixed"`, and several carry a
`note` documenting that an EARLIER certification pass (batch 6/7/8) found the fix incomplete
before a LATER batch closed it. That history is exactly what an RC1 gate needs to re-check:
not "was this ever fixed" but "does the FIXED behaviour hold on the final candidate." I
re-verified all 11 against `4097dac4`, using the census's own repro shape wherever it was a
pure API/tool/code-level probe (no LLM needed to re-prove a code-level mechanism), and one live
`ollama`/`llama3.1:8b` round-trip through `vy.py` for a fresh end-to-end sanity check. All 11
closure commits (`c81d879`, `1574ed8`, `e81c9e7`, `68bb7aa4`, `6b70230`, `f407107`) are
confirmed ancestors of `4097dac4` (`git merge-base --is-ancestor`).

Given the volume of unrelated chat/agent work merged since census (batch 6 through 11 on
`src/modules/chat/`, `src/lib/host-actions.ts`, `sidecar/services/agent_runtime.py` — dozens of
`R15-AGENT-*`/`R15-UI-*` commits), a full from-scratch re-drive of all 24 `COVERAGE.json` rows
was out of this pass's time/ollama-contention budget (three sibling RC1 drives shared the one
local `ollama` instance; my own `llama3.1:8b` call took 238s against a 6-50s baseline). I
prioritized the 11 known findings plus the interactions they map to; the remaining rows carry
the census score forward with a note, per `COVERAGE.json`.

## Census → RC1 scored table (the 11 admitted findings)

| Raw id | Register | Census verdict | RC1 verdict | Evidence |
|---|---|---|---|---|
| SURF-COMPOSER-CHAT-1 (ollama tool-call rescue missing) | R15-AGENT-018 | broken (high) | **ok** | shared `tool_call_rescue.py` used by both `ollama.py:262` and `openai.py:760`; residual noted below |
| SURF-COMPOSER-CHAT-2 (compare_symbols invents ticker) | R15-AGENT-045 | broken (medium) | **ok** | live in-process `compare_symbols` on "Cochin Shipyard"/"Mazagon Dock" → both resolve to COCHINSHIP/MAZDOCK with real quotes+fundamentals, `rc1/02-compare-symbols-repro.log` |
| SURF-COMPOSER-CHAT-3 (502 leaks raw yfinance text) | R15-DATA-061 | broken (low) | **ok** | `GET /quotes/ZZZZNOTREAL` → 404 `not_found` sentence; `GET /history/XYZ%2FABC` → clean 502, no `AttributeError` text; `rc1/04-resolve-quotes-repros.txt` |
| SURF-COMPOSER-CHAT-4 (dropped batch symbol renders "—") | R15-DATA-062 | broken (low) | **ok** | `sidecar/routers/quotes.py:87-88` now forces each returned quote's `symbol` to the REQUESTED spelling (C14), fixing the client-side join |
| SURF-COMPOSER-CHAT-5 (intent gate strips write_note/screener) | R15-AGENT-019 | broken (high) | **ok** | in-process `classify_intent` on the exact 4 census prompts (write a note / screen for / save this screen / jot down) → all now `edit` not `read`; `rc1/00-classify-intent-repro.txt` |
| SURF-COMPOSER-CHAT-6 (stop doesn't cancel tool task) | R15-AGENT-002 | broken (high) | **ok** | in-process repro: `aclose()` on the SSE generator mid-dispatch now cancels the tool task (`agent_runtime.py:1130-1134`); `rc1/01-stop-cancel-repro.py`/`.out` |
| SURF-COMPOSER-CHAT-7 (add_to_watchlist applies invented ticker) | R15-AGENT-044 | broken (medium) | **ok** | `host-actions.ts:2052` `addResolvedEquity` now calls `GET /resolve` before adding; live `GET /resolve?q=Mazagon Dock` → MAZDOCK 0.92 confidence |
| SURF-COMPOSER-CHAT-8 (empty ollama tool_call_id breaks ack) | R15-AGENT-046 | broken (medium) | **ok** | `agent_runtime.py:1987` now mints `call_{uuid4}` for every tool call regardless of provider — fixes both the per-turn AND cross-run uniqueness gap the census/batch-6 residual flagged |
| SURF-COMPOSER-CHAT-9 (10-100x wrong money figures) | R15-AGENT-001 | broken (critical) | **ok (code-confirmed; live check inconclusive)** | `semantics.py:1216-1223` `display_value` pre-scales every `_PROMPT_KEYS` metric (incl. `market_cap`) to crore with a spelled unit before it reaches the model payload — the register's stated fix shape. A live re-drive (`rc1/03-t1-cochinship.*`) hit a `fundamentals` tool TIMEOUT under heavy sibling-agent ollama contention before the model could quote a market cap, so it self-computed one from partial data instead (₹19,343 cr, wrong) — an environment artifact of shared-ollama load, not a reproduction of the original defect (no `dividend_yield`/`market_cap` payload value was even read). See notes. |
| SURF-COMPOSER-CHAT-10 (ASK narrates a staged change as done) | R15-AGENT-033 | broken (medium) | **partial** | `agent_runtime.py:1343` `_staged_actions_notice` + `:1780` `turn.staged_actions` now emit a machine-readable end-of-turn ground truth of what actually staged vs applied, independent of the model's prose — a real mitigation, code-confirmed. Not re-driven live this pass; the model's own narration can still claim "I've set X" (the notice runs alongside it, not instead of it), so left partial rather than ok. |
| SURF-COMPOSER-CHAT-11 (delegate resume drops model, pause unreachable) | R15-LIFECYCLE-013 | broken (medium) | **ok** | `run_manager.py:551-554` resume now passes `provider=run.provider, model=run.model` explicitly; `run_manager.py:305-313` a halted `ask_user` run now transitions to `status="paused"` directly from the run loop (the old `pause_run` had no caller at all — now bypassed by a different, working mechanism) |

**9 of 11 census `broken` interactions verified `ok` at RC1; 1 upgraded to `partial` (real
server-side mitigation, model-narration risk remains); 1 code-confirmed `ok` but the live
re-drive was inconclusive due to shared-ollama contention, not a product defect.**

No regression found: nothing the census scored `ok` regressed at RC1 in the interactions
driven this pass. No fresh (non-register) defect found in what was driven.

## What this pass did NOT re-drive

The 13 `COVERAGE.json` rows outside the 11 findings above (`composer-mount`,
`composer-depth-control`, `composer-model-control`, `composer-plus-menu`,
`composer-mention-picker`, `composer-slash-picker`, `composer-queue`, `chat-agents-rail`,
`chat-empty-state`, `chat-suggestion-chips`, `chat-plan-view`, `chat-research-activity`,
`chat-budget-config`, `agent-mode-toggle`, `agent-persona-picker`, `agent-command-bus`,
`llm-chat-streaming`, `chat-markdown-render`, `context-provider-badge`) carry the census score
forward in `rc1/COVERAGE.json` with a note — not independently re-verified this pass. They are
mostly pure/deterministic frontend logic (`composer-collapse.ts`, `model-options.ts`,
`mentions.ts`, `slash-commands.ts`, `ComposerPlusMenu.tsx`'s `buildPlusMenuSections`) that no
commit in the `git log` window touched by name; a fuller RC1 pass should still re-run
`50-existing-unit-tests.log`'s 269-test vitest suite (not re-run this pass) to catch any
regression these rows would show.

## Spend

Local/keyless only this pass — one `ollama`/`llama3.1:8b` invoke via `vy.py`
(`rc1-cc-t1-cochinship`, 237.6s, $0.00). No paid-provider calls.

---

## Pass 2 — re-verified against 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 (gate round 2)

The candidate advanced from `4097dac4` (pass 1, above) to `4c6dfe8c` on the same integration
branch — `4097dac4` confirmed an ancestor (`git merge-base --is-ancestor`), 297 commits between
them. Most are `R15-LEAD-030/033/035/036` citation-guard and figure-guard rework in
`agent_runtime.py` plus `R15-AGENT-090/092/093` fixes — none revert or touch the 11 findings'
own fix sites. Own sidecar re-booted from `rc1-cand` (now at `4c6dfe8c`) on `:52320`, same
`rc1-data-rc1-drive-composer-chat` data dir (already a keyless copy of `rc1-seed-data`),
stopped by killing its sleep pid (58519) at the end of this pass.

### Delta method (not a full re-drive — targeted regression check)

1. Grepped every fix anchor cited in pass 1's table against the current source — all present
   unchanged in mechanism: `tool_call_rescue.py` (shared by `services/llm/ollama.py` +
   `services/llm/openai.py`), `classify_intent` (`services/planner.py:203`), the `aclose()` ->
   `task.cancel()` path (`agent_runtime.py:1213-1220`), `addResolvedEquity` calling `GET
   /resolve` first (`host-actions.ts:2055-2058`), the `call_{uuid4().hex}` id mint
   (`agent_runtime.py:2863`), `_staged_actions_notice` (`agent_runtime.py:1432`), `run_manager`
   resume passing `provider=run.provider`/paused-on-halt (`run_manager.py:305-316,551-561`),
   and the requested-symbol join in `quotes.py`. `semantics.py` moved to
   `services/research/semantics.py` (path change only) — `display_value`/`_PROMPT_KEYS` still
   there (line 189); it now also carries a NEW `market_cap_witness` divergence check
   (lines 830-892) cross-checking provider market cap against an exchange-master-implied
   figure — an additional safeguard layered on top of the R15-AGENT-001 fix, not a regression.
2. Ran the sidecar's own regression suite for this surface rather than hand-rolling repros for
   everything pass 1 covered by test: `pytest tests/test_compare_symbols.py
   tests/test_tool_call_rescue.py` → 21 passed; `pytest tests/test_agent_runtime.py
   tests/test_run_manager.py tests/test_planner.py` → 320 passed (`rc1/v2-05-*.txt`,
   `rc1/v2-06-*.txt`).
3. Live re-checks on the fresh `:52320` sidecar (`rc1/v2-01..04`): `GET /resolve?q=Mazagon
   Dock` → MAZDOCK 0.92 confidence (unchanged); `GET /quotes?symbols=RELIANCE.NS,ZZZZNOTREAL,
   TCS.NS` → both real symbols returned under their REQUESTED spelling, the dead one dropped
   cleanly (no join failure); `GET /quotes/ZZZZNOTREAL` → clean 404 `not_found` sentence, no
   raw provider text; in-process `classify_intent` on the same 4 census prompts → 3/4 `edit`,
   1/4 now `build` (compound-detection path, added since pass 1) but `IntentResult.is_actionable`
   (`intent != "read"`) is still `True` for all 4 — the original defect (classified `read`,
   tools stripped) does not recur under any of the 4 prompts.
4. Re-ran pass 1's own in-process stop-cancel repro (`01-stop-cancel-repro.py`, unmodified)
   against the current `_dispatch_tool_with_progress` (signature/mechanism unchanged) →
   `tool task cancelled on aclose: True` (`rc1/v2-08-stop-cancel-repro.out`).
5. Host-action live acks (watchlist add, note write) remain **NOT independently re-verifiable
   headless-live**: watchlist-add is a frontend `SerializedWorkspace` store mutation, not a
   sidecar route (`GET/POST /watchlist` → 404 on the sidecar, confirmed live,
   `rc1/v2-07-watchlist-roundtrip.txt` — expected, matches pass 1's code-level verification via
   `/resolve`); notes are not a sidecar router either (no `routers/notes.py`) — both are
   `NEEDS-GUI` for a live round-trip, consistent with pass 1's scoring, not a new gap.

### Result

**No regression** in any of the 11 pass-1-verified findings at `4c6dfe8c`. **No new defect**
found in what this pass drove. The `classify_intent` label drift (edit→build on one of the 4
census prompts) is a labeling change with no behavioural effect (both keep the tool surface)
and is not filed as a finding. `rc1-drive-composer-chat.json` stays `[]`.

### Spend

Zero live-model spend this pass (no ollama/OpenRouter/OpenAI calls — all checks were
pytest/code-level/direct-HTTP against the local sidecar, no LLM round-trip needed to
re-confirm mechanisms already proven end-to-end in pass 1 and in the existing test suite).
