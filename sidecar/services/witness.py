"""The shared predicates of the India-only research witnesses.

Every disclosure-only cross-check that consults an Indian exchange lane
(:mod:`services.ownership_check`, :mod:`services.market_cap_witness`,
:mod:`services.dividend_actions`, :mod:`services.research.range_check`) decides
two things the same way, so they are decided HERE once and imported — a copy
that drifts would let one witness fire where another stays silent.

``is_india_listing`` reads the RESOLVED listing, never bare-ticker membership in
the Indian masters: the fundamentals leg returns the Yahoo listing form
(``AMAL.BO`` for Amal Ltd on BSE, ``AMAL`` for Amalgamated Financial on NASDAQ),
and a bare ``AMAL`` bound to the US company must never fetch Amal Ltd's BSE
shareholding as if it were the US company's.
"""

from __future__ import annotations


def is_india_listing(listing: object) -> bool:
    """True when ``listing`` is an NSE or BSE listing (a ``.NS``/``.BO`` form)."""
    return isinstance(listing, str) and listing.strip().upper().endswith((".NS", ".BO"))


def is_block_error(exc: BaseException) -> bool:
    """True when ``exc`` looks like an exchange block/throttle (vs a plain miss).

    Matched on the ProviderError text the NSE/BSE lanes raise ("blocked",
    "HTTP 401/403/429"): a block should open the exchange circuit; a benign
    "no scrip code" / "no pattern" miss should not.
    """
    text = str(exc).lower()
    return "blocked" in text or any(code in text for code in ("http 401", "http 403", "http 429"))


__all__ = ["is_block_error", "is_india_listing"]
