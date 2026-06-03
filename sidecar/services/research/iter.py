"""ITER / HEAVY deep research — IterResearch-style workspace reconstruction.

Two upgraded entry points layered on the proven single-pass loop in
:mod:`services.research.deep` (which stays UNTOUCHED as the guaranteed fallback):

``run_iter_research`` — the IterResearch loop (adapted from Alibaba's
Tongyi-DeepResearch). The single-pass loop re-injects the ENTIRE findings history
into every plan/reflect/synthesis prompt; over many rounds that bloats the working
context and degrades reasoning ("cognitive suffocation"). Instead this loop keeps
ONE central evolving REPORT and, each round, reconstructs a minimal working context
from ``{task + distilled report + this round's fresh evidence}`` — older raw
observations are distilled into the report and dropped from the prompt. The power
is in the LOOP, not the model: it is bounded + correct on a weak fallback model and
sharper on a strong one.

``run_heavy_research`` — "Heavy mode" / the expert panel. N independent explorers
each run the full iter loop on a DISTINCT angle with their OWN evolving report
(concurrently), then a synthesis agent integrates their distilled reports into one
citation-backed brief, de-duping sources and renumbering ``[n]`` markers. This is
test-time scaling: more parallel reasoning, one merged answer.

Both reuse :mod:`deep`'s tested helpers verbatim (researchers, source de-dup,
``_Findings``) and hold the SAME three invariants — top-of-round breach →
abort→synthesize (never a bare timeout), one ``budget.record`` per round, the
coverage floor — so a budget breach always ships a brief and never raises. Every
step is emitted live (``on_step``) so the activity surface animates the work,
including the parallel angle exploration in Heavy mode.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from services.budget_guard import BudgetGuard
from services.research.deep import (
    _ROUND_MODEL,
    _ROUND_PROVIDER,
    LLMCall,
    OnStep,
    ToolCall,
    _coverage_met,
    _emit,
    _Findings,
    _record_structured,
    _record_web,
    _reflect_says_complete,
    _run_researcher,
    _safe_llm,
    _safe_tool,
    _split_subquestions,
    _synthesize_brief,
)
from services.research.fast import snapshot_structured
from services.research.models import ResearchBrief, ResearchSource, ResearchStep

#: Hard cap on the rendered working report so the reconstructed context stays
#: bounded no matter how chatty the distill model is — the IterResearch invariant
#: that prevents context bloat. The newest distilled content is kept on overflow.
_REPORT_CHAR_CAP = 6000

#: Heavy mode angle bounds. The paper-grade panel uses a small N (~3 independent
#: Research Agents + one Synthesis Agent); 2 is the floor for "heavy" to mean a
#: panel at all, 3 the ceiling so the budget fan-out stays sane.
_MIN_ANGLES = 2
_MAX_ANGLES = 3


@dataclass(slots=True)
class _Report:
    """The single central evolving report — the only cross-round memory.

    ``body`` is rewritten (not appended) each round by the distill step. Sources +
    coverage live in :class:`~services.research.deep._Findings` (so ``[n]`` markers
    survive even if the distill model drops one); the report is the distilled
    PROSE the next round reasons from.
    """

    task: str
    body: str = ""
    round: int = 0

    def render(self) -> str:
        """The bounded working report for the next round's context."""
        text = self.body.strip()
        if len(text) > _REPORT_CHAR_CAP:
            # Keep the newest distilled content (the tail) on overflow.
            text = "…\n" + text[-_REPORT_CHAR_CAP:]
        return text or "(no findings distilled yet)"


def _default_questions(symbol: str, limit: int) -> list[str]:
    """A sane fan-out when the planner LLM returns nothing usable."""
    return [
        f"What is the recent price action and trend for {symbol}?",
        f"What do the latest fundamentals say about {symbol}?",
        f"What recent news or catalysts affect {symbol}?",
    ][:limit]


def _numbered_sources(findings: _Findings) -> str:
    """The ``[n]`` source list handed to the distill/synthesis prompts."""
    return "\n".join(f"[{i + 1}] {s.title} — {s.url}" for i, s in enumerate(findings.all_sources()))


async def _distill(
    llm_call: LLMCall,
    *,
    query: str,
    symbol: str,
    report: _Report,
    round_findings: list[str],
    findings: _Findings,
) -> str:
    """Rewrite the central report integrating this round's findings (the core
    IterResearch move). Returns the new report markdown, or ``""`` on a dead LLM
    (the caller then KEEPS the prior report — never blanks it)."""
    return await _safe_llm(
        llm_call,
        [
            {
                "role": "system",
                "content": (
                    "You maintain ONE evolving research report. Given the CURRENT "
                    "report and the NEW findings from this round, output the UPDATED "
                    "report as markdown: integrate the new findings, keep only the "
                    "conclusions that matter to the task, remove redundancy, and "
                    "preserve inline [n] citation markers. Output ONLY the report "
                    "markdown (no preamble, no changelog) — rewrite the whole report. "
                    "Keep it tight, under ~400 words."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Task: {query}\nSymbol: {symbol}\n\n"
                    f"Current report:\n{report.render()}\n\n"
                    "New findings this round:\n"
                    + ("\n".join(f"- {f}" for f in round_findings) or "(none)")
                    + f"\n\nKnown sources (for [n] markers):\n{_numbered_sources(findings)}"
                ),
            },
        ],
    )


