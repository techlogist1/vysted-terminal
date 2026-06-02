# Recon — A3:research-codemap

`STEP_KINDS` is informational — `ResearchStep` does NOT validate `kind` against it (the `engine` kind already ships without being in the tuple). That means an explorer-tagged kind/detail is additive with no schema gate. I have everything. Writing the blueprint.

---

# Blueprint: Graft an IterResearch loop onto the deep-research engine

## (1) Findings — what exists today (file:line precise)

**ResearchStep schema** (`sidecar/services/research/models.py:58-80`): `@dataclass(slots=True)` with positional `kind: str`, `detail: str`, then kw `latency_ms: int|None=None`, `status: str="ok"`. `to_dict()` → `{kind, detail, latency_ms, status}`. **`STEP_KINDS` (line 28) is informational only** — nothing validates `kind` against it; `deep_research.py:69` already emits `kind="engine"` (not in the tuple) and it renders fine. **So an `explorer`/`synthesis` kind or an explorer-tagged `detail` is purely additive — no schema change, no Tier-1 touch.** `ResearchBrief` (line 83-123) carries `query, symbol, mode, markdown, sources, structured, steps, source_count, cost, web_available, note`; `mode` validated nowhere against `RESEARCH_MODES` — `mode="deep"` is a free string.

**`on_step` signature** (`deep.py:47`): `OnStep = Callable[[ResearchStep], Any]`, may be sync or coroutine; `_emit` (line 59-69) awaits if coroutine, **swallows all exceptions** (a broken sink never aborts a run). `on_step` defaults `None`.

**Step flow tool→queue→SSE→UI** (Track A): tool reads the sink via `config.get_step_sink()` (research.py:46, deep_research.py:171) — a `ContextVar` (`config.py:185-202`). The runtime wraps each tool dispatch: `_dispatch_tool_with_progress` (`agent_runtime.py:359-398`) creates an `asyncio.Queue`, sets the sink to `queue.put_nowait` via `config.set_step_sink`, runs the tool as a task, drains the queue yielding `LLMResearchStepEvent` per step + a terminal `_ToolDone(result)`. The invoke loop (line 630-634) yields step events to the SSE consumer. `LLMResearchStepEvent` (`models/llm.py:136-163`): `{kind:"research_step", tool_call_id, tool, step_kind, detail, latency_ms, status, index}`. Frontend: `streaming.ts:188-199` normalizes to camelCase; `ChatSidebar.tsx:580/588` routes `deep_research`/`research` tool-use to `appendResearchStep`→`ResearchActivity.tsx` (per-`step_kind` icon map, line 40-48, falls back to generic for unknown kinds). **The brief itself does NOT auto-render** — the agent calls a separate `publish_brief` host-action (`host-actions.ts:436-446`→`useBriefStore.setBrief`→`BriefPanel.tsx`). The `deep_research` tool result is just JSON the model reads.

**BudgetGuard metering** (`budget_guard.py`): constructed in `deep_research.py:161-164/202-205` as `max_steps=rounds*(_MAX_RESEARCHERS+2)`, `max_wall_seconds=wall`. Inside the loop (`deep.py:415-421`): `budget.breach()` at top-of-round → first non-None reason → `abort_synthesize`; then exactly **one `budget.record(None, _ROUND_MODEL, _ROUND_PROVIDER)` per round**. `record` (budget_guard.py:116) ticks `_steps` always, folds tokens only if usage given (deep passes `None` — step ceiling is the live bound). `breach` order: tokens→spend→wall→steps. The function **never raises on breach** (invariant).

**LLM call inside deep.py**: injected `llm_call: Callable[[messages], Awaitable[str]]` (line 45). Bound in `deep_research.py:158/197` to `oneshot.complete(provider, model, key, messages)` — a non-streaming join of one completion (`oneshot.py:48`), tolerant of `""`. Tools injected as `agent_tools.invoke_tool` (deep_research.py:168/211). Researchers (`deep.py:230-288`) gather web + one structured leg + an extraction LLM call; the loop is plan→researchers→compress→reflect→(reenter)→synthesize, all single-pass single-context.

