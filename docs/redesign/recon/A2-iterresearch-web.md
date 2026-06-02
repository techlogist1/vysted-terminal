# Recon — A2:iterresearch-web

I have a complete, file:line-precise picture. The frontend renders step kinds by string lookup with a generic fallback (line 51 `STEP_META[kind] ?? ...`), so new step kinds are additive and non-breaking. `STEP_KINDS` in `models.py` is a soft tuple, not enforced. Now I'll write the blueprint.

---

# IterResearch / Heavy-Mode Blueprint — Vysted DEEP research

## 1. Findings (what exists today, file:line precise)

**The loop:** `sidecar/services/research/deep.py::run_deep_research` (L363–563). Shape: resolve_symbol → `while True:` [budget gate L415 → plan L424 → parallel `_run_researcher` fan-out L464 → compress (cosmetic step only, L494) → reflect L506 → coverage-floor break L538] → final synthesize L546.

**The bug vs IterResearch:** the loop is _naive append-everything_. `_Findings.findings` (L156, `list[str]`) is only ever `append`-ed (L479) and never pruned. Every round, the **entire** findings list is re-injected into the plan prompt (L439–442), reflect prompt (L520–521) and final synthesis (L345). Over many rounds this is exactly the "context bloat / cognitive suffocation" IterResearch is built to avoid. There is **no central evolving report**, **no per-round workspace reconstruction**, **no distill step** (compress L494 is a no-op label, emits a step but transforms nothing), and **no Heavy/parallel-angle mode** (the fan-out at L464 splits _sub-questions of one angle_, not independent agents with their own workspaces).

**Web research — IterResearch's actual algorithm** (sources below): each round the agent keeps ONLY (a) the original task, (b) the single continuously-rewritten **central report** (a markdown working draft of conclusions-so-far), and (c) the **most recent round's tool outputs** — and DROPS all older raw observations. The model: `think → act(one tool) → distill new evidence INTO the report (rewriting it, not appending) → reconstruct next round's context from {task + report + latest evidence}`. Termination = model emits `<answer>` or hits `MAX_LLM_CALL_PER_RUN=100` / 150-min / 110K-token ceilings (ReAct constants in `inference/react_agent.py`). **Heavy mode** = N independent Research Agents (paper-grade runs use a small N, ~3) each run the _full_ IterResearch loop on a different angle with its OWN report; a final **Synthesis Agent** integrates the N distilled reports into one citation-backed brief ("expert panel" — `IterResearch + Research-Synthesis`).

**Contract surface (non-breaking levers):**

- `STEP_KINDS` (`models.py` L28) is a _soft_ tuple, not validated. New kinds (`distill`, `angle`) are additive.
- Frontend `ResearchActivity.tsx` L51: `STEP_META[kind] ?? {icon: Wrench, label: kind}` — **unknown step kinds render gracefully**, no frontend change required (optional polish: add `distill`/`angle` to `STEP_META` L40–48).
- `ResearchBrief` (`models.py` L83) — adding optional fields with `to_dict()` is non-breaking; `types/data.ts` mirror only needed if frontend reads the new field.
- Handler `deep_research.py` clamps `rounds∈[1,5]`, `wall∈[30,300]` (L248–249); `backend` enum `native|perplexity|tongyi` (catalog L300).
- **Tier-1 / §6.5: untouched.** Research is read-only, no order path. No locked file is in scope.

## 2. Exact change plan

**A. `sidecar/services/research/deep.py` — convert the loop to IterResearch (core change).**

- Add a `_Report` dataclass (central evolving report): `{ task: str, sections: list[str] (distilled conclusions, citation markers preserved), open_questions: list[str], coverage: dict[str,bool], sources: list[ResearchSource] }`. Sources/coverage migrate off `_Findings`; **keep `_Findings` as the source/coverage accumulator** (it already de-dupes by url, L169) so citations survive across rounds.
- Replace per-round context build (L439, L520): the plan + reflect prompts receive ONLY `report.render()` (the rewritten markdown report, bounded length) + the **latest round's** researcher findings — never the full historical `findings` list.
- Insert a real **distill** step between researchers (L491) and reflect: one `_safe_llm` call that takes `{current report + this round's raw findings}` and returns the _rewritten_ report markdown (replace, not append). Emit `ResearchStep("distill", ...)`. This is the "compress" L494 made real — rename or keep `compress` kind for back-compat, add `distill`.
- Final synthesis (L319 `_final_synthesis`) reads `report.render()` + numbered sources instead of `findings.findings` (L345) — citations already numbered via `all_sources()`.
- Keep all three invariants verbatim: top-of-round breach→abort (L415), `budget.record` (L421), coverage floor (L537). The report just changes _what context the LLM sees_, not the budget/abort contract.

**B. `sidecar/services/research/deep.py` — add `run_heavy_research` (Heavy mode).**

- New coroutine `run_heavy_research(query, *, angles: int = 3, tool_call, llm_call, budget, on_step, max_researchers)`. Step 1: one `_safe_llm` "angle-planner" call → split into N distinct angles via existing `_split_subquestions(…, limit=angles)` (L91). Step 2: `asyncio.gather` N `run_deep_research` calls, **each with its own `_Findings`/`_Report` and a per-angle budget slice** (`BudgetGuard(max_steps=budget//angles)`), emitting `ResearchStep("angle", f"angle {i}: …")`. Step 3: a **Synthesis Agent** — one `_safe_llm` call given the N briefs' `markdown` + a **merged, re-de-duped** source list (reuse `_Findings.all_sources` de-dup by url across all N), instructed to integrate, dedupe overlapping claims, and renumber `[n]` against the merged source list. Returns one `ResearchBrief(mode="deep", note="heavy:Nangles")`. **Abort-safe:** if any angle raises, `return_exceptions=True` → drop it, synthesize from survivors (never raise).

