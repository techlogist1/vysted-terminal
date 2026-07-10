"""Declared-but-unpaid dividend detection (R13 / D57).

The R13 probe found Yahoo's trailing dividend scalars can ANTICIPATE a dividend
that is declared but whose record date is still in the FUTURE: PFC's
``trailingAnnualDividendRate`` (18.55) = the trailing-12m PAID history (14.60) +
a declared FINAL dividend of ₹3.95 whose record date is 2026-07-31. The repo
maps ``dividend_per_share`` = Yahoo ``dividendRate``; whenever a scalar (or the
paid history) is stated without separating the declared-not-yet-paid leg,
"paid" and "declared" collapse into one number and the D56 note mis-attributes
the gap.

:func:`get_declared_unpaid_dividend` reads the NSE corporate-actions feed (via
:func:`services.nse_provider.get_corporate_actions`) and returns the NEAREST
dividend whose record/ex date is still in the future — the amount + record date
the derived semantics leg surfaces as a SEPARATE "declared, not yet paid" fact.
It NEVER raises into research: any failure becomes ``None`` (absence is honest),
and a detected block is reported to the shared EXCHANGE circuit breaker
(mirroring :mod:`services.ownership_check`)."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from typing import Any

from services import locale, nse_provider, provider_health, symbol_resolver
from services.ownership_check import EXCHANGE

logger = logging.getLogger(__name__)

#: The fundamentals-leg key the snapshot builder attaches this result under, and
#: that :func:`services.research.semantics.derive_semantics` reads.
DECLARED_KEY = "dividend_declared"

#: A corporate-action ``subject`` is a dividend when it names one (the feed also
#: carries bonuses / splits / rights we ignore for the dividend leg).
_DIVIDEND_SUBJECT_RE = re.compile(r"dividend", re.IGNORECASE)
#: The per-share amount inside a subject like "Dividend - Rs 3.95 Per Share".
_AMOUNT_RE = re.compile(r"(?:rs\.?|₹|inr)\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)


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
    """True when ``symbol`` is an NSE listing (the corporate-actions lane is NSE).

    A non-NSE ticker is skipped without a network call — the corporate-actions
    endpoint is NSE-only, so there is nothing to fetch.
    """
    if not isinstance(symbol, str) or not symbol:
        return False
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    return symbol_resolver.is_nse_symbol(bare)


def _is_blocked(exc: BaseException) -> bool:
    """True when ``exc`` looks like an exchange block/throttle (vs a plain miss)."""
    text = str(exc).lower()
    return "blocked" in text or any(code in text for code in ("http 401", "http 403", "http 429"))


def _parse_amount(subject: str) -> float | None:
    """The per-share amount in a dividend subject, or ``None``."""
    match = _AMOUNT_RE.search(subject)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _parse_action_date(raw: object) -> date | None:
    """A corporate-action date ("31-Jul-2026") → ``date``; ``None`` if unparseable."""
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or text == "-":
        return None
    try:
        return datetime.strptime(text, "%d-%b-%Y").date()  # %b is case-insensitive
    except ValueError:
        return None


def _ist_today() -> date:
    return datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()


def _select_declared(rows: list[dict], today: date) -> DeclaredDividend | None:
    """The nearest dividend whose record/ex date is still in the future."""
    candidates: list[DeclaredDividend] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        subject = row.get("subject")
        if not isinstance(subject, str) or not _DIVIDEND_SUBJECT_RE.search(subject):
            continue
        record = _parse_action_date(row.get("recDate")) or _parse_action_date(row.get("exDate"))
        if record is None or record <= today:
            continue  # already ex-date / paid, or undated — not declared-unpaid
        amount = _parse_amount(subject)
        if amount is None:
            continue
        candidates.append(
            DeclaredDividend(amount=amount, record_date=record.isoformat(), subject=subject.strip())
        )
    if not candidates:
        return None
    # The nearest upcoming record date is the next dividend to go ex.
    return min(candidates, key=lambda d: d.record_date)


def _fetch(symbol: str) -> DeclaredDividend | None:
    """The declared-unpaid dividend (BLOCKING; runs under ``to_thread``)."""
    rows = nse_provider.get_corporate_actions(symbol)
    return _select_declared(rows, _ist_today())


async def get_declared_unpaid_dividend(symbol: str) -> DeclaredDividend | None:
    """The nearest declared-but-unpaid dividend for ``symbol``, or ``None``.

    ``None`` when the listing is not an NSE name, the exchange circuit is open,
    the feed is unreachable, or no future-record dividend is declared — never
    raises into the research snapshot.
    """
    if not is_applicable(symbol):
        return None
    if provider_health.is_open(EXCHANGE):
        return None  # circuit open — serve no exchange facts this round (D52)
    try:
        result = await asyncio.to_thread(_fetch, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if _is_blocked(exc):
            provider_health.record_rate_limited(EXCHANGE)
        else:
            logger.debug("declared-dividend lane unavailable for %s: %s", symbol, exc)
        return None
    provider_health.record_success(EXCHANGE)
    return result


__all__ = [
    "DECLARED_KEY",
    "DeclaredDividend",
    "get_declared_unpaid_dividend",
    "is_applicable",
]
