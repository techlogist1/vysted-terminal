"""Locale primitives for region-native, correctness-gated data (Pass B / Pillar A).

Constitution VIII ("Locale-Native & Correct, Everywhere"): the active region
shapes ticker/exchange resolution, currency, market-hours-aware freshness, and
default sources. This module is the small, dependency-light home for the shared
locale facts the provider registry, the correctness gate, the India provider,
and the news/macro handlers all read:

  * :func:`region_currency` — the display currency per region (INR for IN).
  * :func:`region_for_suffix` — a ``.NS`` / ``.BO`` ticker is intrinsically Indian.
  * :func:`market_timezone` / :func:`market_session` — IST vs ET session context.
  * :func:`most_recent_session` / :func:`is_market_open` — an exchange-calendar
    aware "what is the latest trading day?" used by the staleness gate (FR-063)
    so a weekend/holiday close is not mistaken for stale data.
  * :func:`freshness_for` — labels a value ``live`` / ``eod`` / ``stale`` with an
    ``as_of`` date, so the frontend can badge it (FR-041/065) — never showing a
    cache/EOD value as live.

The trading-holiday tables are a *best-effort* bundled snapshot (NSE + US, the
current window). They make the staleness check calendar-aware; getting one
holiday wrong only shifts the "most recent session" by a day, and the staleness
tolerance is deliberately generous (EOD data is inherently T+1), so the tables
never need to be exhaustive to be safe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# --- Region constants -------------------------------------------------------

REGION_US = "US"
REGION_IN = "IN"
REGION_GLOBAL = "GLOBAL"

_CURRENCY_BY_REGION = {REGION_US: "USD", REGION_IN: "INR", REGION_GLOBAL: "USD"}

# Yahoo-style exchange suffixes that pin a symbol to a region regardless of the
# user's active locale (an ``.NS`` ticker is an NSE instrument anywhere).
_SUFFIX_REGION = {".NS": REGION_IN, ".BO": REGION_IN}

_TZ_BY_REGION = {
    REGION_US: ZoneInfo("America/New_York"),
    REGION_IN: ZoneInfo("Asia/Kolkata"),
    REGION_GLOBAL: ZoneInfo("America/New_York"),
}

# Regular cash-session open/close in each region's local time.
_SESSION_BY_REGION = {
    REGION_US: (time(9, 30), time(16, 0)),
    REGION_IN: (time(9, 15), time(15, 30)),
    REGION_GLOBAL: (time(9, 30), time(16, 0)),
}

# Best-effort bundled market-holiday snapshot (NSE + NYSE). Covers the active
# window; the staleness gate's tolerance makes exhaustiveness unnecessary.
_NSE_HOLIDAYS: frozenset[str] = frozenset(
    {
        # 2025
        "2025-02-26",
        "2025-03-14",
        "2025-03-31",
        "2025-04-10",
        "2025-04-14",
        "2025-04-18",
        "2025-05-01",
        "2025-08-15",
        "2025-08-27",
        "2025-10-02",
        "2025-10-21",
        "2025-10-22",
        "2025-11-05",
        "2025-12-25",
        # 2026 (major NSE trading holidays — best effort)
        "2026-01-26",
        "2026-02-15",
        "2026-03-04",
        "2026-03-21",
        "2026-03-31",
        "2026-04-01",
        "2026-04-03",
        "2026-04-14",
        "2026-05-01",
        "2026-08-15",
        "2026-08-28",
        "2026-10-02",
        "2026-10-20",
        "2026-11-09",
        "2026-11-24",
        "2026-12-25",
    }
)
_US_HOLIDAYS: frozenset[str] = frozenset(
    {
        # 2025
        "2025-01-01",
        "2025-01-20",
        "2025-02-17",
        "2025-04-18",
        "2025-05-26",
        "2025-06-19",
        "2025-07-04",
        "2025-09-01",
        "2025-11-27",
        "2025-12-25",
        # 2026
        "2026-01-01",
        "2026-01-19",
        "2026-02-16",
        "2026-04-03",
        "2026-05-25",
        "2026-06-19",
        "2026-07-03",
        "2026-09-07",
        "2026-11-26",
        "2026-12-25",
    }
)
_HOLIDAYS_BY_REGION = {REGION_US: _US_HOLIDAYS, REGION_IN: _NSE_HOLIDAYS}

# How many *trading sessions* an EOD value may lag the most-recent expected
# session before it is treated as a broken feed (rejected) rather than normal
# T+1 EOD. Trading-session counting (not calendar days) keeps a holiday cluster
# — Diwali week, a long weekend — from falsely rejecting fresh-as-possible data.
_STALE_REJECT_SESSIONS = 3


def region_currency(region: str) -> str:
    """Return the ISO-4217 display currency for ``region`` (default USD)."""
    return _CURRENCY_BY_REGION.get(region, "USD")


def region_for_suffix(symbol: str) -> str | None:
    """Return the region a Yahoo-style exchange suffix pins ``symbol`` to.

    ``RELIANCE.NS`` / ``TATASTEEL.BO`` → ``IN``; an un-suffixed ticker → ``None``
    (the caller decides via the user's locale or a master lookup).
    """
    upper = symbol.strip().upper()
    for suffix, region in _SUFFIX_REGION.items():
        if upper.endswith(suffix):
            return region
    return None


def strip_exchange_suffix(symbol: str) -> str:
    """Strip a ``.NS`` / ``.BO`` suffix → the bare exchange symbol (``GOLDBEES``)."""
    upper = symbol.strip().upper()
    for suffix in _SUFFIX_REGION:
        if upper.endswith(suffix):
            return upper[: -len(suffix)]
    return upper


def market_timezone(region: str) -> ZoneInfo:
    """Return the exchange timezone for ``region`` (IST for IN, ET for US)."""
    return _TZ_BY_REGION.get(region, _TZ_BY_REGION[REGION_US])


def market_session(region: str) -> tuple[time, time]:
    """Return the (open, close) local session times for ``region``."""
    return _SESSION_BY_REGION.get(region, _SESSION_BY_REGION[REGION_US])


def _is_trading_day(day: date, region: str) -> bool:
    if day.weekday() >= 5:  # Saturday / Sunday
        return False
    return day.isoformat() not in _HOLIDAYS_BY_REGION.get(region, frozenset())


def most_recent_session(region: str, now: datetime | None = None) -> date:
    """Return the most recent completed-or-current trading day for ``region``.

    Walks back from "today in the exchange timezone" over weekends + bundled
    holidays. Used by the staleness gate so a Friday close read on a Sunday is
    not flagged stale.
    """
    tz = market_timezone(region)
    local_now = (now or datetime.now(tz=UTC)).astimezone(tz)
    day = local_now.date()
    for _ in range(15):  # at most ~2 weeks of weekend+holiday run
        if _is_trading_day(day, region):
            return day
        day -= timedelta(days=1)
    return day


def trading_sessions_between(earlier: date, later: date, region: str) -> int:
    """Count trading sessions strictly after ``earlier`` up to and incl. ``later``.

    ``0`` when ``earlier >= later``. Used by the staleness gate so "how far behind
    is this value" is measured in market sessions, not calendar days.
    """
    if earlier >= later:
        return 0
    count = 0
    day = earlier + timedelta(days=1)
    while day <= later:
        if _is_trading_day(day, region):
            count += 1
        day += timedelta(days=1)
    return count


def is_market_open(region: str, now: datetime | None = None) -> bool:
    """True if ``region``'s cash session is currently open."""
    tz = market_timezone(region)
    local_now = (now or datetime.now(tz=UTC)).astimezone(tz)
    if not _is_trading_day(local_now.date(), region):
        return False
    open_t, close_t = market_session(region)
    return open_t <= local_now.time() <= close_t


@dataclass(frozen=True)
class Freshness:
    """How fresh a served value is, for provenance/staleness badging (FR-041)."""

    state: str  # "live" | "eod" | "stale"
    as_of: date | None
    is_stale: bool
    note: str


def freshness_for(
    region: str,
    as_of: date | None,
    *,
    intraday: bool,
    now: datetime | None = None,
) -> Freshness:
    """Classify a value's freshness against ``region``'s trading calendar.

    ``intraday`` data taken while the market is open is ``live``; otherwise a
    value dated to the most-recent session is ``eod`` (normal T+1), and anything
    older than that by more than the tolerance is ``stale``.
    """
    recent = most_recent_session(region, now)
    if as_of is None:
        return Freshness("eod", None, True, "no timestamp on the served value")
    if intraday and is_market_open(region, now) and as_of >= recent:
        return Freshness("live", as_of, False, "intraday, market open")
    lag_sessions = trading_sessions_between(as_of, recent, region)
    if lag_sessions > _STALE_REJECT_SESSIONS:
        return Freshness(
            "stale",
            as_of,
            True,
            f"value dated {as_of.isoformat()} is {lag_sessions} sessions behind the "
            f"last {region} session ({recent.isoformat()})",
        )
    return Freshness("eod", as_of, as_of < recent, f"end-of-day close for {as_of.isoformat()}")


def is_rejectably_stale(region: str, as_of: date | None, now: datetime | None = None) -> bool:
    """True if ``as_of`` is so far behind the last session it should be rejected.

    ``None`` (no timestamp) is NOT rejectable here — the correctness gate handles
    missing-field rejection separately; this is purely the calendar-aware
    "the feed is clearly broken" check (FR-063).
    """
    if as_of is None:
        return False
    recent = most_recent_session(region, now)
    return trading_sessions_between(as_of, recent, region) > _STALE_REJECT_SESSIONS
