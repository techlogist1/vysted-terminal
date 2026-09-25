"""Earnings calendar + estimates + surprises provider — Phase 6 (Teammate E).

Public surface
~~~~~~~~~~~~~~

* :func:`get_upcoming(start, end, watchlist)` — :class:`EarningsEvent` list
  filtered to the date window, optionally restricted to a watchlist of
  symbols.
* :func:`get_history(symbol)` — :class:`EarningsHistoryResponse` of past
  reported quarters with actual vs. consensus.
* :func:`get_surprises(symbol)` — :class:`EarningsSurprisesResponse` —
  the analyst-mean diff against the actual report for each past quarter.
* :func:`get_estimate_detail(symbol)` — :class:`EarningsEstimateDetail`
  for the *next* upcoming report — mean / high / low / analyst counts (median
  and stddev only when the provider supplies them; yfinance does not).

Data sources
~~~~~~~~~~~~

Baseline coverage is via ``yfinance``'s ``Ticker.calendar``,
``Ticker.earnings_dates``, ``Ticker.earnings_history`` and
``Ticker.earnings_estimate`` accessors. Where openbb-mcp is bundled and
exposes an ``equity_calendar_earnings`` tool we layer richer consensus +
dispersion onto the events; missing-tool fallback is silent.

Caching
~~~~~~~

Routes read through :mod:`services.data_cache` with keys
``earnings:upcoming:<start>:<end>:<watchlist>`` (TTL 6 hours) and
``earnings:<symbol>:history`` / ``earnings:<symbol>:surprises`` /
``earnings:<symbol>:estimates`` (TTL 24 hours).

The provider returns pure dataclasses; cache (de)serialisation happens
in the router layer so the provider stays straight-forward to test.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd

from config import get_region
from models.earnings import (
    EarningsEstimateDetail,
    EarningsEvent,
    EarningsHistoryEntry,
    EarningsHistoryResponse,
    EarningsSurprise,
    EarningsSurprisesResponse,
    EarningsUpcomingResponse,
)
from services.errors import ProviderError
from services.nse_provider import _EVENT_CALENDAR_PATH, _get_json
from services.yfinance_provider import _yahoo_symbol

logger = logging.getLogger(__name__)

PROVIDER = "yfinance"

# Default US universe used when no watchlist is supplied outside the IN
# region — small list, deterministic, large-cap so the upstream has data for
# them. An IN session reads NSE's market-wide event calendar instead.
_DEFAULT_UNIVERSE: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "META",
    "AMZN",
    "TSLA",
    "JPM",
    "V",
    "WMT",
)


def _num(value: Any) -> float | None:
    """Coerce a possibly-missing/NaN value to ``float | None``."""
    if value is None:
        return None
    try:
        if pd.isna(value):  # type: ignore[arg-type]
            return None
    except (TypeError, ValueError):
        pass
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _revenue_currency(payload: dict[str, Any]) -> str:
    """Yahoo reports statement-size revenue fields in the filer's reporting
    currency (``financialCurrency``), which for a foreign reporter (WIT: ADS
    trades in USD, reports in INR) differs from the trading ``currency`` every
    other money field on the payload carries. Falls back to ``currency`` when
    ``financialCurrency`` is absent — never a bare 'USD' default hiding a
    missing field (R15-DATA-113)."""
    return str(payload.get("financial_currency") or payload.get("currency") or "USD")


def _analyst_count(frame: Any) -> int | None:
    """The current-quarter ``numberOfAnalysts`` of a yfinance estimate frame
    (``earnings_estimate`` / ``revenue_estimate``), or ``None`` when absent —
    never a borrowed count or a 0 standing in for "unknown" (R15-DATA-032)."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    count = _num(frame.iloc[0].get("numberOfAnalysts"))
    return int(count) if count is not None else None


