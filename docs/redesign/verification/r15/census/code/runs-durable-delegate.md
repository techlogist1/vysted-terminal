# APOSD critique — runs-durable-delegate

Worker model: `claude-fable-5-1`. Skill `aposd-critique` loaded and followed (two personas,
18 principles, specificity gate). Scope: all 7 owning files read in full (1,609 LOC) plus the
call sites that decide whether the subsystem's promises hold (`agent_runtime.invoke_agent`
round loop, `app.py` lifespan, `ChatSidebar` launch/foreground, `AgentsRail`, `BudgetConfig`).
Raw findings: `../raw/code-runs-durable-delegate.json` (14, prefix `COD-runs-durable-delegate-`).

## Tactical Tornado verdict — HIGH risk

The three Python modules are individually tidy; the subsystem as a whole is tactical. It was
built FR-by-FR (FR-026 guard, FR-027 durable row, FR-028 pause/answer) and each FR is "done"
against its own unit test, but the one abstraction the feature exists for — _a background run
whose state and OUTPUT are owned by the sidecar and collectable by any client_ — was never
built. Most damning pattern: **the driver consumes the agent's event stream and throws it
away** (`run_manager.py:164-178`), keeping a display digest it calls a "checkpoint"; the only
read API cuts that to 500 chars (`runs_store.py:184`); no UI fetches it. A user delegates,
pays, and the row disappears. 11 red flags: information leakage x3 (checkpoint format, wire
casing, "active" definition), conjoined methods x1 (`_drive_run` / `resume_run`), comments that
lie x5, dead surface x5 symbols, special-general mixture x1 (`breach_reason`).

## Design principles score — 3 pass / 10 at-risk / 5 violate (3/18)

| #   | Principle                       | Grade   | Evidence (file:line : pattern)                                                                                                                                                                                                                                                                                 | Consequence                                                                                                                                  |
| --- | ------------------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Strategic over tactical         | violate | `routers/runs.py:44-60` `_dual_case` "keeps either consumer working without a contract negotiation"; `run_manager.py:29-34` control plane shipped without its trigger                                                                                                                                          | Debt is written down as a feature; every later change pays for two spellings and a dead plane                                                |
| 2   | Deep modules                    | pass    | `budget_guard.py:87-172` record/breach/cost hides pricing + clock; `run_manager.py:237-413` five verbs hide `_TASKS`                                                                                                                                                                                            | Callers never touch asyncio or SQL                                                                                                           |
| 3   | Information hiding              | violate | checkpoint format known to `run_manager.py:126-129`, `:338-343`, `:369-382` and `runs_store.py:168-185`; its one invariant ("first user turn = prompt") is broken by its own writer at `:127-129`                                                                                                              | Second answer makes the first answer the prompt (proof P1b)                                                                                  |
| 4   | General-purpose modules         | pass    | `budget_guard.py:95-103` four optional ceilings, injectable `_now`, no run/store knowledge                                                                                                                                                                                                                      | Guard reusable + trivially testable                                                                                                          |
| 5   | Different layer, different abs. | at-risk | `routers/runs.py:133` `code = 409 if "already running" in str(exc) else 404`; `models/run.py:95-104` `RunLaunchResponse` unused while `routers/runs.py:84` returns a raw dict                                                                                                                                  | Error identity crosses the layer as prose; rewording a message changes an HTTP status                                                        |
| 6   | Pull complexity downward        | violate | breach decision sits in the consumer `run_manager.py:176-178`, but only the callback `:133-140` is synchronous with the round boundary (`agent_runtime.py:1466-1473` then tool dispatch `:1551-1575`); client owns "which runs exist" `delegate-runs.ts:164-166`                                                | Ceiling overshoots by a tool batch + one provider request (P5); runs invisible after reload                                                  |
| 7   | Better together / apart         | pass    | store (no asyncio) / manager (no SQL) / guard (neither): `runs_store.py:10-13`, `budget_guard.py:87-93`                                                                                                                                                                                                         | Clean seams; each file testable alone                                                                                                        |
| 8   | Define errors out of existence  | violate | `run_manager.py:291-298`, `:309-316`, `:361-366` no status guards; `runs_store.py:273-275` any transition; `run_manager.py:211-215` shutdown leaves `running`                                                                                                                                                   | done -> cancelled (P3), done -> paused -> re-run, zombie `running` rows (P6)                                                                 |
| 9   | Design it twice                 | at-risk | `models/run.py:30-31` "task is suspended on a future awaiting answer_run" and `runs_store.py:27-28` "the accumulated messages list" describe a better second design that was never built; code is the first one (cancel + lossy digest)                                                                         | Readers trust a design that does not exist                                                                                                   |
| 10  | Comments describe non-obvious   | at-risk | good: `run_manager.py:143-151` (why `asyncio.timeout`), `:118-122`. False: `delegate-runs.ts:190` "the poll will reconcile", `models/run.py:10-14` (wire is camelCase), `app.py:149` ("FIRST" — it is third), `budget_guard.py:24` (steps = "turn that fired tools"; `:125` counts every round)                 | Unknown unknowns: the comment is the only guard and it is wrong                                                                              |
| 11  | Comments first                  | at-risk | `run_manager.py:16-18` "resumable checkpoint", `:26-27` "genuine human-in-the-loop handshake" promise what `:401-412` (provider/model/key = None) cannot deliver                                                                                                                                                | Interface contract over-states the implementation                                                                                            |
| 12  | Choosing names                  | at-risk | `run_manager.py:175` `breach_reason = … getattr(event, "message", …)` (agent errors stored as a "breach"); `checkpoint` is a display digest; `agent-runs.ts:116` `clearFinished` keeps only `running`                                                                                                           | Wrong mental image -> wrong fixes                                                                                                            |
| 13  | Modifying existing code         | at-risk | R10 patch `runs_store.py:72-86` persisted depth+region (the reported symptom) and left provider/model unpersisted (the root)                                                                                                                                                                                    | Same bug class still open (finding 2)                                                                                                        |
| 14  | Consistency                     | at-risk | `routers/runs.py:119-120` answer -> 404 for the error resume maps to 409 at `:133`; unknown run: `cancel_run`/`pause_run` return False, `answer_run`/`resume_run` raise; "active" = running\|paused at `agent-runs.ts:96,107,118` but running-only at `:116`                                                    | Each verb must be re-learned                                                                                                                 |
| 15  | Code should be obvious          | at-risk | `run_manager.py:126-129` history-then-prompt ordering; `runs_store.py:253-262` `None` = leave-as-is plus a `clear_question` escape flag                                                                                                                                                                         | Ordering bug survived review because nothing looks wrong locally                                                                             |
| 16  | Design for the future           | at-risk | `runs_store.py:19-20` `mode` column "so a future foreground-runs surface can reuse the table"; pause plane with no trigger (`run_manager.py:301-316`, zero callers)                                                                                                                                             | Hooks for futures that did not arrive; carrying cost now                                                                                     |
| 17  | Performance as design           | at-risk | `runs_store.py:246-250` `SELECT *` (checkpoints) no LIMIT, polled every 2 s (`delegate-runs.ts:40`); `runs_store.py:296-304` second connection + full re-digest per cost write, on the event loop (`run_manager.py:137`)                                                                                       | Cost grows with history forever; no retention                                                                                                |
| 18  | Increments are abstractions     | violate | FR-by-FR build: output never deliverable (`run_manager.py:164-181`, `runs_store.py:184`, `ChatSidebar.tsx:1178-1187`), client cannot re-attach (`delegate-runs.ts:134-143`)                                                                                                                                     | The feature's core promise is missing while every FR test is green                                                                           |

