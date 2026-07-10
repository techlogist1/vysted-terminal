"""Ownership cross-check — yfinance insider/institution % vs the exchange SHP
(R13 / D68).

D56 (dividend) and D66 (growth) taught the app to FLAG, never silently absorb,
two sources that disagree. This applies that discipline to OWNERSHIP. The R13
probe found yfinance's ``heldPercentInsiders``/``heldPercentInstitutions`` drift
materially from the exchange shareholding pattern:

  * institutions **~141x** overstated on a BSE micro-cap (yf 8.455% vs the BSE
    filing's 0.06%);
  * ``heldPercentInsiders`` overstates the NSE/BSE promoter-group percentage by
    3.5–5.4pp on several NSE names — **insiders ≠ promoter-group** by definition
    (yfinance's insider roster mixes promoter rows with UNREPORTED-position rows
    and carries individually-dated, off-cycle as-of dates the quarterly master
    does not).

:func:`get_exchange_ownership` fetches the LATEST exchange shareholding pattern
(the NSE quarterly master or the BSE SEBI XBRL, via
:func:`services.corporate_disclosures.get_shareholding`). It NEVER raises into
research: any failure becomes ``None`` (the caller then attaches no exchange
facts — absence is honest). A detected block is reported to a shared EXCHANGE
circuit breaker, mirroring :mod:`services.growth_check`'s Yahoo-family wiring.
The cross-check DISCLOSES, never substitutes: the provider values are left
untouched everywhere; a divergence surfaces as separately-labeled facts + a
conflict in the derived semantics leg
(:func:`services.research.semantics.derive_semantics`).

Wiring contract (mirrors D66)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The snapshot builder attaches this module's result onto the fundamentals leg's
``data`` dict under the key ``ownership_exchange`` — a plain dict
``{promoter_percent, institutions_percent, public_percent, as_of_quarter,
source}`` (percentages 0-100, ``as_of_quarter`` an ISO date). ``derive_semantics``
reads it alongside the provider's ``held_percent_insiders`` /
``held_percent_institutions`` fractions.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any

from services import locale, provider_health, symbol_resolver

logger = logging.getLogger(__name__)

#: The provider-health FAMILY for the NSE/BSE shareholding lanes. Distinct from
#: the Yahoo family (a different upstream / block semantics) — a Yahoo throttle
#: must not open the exchange circuit, and vice-versa.
EXCHANGE = "exchange"

#: The fundamentals-leg key the snapshot builder attaches this result under, and
#: that :func:`services.research.semantics.derive_semantics` reads.
OWNERSHIP_KEY = "ownership_exchange"


@dataclass(frozen=True)
class ExchangeOwnership:
    """The latest exchange shareholding pattern, as the cross-check needs it.

    Percentages are 0-100 (as the exchanges publish them); ``None`` when the
    filing did not carry that category — never fabricated. ``as_of_quarter`` is
    the ISO quarter-end date, and ``source`` is the serving lane ("NSE"/"BSE"),
    both carried into the conflict payload so a disagreement names its evidence.
    """

    promoter_percent: float | None
    institutions_percent: float | None
    public_percent: float | None
    as_of_quarter: str
    source: str

    def as_wire(self) -> dict[str, Any]:
        """The plain dict attached under :data:`OWNERSHIP_KEY`."""
        return asdict(self)


def should_cross_check(fund: dict[str, Any]) -> bool:
    """Whether the fundamentals payload carries an ownership scalar to reconcile.

    True only when the provider actually ships a numeric
    ``held_percent_insiders`` or ``held_percent_institutions`` — there is
    nothing to cross-check otherwise, and fetching the exchange filing would
    spend budget for no comparison.
    """
    return any(
        isinstance(fund.get(key), (int, float)) and not isinstance(fund.get(key), bool)
        for key in ("held_percent_insiders", "held_percent_institutions")
    )


def is_applicable(symbol: str) -> bool:
    """True when ``symbol`` is an Indian exchange listing (NSE or BSE).

    The exchange shareholding lane exists only for NSE/BSE names; a US/other
    listing has no such filing to compare against, so the cross-check is skipped
    without a network call.
    """
    if not isinstance(symbol, str) or not symbol:
        return False
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    return symbol_resolver.is_nse_symbol(bare) or symbol_resolver.is_bse_symbol(bare)


def _is_blocked(exc: BaseException) -> bool:
    """True when ``exc`` looks like an exchange block/throttle (vs a plain miss).

    Matched on the ProviderError text the NSE/BSE lanes raise ("blocked",
    "HTTP 401/403/429") — a block should open the circuit; a benign "no scrip
    code" / "no pattern" miss should not.
    """
    text = str(exc).lower()
    return "blocked" in text or any(code in text for code in ("http 401", "http 403", "http 429"))


def _fetch_latest(symbol: str) -> ExchangeOwnership | None:
    """The latest exchange shareholding pattern (BLOCKING; runs under to_thread)."""
    from services import corporate_disclosures

    response = corporate_disclosures.get_shareholding(symbol)
    if not response.patterns:
        return None
    latest = response.patterns[0]  # newest quarter first
    return ExchangeOwnership(
        promoter_percent=latest.promoter_percent,
        institutions_percent=latest.institutions_percent,
        public_percent=latest.public_percent,
        as_of_quarter=latest.quarter_end.isoformat(),
        source=latest.source or "exchange",
    )


async def get_exchange_ownership(symbol: str) -> ExchangeOwnership | None:
    """The latest exchange shareholding pattern for ``symbol``, or ``None``.

    ``None`` when the listing is not an Indian exchange name, the exchange
    circuit is open, the filing is unreachable, or no pattern is served — never
    raises into the research snapshot. ``symbol`` should be the listing the
    fundamentals leg resolved to (its exchange suffix is stripped internally).
    """
    if not is_applicable(symbol):
        return None
    if provider_health.is_open(EXCHANGE):
        return None  # circuit open — serve no exchange facts this round (D52)
    try:
        result = await asyncio.to_thread(_fetch_latest, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if _is_blocked(exc):
            provider_health.record_rate_limited(EXCHANGE)
        else:
            logger.debug("exchange ownership unavailable for %s: %s", symbol, exc)
        return None
    provider_health.record_success(EXCHANGE)
    return result


__all__ = [
    "EXCHANGE",
    "OWNERSHIP_KEY",
    "ExchangeOwnership",
    "get_exchange_ownership",
    "is_applicable",
    "should_cross_check",
]
