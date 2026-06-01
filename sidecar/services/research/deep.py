"""DEEP research — the bounded multi-researcher loop (FR-071/072, US13).

``run_deep_research`` is the expensive, grounded half of the research engine. It
runs a LangGraph-style loop — plan → parallel researchers → compress → reflect →
(re-enter while under budget) → synthesize — over an INJECTED tool layer and LLM
adapter, metered by a :class:`~services.budget_guard.BudgetGuard`.

Three invariants the loop holds, all load-bearing:

  - **Abort → synthesize, never a bare timeout.** ``budget.breach()`` is checked
    at the TOP of every round. The FIRST breach forces an IMMEDIATE synthesis
    from whatever was gathered and stamps the breach reason on ``brief.note``.
    The function NEVER raises on a budget breach — a short brief beats an error
    (SC-008 framing applied to research).

  - **Coverage floor.** Reflect may NOT declare the run complete until at least
    one source each for price / fundamentals / news / web is in hand. This stops
    a model from calling "done" on a thin run.

  - **Step accounting.** Each round records exactly one
    ``budget.record(None, model, provider)`` so the step ceiling advances even
    though token usage isn't available at this layer (the lead's handler wires
    real usage when it has it). The record happens AFTER the top-of-round breach
    check so the round that trips the step ceiling is the one whose breach the
    NEXT top-of-round check catches.

Everything model- or provider-facing is injected (``tool_call``, ``llm_call``)
so the loop is unit-testable with fakes and carries no import-time coupling to a
concrete provider.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from services.budget_guard import BudgetGuard
from services.research.models import ResearchBrief, ResearchSource, ResearchStep

#: Injected tool dispatcher — ``await tool_call(name, args) -> dict``.
ToolCall = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
#: Injected one-shot LLM completion — ``await llm_call(messages) -> str``.
LLMCall = Callable[[list[dict[str, Any]]], Awaitable[str]]
#: Injected step sink — ``on_step(ResearchStep) -> None`` (may be a coroutine).
OnStep = Callable[[ResearchStep], Any]

#: The four coverage dimensions the floor requires before "complete" (FR-071).
_COVERAGE_DIMS = ("price", "fundamentals", "news", "web")

#: Model/provider strings stamped on each ``budget.record`` so the step ceiling
#: advances and the cost snapshot is attributable. The real values are wired by
#: the lead's handler when usage is available; here they label the round.
_ROUND_MODEL = "research-deep"
_ROUND_PROVIDER = "research"


async def _emit(on_step: OnStep | None, step: ResearchStep) -> None:
    """Send one step to the sink, awaiting it if it's a coroutine, swallowing
    a sink failure (a broken progress sink must not abort the research run)."""
    if on_step is None:
        return
    try:
        result = on_step(step)
        if asyncio.iscoroutine(result):
            await result
    except Exception:  # noqa: BLE001 — a progress sink failure is non-fatal
        pass


async def _safe_tool(tool_call: ToolCall, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke one tool, converting any failure to an ``ok: False`` dict."""
    try:
        result = await tool_call(name, args)
    except Exception as exc:  # noqa: BLE001 — a tool miss is soft inside a round
        return {"ok": False, "error": f"{name} failed: {exc}"}
    return result if isinstance(result, dict) else {"ok": False, "error": "non-dict result"}


async def _safe_llm(llm_call: LLMCall, messages: list[dict[str, Any]]) -> str:
    """One-shot LLM completion, converting a failure to an empty string so the
    loop degrades to abort→synthesize rather than raising mid-round."""
    try:
        out = await llm_call(messages)
    except Exception:  # noqa: BLE001 — an LLM failure ends the round, not the run
        return ""
    return out if isinstance(out, str) else ""


def _split_subquestions(text: str, *, limit: int) -> list[str]:
    """Parse an LLM plan/reflect completion into a list of sub-questions.

    Accepts newline- or semicolon-separated lines, strips list-marker prefixes
    (``-``, ``*``, ``1.``), drops empties, and caps at ``limit`` so a chatty
    model can't widen the researcher fan-out past the configured ceiling.
    """
    raw_lines: list[str] = []
    for chunk in text.replace(";", "\n").splitlines():
        line = chunk.strip()
        if not line:
            continue
        # Strip common list markers: "- ", "* ", "1. ", "2) ".
        while line and (line[0] in "-*•"):
            line = line[1:].strip()
        if len(line) > 2 and line[0].isdigit():
            # Drop a leading ordered-list prefix: "<digits><.|)>".
            i = 0
            while i < len(line) and line[i].isdigit():
                i += 1
            if i < len(line) and line[i] in ".)":
                line = line[i + 1 :].strip()
        if line:
            raw_lines.append(line)
    # De-dup preserving order, then cap.
    seen: set[str] = set()
    out: list[str] = []
    for line in raw_lines:
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
        if len(out) >= limit:
            break
    return out