## What is working

- **BudgetGuard is a genuinely deep, honest module** (`budget_guard.py:87-172`): all-optional
  ceilings, deterministic breach order, injectable clock, over-estimates cache tokens on the safe
  side, and says out loud that `spend_usd` is an estimate. Prices single-sourced from the
  registry (`:53-57`).
- **The wall-clock backstop is reasoned, not cargo** (`run_manager.py:143-152`, `:193-210`): the
  comment explains why a round-boundary check is insufficient, and the handler refuses to
  mislabel a tool's own `TimeoutError` as a ceiling breach.
- **Secrets discipline is structural where it counts**: the options allow-list
  (`runs_store.py:72-86`) is an allow-list, not a block-list; the key lives only on the task
  closure. No path found that writes a key to SQLite.

## Priority issues

**[P0] A Delegate run's output is never delivered** — raw 1. Principle: increments are
abstractions / pull complexity down. Symptom: unknown unknowns. `_drive_run` keeps only delta
text and `[tool_use x]` markers (`run_manager.py:164-181`); `publish_brief` and proposed-change
events die there although the launch note promises "any changes it proposes still need your
review" (`ChatSidebar.tsx:848-849`). `GET /runs/{id}` truncates each message to 500 chars
(`runs_store.py:184`), the rail hides finished runs (`AgentsRail.tsx:29-32`), foreground prints
one status line (`ChatSidebar.tsx:1178-1187`). Live: a 54,450-token / $0.1089 run on the
isolated sidecar is retrievable only as `"I'll pull live valuation data … major IT names an"`.
Fix: persist the final text + brief payload untruncated on the row; return from `GET
/runs/{id}`; in the poller's terminal branch (`delegate-runs.ts:176-179`) fetch once and append
to chat / route the brief through the existing proposed-changes gate. Alternative considered:
stream events over SSE per run — rejected, it re-couples the run to a connection, which is what
Delegate exists to avoid.

