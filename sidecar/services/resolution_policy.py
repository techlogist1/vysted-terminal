"""Resolution policy — the ONE acceptance policy for symbol resolution (R10, E1).

Before R10 three gates judged the same resolver output with two different
truths: the research target binding accepted anything >= 0.5
(``CONFIDENCE_FLOOR``), the agent-facing path disambiguated under 0.72
(``DISAMBIGUATION_THRESHOLD``), and the fuzzy scorer floored at 0.6 — so
"Reliance Q4 results" silently bound Freelancer Ltd for research while the
agent path would have asked. This module is the single decision point: every
consumer maps a :class:`~services.symbol_resolver.Resolution` to ONE
:class:`ResolutionDecision` via :func:`decide`. No other module may define an
acceptance threshold (a grep-style test pins this).

Outcomes:

  - ``bound``        — confidence >= :data:`ACCEPT` at a STRONG band (exact
                       ticker, marquee primary, name-exact, first-word, or
                       prefix — band >= :data:`BAND_PREFIX`). A bare-substring
                       or whole-string-fuzzy match NEVER binds: a query that is
                       merely a word *inside* a longer name ("Technologies" →
                       Palantir, "Steel" → one of many) is a guess, not an
                       identity (R10 review hardening).
  - ``disambiguate`` — confidence in ``[REJECT, ACCEPT)``, a marquee family
                       name, ANY substring / whole-string fuzzy match (it
                       may be offered as a "did you mean?", never auto-bound —
                       the E1 wrong-entity class), or a RESIDUAL TIE (R11,
                       D58b): the top candidates are DISTINCT instruments tied
                       EXACTLY in ``(band, score)`` with nothing left to
                       separate them — the 'jindal'/'godrej' class, where a
                       first-word tie used to bind whichever iterated first in
                       the master, an arbitrary guess.
  - ``unresolved``   — nothing matched, or confidence < :data:`REJECT`.

Residual-tie semantics (D58b): two rows of the SAME bare symbol (an NSE/BSE
dual listing, an India+US ADR) are one instrument, never a tie. Distinct
instruments in DIFFERENT regions tied in ``(band, score)`` were separated by
the resolver's locale rank (region is real ranking evidence there), so that
bind stands. Only distinct SAME-REGION instruments tied exactly in
``(band, score)`` are residual — the ranking has genuinely nothing left, and a
bind would be dict-iteration luck.

The band vocabulary lives here (the resolver imports it) so the policy can
read a candidate's match band without a circular import: this module imports
``symbol_resolver`` types only for type checking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # import-light: no runtime dependency on the resolver
    from services.symbol_resolver import Instrument, Resolution

#: Confidence at or above which a non-fuzzy match binds outright.
ACCEPT = 0.72
#: Confidence below which a match is rejected as unresolved (never offered).
REJECT = 0.50

#: Match bands, strongest first. The sort key in the resolver is
#: ``(band, locale_match, name_score)`` — a cross-locale higher band ALWAYS
#: beats a same-locale lower band (the additive locale bonus is gone).
BAND_EXACT_TICKER = 6
BAND_MARQUEE = 5
BAND_NAME_EXACT = 4
BAND_FIRST_WORD = 3
BAND_PREFIX = 2
BAND_SUBSTRING = 1
BAND_FUZZY = 0


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    """The one acceptance verdict for a resolution."""

    outcome: Literal["bound", "disambiguate", "unresolved"]
    instrument: Instrument | None
    candidates: list[Instrument]
    reason: str


def _residual_tie(best: Instrument, candidates: list[Instrument]) -> bool:
    """True when the nearest DISTINCT instrument ties ``best`` exactly (D58b).

    Walks the ranked candidates past every row of ``best``'s own bare symbol
    (a dual listing / ADR is the same instrument) to the first genuinely
    different instrument. An exact ``(band, score)`` tie there, in the SAME
    region, means the resolver's ranking had nothing left to separate the two
    and the winner is master-iteration order — a residual tie. A cross-region
    tie is NOT residual: region is the separating evidence (the locale rank),
    so the bind stands.
    """
    for cand in candidates:
        if cand.symbol == best.symbol:
            continue
        return cand.band == best.band and cand.score == best.score and cand.region == best.region
    return False


def decide(resolution: Resolution) -> ResolutionDecision:
    """Map a resolver :class:`Resolution` to the ONE acceptance decision.

    Pure and deterministic: reads only the resolution's best/candidates/score
    and the best candidate's match band. A marquee family hit below ACCEPT is
    a forced, curated disambiguation; a substring or whole-string fuzzy hit is
    NEVER bound no matter how high its score — only a STRONG band (>= prefix)
    binds outright (R10 review: "Lookup Technologies" must not bind PLTR).
    R11 (D58b): even a strong band never binds through a residual tie — when
    the top candidates are distinct same-region instruments tied exactly in
    ``(band, score)``, the honest outcome is an explicit choice.
    """
    best = resolution.best
    if best is None:
        return ResolutionDecision("unresolved", None, [], "no instrument matched the query")
    confidence = resolution.confidence
    band = best.band
    candidates = list(resolution.candidates)
    if band == BAND_MARQUEE and confidence < ACCEPT:
        return ResolutionDecision(
            "disambiguate",
            None,
            candidates,
            "marquee family name — an explicit choice is required",
        )
    if confidence >= ACCEPT and band >= BAND_PREFIX:
        if _residual_tie(best, candidates):
            return ResolutionDecision(
                "disambiguate",
                None,
                candidates,
                f"top candidates tie exactly at band {band} — "
                "an explicit choice is required, never an arbitrary bind",
            )
        return ResolutionDecision(
            "bound", best, candidates, f"score {confidence:.2f} >= accept at band {band}"
        )
    if confidence >= REJECT:
        reason = (
            "substring/fuzzy match — offered for disambiguation, never auto-bound"
            if band < BAND_PREFIX
            else f"score {confidence:.2f} in the disambiguation band"
        )
        return ResolutionDecision("disambiguate", None, candidates, reason)
    return ResolutionDecision(
        "unresolved", None, candidates, f"score {confidence:.2f} below the reject floor"
    )


__all__ = [
    "ACCEPT",
    "BAND_EXACT_TICKER",
    "BAND_FIRST_WORD",
    "BAND_FUZZY",
    "BAND_MARQUEE",
    "BAND_NAME_EXACT",
    "BAND_PREFIX",
    "BAND_SUBSTRING",
    "REJECT",
    "ResolutionDecision",
    "decide",
]