def _coverage_met(coverage: dict[str, bool]) -> bool:
    """True iff every coverage dimension has at least one source."""
    return all(coverage.get(dim, False) for dim in _COVERAGE_DIMS)


def _reflect_says_complete(text: str) -> bool:
    """Heuristic: does a reflect completion declare coverage met?

    Looks for an affirmative marker (``complete`` / ``done`` / ``sufficient`` /
    ``no gaps`` / ``yes``) and the ABSENCE of an explicit gap signal. Conservative
    — when ambiguous it returns False so the loop keeps going (bounded anyway by
    the budget), rather than declaring a thin run done.
    """
    low = text.strip().lower()
    if not low:
        return False
    gap_markers = ("gap", "missing", "incomplete", "not enough", "more research")
    negative = any(g in low for g in gap_markers)
    if negative:
        return False
    return any(p in low for p in ("complete", "done", "sufficient", "no gaps", "covered", "yes"))


class _Findings:
    """Mutable accumulator threaded through the loop.

    Holds the running findings text (for compress/synthesize), the web citations
    gathered (the ``[n]`` sources), the structured provenance seen, and the
    coverage flags. Kept as a small object rather than a tuple so the round
    helpers read/mutate it without a wide return signature.
    """

    __slots__ = ("findings", "web_sources", "structured_sources", "coverage")

    def __init__(self) -> None:
        self.findings: list[str] = []
        self.web_sources: list[ResearchSource] = []
        self.structured_sources: list[ResearchSource] = []
        self.coverage: dict[str, bool] = dict.fromkeys(_COVERAGE_DIMS, False)

    def all_sources(self) -> list[ResearchSource]:
        """Web citations first (they own the low ``[n]`` markers), then
        structured-provenance sources — de-duplicated by url."""
        seen: set[str] = set()
        out: list[ResearchSource] = []
        for src in [*self.web_sources, *self.structured_sources]:
            if src.url in seen:
                continue
            seen.add(src.url)
            out.append(src)
        return out


def _record_structured(findings: _Findings, name: str, dim: str, result: dict[str, Any]) -> None:
    """Fold a structured tool result into findings + coverage + provenance."""
    if not result.get("ok"):
        return
    findings.coverage[dim] = True
    provider = None
    for key in ("provider", "source", "mode"):
        val = result.get(key)
        if isinstance(val, str) and val:
            provider = val
            break
    findings.structured_sources.append(
        ResearchSource(
            url=f"vysted://{dim}/{name}",
            title=f"{dim.title()} for {name}",
            excerpt=f"Structured {dim} pull" + (f" via {provider}" if provider else "") + ".",
            domain=provider or "vysted",
        )
    )


def _record_web(findings: _Findings, result: dict[str, Any]) -> None:
    """Fold a web_search result into citations + coverage."""
    if not result.get("ok"):
        return
    citations = result.get("citations") or []
    results = result.get("results") or []
    rows = citations if citations else results
    added = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        url = row.get("url")
        if not url:
            continue
        findings.web_sources.append(
            ResearchSource(
                url=str(url),
                title=str(row.get("title") or url),
                excerpt=str(row.get("excerpt") or row.get("snippet") or ""),
                domain=str(row.get("source") or "web"),
            )
        )
        added = True
    if added:
        findings.coverage["web"] = True