**[P0] Resume cannot work** — raw 2 (+ raw 11). Principle: information hiding. Symptom:
change amplification. `resume_run` hard-codes `provider=None, model=None` (`run_manager.py:406-407`),
the routes never pass `api_key`/`budget` (`routers/runs.py:118,130`) though the manager accepts
them (used only by tests, `test_run_manager.py:270,293`), and no UI calls resume. Fix: add
`provider`,`model` to `_PERSISTED_OPTION_KEYS`; accept `apiKey` on resume/answer bodies;
accumulate cost instead of `cost=RunCost()` (`:399`). Alternative: drop resume and the claim —
legitimate if finding 10 is resolved by deletion.

**[P1] The ceiling is not hard and the verdict is not honest** — raw 3, 4, 11, 12. Principle:
pull complexity downward. The stop decision belongs in the callback (raise `_BudgetBreach`);
"finished at the ceiling" is `done`, not `error`; price with the resolved provider
(`agent_runtime.py:1467` passes only the model); fill `None` ceilings server-side
(`run_manager.py:258`).

**[P1] Lifecycle is convention, not structure** — raw 5, 6. Principle: define errors out of
existence. One transition table enforced as `UPDATE … WHERE status IN (…)`; one startup
statement turning orphaned `running` rows into `error: interrupted`; checkpoint inside
`_on_round_usage`. Removes the substring-matched 409 for free.

**[P2] The client is the source of truth for durable runs** — raw 7, 8. Adopt `GET /runs`
running|paused rows at sidecar-ready; make durable cancel pessimistic.

Remaining raw findings: 9 (resume/answer turn order, proof P1), 10 (dead FR-028 plane — operator
decision: wire or delete), 13 (dual-case contract), 14 (unbounded table / per-write re-digest).

## Persona walkthroughs

**Tactical Tornado.** Asked for "durable", they add a SQLite row and stop (`runs_store.py:6-8`
documents the post-restart zombie as intended). Asked for "resumable", they dump whatever the
loop happened to print into `checkpoint_json` (`run_manager.py:126-129,168-181`) and re-parse it
with a positional convention (`:369-382`). Told the poller reads snake_case while the model emits
camelCase, they emit both (`routers/runs.py:44-60`). Told pause cannot be triggered, they write a
test that pauses a finished run (`test_run_manager.py:258-266`) and a docstring that calls it
"fully implemented" (`run_manager.py:33`). Every step is locally reasonable and green.

**Strategic Thinker.** Starts from the caller's sentence: "run this in the background under a
budget; show me where it is; give me the result; let me stop or continue it — from any client, at
any time." That yields a run row owning `{launch params (non-secret), status via a guarded
transition, cost (cumulative), turns[], result}`; `on_round_usage` becomes the single place that
meters, checkpoints, and can stop the loop; the frontend store becomes a cache of `GET /runs`.
Same three modules, same size — the difference is which side of each interface the knowledge
sits on.

## Proofs (no network, faked provider; all re-runnable)

Run from `sidecar/`: `./.venv/bin/python <script>` (script below). Output captured this run:

```
P2 status/detail/transcript: error | step ceiling 1 reached (1 taken) | [user 'q', assistant 'FULL ANSWER.']
P5 status: error | provider calls after 1-round breach: 2 | cost: tokens=100000 spend_usd=0.5 steps=1
P1a messages on 1st answer: [('assistant','FULL ANSWER.'), ('user','ANSWER ONE'), ('user','ORIGINAL PROMPT')]
P1b messages on 2nd answer: [… ('user','ORIGINAL PROMPT'), ('assistant','FULL ANSWER.'), ('user','ANSWER TWO'), ('user','ANSWER ONE')]
P3 done-run after cancel_run: done -> cancelled
P4 resume invoke kwargs: {'provider': None, 'model': None, 'api_key': None}
P6 after shutdown(): status = running | checkpoint msgs = 1
```

Live read-only check (isolated sidecar `:52152`, GET only): 2 rows (1 cancelled, 1 done);
the done row = 54,450 tokens, `spend_usd` 0.1089, 10 checkpoint messages, final assistant
message exactly 500 chars, cut mid-word.

<details><summary>proof script</summary>

```python
import asyncio, os, sys, tempfile
from config import DATA_DIR_ENV
os.environ[DATA_DIR_ENV] = tempfile.mkdtemp(prefix="r15-runs-proof-")
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage
from models.run import RunBudget
from services import agent_runtime, run_manager, runs_store

