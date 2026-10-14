# R15 Stage 1 census — code critique: `agent-runtime` (Agent Runtime)

**Model:** `claude-opus-5[1m]` · **Skill:** `aposd-critique` (loaded; the two personas
were run sequentially in one context — **assessment independence: degraded
(sequential)**, no sub-agents dispatched under the Stage-1 read-only budget).
**Scope:** the 21 files / 2,639 LOC of the `agent-runtime` entry in
`CODE_PARTITION.json`, all read in full (`agent_runtime.py` 1,631 lines,
`agents_store.py`, both routers, both models, the 13 persona JSONs + `_schema.json`).
Repo read-only; the only writes are this file and `../raw/code-agent-runtime.json`.
Two claims were proven by running the real code under the sidecar venv with a
scripted fake provider (no network, no writes) — probe transcript inlined below.

---

## Tactical Tornado verdict

**Medium.** This is not hacked-together code — it is *accreted* code. Every
increment (D21, R9 two-tier search, R10 E2/E3.3/E5/E7, R13 JARVIS 1b/1c, WS8, FR-081,
FR-115) was appended into the same function rather than given a home, and the result
is a 403-line `invoke_agent` (`agent_runtime.py:1229-1631`) that owns fourteen
separate concerns. Individually most of the increments are *good* engineering: the
catalog-derived tool grant (`:189-220`) deliberately kills a whole class of drift, and
the ack read-back (`:1083-1145`) replaced optimistic narration with ground truth. The
tornado signature is not laziness — it is that **the same problem was solved twice,
differently, in two places**, and that **an invariant the code needs is written in a
comment instead of enforced by the structure**.

The most damning pattern: the tool-round cap. `agent_runtime.py:1627-1631` ends the
loop body with

```python
rounds += 1
if rounds >= _MAX_TOOL_ROUNDS:
    # Hit the cap — let the next provider stream finalise. The
    # subsequent loop iteration sees no pending tools and exits
    # via the ``not pending_tools`` branch above.
    continue
```

The `continue` is a literal no-op (it is the last statement of a `while True` body),
and the comment states an assumption — "the subsequent loop iteration sees no pending
tools" — that **nothing enforces**: `tool_ids` is still sent on the 7th stream, so a
looping model calls tools again. Proven below: the 7th round's tool calls are streamed
to the UI (where `ChatSidebar.tsx:941-951` stages or auto-applies them) and then
**never dispatched**, and the turn ends with zero assistant text. Forty lines earlier,
the *web-search* cap solves the identical problem correctly — it returns a
"answer from the sources you already gathered" tool result (`:1554-1565`) — so the
right answer already exists in the same function.

Flags found: 12 (2 duplicated-truth pairs with identical membership, 3 cross-layer
leaks, 2 silent-degrade paths, 1 network call with no timeout beside three siblings
that all pass one, 1 leaked task on client abort, 1 dead config field, 1 dead
function kept alive by its own test, 1 no-op branch). Zero temporal decomposition,
zero pass-through methods of consequence.

---

## Probe transcript (real code, scripted fake provider, no network)

```
PROBE-1 round cap
  provider rounds          : 7
  tool_use events yielded  : 7 ['tc1' … 'tc7']
  tools actually dispatched: 6 ['tc1' … 'tc6']
  undispatched, announced  : ['tc7']
  assistant text frames    : 0
  last event kind          : LLMDoneEvent

PROBE-2 client abort mid-tool
  right after aclose(): tool finished = False
  0.6s later          : tool finished = True      # the consumer left; the tool ran on
```

