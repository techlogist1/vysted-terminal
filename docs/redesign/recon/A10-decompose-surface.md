# Recon — A10:decompose-surface

I now have a complete, file:line-precise understanding. Producing the blueprint.

# Plan-Then-Execute Surface — Implementation Blueprint (Track 6 #2)

## (1) Findings — what exists today

**Planner (`sidecar/services/planner.py`)** — `decompose(goal, *, llm_call, context)` (L332-366) is a tested utility, NOT wired anywhere. Returns a `Plan` (L247-266) with `.goal`, `.steps: list[PlanStep]`, `.note`, `.ok`. Each `PlanStep` (L233-244) is `action ∈ PLAN_ACTIONS` (L216-225) + `args: dict` + `rationale`. `PLAN_ACTIONS` = `open_panel, set_chart_symbol, set_chart_indicators, add_to_watchlist, arrange_layout, research, deep_research, answer`. `classify_intent` (L159) already returns `.compound` (L184: chain-cue OR ≥2 panel nouns). `llm_call` is `Callable[[str], Awaitable[str]]`.

**Runtime (`sidecar/services/agent_runtime.py`)** — `invoke_agent` (L460) yields `LLMStreamEvent`s. Intent is already classified at L511-513 for the read-only gate (`mode=="agent"` only). Request creds are published at L548 via `config.set_request_llm_creds(provider_id, resolved_model, api_key)` — readable via `config.get_llm_creds()` (config.py L158). `oneshot.complete(provider, model, api_key, messages)` (`services/llm/oneshot.py` L45) is the one-shot seam used by deep_research (deep_research.py L158-159, L197-198). The tool loop starts at L552. `LLMResearchStepEvent` is built by `_step_event` (L331) — it is the existing live-step event.

**SSE wire** — events are Pydantic discriminated unions in `sidecar/models/llm.py`; `LLMResearchStepEvent` (L~+research_step, kind=`"research_step"`) carries `tool_call_id, tool, step_kind, detail, latency_ms, status, index`. Router (`routers/agents.py` L86-91) serializes any event via `event.model_dump()` → `data: {json}\n\n`. Frontend `streaming.ts` `normalizeEvent` (L172-220) maps snake→camel **per known kind** and **returns `null` for unknown kinds** (L220) — so a NEW kind is silently dropped unless added here.

**Frontend** — `chat-history.ts`: `ResearchStepView` (L25-36) + `appendResearchStep` (L135-146) attach steps to the streaming message. `ResearchActivity.tsx` renders them. `ChatSidebar.tsx`: handler dispatch in `makeHandlers` (L1168-1198); per-event sinks wired at L545-588. Host-action tool_use → `enqueueChange(...)` at L569-576 with `batchId: assistantId` (one turn = one batch). `useProposedChangesStore.enqueue` (proposed-changes.ts L56-83): AUTO auto-applies non-order kinds (L79); `order` kind NEVER auto-applies and routes through §6.5 on accept (L100-108). `host-actions.ts` `HOST_ACTION_NAMES` (L35-45) = exactly the plan vocabulary minus `research/deep_research/answer`; `describeHostAction` maps each to a `kind` (`chart/panel/watchlist/order`).

**Capability signal** — `native_search.SUPPORTS_NATIVE_SEARCH` (L49) and frontend `model-catalog.ts` `supportsTools` (per-model `boolean|null`) are the tool-capability signals. `hardware_fit.can_run_locally` (L380) gates LOCAL models. **qwen-7b via ollama is the unreliable local path** — gate on it explicitly.

## (2) Exact change plan

**A. `sidecar/models/llm.py`** — add `LLMAgentPlanEvent` next to `LLMResearchStepEvent`:

```python
class LLMAgentPlanEvent(BaseModel):
    kind: Literal["agent_plan"] = "agent_plan"
    goal: str
    steps: list[dict[str, Any]] = Field(default_factory=list)  # {action,args,rationale,staged:bool}
    note: str | None = None
```