class OneShot:
    def __init__(self): self.seen = []
    async def stream_chat(self, messages, model, api_key=None, **kw):
        self.seen.append([(m.role, m.content[:40]) for m in messages if m.role != "system"])
        yield LLMDeltaEvent(text="FULL ANSWER.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=50, output_tokens=20))

class Looping:
    calls = 0
    async def stream_chat(self, messages, model, api_key=None, **kw):
        self.calls += 1
        yield LLMToolUseEvent(tool_call_id=f"c{self.calls}", name="price_data", input={})
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=100_000, output_tokens=0))

class Slow:
    async def stream_chat(self, messages, model, api_key=None, **kw):
        await asyncio.sleep(30); yield LLMDoneEvent()

async def wait(rid):
    t = run_manager._TASKS.get(rid)
    if t is not None:
        try: await asyncio.wait_for(asyncio.shield(t), 10)
        except BaseException: pass
    return runs_store.get_run(rid)

def use(p): agent_runtime.get_provider = lambda *_a, **_k: p

async def main():
    agent_runtime.reload()
    use(OneShot())
    r = await wait(run_manager.launch_run(agent_id="copilot", prompt="q", budget=RunBudget(max_steps=1)))
    print("P2", r.status, r.detail, r.transcript)
    lp = Looping(); use(lp)
    r = await wait(run_manager.launch_run(agent_id="copilot", prompt="q", budget=RunBudget(max_tokens=1000)))
    print("P5", r.status, lp.calls, r.cost)
    p = OneShot(); use(p)
    rid = run_manager.launch_run(agent_id="copilot", prompt="ORIGINAL PROMPT"); await wait(rid)
    run_manager.pause_run(rid, "Q1?"); run_manager.answer_run(rid, "ANSWER ONE"); await wait(rid)
    print("P1a", p.seen[-1])
    run_manager.pause_run(rid, "Q2?"); run_manager.answer_run(rid, "ANSWER TWO"); await wait(rid)
    print("P1b", p.seen[-1])
    use(OneShot())
    rid = run_manager.launch_run(agent_id="copilot", prompt="q"); before = (await wait(rid)).status
    run_manager.cancel_run(rid); print("P3", before, "->", runs_store.get_run(rid).status)
    cap, real = {}, agent_runtime.invoke_agent
    async def spy(**kw):
        cap.update({k: kw.get(k) for k in ("provider", "model", "api_key")})
        async for e in real(**kw): yield e
    agent_runtime.invoke_agent = spy; run_manager.resume_run(rid); await wait(rid)
    agent_runtime.invoke_agent = real; print("P4", cap)
    use(Slow()); rid = run_manager.launch_run(agent_id="copilot", prompt="q")
    await asyncio.sleep(0.05); await run_manager.shutdown()
    r = runs_store.get_run(rid); print("P6", r.status, r.checkpoint_messages)

asyncio.run(main())
```

</details>

## Minor observations

- `_coerce_snapshot` (`run_manager.py:79-82`) swallows every validation error into a bare
  `by_source` wrapper — legitimate masking, but with no log line a malformed snapshot is
  undiagnosable.
- `RunBudget.max_steps` above 7 is a no-op (`_MAX_TOOL_ROUNDS = 6`, `agent_runtime.py:543`); the
  UI default is 12 (`BudgetConfig.tsx:11`) — the steps field cannot bind at its default.
- The original chat `history` sent at launch (`ChatSidebar.tsx:863`) is not in the checkpoint, so
  a resume loses the conversation the run was launched from.
- `setInterval` poller is never cleared in production (`delegate-runs.ts:61-66`); cheap (early
  return) but has no in-flight guard or fetch timeout.
- `launchDelegateRun` with a 201 lacking both `runId`/`run_id` leaves a local row `running`
  forever with no abort (`delegate-runs.ts:118-123`).
- `docs/SIDECAR_API.md` has no section for the six run routes.

## Questions to consider

- If a run's result cannot be collected, is Delegate a shippable mode for launch, or should the
  composer hide it until raw 1 lands?
- FR-028: is a self-pausing agent (`ask_user`) on the launch roadmap? If not, deleting the
  pause/answer plane removes raw 9 and 10 and ~200 LOC + a UI form in one move.
- Should the spend ceiling be documented as "soft, +1 round" or made hard (raw 3)? The word
  "hard" appears 9 times across these files.

## Run notes

- Skill: `aposd-critique` loaded; `references/principles.md` read.
- Assessment independence: **degraded (sequential)** — this worker has no sub-agent tool;
  Assessment A (principles table) was completed before B (red-flag scan).
- Snapshot persistence to `.aposd/critique/`: **skipped on purpose** — the census contract names
  the two output files, and a stray untracked tree in the operator's repo is what the R15
  push-guard exists to catch.
- No GUI, no POST to the live app; isolated sidecar used GET-only; no LLM calls; one scratch
  proof script run against the source venv with a temp data dir.