Driver: `invoke_agent("copilot", …)` with a provider that emits one `tool_use` per
round, `agent_runtime._dispatch_tool` wrapped to count dispatches; and
`_dispatch_tool_with_progress` driven directly with a 0.4 s local tool, then
`aclose()`d mid-flight (what an ASGI SSE disconnect does).

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|-----------|---------|----------------------|-------------|
| 1 | Strategic over tactical | **at-risk** | `agent_runtime.py:189-220` `_grant_first_party_hands` is a real strategic fix (catalog-derived grant kills the E5 "I have no backtesting tool" drift class) — but it sits beside `:1229-1631`, where fourteen increments were appended into one function | Each new feature is cheap to add and impossible to test or change in isolation |
| 2 | Deep modules | **pass** | The public surface is `list_agents()` / `get_agent(id)` / `invoke_agent(…)` (`:283-321`, `:1229`) over 1,631 lines of provider quirks, tool dispatch, gating and auto-publish | Small interface over a large body — the right ratio; the routers stay genuinely thin (`routers/agents.py:91-112`) |
| 3 | Information hiding | **violate** | `:846-927` decodes the research tool's *private* payload variants: `web.citations` **or** `web.results`, `row.excerpt` **or** `row.snippet`, `web.note`/`detail`/`reason`, `web_available` vs `web.available` | The runtime knows the research subsystem's internal shape history; a FAST-payload rename silently empties the brief's sources |
| 4 | Information leakage | **violate** | `:55` `from services.llm.openai import INVALID_ARGS_SENTINEL` — the provider-agnostic loop imports one adapter's sentinel to detect bad args (`:642`); `:906-927` hand-mirrors the frontend's `briefFromInput` snake_case keys; `_LOOP_TO_MODE_DEPTH` (`:770-783`) encodes the research engines' loop ids | Three layers' internals are re-stated here; each one drifts independently and nothing tests the pairing |
| 5 | General-purpose modules | **at-risk** | `_step_event` (`:696-721`) is deliberately duck-typed "so a future tool can emit progress without importing the research models" — genuinely general; but the same loop then special-cases `if tool_call.name in _RESEARCH_TOOLS` (`:1602`) and `if event.name == "publish_brief"` (`:1449-1457`) | Special-general mixture: one tool's behaviour is welded into the generic dispatch loop |
| 6 | Different layer, different abstraction | **violate** | `_ADAPTER_OPTION_KEYS` (`:98-107`) + the scrub at `:1381-1385` — the *runtime* decides which kwargs each provider SDK tolerates; `routers/llm.py:126-130` answers the same question with a 4-key **deny-list** | Two opposite policies for one problem; `/llm/chat` still forwards an unknown `depth` key straight into the SDK — the exact crash `:1363-1366` documents |
| 7 | Pull complexity downward | **violate** | The `depth`-alias pop (`:1368`), the option scrub (`:1381`) and the Gemini `metadata["name"]` pairing (`:1576-1586`) are all adapter-shaped repairs living in the shared loop | Every caller of an adapter must re-learn the repair; the adapter layer stays naive |
| 8 | Better together / apart | **at-risk** | `_auto_publish_event` (`:795-932`, 138 lines) + `_mode_depth_from_execution` (`:786-792`) are pure research-payload → brief translation, living in the agent loop | Two subsystems change together but are edited in different files by different owners |
| 9 | Define errors out of existence | **violate** | `:1472` + `:1627-1631` — at the round cap the last round's tool calls are announced and dropped (proven); `:1396-1399` calls `oneshot.complete` with **no** `timeout` while the docstring at `oneshot.py:60-73` warns the adapter has none (~600 s SDK default); `agents_store.py:87` `json.loads` is unguarded | Three ways to turn a failure into a silent dead end: a turn with no answer, a stalled composer, a 500 on the whole custom-agent list |
| 10 | Design it twice | **pass** | `_superseded_by_later_apply` (`:971-988`) reasons through a rival rule (per-call contradiction vs single-slot panel truth) and documents why the loser loses; `:1157-1169` weighs auto-dispatch vs staged narration | The alternative is written down, not just the winner — this is why the divergence notices are honest |
| 11 | Comments describe non-obvious | **pass** | `:1580-1585` ("Gemini pairs a `function_response` to its call by name, not id") and `:748-750` ("the drain loop blocks on the queue — always wake it") explain *why*, which code cannot carry | Genuine unknown-unknown reduction; both are traps a reader would otherwise re-introduce |
| 12 | Comments as design record | **at-risk** | `:1516-1526` "WS8 Step 4 … NEEDS-MANUAL-CHECK", `:1544-1547` "R13 JARVIS 1b", `:766` "R10, E2", `:1307` "FR-080/081/WS5" — ~40 in-code ticket references | CLAUDE.md's own rule ("history … belongs in `CHANGELOG.md`") is applied to the DNA file and not to the code; a reader must do archaeology to know whether a branch is still load-bearing |
| 13 | Choosing names | **pass** | `_grant_first_party_hands`, `_grounded_host_action_result`, `_superseded_by_later_apply`, `_ToolDone`, `_STEP_SENTINEL` | Names carry the model; the orthogonal `mode` / `autonomy` axes are explicitly documented at `models/agent.py:84-96` |
| 14 | Modifying existing code | **violate** | `_grant_first_party_hands` made every persona's `tools` array dead (buffett declares 3, gets 50 — verified) yet `_schema.json:36-41` still documents it as the allow-list and `routers/agents.py:76` still publishes it; `_schema.json:43-46` still lists 7 providers after `openrouter` became the 8th (`model_registry.provider_ids()`) | The new mechanism was added; the old one was left standing and still looks authoritative to the next maintainer |
| 15 | Consistency | **violate** | Round cap drops calls (`:1472`) vs web-search cap synthesizes (`:1554-1565`); runtime allow-list (`:1381`) vs router deny-list (`routers/llm.py:126`); first-party loader skips one bad file and keeps the roster (`:250-262`) vs `agents_store.list_agents` where one bad row kills the whole list (`agents_store.py:87,103-111`) | Three identical problems, three different answers; a reader cannot generalise any of them |
| 16 | Code should be obvious | **at-risk** | `:1627-1631` — a `continue` that is a no-op, under a comment asserting an invariant the code does not enforce; `:406-409` labels `charts[0]` "Focused chart" when `focusedPanel` is right there in the same dict | Both read as correct and are not; the first cost a whole feature (proven), the second corrupts the model's context |
| 17 | Design for the future | **at-risk** | No wall budget on a foreground turn: `_MAX_TOOL_ROUNDS = 6` (`:543`) × a research guard up to `480 + 90 = 570 s` (`:585-609`); `BudgetGuard` is wired only through the delegate path's `on_round_usage` (`:1466`) | A chat turn can legitimately run ~57 minutes with no ceiling and no way for the user to bound it |
| 18 | Performance as design | **at-risk** | `routers/agents.py:88` calls `get_agent` for the 404 and `invoke_agent` calls it again (`:1264`) — two SQLite connects, each running `CREATE TABLE IF NOT EXISTS` (`agents_store.py:72`), per custom-agent invoke; `classify_intent(prompt)` runs twice (`:1282`, `:1393`) | Small, but it is repeated work on the hottest path, and the double connect is invisible at the call site |