Mirror in `types/ai.ts` (LLMStreamEvent union) — **same commit** (CLAUDE.md hand-mirror rule). Export from `__all__`.

**B. `sidecar/services/agent_runtime.py`** — add a plan PRE-PASS before the tool loop (after L548, before L550 `rounds = 0`). New gate helper + emit:

```python
def _planner_enabled(provider_id, model, mode) -> bool:
    if mode != "agent":
        return False
    if provider_id == "ollama":   # local qwen-7b unreliable → today's preamble path
        return False
    return provider_id in native_search.SUPPORTS_NATIVE_SEARCH or provider_id in ("openrouter", "deepseek")
```

Then, gated on `_planner_enabled(...) and classify_intent(prompt).compound`:

```python
async def _llm_call(p: str) -> str:
    return await oneshot.complete(provider_id, resolved_model, api_key, [{"role":"user","content":p}])
plan = await decompose(prompt, llm_call=_llm_call, context=(terminal or {}))
if plan.ok and len(plan.steps) > 1:
    staged = [{**s.to_dict(), "staged": s["action"] in _STAGEABLE} for s in plan.steps]
    yield LLMAgentPlanEvent(goal=plan.goal, steps=staged, note=plan.note)
```

Where `_STAGEABLE = {"open_panel","set_chart_symbol","set_chart_indicators","add_to_watchlist","arrange_layout"}` — **`research/deep_research/answer` are NOT staged** (they execute inside the loop), and **there is no order action in `PLAN_ACTIONS`** so §6.5 is structurally untouched. The plan is ADVISORY: it does NOT replace the loop. The model still drives tool_use; the plan is a visible scaffold + pre-staged host-actions the user can accept. Import `oneshot`, `decompose`, `LLMAgentPlanEvent` at top.

**C. `sidecar/services/llm/native_search.py`** — no edit; reuse `SUPPORTS_NATIVE_SEARCH` as the capability set (already imported in runtime L49).

**D. `src/modules/chat/streaming.ts`** — in `normalizeEvent` (before L220 `return null`):

```ts
if (kind === "agent_plan") {
  return {
    kind: "agent_plan",
    goal: String(payload.goal ?? ""),
    steps: Array.isArray(payload.steps) ? (payload.steps as PlanStepView[]) : [],
    note: typeof payload.note === "string" ? payload.note : undefined,
  };
}
```

**E. `src/store/chat-history.ts`** — add `PlanStepView` interface + `plan?: AgentPlanView` field on `ChatMessage` (L57 area) + `setPlan: (id, plan) => void` reducer (mirror `appendResearchStep` shape, L135). One plan per message.

**F. New `src/modules/chat/PlanView.tsx`** — render `message.plan` as `Plan: 1) {rationale|action} 2) …`, each staged step showing a small "queued for review" pill; mirror `ResearchActivity` styling (mono, `border-amber-500/40`). Pure presentational; reads from `message.plan`.

**G. `src/modules/chat/ChatSidebar.tsx`** —

- `makeHandlers` (L1186 area): add `else if (event.kind === "agent_plan") internal.onPlan(event)`.
- `InternalHandlers` (L1156): add `onPlan: (plan: AgentPlanView) => void`.
- In the handler block (after L587): `onPlan: (plan) => { setPlan(assistantId, plan); for (const s of plan.steps) if (s.staged && isHostActionMutation(s.action)) enqueueChange({ toolCallId: `plan-${assistantId}-${i}`, name: s.action, input: s.args, batchId: assistantId, agentId: agentForCall ?? undefined, agentName }); }`. This stages plan steps into the **same batch** as the turn — the existing `ProposedChangesReview` bulk accept/reject covers them. Render `<PlanView>` next to `ResearchActivity` at L738.

