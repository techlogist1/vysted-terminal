"""Lexicon-based sentiment scoring for news headlines.

Uses VADER (``vaderSentiment``) — a pure-Python, rule/lexicon-based sentiment
analyser. This is a deliberate Tier-3 decision (see CLAUDE.md "Decision
authority"): the sidecar ships as a PyInstaller ``--onefile`` binary, and a
model-based scorer such as FinBERT would drag in ``torch`` — a multi-hundred-MB
native dependency tree that cannot be vetted against the macOS CI runner
locally. VADER is a single pure-Python wheel with no native extensions, so it
bundles cleanly. The tradeoff: VADER is tuned for social-media text rather than
financial copy, so per-item scores are coarser than a finance-tuned model would
give — acceptable for a Phase 1 "at a glance" sentiment indicator.

Scores are normalised to VADER's ``compound`` value, already in ``[-1, 1]``.
The label thresholds follow the VADER author's published recommendation
(``>= 0.05`` positive, ``<= -0.05`` negative, between is neutral).
"""

from __future__ import annotations

from dataclasses import dataclass

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# VADER's recommended cutoffs for the compound score.
_POSITIVE_THRESHOLD = 0.05
_NEGATIVE_THRESHOLD = -0.05

# A single analyser instance is reused — it loads its lexicon once and is
# stateless across calls, so it is safe to share.
_analyzer = SentimentIntensityAnalyzer()


@dataclass(frozen=True)
class SentimentResult:
    """A sentiment score in ``[-1, 1]`` plus its coarse label."""

    score: float
    label: str


def label_for_score(score: float) -> str:
    """Map a compound score in ``[-1, 1]`` to a coarse sentiment label."""
    if score >= _POSITIVE_THRESHOLD:
        return "positive"
    if score <= _NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"


def score_text(text: str | None) -> SentimentResult:
    """Score a single piece of text (a headline, optionally with its summary).

    Empty or whitespace-only input scores a neutral ``0.0`` rather than raising
    — a news item with no usable text simply gets no sentiment signal.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return SentimentResult(score=0.0, label="neutral")
    compound = float(_analyzer.polarity_scores(cleaned)["compound"])
    return SentimentResult(score=compound, label=label_for_score(compound))