**Summary: 4 pass, 7 at risk, 7 violate (4/18 pass).**

---

## What's working

- **The catalog-derived tool grant** (`:189-220` + `catalog.default_grant_tool_ids`).
  It does not paper over the drift — it removes the possibility of it: a first-party
  agent's effective belt is *computed*, so a JSON file can no longer fall behind the
  registry. This is the single best design decision in the subsystem.
- **The ack read-back** (`:1065-1145`, `:991-1048`). Replacing "the tool call
  succeeded, therefore say it happened" with "poll the panel's ack, then rewrite the
  tool result from the real outcome" is the correct shape for an agent that narrates
  its own effects, and `_superseded_by_later_apply` shows the author thought about
  the false-positive case rather than shipping the naive version.
- **`_dispatch_tool` never raises** (`:648-676`). Every failure — unregistered tool,
  handler exception, timeout, unserialisable payload — becomes a structured
  `{"ok": false, …}` the model can recover from. The loop above it is therefore
  allowed to be simple.

---

## Priority findings

### P0 — the round cap announces tool calls it never runs, and ends the turn silent

`agent_runtime.py:1472` breaks to the dispatcher only while `rounds < _MAX_TOOL_ROUNDS`;
`:1627-1631` increments and no-op-`continue`s on the assumption the next round will be
tool-free. It is not: `tool_ids` is still sent (`:1438`), so round 7's `tool_use` events
are yielded at `:1459` — where `ChatSidebar.tsx:941-951` stages them in the proposal
gate or auto-applies them — and then the `done` branch returns without dispatching
anything. Proven: 7 announced, 6 dispatched, **0 assistant text frames**.
*Complexity symptom:* unknown unknowns — the comment tells the next reader the case
cannot happen. *Fix:* on the final round, re-enter once with `tool_ids=[]` and a
`{"ok": false, "message": "tool budget exhausted — answer from what you have"}`
tool result, exactly as the web-search cap already does at `:1554-1565`.

### P0 — "Focused chart" is `charts[0]`, and contradicts the deixis line beside it

`:406-409` renders `charts[0]` as "Focused chart: X (tf, indicators)". The frontend
builds `charts` by iterating `Object.entries(bySource)` (`context-provider.ts:225-236`)
— bus insertion order — while it resolves `focusedSymbol` from the chart whose
`panelId === focusedPanel` (`context-provider.ts:276-278`). With two chart panels open
and the second focused, one system message says *"Focused chart: AAPL (1d, RSI)"* and
the next line says *"When the user says 'this' … they mean NVDA"*. The snapshot already
carries `focusedPanel` (`context-provider.ts:315`); `_render_terminal_preamble` never
reads it. *Complexity symptom:* change amplification via a wrong shared assumption —
the model may fetch, compare and narrate the wrong instrument, which `copilot.json`'s
own prompt calls "a correctness failure, never acceptable". *Fix:* pick the chart whose
`panelId` matches `ts["focusedPanel"]`, else fall back to `charts[0]`.

### P1 — the planner pre-pass is the only `oneshot.complete` caller with no timeout