**Backend dispatch seam** (`deep_research.py:225-256`): `_deep_research` reads `backend` arg (`native`/`perplexity`/`tongyi`) → routes to `_run_native`/`_run_perplexity`/`_run_tongyi`. **This is the clean additive seam.**

## (2) Exact change plan (additive; old loop is the fallback)

**A. New file `sidecar/services/research/iter.py`** — `run_iter_research(query, *, region, tool_call, llm_call, budget, on_step, num_explorers=3, max_rounds=2)`. Reuse `deep.py`'s helpers (import `_Findings`, `_run_researcher`, `_record_web`, `_record_structured`, `_split_subquestions`, `_final_synthesis`, `_synthesize_brief`, `_emit`, `_safe_llm` — or move shared helpers to a `_common.py` and have both import; cheaper to just import the private names from `deep`). Loop shape per round:

1. **Top-of-round `budget.breach()` → abort→synthesize** (copy deep.py:415-417 verbatim; same invariant).
2. `budget.record(None, _ROUND_MODEL, _ROUND_PROVIDER)`.
3. **Reconstruct workspace** = build a fresh `messages` planning context each round from `findings.findings` + `findings.coverage` (deep already does this — the plan prompt at deep.py:425 is stateless per round, so "reconstruct" is satisfied by _not_ threading a growing transcript; emit a `ResearchStep("plan", f"round {r}: reconstructed workspace, {len(findings.findings)} findings")`).
4. **N parallel explorers**: `asyncio.gather(*(_run_researcher(q, ...) for q in subqs[:num_explorers]))`. After each, emit `ResearchStep("tool", f"explorer {i}: {q}")` — **tag the explorer in `detail`** (`f"[E{i}] {q}"`), no schema change. Fold results via existing `_record_web`/`_record_structured`.
5. `compress` + `reflect` steps (reuse).
6. Coverage floor + reflect-complete → break (reuse `_coverage_met`/`_reflect_says_complete`).
7. **Synthesis pass**: after loop or on abort, call `_final_synthesis` then emit `ResearchStep("synthesize", "iter synthesis")`. Return `_synthesize_brief(..., mode handled by overriding the dataclass `mode`field to`"deep"` so frontend stays on the DEEP badge — or pass through and the FE renders DEEP).

**B. `sidecar/services/research/deep.py`** — _no edit required_ if iter.py imports its helpers. If you'd rather not import privates, add `__all__` entries for the shared helpers (one-line, additive). Prefer the import route — zero diff to the running loop.

**C. `sidecar/services/agent_tools/deep_research.py`** — add a `mode` arg branch:

- In `_deep_research` (line 240-256): read `mode = str(args.get("mode") or "single").lower()`; when `backend=="native"` and `mode in ("iter","heavy")`, route to a new `_run_iter(query, rounds, wall)` instead of `_run_native`. `_run_iter` mirrors `_run_native` (creds, `_emit_backend_step("Iter deep-research — N explorers/round")`, same `BudgetGuard(max_steps=rounds*(num_explorers+2), max_wall_seconds=wall)`), but calls `iter.run_iter_research(...)`. Old `_run_native` stays as the default → **fallback preserved**.
- Set `out["backend"]="native"`, `out["mode"]="iter"`.

**D. `sidecar/services/agent_tools/catalog.py`** (deep_research input_schema ~line 297) — add an optional `mode` enum `["single","iter"]` default `"single"` to the schema, with a one-line description. **This is a derived-from-catalog edit** (the §"capability catalog is the ONE source of truth" rule): `TOOL_SCHEMAS`/allow-list/MCP project automatically. No hand-edit of `schemas.py`. Run the parity tests (below).

**E. Frontend** — `src/modules/chat/ResearchActivity.tsx:40-48`: optionally add an `explorer` entry to `STEP_META` (else it falls back to the generic Wrench look — acceptable, additive). No store/contract change; explorer-tagged `detail` already renders. `slash-commands.ts:168`: add a `/deepiter` (or extend `/deep` to pass mode) → `template: (args) => `/deep iter — go deeper on ${args}``so the model picks`mode:"iter"`. **No edit to brief.ts / BriefPanel / streaming.ts** — the `research_step`path and`publish_brief` path are mode-agnostic.

## (3) Risks + safe fallback

| Risk                                                                                | Fallback                                                                                                                                                                                                                        |
| ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Iter loop burns budget faster (N explorers × rounds).                               | Same `BudgetGuard` ceiling + top-of-round `breach()`→abort→synthesize is _copied verbatim_; the step formula `rounds*(num_explorers+2)` already accounts for fan-out. A breach ships a short brief, never an error.             |
| `_run_researcher` import coupling to deep.py internals breaks if deep.py refactors. | Move shared helpers to `research/_common.py` (pure move, both import) — or pin to importing `deep._run_researcher` and add a `test_research_iter.py` that asserts the symbol exists.                                            |
| `mode="iter"` reaches MCP surface unvalidated.                                      | The enum in catalog gates it; `_deep_research` defaults any unknown `mode` to `single` (`mode not in {"iter","heavy"}` → native).                                                                                               |
| Step-stream floods UI (N explorers emit concurrently → out-of-order `index`).       | `index` is assigned by the runtime drain loop (`_dispatch_tool_with_progress` line 393), monotonic per dispatch — explorer concurrency inside the tool is serialized through the single `queue`, so ordering stays well-formed. |
| Brief `mode` mismatch (FE only knows FAST/DEEP).                                    | Keep `ResearchBrief.mode="deep"` for iter (it IS a deep run); surface "iter" only in `out["mode"]`/engine line, never in the brief dataclass.                                                                                   |

## (4) Verification

- **pytest (new + parity):**
  `python -m pytest sidecar/tests/test_research_iter.py sidecar/tests/test_research_deep.py sidecar/tests/test_budget_guard.py sidecar/tests/test_research_tools.py -q` — assert: (a) iter returns a `ResearchBrief` with `mode=="deep"`; (b) a breach on round 1 still returns a brief with `note` set (no raise); (c) `on_step` receives ≥1 `explorer`-tagged step per round; (d) `budget.record` called exactly once/round.
  `python -m pytest sidecar/tests/test_capability_catalog.py sidecar/tests/test_mcp_catalog_parity.py -q` — registry⟺catalog⟺MCP parity after the `mode` schema add.
- **vitest:** `pnpm vitest run src/store/brief.test.ts src/modules/chat/chat-history.test.ts` (if STEP_META edited).
- **curl (live sidecar, port from launch):** `curl -N -X POST 127.0.0.1:$PORT/agents/copilot/stream -H 'content-type: application/json' -d '{"prompt":"/deep iter NVDA datacenter demand","mode":"agent"}'` — watch the SSE for `research_step` frames with `step_kind:"plan"` then multiple `tool` frames whose `detail` carries `[E0]/[E1]/[E2]`, then `synthesize`, then a `publish_brief` tool_use. (CORS-masks-500: curl direct, not via webview.)
- **rig:** `tauri-mcp` start session → send `/deep iter <ticker>` in the agent dock → screenshot the `ResearchActivity` surface mid-run (must show explorer steps animating) + the populated `BriefPanel` after. Capture dark theme, populated state only.

**In short:**

- The cleanest seam is `_deep_research`'s `backend`/`mode` dispatch (`deep_research.py:240-256`) → new `_run_iter` → new `services/research/iter.py` reusing deep.py's helpers + BudgetGuard pattern verbatim. Old `_run_native` is the untouched fallback.
- `ResearchStep` does not validate `kind`, so explorer/synthesis tagging is additive — **zero Tier-1 touch, zero contract change** (step-stream + budget invariants preserved by copying them).
- Only real edits: new `iter.py`, a `mode` branch in `deep_research.py`, a one-line enum in `catalog.py` (run the two parity tests), optional FE `STEP_META`/slash-command polish.
- Confidence: 8/10 — uncertain only whether the lead prefers importing deep.py privates vs extracting a `_common.py` (both safe; the move is cleaner long-term).