def _surprise_pct(actual: float, estimate: float) -> float | None:
    """Return ``(actual - estimate) / |estimate|`` or None on divide-by-zero."""
    if estimate == 0:
        return None
    return (actual - estimate) / abs(estimate)


# ---------------------------------------------------------------------------
# Sync yfinance accessors (run on a worker thread by the async public API).
# ---------------------------------------------------------------------------


def _yf_ticker(symbol: str) -> Any:
    """Construct a yfinance ``Ticker`` instance — split out so tests can patch."""
    import yfinance as yf

    return yf.Ticker(symbol)


def _fetch_calendar_sync(symbol: str) -> dict[str, Any]:
    """Return a dict of the yfinance calendar (dates + estimates).

    yfinance exposes ``Ticker.calendar`` (a dict with ``"Earnings Date"`` and
    ``"Earnings Average"`` keys) plus ``Ticker.earnings_dates`` (a DataFrame
    indexed by report date with columns ``EPS Estimate`` / ``Reported EPS`` /
    ``Surprise(%)``). We pull both and let the caller merge. ``symbol`` is
    resolved once here, region-aware (``_yahoo_symbol``), and echoed back.
    """
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = _yf_ticker(normalized)
        calendar = getattr(ticker, "calendar", None) or {}
        try:
            earnings_dates = ticker.earnings_dates
        except Exception:  # noqa: BLE001 — optional accessor
            earnings_dates = None
        try:
            info = ticker.info or {}
        except Exception:  # noqa: BLE001
            info = {}
        try:
            est_frame = ticker.earnings_estimate
        except Exception:  # noqa: BLE001
            est_frame = None
        try:
            rev_frame = ticker.revenue_estimate
        except Exception:  # noqa: BLE001
            rev_frame = None
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance earnings calendar failed for {symbol!r}: {exc}") from exc

    return {
        "symbol": normalized,
        "calendar": calendar,
        "earnings_dates": earnings_dates,
        "earnings_estimate": est_frame,
        "revenue_estimate": rev_frame,
        "currency": info.get("currency") or "USD",
        "financial_currency": info.get("financialCurrency"),
        "name": info.get("longName") or info.get("shortName"),
    }


def _fetch_history_sync(symbol: str) -> dict[str, Any]:
    """Return the yfinance earnings_history DataFrame for ``symbol`` (resolved
    here), plus ``Ticker.earnings_dates`` (R15-LEAD-016) — the announcement
    dates used to resolve each entry's true ``reported_date``, distinct from
    ``period_end``."""
    normalized = _yahoo_symbol(symbol)
    try:
        ticker = _yf_ticker(normalized)
        try:
            history = ticker.earnings_history
        except Exception:  # noqa: BLE001
            history = None
        try:
            earnings_dates = ticker.earnings_dates
        except Exception:  # noqa: BLE001
            earnings_dates = None
        try:
            info = ticker.info or {}
        except Exception:  # noqa: BLE001
            info = {}
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance earnings history failed for {symbol!r}: {exc}") from exc
    return {
        "symbol": normalized,
        "history": history,
        "earnings_dates": earnings_dates,
        "currency": info.get("currency") or "USD",
        "financial_currency": info.get("financialCurrency"),
    }


def _as_date(value: Any) -> date | None:
    """Best-effort coercion of a pandas index label / cell to a plain ``date``."""
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return None