`:1396-1399` awaits a full LLM completion **before the first token of the turn streams**.
`oneshot.py:60-73` documents that adapters carry no per-stream timeout (OpenAI SDK
default ~600 s) and that `timeout=` exists for exactly this; `deep_research.py:323` and
`company_narrative.py:468` both pass one. The `except Exception` at `:1412` catches a
crash, not a hang. *Complexity symptom:* cognitive load — the guard *looks* total.
*Fix:* `timeout=15` on the call; a slow planner degrades to the preamble-driven loop,
which is already the documented behaviour for weak models.

### P1 — Stop does not stop: the tool task outlives the aborted stream

`_dispatch_tool_with_progress` (`:752-763`) creates the tool task and, on the way out,
resets the step sink but never cancels it. When the user hits Stop
(`ChatSidebar.tsx:1297` → `AbortController.abort()` → ASGI closes the generator), the
running tool keeps going — proven. For a `deep`/`ultra` research round that is up to
570 s (`:585-609`) of continued BYOK provider spend on a turn the user abandoned, and
three stop-and-retry cycles leave three research runs racing. *Fix:* `task.cancel()`
in the `finally`, with `contextlib.suppress(asyncio.CancelledError)` around an await.

### P2 — two frozensets with identical membership and different safety meanings

`_STAGEABLE_PLAN_ACTIONS` (`:61-70`) and `_READ_SAFE_PANEL_ACTIONS` (`:76-85`) are
*equal* (verified). One bounds what a plan may pre-stage; the other is the §6.5-adjacent
allow-list that survives the read-only strip (`:1300-1305`). The next person to add a
panel action will edit one — silently widening the read-only gate, or silently failing
to. *Fix:* one constant named for the shared property (`_READ_SAFE_PANEL_ACTIONS`), the
other defined from it, or a one-line test pinning the relation.

---

## Persona walkthrough

**Tactical Tornado.** If the Tornado wrote this, the next capability would be one more
`if event.name == "…"` inside the round loop, beside `:1449` and `:1602`, and one more
prose paragraph in `TERMINAL_CAPABILITIES_PREAMBLE` (`:151-186`) restating the tool
list the catalog already owns. The preamble is the live drift site: it names ~20 tools
in English, `copilot.json` names them again in its own 6,000-word prompt, and
`_grant_first_party_hands` then appends the preamble on top of that prompt — so the
flagship agent carries both copies. Rename a catalog tool and 13 agents keep promising a
capability that answers `"tool 'x' is not available in this build"` (`:670`).

**Strategic Thinker.** The redesign is mostly *extraction*, not rewriting. Lift
`_auto_publish_event` + `_mode_depth_from_execution` (`:786-932`) into the research
tool, so it returns a brief-shaped result the loop publishes without knowing that
`loop == "iter"` means deep or that FAST strands its citations under `web.`. Lift the
option scrub (`:98-107`, `:1381-1385`) into the adapter base, so `routers/llm.py:126-130`
can delete its deny-list. Turn the round cap into an explicit final-synthesis round.
Those three moves take ~250 lines out of `invoke_agent`, delete a whole class of drift,
and leave the loop doing one thing: stream, dispatch, feed back, terminate.

---

## Minor observations

- `agents_store._ensure_schema` (`agents_store.py:79-82`) has exactly one caller in the
  repo: `tests/test_agents_store.py:49-51`, the test that tests it. The same dead
  function + dead test pair is copy-pasted into `plugins_store.py:89`,
  `portfolio_db.py:61` and `runs_store.py:119`.
- `_resolve_model` (`:536`) falls back to `"gpt-4.1-mini"` for *any* provider missing
  from the registry — an OpenAI model id sent to Anthropic reads to the user as a
  broken key.
- `copilot.json` ships `defaultProvider: "ollama"` / `qwen2.5:7b`, which
  `_PLANNER_PROVIDERS` (`:90`) excludes as unreliable — the flagship agent's
  out-of-box configuration is the deliberately degraded lane.
- `_MAX_PREAMBLE_CLAIMS`, `_ACK_GRACE_SECONDS`, `_ACK_POLL_SECONDS` are module-level
  "so tests can shrink it to ~0" (`:938`). Acceptable, but it is configuration by
  monkeypatch.

## Questions to consider

- If the research tool returned a *brief*, would `agent_runtime` need to know what
  `"iter"`, `"heavy"` or `web.citations` mean at all?
- The frontend applies host actions from the `tool_use` **event**, while the runtime
  builds a `host_action` directive into the tool **result** that only the model sees
  (`:1190-1225`). Two dispatch stories for one action — which one is the contract?
- `_MAX_TOOL_ROUNDS` bounds *rounds*. Is the thing that actually needs bounding the
  round count, or the turn's wall-clock and spend?
