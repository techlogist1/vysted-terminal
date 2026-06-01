"""Research engine core — the FAST bundle + the DEEP bounded loop (US12/US13).

Two grounded research entry points sit on top of the agent-tool layer and the
LLM adapter layer, sharing one set of serialisable models:

  - :func:`services.research.fast.gather_fast` — a NO-LLM structured pull: one
    symbol resolve, a parallel fan-out over price / fundamentals / news / SEC
    filings, and ONE web round. It returns a structured bundle the agent
    synthesises prose from (prompt-driven). Honest about a missing web backend —
    never an empty or fabricated web section (FR-070).

  - :func:`services.research.deep.run_deep_research` — a LangGraph-style bounded
    loop: plan → parallel researchers → compress → reflect → (re-enter while
    under budget) → synthesize. A :class:`~services.budget_guard.BudgetGuard`
    ceiling breach forces an IMMEDIATE abort→synthesize from whatever was
    gathered (never a bare timeout/error), with the breach reason on the brief
    (FR-071/072). A coverage floor keeps reflect from declaring "done" before at
    least one source each for price/fundamentals/news/web is in hand.

The models (:mod:`services.research.models`) are plain dataclasses with
``to_dict()`` so a brief crosses the wire / persists without pulling in pydantic
here. The structured-data provider strings are carried through for provenance.
"""

from __future__ import annotations

from services.research.models import (
    ResearchBrief,
    ResearchSource,
    ResearchStep,
)

__all__ = [
    "ResearchBrief",
    "ResearchSource",
    "ResearchStep",
]