def _extract_announcement_dates(frame: Any) -> list[date]:
    """Every ALREADY-REPORTED announcement date in a ``Ticker.earnings_dates``
    frame (R15-LEAD-016) — a future scheduled event (``Reported EPS`` still
    ``NaN``) is not an announcement yet, so it is excluded; a frame that lacks
    the column (schema drift) is read unfiltered rather than dropped whole.
    Best-effort: an unreadable/empty frame yields ``[]``, never a crash."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    if "Reported EPS" in frame.columns:
        frame = frame[frame["Reported EPS"].notna()]
    dates: list[date] = []
    for idx in frame.index:
        parsed = _as_date(idx)
        if parsed is not None:
            dates.append(parsed)
    return dates


def _nearest_reported_date(period_end: date, announcement_dates: list[date]) -> date | None:
    """The earliest announcement date 0-120 days after ``period_end`` — the
    quarter's actual report date, never the quarter end itself (R15-LEAD-016).
    ``None`` when no announcement date falls in that window."""
    candidates = [d for d in announcement_dates if 0 <= (d - period_end).days <= 120]
    return min(candidates) if candidates else None


# ---------------------------------------------------------------------------
# Calendar event construction
# ---------------------------------------------------------------------------


def _event_from_calendar(
    payload: dict[str, Any], start_date: date, end_date: date
) -> EarningsEvent | None:
    """Construct an :class:`EarningsEvent` from a yfinance calendar payload.

    Returns ``None`` when the calendar has no future earnings date or the
    date falls outside the requested window. ``calendar["Earnings Date"]``
    is a list of ``date`` objects; the first entry is the next reporting
    date.
    """
    cal = payload.get("calendar") or {}
    earnings_dates = cal.get("Earnings Date") or []
    if not isinstance(earnings_dates, (list, tuple)) or not earnings_dates:
        return None
    raw = earnings_dates[0]
    scheduled: date
    if isinstance(raw, datetime):
        scheduled = raw.date()
    elif isinstance(raw, date):
        scheduled = raw
    else:
        try:
            scheduled = datetime.fromisoformat(str(raw)).date()
        except ValueError:
            return None

    if scheduled < start_date or scheduled > end_date:
        return None

    # R15-DATA-032: yfinance surfaces no dispersion, so ``eps_estimate_stddev``
    # stays None (the field is for a provider that measures it).
    return EarningsEvent(
        symbol=payload["symbol"],
        company_name=payload.get("name"),
        scheduled_date=scheduled,
        time_of_day="unknown",
        # R15-DATA-067: yfinance names no fiscal period; the report month does
        # not determine one (JPM's October report is its Q3), so none is stamped.
        eps_estimate_mean=_num(cal.get("Earnings Average")),
        estimate_analyst_count=_analyst_count(payload.get("earnings_estimate")),
        currency=str(payload.get("currency") or "USD"),
        provider=PROVIDER,
    )


# ---------------------------------------------------------------------------
# NSE market-wide event calendar (the IN default universe, R15-DATA-028)
# ---------------------------------------------------------------------------

_NSE_EVENT_CALENDAR_REFERER = (
    "https://www.nseindia.com/companies-listing/corporate-filings-event-calendar"
)


def _nse_results_events(start_date: date, end_date: date) -> list[EarningsEvent]:
    """Every NSE board meeting in ``[start, end]`` whose purpose is results.

    The feed is market-wide (no ``symbol`` param), so it answers "which Indian
    companies report this week" — a board meeting for a dividend, split or
    fund raise is not a results event and is excluded. The feed carries no
    consensus, so the estimate fields stay None."""
    params = {
        "index": "equities",
        "from_date": start_date.strftime("%d-%m-%Y"),
        "to_date": end_date.strftime("%d-%m-%Y"),
    }
    payload = _get_json(_EVENT_CALENDAR_PATH, params, _NSE_EVENT_CALENDAR_REFERER)
    if not isinstance(payload, list):
        raise ProviderError("nse event calendar: malformed payload")
    events: list[EarningsEvent] = []
    for row in payload:
        if not isinstance(row, dict) or "results" not in str(row.get("purpose") or "").lower():
            continue
        symbol = str(row.get("symbol") or "").strip()
        try:
            scheduled = datetime.strptime(str(row.get("date")), "%d-%b-%Y").date()
        except ValueError:
            continue
        if not symbol or not start_date <= scheduled <= end_date:
            continue
        events.append(
            EarningsEvent(
                symbol=f"{symbol}.NS",
                company_name=row.get("company") or None,
                scheduled_date=scheduled,
                time_of_day="unknown",
                currency="INR",
                provider="nse",
            )
        )
    return events


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def get_upcoming(
    start: date | None = None,
    end: date | None = None,
    watchlist: list[str] | None = None,
) -> EarningsUpcomingResponse:
    """Return scheduled earnings events in ``[start, end]`` for ``watchlist``.

    Defaults: ``start`` = today, ``end`` = today + 7 days. With no
    ``watchlist`` an IN session reads NSE's market-wide event calendar (every
    results board meeting in the window); any other region uses a small
    built-in universe of US large-caps so the panel populates.
    """
    today = datetime.now(tz=UTC).date()
    start_date = start or today
    end_date = end or (today + timedelta(days=7))
    if start_date > end_date:
        raise ProviderError("start_date must be on or before end_date")
    if not watchlist and get_region() == "IN":
        events_in = await asyncio.to_thread(_nse_results_events, start_date, end_date)
        events_in.sort(key=lambda event: (event.scheduled_date, event.symbol))
        return EarningsUpcomingResponse(start_date=start_date, end_date=end_date, events=events_in)
    universe = list(watchlist) if watchlist else list(_DEFAULT_UNIVERSE)

    async def _one(symbol: str) -> EarningsEvent | None:
        try:
            payload = await asyncio.to_thread(_fetch_calendar_sync, symbol)
        except ProviderError as exc:
            # Was a silent drop; log it like the _event_from_calendar path so a
            # symbol vanishing from the calendar is traceable (Phase 9.5).
            logger.warning("earnings: calendar fetch failed for %r: %s", symbol, exc)
            return None
        try:
            return _event_from_calendar(payload, start_date, end_date)
        except Exception:  # noqa: BLE001 — log and continue past one bad symbol
            logger.warning("earnings: failed to build event for %r", symbol, exc_info=True)
            return None

    events_raw = await asyncio.gather(*(_one(sym) for sym in universe))
    events = [event for event in events_raw if event is not None]
    events.sort(key=lambda event: (event.scheduled_date, event.symbol))
    return EarningsUpcomingResponse(
        start_date=start_date,
        end_date=end_date,
        events=events,
    )


async def get_history(symbol: str) -> EarningsHistoryResponse:
    """Return the historical earnings results for ``symbol``.

    ``period_end`` is the fiscal quarter end (the ``earnings_history`` index)
    and the sort key. ``reported_date`` is the ACTUAL announcement date — the
    nearest ``Ticker.earnings_dates`` entry 0-120 days after ``period_end``, or
    ``None`` when none is found in that window (R15-LEAD-016: the OLD code
    reported ``period_end`` itself as ``reported_date``, which is wrong
    whenever a company reports weeks after its quarter closes)."""
    payload = await asyncio.to_thread(_fetch_history_sync, symbol)
    normalized = payload["symbol"]
    history_frame = payload.get("history")
    currency = str(payload.get("currency") or "USD")
    revenue_currency = _revenue_currency(payload)
    announcement_dates = _extract_announcement_dates(payload.get("earnings_dates"))
    entries: list[EarningsHistoryEntry] = []
    if isinstance(history_frame, pd.DataFrame) and not history_frame.empty:
        for raw_idx, row in history_frame.iterrows():
            period_end = _as_date(raw_idx)
            if period_end is None:
                continue
            eps_actual = _num(row.get("epsActual"))
            if eps_actual is None:
                continue
            eps_estimate = _num(row.get("epsEstimate"))
            entries.append(
                EarningsHistoryEntry(
                    period_end=period_end,
                    reported_date=_nearest_reported_date(period_end, announcement_dates),
                    eps_actual=eps_actual,
                    eps_estimate_mean=eps_estimate,
                    revenue_actual=_num(row.get("revenueActual")),
                    revenue_estimate_mean=_num(row.get("revenueEstimate")),
                    currency=currency,
                    revenue_currency=revenue_currency,
                )
            )
    entries.sort(key=lambda entry: entry.period_end, reverse=True)
    return EarningsHistoryResponse(symbol=normalized, history=entries)


async def get_surprises(symbol: str) -> EarningsSurprisesResponse:
    """Return per-quarter surprises (actual vs. consensus) for ``symbol``."""
    history = await get_history(symbol)
    normalized = history.symbol
    surprises: list[EarningsSurprise] = []
    for entry in history.history:
        estimate = entry.eps_estimate_mean
        if estimate is None:
            # Without a pre-report consensus there is no surprise to score.
            continue
        surprise = entry.eps_actual - estimate
        revenue_estimate = entry.revenue_estimate_mean
        revenue_actual = entry.revenue_actual
        revenue_pct: float | None = None
        if revenue_estimate is not None and revenue_actual is not None and revenue_estimate != 0:
            revenue_pct = (revenue_actual - revenue_estimate) / abs(revenue_estimate)
        surprises.append(
            EarningsSurprise(
                symbol=normalized,
                period_end=entry.period_end,
                reported_date=entry.reported_date,
                fiscal_period=entry.fiscal_period,
                eps_actual=entry.eps_actual,
                eps_estimate_mean=estimate,
                eps_surprise=surprise,
                eps_surprise_pct=_surprise_pct(entry.eps_actual, estimate),
                revenue_actual=revenue_actual,
                revenue_estimate_mean=revenue_estimate,
                revenue_surprise_pct=revenue_pct,
                currency=entry.currency,
                revenue_currency=entry.revenue_currency,
                provider=PROVIDER,
            )
        )
    return EarningsSurprisesResponse(symbol=normalized, surprises=surprises)


async def get_estimate_detail(symbol: str) -> EarningsEstimateDetail:
    """Return the analyst estimate breakdown for the next earnings event."""
    payload = await asyncio.to_thread(_fetch_calendar_sync, symbol)
    normalized = payload["symbol"]
    cal = payload.get("calendar") or {}
    earnings_dates = cal.get("Earnings Date") or []
    if not earnings_dates:
        raise ProviderError(f"no upcoming earnings event found for {symbol!r}")
    raw = earnings_dates[0]
    if not isinstance(raw, date):
        try:
            datetime.fromisoformat(str(raw))
        except (TypeError, ValueError) as exc:
            raise ProviderError(f"could not parse earnings date {raw!r} for {symbol!r}") from exc

    eps_mean = _num(cal.get("Earnings Average"))
    eps_high = _num(cal.get("Earnings High"))
    eps_low = _num(cal.get("Earnings Low"))
    if eps_mean is None or eps_high is None or eps_low is None:
        raise ProviderError(f"incomplete estimate fields for {symbol!r}")

    rev_mean = _num(cal.get("Revenue Average"))
    rev_high = _num(cal.get("Revenue High"))
    rev_low = _num(cal.get("Revenue Low"))

    return EarningsEstimateDetail(
        symbol=normalized,
        # R15-DATA-032: yfinance surfaces no median or stddev — they stay None
        # rather than the mean / a (high-low)/4 proxy on a measured-value field.
        eps_estimate_mean=eps_mean,
        eps_estimate_high=eps_high,
        eps_estimate_low=eps_low,
        estimate_analyst_count=_analyst_count(payload.get("earnings_estimate")),
        revenue_estimate_mean=rev_mean,
        revenue_estimate_high=rev_high,
        revenue_estimate_low=rev_low,
        revenue_analyst_count=_analyst_count(payload.get("revenue_estimate")),
        currency=str(payload.get("currency") or "USD"),
        revenue_currency=_revenue_currency(payload),
        provider=PROVIDER,
        as_of=datetime.now(tz=UTC),
    )


__all__ = [
    "PROVIDER",
    "get_estimate_detail",
    "get_history",
    "get_surprises",
    "get_upcoming",
]