async def _run_researcher(
    sub_question: str,
    *,
    symbol: str,
    region: str | None,
    tool_call: ToolCall,
    llm_call: LLMCall,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """One researcher: a couple of tool lookups + a short LLM extraction.

    Pulls the web (always — the freshest, most question-shaped source) plus one
    structured leg chosen by what the sub-question is about, then asks the LLM to
    extract the finding. Returns ``(finding_text, web_result, structured_pair)``
    where ``structured_pair`` is ``{"dim": ..., "result": ...}`` (or empty) so
    the caller folds coverage on the main task, not inside the gathered child.
    """
    low = sub_question.lower()
    if any(k in low for k in ("valuation", "fundamental", "earnings", "margin", "revenue", "debt")):
        dim, tool, args = "fundamentals", "fundamentals", {"symbol": symbol}
    elif any(k in low for k in ("filing", "10-k", "10-q", "8-k", "sec", "insider")):
        dim, tool, args = "fundamentals", "sec_filings_list", {"symbol": symbol}
    elif any(k in low for k in ("price", "chart", "trend", "volatility", "momentum", "technical")):
        dim, tool, args = "price", "price_data", {"symbol": symbol}
    else:
        dim, tool, args = "news", "news", {"symbols": [symbol]}

    web_args: dict[str, Any] = {"query": f"{symbol} {sub_question}"}
    if region:
        web_args["region"] = region

    structured_res, web_res = await asyncio.gather(
        _safe_tool(tool_call, tool, args),
        _safe_tool(tool_call, "web_search", web_args),
    )

    extract = await _safe_llm(
        llm_call,
        [
            {
                "role": "system",
                "content": (
                    "You are a research analyst. Extract the key finding for the "
                    "sub-question from the provided data in 1-2 sentences. Cite "
                    "concretely; do not invent facts not in the data."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Sub-question: {sub_question}\n"
                    f"Structured ({tool}): {structured_res}\n"
                    f"Web: {web_res}"
                ),
            },
        ],
    )
    finding = extract.strip() or f"(no finding extracted for: {sub_question})"
    structured_pair = {"dim": dim, "result": structured_res} if structured_res.get("ok") else {}
    return finding, web_res, structured_pair


def _synthesize_brief(
    *,
    query: str,
    symbol: str,
    markdown: str,
    findings: _Findings,
    structured: dict[str, Any],
    steps: list[ResearchStep],
    budget: BudgetGuard,
    note: str | None,
) -> ResearchBrief:
    """Assemble the final :class:`ResearchBrief` from accumulated state."""
    sources = findings.all_sources()
    return ResearchBrief(
        query=query,
        symbol=symbol,
        mode="deep",
        markdown=markdown,
        sources=sources,
        structured=structured,
        steps=steps,
        source_count=len(sources),
        cost=budget.cost(),
        web_available=bool(findings.web_sources),
        note=note,
    )


async def _final_synthesis(
    llm_call: LLMCall, *, query: str, symbol: str, findings: _Findings
) -> str:
    """Ask the LLM to write the brief markdown with inline ``[n]`` citations.

    The numbered source list is handed to the model so its ``[n]`` markers line
    up with :meth:`_Findings.all_sources`. On an empty/failed completion a terse
    deterministic fallback is returned (never an empty brief).
    """
    sources = findings.all_sources()
    numbered = "\n".join(f"[{i + 1}] {s.title} — {s.url}" for i, s in enumerate(sources))
    body = await _safe_llm(
        llm_call,
        [
            {
                "role": "system",
                "content": (
                    "Write a concise research brief in markdown. Use inline [n] "
                    "citation markers that reference the numbered sources. Do not "
                    "fabricate sources or facts beyond the findings."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Query: {query}\nSymbol: {symbol}\n\n"
                    f"Findings:\n" + "\n".join(f"- {f}" for f in findings.findings) + "\n\n"
                    f"Sources:\n{numbered}"
                ),
            },
        ],
    )
    if body.strip():
        return body.strip()
    # Deterministic fallback — abort path with a dead LLM still ships a brief.
    lines = [f"# Research brief: {query}", "", f"Symbol: {symbol}", ""]
    if findings.findings:
        lines.append("## Findings")
        lines.extend(f"- {f}" for f in findings.findings)
    else:
        lines.append("_No findings were gathered before the run ended._")
    return "\n".join(lines)


async def run_deep_research(
    query: str,
    *,
    region: str | None = None,
    tool_call: ToolCall,
    llm_call: LLMCall,
    budget: BudgetGuard,
    on_step: OnStep | None = None,
    max_researchers: int = 3,
) -> ResearchBrief:
    """Run the DEEP bounded research loop for ``query``; return a brief.

    See the module docstring for the loop shape and the three invariants. The
    function ALWAYS returns a :class:`ResearchBrief` — a budget breach aborts to
    synthesis (with ``note`` set to the breach reason), never raises.
    """
    findings = _Findings()
    steps: list[ResearchStep] = []
    structured: dict[str, Any] = {}

    # Resolve once up front so every round + the web rounds use a clean symbol.
    resolve_args: dict[str, Any] = {"query": query}
    if region:
        resolve_args["region"] = region
    resolved = await _safe_tool(tool_call, "resolve_symbol", resolve_args)
    instrument = (resolved.get("resolved") or {}) if resolved.get("ok") else {}
    symbol = instrument.get("symbol") or query
    structured["resolved"] = resolved

    async def abort_synthesize(reason: str) -> ResearchBrief:
        """Immediate abort→synthesis from whatever is gathered (never raises)."""
        t0 = time.monotonic()
        markdown = await _final_synthesis(llm_call, query=query, symbol=symbol, findings=findings)
        latency = int((time.monotonic() - t0) * 1000)
        step = ResearchStep("synthesize", f"abort→synthesize: {reason}", latency_ms=latency)
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

    open_questions: list[str] = []

    while True:
        # --- top-of-round budget gate: FIRST breach => abort→synthesize -------
        reason = budget.breach()
        if reason is not None:
            return await abort_synthesize(reason)

        # Each round counts as one step so the step ceiling advances. No usage at
        # this layer — pass None; the lead's handler wires real usage if it has it.
        budget.record(None, _ROUND_MODEL, _ROUND_PROVIDER)

        # --- plan: what's unanswered? -> sub-questions ------------------------
        t0 = time.monotonic()
        plan_text = await _safe_llm(
            llm_call,
            [
                {
                    "role": "system",
                    "content": (
                        "You are planning a research run. List the open "
                        "sub-questions still unanswered, one per line. Be specific."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Query: {query}\nSymbol: {symbol}\n"
                        f"Findings so far:\n"
                        + ("\n".join(f"- {f}" for f in findings.findings) or "(none yet)")
                    ),
                },
            ],
        )
        open_questions = _split_subquestions(plan_text, limit=max_researchers)
        if not open_questions:
            # No plan came back (dead/blank LLM) — seed a default fan-out so the
            # round still does real work rather than stalling.
            open_questions = [
                f"What is the recent price action and trend for {symbol}?",
                f"What do the latest fundamentals say about {symbol}?",
                f"What recent news affects {symbol}?",
            ][:max_researchers]
        plan_step = ResearchStep(
            "plan",
            f"planned {len(open_questions)} sub-question(s)",
            latency_ms=int((time.monotonic() - t0) * 1000),
        )
        steps.append(plan_step)
        await _emit(on_step, plan_step)

        # --- parallel researchers --------------------------------------------
        researcher_t0 = time.monotonic()
        results = await asyncio.gather(
            *(
                _run_researcher(
                    q,
                    symbol=symbol,
                    region=region,
                    tool_call=tool_call,
                    llm_call=llm_call,
                )
                for q in open_questions[:max_researchers]
            )
        )
        for q, (finding, web_res, structured_pair) in zip(
            open_questions[:max_researchers], results, strict=False
        ):
            findings.findings.append(finding)
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

        # --- compress (citation-preserving) ----------------------------------
        compress_t0 = time.monotonic()
        compress_step = ResearchStep(
            "compress",
            f"compressed {len(findings.findings)} finding(s), "
            f"{len(findings.all_sources())} source(s)",
            latency_ms=int((time.monotonic() - compress_t0) * 1000),
        )
        steps.append(compress_step)
        await _emit(on_step, compress_step)

        # --- reflect: coverage met? gaps? ------------------------------------
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
                        f"Query: {query}\n"
                        f"Coverage: {findings.coverage}\n"
                        f"Findings:\n" + "\n".join(f"- {f}" for f in findings.findings)
                    ),
                },
            ],
        )
        reflect_step = ResearchStep(
            "reflect",
            "assessed coverage",
            latency_ms=int((time.monotonic() - reflect_t0) * 1000),
        )
        steps.append(reflect_step)
        await _emit(on_step, reflect_step)

        # Coverage FLOOR: reflect may only declare complete once every dimension
        # (price/fundamentals/news/web) has >=1 source. Under-covered runs keep
        # going (bounded by the budget) regardless of what the model said.
        coverage_floor = _coverage_met(findings.coverage)
        if coverage_floor and _reflect_says_complete(reflect_text):
            break

        # Otherwise re-enter the loop — the top-of-round budget gate decides
        # whether the next round runs or we abort→synthesize.

    # --- clean completion: final synthesize ---------------------------------
    synth_t0 = time.monotonic()
    markdown = await _final_synthesis(llm_call, query=query, symbol=symbol, findings=findings)
    synth_step = ResearchStep(
        "synthesize",
        "wrote brief",
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


__all__ = ["LLMCall", "OnStep", "ToolCall", "run_deep_research"]
