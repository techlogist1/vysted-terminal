"""Market-cap share-count WITNESS from the app's own India masters (R13 / D72).

The derived semantics leg already flags a market cap that disagrees with
``price x shares_outstanding`` — but it uses the PROVIDER's OWN share count, so
the check is circular: if yfinance ships a stale share count, its market cap and
its ``price x shares`` agree with each other and nothing fires. The R13 battery
caught exactly this: RBA (Restaurant Brands Asia) shows a provider market cap of
~Rs 5,233 Cr vs the world's ~Rs 4,236 Cr (23% high) during live promoter-stake
churn (an open offer + sell-downs moving the float) — the provider's share count
lagged reality, so the internal check stayed silent.

This adds an INDEPENDENT witness: the app bundles a BSE-derived share count for
every BSE-listed name (``india_sector_map.json`` — ``shares_outstanding`` =
BSE ListOfScripData Mktcap / bhavcopy close, an offline exchange figure, NOT a
provider quote). Comparing the provider market cap against ``close x`` that
NON-provider share count breaks the circularity. D56/D66/D68 discipline again:
DISCLOSE, never substitute — the provider market cap is untouched; a divergence
surfaces as a conflict naming both figures and both share-count sources.

Applicability is gated to Indian names that carry a BSE-derived master share
count. The 135 NSE-only enrichment rows whose share count was backfilled from
yfinance (they have no BSE ``scrip_code``) are EXCLUDED — using them would
reintroduce the circularity this witness exists to break.

:func:`get_market_cap_witness` is the entry point. It reads the bundled master
only (no network), never raises into research (every failure becomes ``None``),
and runs the lookup under ``to_thread`` so the first 1 MB map parse never blocks
the event loop.

Wiring contract (mirrors D66)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The snapshot builder attaches this module's result onto the fundamentals leg's
``data`` dict under :data:`MCAP_WITNESS_KEY` — a plain dict
``{shares_outstanding, source, scrip_code}`` (an absolute share COUNT, not
crore/lakh). ``derive_semantics`` reads it alongside the provider ``market_cap``
and the price leg, and applies the divergence tolerance (which lives THERE).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any

from services import locale, symbol_resolver

logger = logging.getLogger(__name__)

#: The fundamentals-leg key the snapshot builder attaches this result under, and
#: that :func:`services.research.semantics.derive_semantics` reads.
MCAP_WITNESS_KEY = "market_cap_witness"

#: Human label for the witness share-count source, carried into the conflict
#: payload so a disagreement names its (non-provider) evidence.
_SOURCE = "BSE ListOfScripData (bundled India master)"


@dataclass(frozen=True)
class MarketCapWitness:
    """A NON-provider share count for an Indian listing, from the bundled master.

    ``shares_outstanding`` is an absolute share COUNT (not crore/lakh), derived
    offline from BSE ListOfScripData; ``scrip_code`` is the BSE code that
    guarantees the count is BSE-derived (an NSE-only enrichment row — yfinance
    share count — has no ``scrip_code`` and is excluded upstream). ``source`` is
    the human label carried into the conflict payload.
    """

    shares_outstanding: float
    source: str
    scrip_code: str

    def as_wire(self) -> dict[str, Any]:
        """The plain dict attached under :data:`MCAP_WITNESS_KEY`."""
        return asdict(self)


def should_cross_check(fund: dict[str, Any]) -> bool:
    """Whether the fundamentals payload carries a provider market cap to witness.

    True only when ``market_cap`` is a real number — there is nothing to witness
    otherwise.
    """
    value = fund.get("market_cap")
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_applicable(symbol: str) -> bool:
    """True when ``symbol`` is an Indian exchange listing (NSE or BSE).

    The bundled share-count master covers NSE/BSE names only; a US/other listing
    has no master share count to witness against.
    """
    if not isinstance(symbol, str) or not symbol:
        return False
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    return symbol_resolver.is_nse_symbol(bare) or symbol_resolver.is_bse_symbol(bare)


def _lookup(symbol: str) -> MarketCapWitness | None:
    """The bundled master share count for ``symbol`` (BLOCKING; under
    ``to_thread`` because the first call parses the ~1 MB map).

    Returns ``None`` unless the record carries BOTH a BSE ``scrip_code`` (so the
    count is BSE-derived, not a yfinance backfill) AND a positive
    ``shares_outstanding`` — absence is honest, and a yfinance-backfilled count
    is never used (that would reintroduce the circularity).
    """
    from services import screener_universe_india

    record = screener_universe_india.sector_seed_for(symbol)
    if not isinstance(record, dict):
        return None
    scrip_code = record.get("scrip_code")
    shares = record.get("shares_outstanding")
    if not scrip_code or not isinstance(scrip_code, str):
        return None  # NSE-only enrichment row → share count is a yfinance backfill
    if isinstance(shares, bool) or not isinstance(shares, (int, float)) or shares <= 0:
        return None
    return MarketCapWitness(
        shares_outstanding=float(shares),
        source=_SOURCE,
        scrip_code=scrip_code,
    )


async def get_market_cap_witness(symbol: str) -> MarketCapWitness | None:
    """A NON-provider share count for ``symbol``, or ``None``.

    ``None`` when the listing is not an Indian exchange name or the bundled
    master carries no BSE-derived share count for it — never raises into the
    research snapshot.
    """
    if not is_applicable(symbol):
        return None
    try:
        return await asyncio.to_thread(_lookup, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        logger.debug("market-cap witness unavailable for %s: %s", symbol, exc)
        return None


__all__ = [
    "MCAP_WITNESS_KEY",
    "MarketCapWitness",
    "get_market_cap_witness",
    "is_applicable",
    "should_cross_check",
]
