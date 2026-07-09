"""Identity cross-check — provider company name vs resolver canonical name (R12, D67).

The D56 dividend cross-check taught the app to flag, never silently absorb, two
data sources that disagree. This applies the same discipline to IDENTITY. In
the R12 battery finding, yfinance's own ``name`` field said "Gujarat Energy
Limited" while the resolver's bundled master still said "Gujarat Gas Limited"
for the same instrument — two contradictory identity signals in the same view,
with nothing reconciling them. The user saw the stale one with full confidence.

This module is a small, deterministic detector: when the fundamentals provider's
company name and the resolver's canonical name for the SAME instrument disagree
past a defensible similarity floor, it emits a machine-readable
``identity_conflict`` in the SAME conflict-note shape the D56 dividend conflict
uses (``field`` / ``sources`` / ``note``), carrying BOTH names. The caller
appends it to the research ``conflicts`` list — the identities are NEVER swapped
silently; the disagreement is surfaced so the user (or a follow-up rename lane)
decides.

Similarity model (simple + deterministic, not fuzzy-magic)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both names are lowercased, split into alphanumeric tokens, and stripped of
generic corporate suffixes (``ltd``/``limited``/``inc``/…). The score is the
**Jaccard** overlap of the two token sets — ``|A ∩ B| / |A ∪ B|`` — a pure
set operation with no ordering, no edit distance, no tuning knobs beyond the
one floor below. Names agree at 1.0 ("Reliance Industries Limited" vs
"Reliance Industries Ltd" → ``{reliance, industries}`` both). A material
disagreement scores low: "Gujarat Gas" vs "Gujarat Energy" →
``{gujarat, gas}`` vs ``{gujarat, energy}`` → ``1/3 ≈ 0.33``. Below
:data:`CONFLICT_THRESHOLD` is a conflict.
"""

from __future__ import annotations

import re
from typing import Any

#: Jaccard token-set similarity at or above which the two names are considered
#: the same identity. Below it, a conflict is emitted. 0.5 flags the finding's
#: "Gujarat Gas" vs "Gujarat Energy" (0.33) while a mere suffix/wording variant
#: ("… Limited" vs "… Ltd") scores 1.0 and never trips.
CONFLICT_THRESHOLD = 0.5

_TOKEN_RE = re.compile(r"[a-z0-9]+")

#: Generic corporate suffixes stripped before comparison so "… Limited" and
#: "… Ltd" compare on their distinctive tokens (mirrors the resolver's set).
_CORP_SUFFIXES = frozenset(
    {
        "limited",
        "ltd",
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "company",
        "co",
        "plc",
        "llc",
        "lp",
        "the",
    }
)


def _tokens(name: str) -> set[str]:
    """Distinctive lowercase tokens of ``name`` (corporate suffixes removed).

    Falls back to the raw token set when stripping suffixes would empty it (a
    company literally named e.g. "Company") so the comparison never degenerates.
    """
    raw = _TOKEN_RE.findall(name.lower())
    core = [t for t in raw if t not in _CORP_SUFFIXES]
    return set(core) if core else set(raw)


def token_set_similarity(a: str, b: str) -> float:
    """Jaccard overlap of the two names' distinctive token sets, in ``[0, 1]``.

    ``1.0`` = identical distinctive tokens; ``0.0`` = no shared token (or either
    name empty). Deterministic and symmetric.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    union = ta | tb
    return len(ta & tb) / len(union) if union else 0.0


def identity_conflict(
    canonical_name: str | None,
    provider_name: str | None,
    *,
    provider: str = "yfinance",
    symbol: str | None = None,
    threshold: float = CONFLICT_THRESHOLD,
) -> dict[str, Any] | None:
    """Emit an ``identity_conflict`` note when the two names materially disagree.

    Returns ``None`` when either name is missing/blank (nothing to compare) or
    when the token-set similarity is at or above ``threshold`` (they agree). When
    they disagree, returns a machine-readable dict in the D56 conflict-note shape
    (``field`` / ``sources`` / ``note``) carrying BOTH names — never a swap.
    """
    if not canonical_name or not provider_name:
        return None
    canonical = canonical_name.strip()
    provided = provider_name.strip()
    if not canonical or not provided:
        return None
    similarity = token_set_similarity(canonical, provided)
    if similarity >= threshold:
        return None

    who = f" for {symbol}" if symbol else ""
    conflict: dict[str, Any] = {
        "field": "identity",
        "kind": "identity_conflict",
        "similarity": round(similarity, 3),
        "sources": [
            {"provider": "resolver (canonical master)", "value": canonical},
            {"provider": provider, "value": provided},
        ],
        "note": (
            f"The fundamentals provider ({provider}) reports the company name "
            f"{provided!r}{who}, which materially disagrees with the resolver's "
            f"canonical name {canonical!r} (token-set similarity "
            f"{similarity:.0%} < {threshold:.0%}). This can indicate a symbol "
            "rename or a mis-resolution; the identities are NOT reconciled "
            "automatically."
        ),
    }
    if symbol:
        conflict["symbol"] = symbol
    return conflict


__all__ = [
    "CONFLICT_THRESHOLD",
    "identity_conflict",
    "token_set_similarity",
]