async def _synthesis_from_report(
    llm_call: LLMCall, *, query: str, symbol: str, report: _Report, findings: _Findings
) -> str:
    """Write the final brief markdown from the evolving report + numbered sources.
    Falls back to the raw report (then a terse stub) so a dead LLM still ships."""
    body = await _safe_llm(
        llm_call,
        [
            {
                "role": "system",
                "content": (
                    "Write a concise research brief in markdown from the working "
                    "report. Use inline [n] citation markers that reference the "
                    "numbered sources. Do not fabricate sources or facts beyond the "
                    "report."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Query: {query}\nSymbol: {symbol}\n\n"
                    f"Working report:\n{report.render()}\n\n"
                    f"Sources:\n{_numbered_sources(findings)}"
                ),
            },
        ],
    )
    if body.strip():
        return body.strip()
    rendered = report.render()
    if rendered and rendered != "(no findings distilled yet)":
        return f"# Research brief: {query}\n\nSymbol: {symbol}\n\n{rendered}"
    return (
        f"# Research brief: {query}\n\nSymbol: {symbol}\n\n"
        "_No findings were gathered before the run ended._"
    )


async def run_iter_research(
    query: str,
    *,
    region: str | None = None,
    tool_call: ToolCall,
    llm_call: LLMCall,
    budget: BudgetGuard,
    on_step: OnStep | None = None,
    max_researchers: int = 3,
) -> ResearchBrief:
    """Run the IterResearch loop for ``query``; always returns a brief.

    Per round: top-of-round breach → abort→synthesize; record one step; RECONSTRUCT
    the working context from ``{report + last round's evidence}`` (not the full
    history); parallel researchers; DISTILL the round into the central report;
    reflect; break on the coverage floor + a "complete" reflect. Never raises.
    """
    findings = _Findings()
    report = _Report(task=query)
    steps: list[ResearchStep] = []
    structured: dict[str, object] = {}

    resolve_args: dict[str, object] = {"query": query}
    if region:
        resolve_args["region"] = region
    resolved = await _safe_tool(tool_call, "resolve_symbol", resolve_args)
    instrument = (resolved.get("resolved") or {}) if resolved.get("ok") else {}
    symbol = instrument.get("symbol") or query
    structured["resolved"] = resolved
    # Snapshot price + fundamentals so an iter/Heavy brief backs the same native
    # metric cards as a FAST one (additive; a failed leg renders no card).
    if resolved.get("ok"):
        structured.update(await snapshot_structured(tool_call, symbol))

    last_round_findings: list[str] = []

    async def abort_synthesize(reason: str) -> ResearchBrief:
        t0 = time.monotonic()
        markdown = await _synthesis_from_report(
            llm_call, query=query, symbol=symbol, report=report, findings=findings
        )
        step = ResearchStep(
            "synthesize",
            f"abort→synthesize: {reason}",
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
        steps.append(step)
        await _emit(on_step, step)
        return _synthesize_brief(
            query=query,
            symbol=symbol,
            markdown=markdown,
            findings=findings,
            structured=structured,
            steps=steps,
            budget=budget,
            note=reason,
        )

    while True:
        # --- top-of-round budget gate: FIRST breach => abort→synthesize -------
        reason = budget.breach()
        if reason is not None:
            return await abort_synthesize(reason)
        budget.record(None, _ROUND_MODEL, _ROUND_PROVIDER)
        report.round += 1

        # --- RECONSTRUCT WORKSPACE: plan from {report + latest evidence} ------
        t0 = time.monotonic()
        plan_text = await _safe_llm(
            llm_call,
            [
                {
                    "role": "system",
                    "content": (
                        "You are planning the next round of a research run. Based on "
                        "the working report and the latest evidence, list the open "
                        "sub-questions STILL unanswered, one per line. Be specific and "
                        "non-redundant with what the report already covers."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Task: {query}\nSymbol: {symbol}\n\n"
                        f"Working report:\n{report.render()}\n\n"
                        "Latest evidence:\n"
                        + ("\n".join(f"- {f}" for f in last_round_findings) or "(first round)")
                        + f"\n\nCoverage so far: {findings.coverage}"
                    ),
                },
            ],
        )
        open_questions = _split_subquestions(
            plan_text, limit=max_researchers
        ) or _default_questions(symbol, max_researchers)
        plan_step = ResearchStep(
            "plan",
            f"round {report.round}: rebuilt workspace → {len(open_questions)} sub-question(s)",
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
        steps.append(plan_step)
        await _emit(on_step, plan_step)

        # --- parallel researchers --------------------------------------------
        researcher_t0 = time.monotonic()
        results = await asyncio.gather(
            *(
                _run_researcher(
                    q, symbol=symbol, region=region, tool_call=tool_call, llm_call=llm_call
                )
                for q in open_questions[:max_researchers]
            )
        )
        last_round_findings = []
        for q, (finding, web_res, structured_pair) in zip(
            open_questions[:max_researchers], results, strict=False
        ):
            last_round_findings.append(finding)
            _record_web(findings, web_res)
            if structured_pair:
                _record_structured(
                    findings, symbol, structured_pair["dim"], structured_pair["result"]
                )
            rstep = ResearchStep(
                "tool",
                f"researcher: {q}",
                latency_ms=int((time.monotonic() - researcher_t0) * 1000),
            )
            steps.append(rstep)
            await _emit(on_step, rstep)

        # --- DISTILL: rewrite the central report (replace, not append) -------
        distill_t0 = time.monotonic()
        new_body = await _distill(
            llm_call,
            query=query,
            symbol=symbol,
            report=report,
            round_findings=last_round_findings,
            findings=findings,
        )
        if new_body.strip():
            report.body = new_body.strip()  # else KEEP the prior report — never blank
        distill_step = ResearchStep(
            "distill",
            f"distilled {len(last_round_findings)} finding(s) into the working report "
            f"({len(report.render())} chars, {len(findings.all_sources())} source(s))",
            latency_ms=int((time.monotonic() - distill_t0) * 1000),
        )
        steps.append(distill_step)
        await _emit(on_step, distill_step)

        # --- reflect: coverage met? gaps? (reads the report, not the history) -
        reflect_t0 = time.monotonic()
        reflect_text = await _safe_llm(
            llm_call,
            [
                {
                    "role": "system",
                    "content": (
                        "Reflect on research coverage. State whether coverage is "
                        "COMPLETE or list remaining GAPS, one per line."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Query: {query}\nCoverage: {findings.coverage}\n\n"
                        f"Working report:\n{report.render()}"
                    ),
                },
            ],
        )
        reflect_step = ResearchStep(
            "reflect", "assessed coverage", latency_ms=int((time.monotonic() - reflect_t0) * 1000)
        )
        steps.append(reflect_step)
        await _emit(on_step, reflect_step)

        # Coverage FLOOR: every dimension needs >=1 source before "complete".
        if _coverage_met(findings.coverage) and _reflect_says_complete(reflect_text):
            break

    # --- clean completion: synthesize from the evolving report --------------
    synth_t0 = time.monotonic()
    markdown = await _synthesis_from_report(
        llm_call, query=query, symbol=symbol, report=report, findings=findings
    )
    synth_step = ResearchStep(
        "synthesize",
        "wrote brief from evolving report",
        latency_ms=int((time.monotonic() - synth_t0) * 1000),
    )
    steps.append(synth_step)
    await _emit(on_step, synth_step)
    return _synthesize_brief(
        query=query,
        symbol=symbol,
        markdown=markdown,
        findings=findings,
        structured=structured,
        steps=steps,
        budget=budget,
        note=None,
    )


def _merge_sources(briefs: list[ResearchBrief]) -> list[ResearchSource]:
    """De-dup the panel's sources by url, preserving first-seen order."""
    seen: set[str] = set()
    out: list[ResearchSource] = []
    for brief in briefs:
        for src in brief.sources:
            if src.url in seen:
                continue
            seen.add(src.url)
            out.append(src)
    return out


def _angle_sink(on_step: OnStep | None, index: int, label: str) -> OnStep:
    """Wrap the parent sink so an explorer's steps are tagged with their angle —
    so the activity surface SHOWS the parallel exploration happening."""
    tag = f"angle {index + 1}"
    short = label[:48]

    async def _sink(step: ResearchStep) -> None:
        await _emit(
            on_step,
            ResearchStep(
                step.kind,
                f"[{tag}: {short}] {step.detail}",
                latency_ms=step.latency_ms,
                status=step.status,
            ),
        )

    return _sink


async def run_heavy_research(
    query: str,
    *,
    angles: int = _MAX_ANGLES,
    region: str | None = None,
    tool_call: ToolCall,
    llm_call: LLMCall,
    budget: BudgetGuard,
    on_step: OnStep | None = None,
    max_researchers: int = 3,
) -> ResearchBrief:
    """Heavy mode — N parallel iter explorers (each its own evolving report) → one
    synthesized, citation-backed brief. Shares ``budget`` across the panel so the
    whole run stays inside the same ceiling (a breach winds each explorer down to
    its partial brief, then synthesis merges the survivors). Never raises."""
    angles = max(_MIN_ANGLES, min(int(angles), _MAX_ANGLES))
    steps: list[ResearchStep] = []

    # --- panel plan: split into N distinct, non-overlapping angles -----------
    t0 = time.monotonic()
    angle_text = await _safe_llm(
        llm_call,
        [
            {
                "role": "system",
                "content": (
                    f"You lead an expert research panel. Break the task into {angles} "
                    "DISTINCT, non-overlapping research angles (for an investment "
                    "thesis these might be: fundamentals & valuation; competitive "
                    "position & market; risks & catalysts; price/technical & flow). "
                    "Output one angle per line — each a short directive, no numbering."
                ),
            },
            {"role": "user", "content": f"Task: {query}"},
        ],
    )
    angle_list = _split_subquestions(angle_text, limit=angles)
    # Pad to N with sensible defaults if the planner under-delivered.
    for fallback in (
        f"Fundamentals, valuation, and financial health for {query}",
        f"Competitive position, market, and demand for {query}",
        f"Risks, catalysts, and recent news for {query}",
    ):
        if len(angle_list) >= angles:
            break
        if fallback not in angle_list:
            angle_list.append(fallback)
    angle_list = angle_list[:angles]
    budget.record(None, _ROUND_MODEL, _ROUND_PROVIDER)
    plan_step = ResearchStep(
        "plan",
        f"expert panel: {len(angle_list)} parallel angle(s)",
        latency_ms=int((time.monotonic() - t0) * 1000),
    )
    steps.append(plan_step)
    await _emit(on_step, plan_step)

    # --- parallel explorers, each its own evolving workspace -----------------
    explorers = [
        run_iter_research(
            f"{query} — focus: {angle}",
            region=region,
            tool_call=tool_call,
            llm_call=llm_call,
            budget=budget,  # shared: the panel stays inside one ceiling
            on_step=_angle_sink(on_step, i, angle),
            max_researchers=max_researchers,
        )
        for i, angle in enumerate(angle_list)
    ]
    briefs = await asyncio.gather(*explorers, return_exceptions=True)
    good = [b for b in briefs if isinstance(b, ResearchBrief)]

    if not good:
        # Every explorer failed (should not happen — iter never raises). Degrade to
        # a single iter run rather than returning nothing.
        return await run_iter_research(
            query,
            region=region,
            tool_call=tool_call,
            llm_call=llm_call,
            budget=budget,
            on_step=on_step,
            max_researchers=max_researchers,
        )

    # --- synthesis agent: integrate the panel into one brief -----------------
    merged_sources = _merge_sources(good)
    numbered = "\n".join(f"[{i + 1}] {s.title} — {s.url}" for i, s in enumerate(merged_sources))
    panel = "\n\n".join(f"## Angle {i + 1}\n{b.markdown}" for i, b in enumerate(good))
    budget.record(None, _ROUND_MODEL, _ROUND_PROVIDER)
    synth_t0 = time.monotonic()
    markdown = await _safe_llm(
        llm_call,
        [
            {
                "role": "system",
                "content": (
                    "You are the lead synthesist integrating an expert research panel "
                    "into ONE cohesive brief. Merge the angle reports, dedupe "
                    "overlapping claims, surface and resolve any disagreement "
                    "explicitly, and RENUMBER inline [n] citation markers against the "
                    "merged source list below. Output a tight, well-structured "
                    "markdown brief."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Task: {query}\n\nPanel reports:\n{panel}\n\n"
                    f"Merged sources (use these [n] numbers):\n{numbered}"
                ),
            },
        ],
    )
    if not markdown.strip():
        markdown = f"# Research brief: {query}\n\n{panel}"  # deterministic fallback
    synth_step = ResearchStep(
        "synthesize",
        f"synthesized {len(good)} angle report(s) into one brief",
        latency_ms=int((time.monotonic() - synth_t0) * 1000),
    )
    steps.append(synth_step)
    await _emit(on_step, synth_step)

    note = f"heavy:{len(good)} angles"
    if len(good) < len(angle_list):
        note += f" ({len(angle_list) - len(good)} angle(s) failed)"
    return ResearchBrief(
        query=query,
        symbol=good[0].symbol,
        mode="deep",
        markdown=markdown.strip(),
        sources=merged_sources,
        structured={
            "panel": [
                {"angle": i + 1, "note": b.note, "symbol": b.symbol} for i, b in enumerate(good)
            ]
        },
        steps=steps + [s for b in good for s in b.steps],
        source_count=len(merged_sources),
        cost=budget.cost(),
        web_available=any(b.web_available for b in good),
        note=note,
    )


__all__ = ["run_heavy_research", "run_iter_research"]