Plan-staged changes ride the EXACT existing gate: AUTO auto-applies UI/chart/watchlist (proposed-changes.ts L79), nothing else lands without accept. Orders impossible (not in vocabulary).

## (3) Risks + safe fallback

| Risk                                                     | Fallback                                                                                                                                                                                                    |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| qwen-7b/local emits garbage plan                         | `_planner_enabled` returns False for `ollama` → today's preamble-driven loop, no plan event.                                                                                                                |
| `decompose` LLM call fails/times out                     | `decompose` already degrades to a single fallback step (planner.py L358-366); guard `len(steps) > 1` so a 1-step "plan" never renders. Wrap the `oneshot.complete` in the existing try (decompose owns it). |
| Plan disagrees with what the model actually does in-loop | Plan is ADVISORY, not authoritative — the loop still runs; staged steps are user-rejectable. No coupling between plan steps and loop tool_use.                                                              |
| Extra one-shot LLM cost per compound turn                | Gate is `compound` only (rare); `decompose` is one cheap completion. Document as Tier-3.                                                                                                                    |
| Unknown SSE kind dropped silently                        | Adding the `agent_plan` branch to `normalizeEvent` is mandatory; if omitted, plan just doesn't render (graceful, no crash).                                                                                 |
| §6.5 regression                                          | `PLAN_ACTIONS` has no order verb; `_STAGEABLE` excludes everything non-host-action; `enqueueChange` order-kind path is untouched. Tier-1 files unedited.                                                    |

## (4) Verification

- **pytest** — `sidecar/tests/test_planner.py` already covers `decompose`. Add `test_agent_runtime.py` cases: compound prompt + `provider="openai"` + `mode="agent"` yields one `agent_plan` event (kind check) with `>1` steps, none with `action=="propose_order"`; `provider="ollama"` yields NO `agent_plan`; non-compound prompt yields none. Run: `cd sidecar && python -m pytest tests/test_planner.py tests/test_agent_runtime.py -q` (background per CLAUDE.md long-command rule).
- **vitest** — `streaming.ts`: assert `normalizeEvent({kind:"agent_plan",goal:"x",steps:[...]})` returns the camel shape. `ChatSidebar.test.tsx`: on an `agent_plan` event, `useProposedChangesStore.pending()` gains the staged host-actions in `batchId===assistantId`, and `message.plan` is set. Run `pnpm vitest run src/modules/chat`.
- **curl** — `curl -N -X POST http://127.0.0.1:<port>/agents/<id>/invoke -H 'Content-Type: application/json' -d '{"prompt":"open a chart of AAPL and research the bull case","mode":"agent","provider":"openai","model":"gpt-4.1-mini","api_key":"…"}'` → confirm a `data: {"kind":"agent_plan",…}` frame precedes the tool_use frames. (Direct-curl per CORS-masks-500 gotcha.)
- **rig** — tauri-mcp: send a compound prompt in agent mode with a cloud provider default; `screenshot` must show the `Plan: 1) … 2) …` surface in the transcript AND the staged items in `ProposedChangesReview` (populated state, not empty). Confirm an `ollama` default shows NO plan surface.

**In short:**

- Add one additive `agent_plan` SSE event; wire `decompose` as a compound-only pre-pass in `invoke_agent` after L548, gated by a new `_planner_enabled` (excludes `ollama`/qwen-7b, requires a tool-capable cloud provider).
- Stageable steps (the 5 host-actions, never orders) ride the EXISTING `enqueueChange` into the turn's batch — zero new safety surface, Tier-1 files untouched.
- Frontend: `normalizeEvent` branch + `chat-history.plan` field + new `PlanView.tsx` + `onPlan` handler; render beside `ResearchActivity`.
- Confidence: 8/10 — uncertain only whether you want the plan to merely PRE-STAGE host-actions (my design) vs. also gate/replace the in-loop tool calls; I kept it advisory to avoid coupling the plan to the live loop and any §6.5 risk.
