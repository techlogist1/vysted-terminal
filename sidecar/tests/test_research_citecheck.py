"""Tests for ``services.research.citecheck`` — citation integrity (R8).

The live failures pinned here: a brief citing ``[47]`` against a 21-source
rail, and a numeric claim citing a different company's PDF (a TMB Bank
document cited as Route's earnings transcript).
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.budget_guard import BudgetGuard
from services.research.citecheck import (
    SOFTENER,
    ensure_citation_integrity,
    soften_sentence,
    strip_invalid_markers,
)
from services.research.models import ResearchSource, ResearchStep


def _run(coro):
    return asyncio.run(coro)


def _sources(n: int) -> list[ResearchSource]:
    return [
        ResearchSource(
            url=f"https://ex.com/{i}",
            title=f"Route Mobile filing {i}",
            excerpt=f"Excerpt {i} about Route Mobile revenue.",
        )
        for i in range(1, n + 1)
    ]


# --- structural pass -----------------------------------------------------------


def test_out_of_range_markers_are_stripped() -> None:
    md = "Revenue grew 23% [2]. Margin contracted [47]. Both held [1][9]."
    cleaned, removed = strip_invalid_markers(md, 3)
    assert removed == 2
    assert "[47]" not in cleaned and "[9]" not in cleaned
    assert "[2]" in cleaned and "[1]" in cleaned
    # No marker residue: tidy punctuation, no double spaces.
    assert "  " not in cleaned
    assert "Margin contracted." in cleaned


def test_zero_sources_strips_every_marker() -> None:
    # The FAST fabricated-citation case: prose cites [1][2] with NO sources.
    md = "Screener data shows a P/E of 12 [1] and ROE of 18% [2]."
    cleaned, removed = strip_invalid_markers(md, 0)
    assert removed == 2
    assert "[1]" not in cleaned and "[2]" not in cleaned
    assert "P/E of 12" in cleaned


def test_markdown_links_are_not_markers() -> None:
    md = "See [1](https://example.com/doc) and a real marker [7]."
    cleaned, removed = strip_invalid_markers(md, 2)
    assert removed == 1
    assert "[1](https://example.com/doc)" in cleaned
    assert "[7]" not in cleaned


def test_soften_sentence_is_deterministic() -> None:
    out = soften_sentence("Revenue grew 23% to Rs 1,234 crore [3].")
    assert out == "Revenue grew 23% to Rs 1,234 crore (not confirmed in this run)."
    # Idempotent-ish: softening twice never stacks the softener.
    assert soften_sentence(out).count(SOFTENER.strip()) == 1


# --- the bounded LLM spot-audit --------------------------------------------------


class _AuditLLM:
    """Fake llm_call recording the audit prompt and returning canned verdicts."""

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[list[dict[str, Any]]] = []

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        self.prompts.append(messages)
        return self.reply


def test_unsupported_claim_loses_citation_and_softens() -> None:
    md = (
        "# Brief\n\n"
        "Revenue grew 23% to Rs 1,234 crore [1].\n"
        "The transcript confirms 400 employees were added [2].\n"
    )
    llm = _AuditLLM("1: SUPPORTED\n2: UNSUPPORTED")
    out = _run(ensure_citation_integrity(md, _sources(2), llm_call=llm))
    assert "[1]" in out  # supported claim untouched
    assert "[2]" not in out  # unsupported citation removed
    assert "400 employees were added (not confirmed in this run)." in out
    # ONE audit call, carrying both claims and their cited source titles.
    assert len(llm.prompts) == 1
    user = llm.prompts[0][-1]["content"]
    assert "Claim 1" in user and "Claim 2" in user
    assert "Route Mobile filing 2" in user


def test_audit_is_conservative_on_garbled_reply() -> None:
    md = "Revenue grew 23% [1]."
    llm = _AuditLLM("the model rambles with no verdict lines")
    out = _run(ensure_citation_integrity(md, _sources(1), llm_call=llm))
    assert out == md  # nothing parseable → nothing changes


def test_audit_is_conservative_on_dead_llm() -> None:
    async def dead(messages: list[dict[str, Any]]) -> str:
        raise RuntimeError("provider down")

    md = "Revenue grew 23% [1]."
    out = _run(ensure_citation_integrity(md, _sources(1), llm_call=dead))
    assert out == md


def test_audit_caps_at_eight_claims() -> None:
    md = "\n".join(f"Metric {i} stood at {i * 11}% [1]." for i in range(1, 15))
    llm = _AuditLLM("\n".join(f"{i}: SUPPORTED" for i in range(1, 9)))
    _run(ensure_citation_integrity(md, _sources(1), llm_call=llm))
    user = llm.prompts[0][-1]["content"]
    assert "Claim 8" in user
    assert "Claim 9" not in user


def test_audit_skipped_under_wall_floor_with_dev_step_not_note() -> None:
    budget = BudgetGuard(max_wall_seconds=10)  # remaining < 15s from the start
    md = "Revenue grew 23% [1]. Bad marker [9]."
    llm = _AuditLLM("1: UNSUPPORTED")
    steps: list[ResearchStep] = []
    out = _run(ensure_citation_integrity(md, _sources(1), llm_call=llm, budget=budget, steps=steps))
    # The structural pass STILL ran; the audit did not.
    assert "[9]" not in out
    assert "[1]" in out  # the audit (which would soften) was skipped
    assert llm.prompts == []
    assert steps and steps[-1].status == "skipped"
    assert "audit skipped" in steps[-1].detail


def test_audit_runs_with_ample_wall_and_records_a_step() -> None:
    budget = BudgetGuard(max_wall_seconds=300)
    md = "Revenue grew 23% [1]."
    llm = _AuditLLM("1: SUPPORTED")
    steps: list[ResearchStep] = []
    _run(ensure_citation_integrity(md, _sources(1), llm_call=llm, budget=budget, steps=steps))
    assert len(llm.prompts) == 1
    assert steps and "audited 1 claim(s)" in steps[-1].detail


def test_non_numeric_sentences_are_not_audited() -> None:
    md = "The company is well positioned [1]."  # cited but carries no figure
    llm = _AuditLLM("1: UNSUPPORTED")
    out = _run(ensure_citation_integrity(md, _sources(1), llm_call=llm))
    assert llm.prompts == []  # nothing numeric to audit
    assert out == md


# --- R9 B3: the raw-evidence store feeds the audit --------------------------------


def test_audit_uses_full_page_text_when_evidence_carries_it() -> None:
    """The spot-audit judges against the cited source's FULL extracted text
    (the run's raw-evidence store), not just the two-line excerpt — a figure
    that lives deep in a filing no longer reads as unsupported."""
    md = "Revenue grew 23% to Rs 1,234 crore [1]."
    llm = _AuditLLM("1: SUPPORTED")
    evidence = {
        "https://ex.com/1": (
            "Full filing text page one ... deep in the annexure: revenue from "
            "operations Rs 1,234 crore for the quarter, up 23% year on year ..."
        )
    }
    _run(ensure_citation_integrity(md, _sources(1), llm_call=llm, evidence=evidence))
    user = llm.prompts[0][-1]["content"]
    assert "extracted page text" in user
    assert "deep in the annexure" in user
    # The two-line excerpt is superseded by the full text for this source.
    assert "Excerpt 1 about Route Mobile revenue." not in user


def test_audit_caps_evidence_and_shows_each_source_once() -> None:
    from services.research.citecheck import EVIDENCE_AUDIT_CHARS

    md = "Revenue grew 23% [1]. Margin reached 21% [1].\n"
    llm = _AuditLLM("1: SUPPORTED\n2: SUPPORTED")
    evidence = {"https://ex.com/1": "FULLTEXT " * 2000}
    _run(ensure_citation_integrity(md, _sources(1), llm_call=llm, evidence=evidence))
    user = llm.prompts[0][-1]["content"]
    assert user.count("extracted page text") == 1  # shown once, referenced after
    assert "(extracted text shown above)" in user
    # The evidence rides capped, never the whole 18k chars.
    start = user.index("extracted page text")
    assert len(user) - start < EVIDENCE_AUDIT_CHARS + 2500


_KAYNES_MD = """# Research brief: Kaynes Technology

**Key Metrics**
---------------

* Revenue growth: +40.5% (quarterly YoY, [2])
* Earnings growth: -0.4% (quarterly YoY, computed from quarterly statements, [n] 1)

**Merged Sources**
------------------

[n] numbers refer to the merged sources listed below:

1. Fundamentals data for KAYNES - vysted://fundamentals/KAYNES
2. Quarterly income statements for Kaynes Technology (2026-06-30 vs 2025-06-30)
6. Press release dated August 22, 2026 ([n] 8)

Note: This brief is built from exchange data and filings gathered on 2026-09-23.

---

References:

[n] 1. Quarterly income statements for Kaynes Technology (2026-06-30 vs 2025-06-30)
[n] 2. Provider's earnings growth scalar value
[n] 7. Exchange filings regarding AGM proceedings and voting results ([n] 9)
"""


def test_model_written_bibliography_and_n_literals_never_ship() -> None:
    """R15-RESEARCH-029: the numbered rail is the only bibliography — the
    model's "Merged Sources"/"References" lists and its "[n] k" literals are
    removed; the real [n] marker and the prose around them survive."""
    llm = _AuditLLM("1: SUPPORTED")
    steps: list[ResearchStep] = []
    out = _run(ensure_citation_integrity(_KAYNES_MD, _sources(3), llm_call=llm, steps=steps))
    assert "References" not in out and "Merged Sources" not in out
    assert "[n]" not in out
    assert "Provider's earnings growth scalar value" not in out
    assert "Revenue growth: +40.5% (quarterly YoY, [2])" in out
    assert "(quarterly YoY, computed from quarterly statements)" in out
    assert "Note: This brief is built from exchange data" in out
    assert "**Key Metrics**" in out
    # Two lists plus the one body literal are named on the dev step.
    assert "3 model-written source list(s)/[n] literal(s)" in steps[-1].detail


def test_trailing_sources_heading_list_is_stripped() -> None:
    """The HAL shape: a closing "### Sources" list the model appended itself."""
    md = "Revenue grew 23% [1].\n\n### Sources\n- [1] HAL annual report\n- [2] Reuters story\n"
    llm = _AuditLLM("1: SUPPORTED")
    out = _run(ensure_citation_integrity(md, _sources(2), llm_call=llm))
    assert out == "Revenue grew 23% [1]."


def test_audit_without_evidence_keeps_excerpt_behavior() -> None:
    md = "Revenue grew 23% [1]."
    llm = _AuditLLM("1: SUPPORTED")
    _run(ensure_citation_integrity(md, _sources(1), llm_call=llm, evidence={}))
    user = llm.prompts[0][-1]["content"]
    assert "Excerpt 1 about Route Mobile revenue." in user
    assert "extracted page text" not in user
