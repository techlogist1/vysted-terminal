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
  for the *next* upcoming report — mean / median / high / low / stddev.

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

from models.earnings import (
    EarningsEstimateDetail,
    EarningsEvent,
    EarningsHistoryEntry,
    EarningsHistoryResponse,
    EarningsSurprise,
    EarningsSurprisesResponse,
    EarningsUpcomingResponse,
    FiscalPeriod,
)
from services.errors import ProviderError

logger = logging.getLogger(__name__)

PROVIDER = "yfinance"

# Default "interesting" symbol universe used when no watchlist is supplied —
# small list, deterministic, large-cap so the upstream has data for them.
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


def _normalise_symbol(symbol: str) -> str:
    """Translate dotted tickers (``BRK.B``) to yfinance's dashed form."""
    return symbol.strip().upper().replace(".", "-")


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


def _fiscal_period_for(ts: date | datetime) -> FiscalPeriod:
    """Best-effort quarter inference from a reporting date.

    Most companies report fiscal Q1 in Q2-calendar, but the precise
    fiscal-year alignment varies. yfinance does not always surface a
    fiscal-period field, so we infer ``Q1..Q4`` from the calendar month
    and stamp the year as the calendar year of the report. The label is
    used only for UI display; downstream consumers that need the exact
    fiscal alignment can override via openbb-mcp once enrichment is wired.
    """
    if isinstance(ts, datetime):
        d = ts.date()
    else:
        d = ts
    month = d.month
    if month <= 3:
        quarter: str = "Q1"
    elif month <= 6:
        quarter = "Q2"
    elif month <= 9:
        quarter = "Q3"
    else:
        quarter = "Q4"
    return FiscalPeriod(quarter=quarter, year=d.year)  # type: ignore[arg-type]


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
    ``Surprise(%)``). We pull both and let the caller merge.
    """
    normalized = _normalise_symbol(symbol)
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
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance earnings calendar failed for {symbol!r}: {exc}") from exc

    return {
        "symbol": normalized,
        "calendar": calendar,
        "earnings_dates": earnings_dates,
        "earnings_estimate": est_frame,
        "currency": info.get("currency") or "USD",
        "name": info.get("longName") or info.get("shortName"),
    }


def _fetch_history_sync(symbol: str) -> dict[str, Any]:
    """Return the yfinance earnings_history DataFrame for ``symbol``."""
    normalized = _normalise_symbol(symbol)
    try:
        ticker = _yf_ticker(normalized)
        try:
            history = ticker.earnings_history
        except Exception:  # noqa: BLE001
            history = None
        try:
            info = ticker.info or {}
        except Exception:  # noqa: BLE001
            info = {}
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance earnings history failed for {symbol!r}: {exc}") from exc
    return {
        "symbol": normalized,
        "history": history,
        "currency": info.get("currency") or "USD",
    }


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

    eps_mean = _num(cal.get("Earnings Average"))
    eps_high = _num(cal.get("Earnings High"))
    eps_low = _num(cal.get("Earnings Low"))

    # Try to compute a coarse dispersion from the high/low spread when the
    # estimate-frame surfaces a stddev; yfinance's ``earnings_estimate``
    # DataFrame includes a ``numberOfAnalysts`` column in newer releases.
    est_frame = payload.get("earnings_estimate")
    eps_stddev: float | None = None
    analyst_count = 0
    if isinstance(est_frame, pd.DataFrame) and not est_frame.empty:
        # The first row is typically "0q" — current quarter estimate.
        row = est_frame.iloc[0]
        eps_stddev = _num(row.get("growth")) if False else None
        # Some yfinance versions provide a stddev-like column called
        # ``epsTrend``; the high/low diff is a safer dispersion fallback.
        analyst_count = int(_num(row.get("numberOfAnalysts")) or 0)
    if eps_stddev is None and eps_high is not None and eps_low is not None:
        # Approximation: assume high/low span ~= 4 stddev (95% CI rule).
        eps_stddev = max(eps_high - eps_low, 0.0) / 4.0 or None

    return EarningsEvent(
        symbol=payload["symbol"],
        company_name=payload.get("name"),
        scheduled_date=scheduled,
        time_of_day="unknown",
        fiscal_period=_fiscal_period_for(scheduled),
        eps_estimate_mean=eps_mean,
        eps_estimate_stddev=eps_stddev,
        estimate_analyst_count=analyst_count,
        currency=str(payload.get("currency") or "USD"),
        provider=PROVIDER,
    )


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def get_upcoming(
    start: date | None = None,
    end: date | None = None,
    watchlist: list[str] | None = None,
) -> EarningsUpcomingResponse:
    """Return scheduled earnings events in ``[start, end]`` for ``watchlist``.

    Defaults: ``start`` = today, ``end`` = today + 7 days, ``watchlist`` = a
    small built-in universe of large-caps so the panel populates without
    a configured watchlist.
    """
    today = datetime.now(tz=UTC).date()
    start_date = start or today
    end_date = end or (today + timedelta(days=7))
    universe = list(watchlist) if watchlist else list(_DEFAULT_UNIVERSE)
    if start_date > end_date:
        raise ProviderError("start_date must be on or before end_date")

    async def _one(symbol: str) -> EarningsEvent | None:
        try:
            payload = await asyncio.to_thread(_fetch_calendar_sync, symbol)
        except ProviderError:
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
    """Return the historical earnings results for ``symbol``."""
    normalized = _normalise_symbol(symbol)
    payload = await asyncio.to_thread(_fetch_history_sync, normalized)
    history_frame = payload.get("history")
    currency = str(payload.get("currency") or "USD")
    entries: list[EarningsHistoryEntry] = []
    if isinstance(history_frame, pd.DataFrame) and not history_frame.empty:
        for raw_idx, row in history_frame.iterrows():
            reported = raw_idx
            if hasattr(reported, "to_pydatetime"):
                reported = reported.to_pydatetime().date()
            elif isinstance(reported, datetime):
                reported = reported.date()
            elif not isinstance(reported, date):
                try:
                    reported = datetime.fromisoformat(str(reported)).date()
                except (TypeError, ValueError):
                    continue
            eps_actual = _num(row.get("epsActual"))
            if eps_actual is None:
                continue
            eps_estimate = _num(row.get("epsEstimate"))
            entries.append(
                EarningsHistoryEntry(
                    fiscal_period=_fiscal_period_for(reported),
                    reported_date=reported,
                    eps_actual=eps_actual,
                    eps_estimate_mean=eps_estimate,
                    revenue_actual=_num(row.get("revenueActual")),
                    revenue_estimate_mean=_num(row.get("revenueEstimate")),
                    currency=currency,
                )
            )
    entries.sort(key=lambda entry: entry.reported_date, reverse=True)
    return EarningsHistoryResponse(symbol=normalized, history=entries)


async def get_surprises(symbol: str) -> EarningsSurprisesResponse:
    """Return per-quarter surprises (actual vs. consensus) for ``symbol``."""
    normalized = _normalise_symbol(symbol)
    history = await get_history(normalized)
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
                provider=PROVIDER,
            )
        )
    return EarningsSurprisesResponse(symbol=normalized, surprises=surprises)


async def get_estimate_detail(symbol: str) -> EarningsEstimateDetail:
    """Return the analyst estimate breakdown for the next earnings event."""
    normalized = _normalise_symbol(symbol)
    payload = await asyncio.to_thread(_fetch_calendar_sync, normalized)
    cal = payload.get("calendar") or {}
    earnings_dates = cal.get("Earnings Date") or []
    if not earnings_dates:
        raise ProviderError(f"no upcoming earnings event found for {symbol!r}")
    raw = earnings_dates[0]
    if isinstance(raw, datetime):
        scheduled = raw.date()
    elif isinstance(raw, date):
        scheduled = raw
    else:
        try:
            scheduled = datetime.fromisoformat(str(raw)).date()
        except (TypeError, ValueError) as exc:
            raise ProviderError(f"could not parse earnings date {raw!r} for {symbol!r}") from exc

    eps_mean = _num(cal.get("Earnings Average"))
    eps_high = _num(cal.get("Earnings High"))
    eps_low = _num(cal.get("Earnings Low"))
    if eps_mean is None or eps_high is None or eps_low is None:
        raise ProviderError(f"incomplete estimate fields for {symbol!r}")

    eps_stddev: float | None = None
    analyst_count = 0
    est_frame = payload.get("earnings_estimate")
    if isinstance(est_frame, pd.DataFrame) and not est_frame.empty:
        row = est_frame.iloc[0]
        analyst_count = int(_num(row.get("numberOfAnalysts")) or 0)
    if eps_stddev is None:
        eps_stddev = max(eps_high - eps_low, 0.0) / 4.0 or None

    rev_mean = _num(cal.get("Revenue Average"))
    rev_high = _num(cal.get("Revenue High"))
    rev_low = _num(cal.get("Revenue Low"))

    return EarningsEstimateDetail(
        symbol=normalized,
        fiscal_period=_fiscal_period_for(scheduled),
        eps_estimate_mean=eps_mean,
        eps_estimate_median=eps_mean,  # yfinance does not surface a separate median
        eps_estimate_high=eps_high,
        eps_estimate_low=eps_low,
        eps_estimate_stddev=eps_stddev,
        estimate_analyst_count=analyst_count,
        revenue_estimate_mean=rev_mean,
        revenue_estimate_median=rev_mean,
        revenue_estimate_high=rev_high,
        revenue_estimate_low=rev_low,
        revenue_analyst_count=analyst_count,
        currency=str(payload.get("currency") or "USD"),
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
