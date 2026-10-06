"""Declared-but-unpaid dividend detection (R13 / D57).

The R13 probe found Yahoo's trailing dividend scalars can ANTICIPATE a dividend
that is declared but whose record date is still in the FUTURE: PFC's
``trailingAnnualDividendRate`` (18.55) = the trailing-12m PAID history (14.60) +
a declared FINAL dividend of ₹3.95 whose record date is 2026-07-31. The repo
maps ``dividend_per_share`` = Yahoo ``dividendRate``; whenever a scalar (or the
paid history) is stated without separating the declared-not-yet-paid leg,
"paid" and "declared" collapse into one number and the D56 note mis-attributes
the gap.

:func:`get_declared_unpaid_dividend` reads the merged NSE+BSE corporate-actions
lane (:func:`services.corporate_disclosures.get_corporate_actions`, so a
BSE-only name is covered too; R15-DATA-025) and returns the NEAREST dividend
whose record/ex date is still in the future — the amount + record date the
derived semantics leg surfaces as a SEPARATE "declared, not yet paid" fact.
It NEVER raises into research: any failure becomes ``None`` (absence is honest),
and a detected block is reported to the shared EXCHANGE circuit breaker
(mirroring :mod:`services.ownership_check`)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any

from models.announcements import CorporateAction
from services import corporate_disclosures, locale, provider_health, symbol_resolver
from services.errors import ProviderError
from services.ownership_check import EXCHANGE
from services.witness import is_block_error, is_india_listing

logger = logging.getLogger(__name__)

#: The fundamentals-leg key the snapshot builder attaches this result under, and
#: that :func:`services.research.semantics.derive_semantics` reads.
DECLARED_KEY = "dividend_declared"


@dataclass(frozen=True)
class DeclaredDividend:
    """A declared dividend whose record date is still in the future.

    ``amount`` is per share (listing currency); ``record_date`` is the ISO
    record/ex date; ``subject`` is the verbatim corporate-action line, so a
    downstream note can quote the exact declaration.
    """

    amount: float
    record_date: str
    subject: str

    def as_wire(self) -> dict[str, Any]:
        """The plain dict attached under :data:`DECLARED_KEY`."""
        return asdict(self)


def is_applicable(symbol: str) -> bool:
    """True when ``symbol`` is an NSE or BSE listing (the corporate-actions lane
    merges both exchanges).

    Decided on the resolved listing (``.NS``/``.BO``, via
    :func:`services.witness.is_india_listing`) whose bare ticker is in an India
    master — never on bare-ticker membership alone, so a US-bound listing is
    skipped without a network call.
    """
    if not is_india_listing(symbol):
        return False
    bare = locale.strip_exchange_suffix(symbol)
    return symbol_resolver.is_nse_symbol(bare) or symbol_resolver.is_bse_symbol(bare)


def _ist_today() -> date:
    return datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()


def _select_declared(actions: list[CorporateAction], today: date) -> DeclaredDividend | None:
    """The nearest dividend whose record/ex date is still in the future."""
    candidates: list[DeclaredDividend] = []
    for action in actions:
        if action.kind != "dividend" or action.amount_per_share is None:
            continue
        record = action.record_date or action.ex_date
        if record is None or record <= today:
            continue  # already ex-date / paid, or undated — not declared-unpaid
        candidates.append(
            DeclaredDividend(
                amount=action.amount_per_share,
                record_date=record.isoformat(),
                subject=action.purpose,
            )
        )
    if not candidates:
        return None
    # The nearest upcoming record date is the next dividend to go ex.
    return min(candidates, key=lambda d: d.record_date)


def _fetch(symbol: str) -> tuple[DeclaredDividend | None, bool]:
    """The declared-unpaid dividend plus whether an exchange lane was blocked
    while the other served (BLOCKING; runs under ``to_thread``)."""
    response = corporate_disclosures.get_corporate_actions(symbol)
    blocked = any(is_block_error(ProviderError(msg)) for msg in response.errors.values())
    return _select_declared(response.actions, _ist_today()), blocked


async def get_declared_unpaid_dividend(symbol: str) -> DeclaredDividend | None:
    """The nearest declared-but-unpaid dividend for ``symbol``, or ``None``.

    ``None`` when the listing is not an NSE/BSE name, the exchange circuit is
    open, the feed is unreachable, or no future-record dividend is declared —
    never raises into the research snapshot.
    """
    if not is_applicable(symbol):
        return None
    if provider_health.is_open(EXCHANGE):
        return None  # circuit open — serve no exchange facts this round (D52)
    try:
        result, blocked = await asyncio.to_thread(_fetch, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if is_block_error(exc):
            provider_health.record_rate_limited(EXCHANGE)
        else:
            logger.debug("declared-dividend lane unavailable for %s: %s", symbol, exc)
        return None
    if blocked:
        provider_health.record_rate_limited(EXCHANGE)
    else:
        provider_health.record_success(EXCHANGE)
    return result


__all__ = [
    "DECLARED_KEY",
    "DeclaredDividend",
    "get_declared_unpaid_dividend",
    "is_applicable",
]