**C. `sidecar/services/agent_tools/deep_research.py` — expose Heavy.**

- Add `heavy: bool` (or `angles: int`, clamp `[1,3]`, default 1) to `_deep_research` args (L240). When `>1` and `backend in {native,tongyi}`, route to `run_heavy_research`; budget `max_steps = angles * rounds * (_MAX_RESEARCHERS+2)`. Emit `_emit_backend_step` naming "Heavy mode — N parallel research angles".

**D. `sidecar/services/agent_tools/catalog.py` (L293–310)** — add `"heavy"`/`"angles"` to `deep_research` input_schema. **This is the one source of truth** (Principle II) — `TOOL_SCHEMAS`/allow-list/MCP derive automatically; do NOT hand-edit `schemas.py`. Update the description string.

**E. `sidecar/services/research/models.py` (L28)** — append `"distill"`, `"angle"` to `STEP_KINDS` (soft tuple; documentation only).

**F. Frontend polish (optional, non-blocking) — `src/modules/chat/ResearchActivity.tsx` L40–48** — add `distill: {icon: Layers, label: "Distilling"}`, `angle: {icon: Compass, label: "Exploring angle"}` to `STEP_META`. Without it, the `?? fallback` (L51) already renders them.

## 3. Risks + safe fallback

- **Distill LLM rewrites away a citation marker** → `_Findings.all_sources()` is the source of truth for `[n]`, not the report text; if distill drops a `[n]`, the source still ships in `brief.sources`. Fallback: if distill returns empty (`_safe_llm`→`""`), **keep last round's report unchanged** (never blank the report).
- **Heavy mode budget starvation** (N angles split one budget → each too thin). Fallback: floor each angle's `max_steps` at `rounds*(_MAX_RESEARCHERS+2)` minimum if total budget allows; if not, degrade to `angles=1` (plain deep) and stamp `note`.
- **Weak fallback model can't follow "rewrite the report"** → the power is the _loop_, but a dumb model may echo. Fallback: distill prompt is strictly bounded ("output ONLY the updated report markdown, ≤N words"); if output exceeds a char ceiling, truncate; the coverage floor + budget still bound the run. Loop still terminates regardless of distill quality.
- **One angle crashes** → `gather(return_exceptions=True)`, synthesize from survivors; if ALL crash, fall back to a single `run_deep_research` (never raise — honors SC-008 abort→synthesize).
- **Context still bloats if report grows unbounded** → enforce a hard char cap on `report.render()` (drop oldest sections, keep newest distilled conclusions) — this IS the IterResearch invariant; make it a constant, not optional.

## 4. Verification (exact steps)

- **Existing parity (must stay green):** `cd sidecar && .venv/bin/python -m pytest tests/test_research_deep.py tests/test_research_tools.py tests/test_tongyi_backend.py -q` — the 3 invariants (abort→synthesize, coverage floor, never-raise) are asserted at `test_research_deep.py` L139/L171/L196/L246; the new loop must preserve them.
- **Catalog/MCP parity (Principle II):** `.venv/bin/python -m pytest tests/test_capability_catalog.py tests/test_mcp_catalog_parity.py -q` — proves the `heavy`/`angles` schema change projected correctly without hand-editing `schemas.py`.
- **New IterResearch behavior — add to `test_research_deep.py`:** (a) `test_deep_report_context_is_bounded` — run ≥3 rounds with a counting `_FakeLLM`, assert the plan/reflect prompt the fake receives never contains round-1 raw findings (i.e., context is reconstructed, not appended); assert `report.render()` length stays under the cap. (b) `test_distill_empty_keeps_prior_report` — distill returns `""`, report unchanged, brief still ships.
- **New Heavy mode — new `test_research_heavy.py`:** `test_heavy_spawns_n_angles_and_synthesizes` (3 angles → 3 sub-runs, one synthesized brief, sources merged + de-duped by url, `[n]` markers resolve); `test_heavy_one_angle_crash_still_synthesizes` (`return_exceptions`); `test_heavy_never_raises_on_dead_llm`.
- **Full gate before any tag:** `pnpm ci-local` (mirrors CI byte-for-byte) + `cd sidecar && ruff format --check . && ruff check .`.
- **Live rig (manual, real model):** with an OpenRouter key set, run `/deep <ticker thesis>` then a Heavy variant; in `ResearchActivity` confirm the step trace shows `distill` and `angle` lines and the final brief carries `[n]` citations that resolve to merged sources. `curl -s 127.0.0.1:$PORT/health` to confirm sidecar up; do NOT pipe long pytest through `head` (deadlocks).

## Sources

- https://tongyi-agent.github.io/blog/introducing-tongyi-deep-research/ (IterResearch workspace reconstruction + central report; Heavy = IterResearch + Research-Synthesis, parallel Research Agents + one Synthesis Agent, "expert panel")
- https://github.com/Alibaba-NLP/DeepResearch (README: ReAct vs IterResearch "Heavy" test-time-scaling; `inference/react_agent.py`, `prompt.py`, tool\_\*.py)
- `inference/react_agent.py` constants: `MAX_LLM_CALL_PER_RUN=100`, 150-min wall, `max_tokens=110*1024`, `<answer>`/`<tool_call>` termination, message-append context.
- https://towardsai.net/p/machine-learning/explaining-tongyi-deepresearch and https://www.marktechpost.com/2025/09/18/... (central report + noise-prevention/quality-check per round; 30B-A3B MoE, 128K ctx) — corroborating detail; exact angle-count N is not published, ~3 is the implementable default.
