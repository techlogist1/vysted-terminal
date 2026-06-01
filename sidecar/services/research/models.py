"""Serialisable models for the research engine (FR-070/071/072).

Plain dataclasses (no pydantic) — a research bundle is a transport/persistence
shape, not a validated request body, and the research package must not pull a
heavy dependency into the hot agent path. Every model exposes ``to_dict()`` so a
:class:`ResearchBrief` round-trips to JSON for the runs store / the frontend
research-cockpit / the MCP surface without bespoke encoders.

Conventions held across the three models:

  - ``to_dict()`` returns only JSON-native scalars / lists / dicts (no datetime,
    no nested dataclass instances) — nested sources/steps are recursed.
  - ``None`` optional fields are kept in the dict (an explicit ``null`` is more
    honest to a consumer than a missing key — e.g. ``note: null`` says "no abort
    reason", ``latency_ms: null`` says "not timed").
  - Provenance (the structured-data ``provider`` string and the web availability
    flag) is carried, never inferred downstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: ``ResearchStep.kind`` values — the stages a research run emits. ``plan`` and
#: ``reflect`` are LLM turns; ``tool`` / ``search`` are data pulls; ``compress``
#: folds findings citation-preserving; ``synthesize`` writes the final brief.
STEP_KINDS = ("plan", "tool", "search", "compress", "reflect", "synthesize")

#: ``ResearchBrief.mode`` values — the two research entry points.
RESEARCH_MODES = ("fast", "deep")


@dataclass(slots=True)
class ResearchSource:
    """A cited source backing a finding — a web citation or a structured pull.

    ``url`` is the canonical citation target. For a structured-data source (e.g.
    "price via yfinance") the ``url`` may be a provider scheme like
    ``"vysted://price/AAPL"`` so the brief's ``[n]`` markers always resolve to
    *something*, and ``domain`` carries the provider/domain label for display.
    """

    url: str
    title: str
    excerpt: str
    domain: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "excerpt": self.excerpt,
            "domain": self.domain,
        }


@dataclass(slots=True)
class ResearchStep:
    """One stage in a research run — surfaced live (DEEP) for a progress trace.

    ``kind`` is one of :data:`STEP_KINDS`; ``detail`` is a short human line
    (e.g. ``"researcher: what is the demand outlook?"``); ``latency_ms`` is the
    wall time of the stage when measured; ``status`` is ``"ok"`` or ``"error"``
    so a non-fatal sub-failure (one researcher that errored) is still recorded
    rather than swallowed.
    """

    kind: str
    detail: str
    latency_ms: int | None = None
    status: str = "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "latency_ms": self.latency_ms,
            "status": self.status,
        }


@dataclass(slots=True)
class ResearchBrief:
    """The output of a research run — markdown prose + the evidence behind it.

    ``markdown`` is the synthesised brief (with inline ``[n]`` citation markers
    in DEEP mode; FAST leaves prose to the agent and ships an empty/short body).
    ``sources`` are the ``[n]``-ordered citations. ``structured`` is the raw
    bundle (price/fundamentals/news/filings) for the cockpit panels. ``steps``
    is the run trace. ``source_count`` is a denormalised ``len(sources)`` for a
    cheap consumer. ``cost`` is the :meth:`BudgetGuard.cost` snapshot.
    ``web_available`` records whether any web citation was actually gathered (vs
    a structured-only run). ``note`` carries an abort/breach reason when a budget
    ceiling cut the run short — ``None`` on a clean finish.
    """

    query: str
    symbol: str
    mode: str
    markdown: str
    sources: list[ResearchSource] = field(default_factory=list)
    structured: dict[str, Any] = field(default_factory=dict)
    steps: list[ResearchStep] = field(default_factory=list)
    source_count: int = 0
    cost: dict[str, Any] = field(default_factory=dict)
    web_available: bool = False
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "symbol": self.symbol,
            "mode": self.mode,
            "markdown": self.markdown,
            "sources": [s.to_dict() for s in self.sources],
            "structured": self.structured,
            "steps": [s.to_dict() for s in self.steps],
            "source_count": self.source_count,
            "cost": self.cost,
            "web_available": self.web_available,
            "note": self.note,
        }


__all__ = [
    "RESEARCH_MODES",
    "STEP_KINDS",
    "ResearchBrief",
    "ResearchSource",
    "ResearchStep",
]
