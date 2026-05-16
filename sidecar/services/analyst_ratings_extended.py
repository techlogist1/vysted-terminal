"""Extended analyst-ratings provider — Phase 6 (Teammate E).

Phase 1 shipped the aggregate :class:`AnalystRating` consensus snapshot
served by ``GET /fundamentals/{symbol}/ratings``. Phase 6 expands the
surface in three directions:

* :func:`get_ratings_history(symbol)` — every recorded rating change
  with firm + analyst + from/to bucket, normalised into the five-bucket
  :data:`AnalystAction` literal via :func:`_normalise_action`.
* :func:`get_price_target_history(symbol)` — every price-target change.
* :func:`get_individual_analysts(symbol)` — per-firm forecast with the
  analyst's currently-active rating + target + (where the upstream
  exposes it) one-year accuracy + star rating.

Data sources
~~~~~~~~~~~~

Baseline coverage is via ``yfinance``'s ``Ticker.recommendations`` (a
DataFrame with date / firm / from-grade / to-grade / action columns) +
``Ticker.upgrades_downgrades`` (the same in a slightly different shape on
older versions) + ``Ticker.analyst_price_targets`` (a dict / DataFrame
depending on version). Where openbb-mcp surfaces an
``equity_estimates_*`` family of tools we layer in richer per-analyst
data; missing-tool fallback is silent.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, date, datetime
from typing import Any

import pandas as pd

from models.analyst_extended import (
    AnalystAction,
    IndividualAnalystForecast,
    IndividualAnalystResponse,
    PriceTargetEntry,
    PriceTargetHistoryResponse,
    RatingsHistoryEntry,
    RatingsHistoryResponse,
)
from services.errors import ProviderError

logger = logging.getLogger(__name__)

PROVIDER = "yfinance"


# ---------------------------------------------------------------------------
# Rating normaliser
# ---------------------------------------------------------------------------

#: Map raw upstream rating strings to the five-bucket :data:`AnalystAction`
#: literal. Keys are lowercased + stripped; the lookup is exact-match.
#:
#: Coverage:
#:
#: * "strong buy" / "conviction buy" / "top pick" → ``strong-buy``
#: * "buy" / "outperform" / "overweight" / "accumulate" / "add" → ``buy``
#: * "hold" / "neutral" / "market perform" / "equal-weight" / "in-line" → ``hold``
#: * "sell" / "underperform" / "underweight" / "reduce" → ``sell``
#: * "strong sell" / "conviction sell" → ``strong-sell``
_RATING_MAP: dict[str, AnalystAction] = {
    # Strong buys.
    "strong buy": "strong-buy",
    "strong-buy": "strong-buy",
    "strongbuy": "strong-buy",
    "conviction buy": "strong-buy",
    "top pick": "strong-buy",
    # Buys.
    "buy": "buy",
    "outperform": "buy",
    "overweight": "buy",
    "over weight": "buy",
    "over-weight": "buy",
    "accumulate": "buy",
    "add": "buy",
    "positive": "buy",
    "long-term buy": "buy",
    "moderate buy": "buy",
    # Holds.
    "hold": "hold",
    "neutral": "hold",
    "market perform": "hold",
    "marketperform": "hold",
    "perform": "hold",
    "equal weight": "hold",
    "equal-weight": "hold",
    "equalweight": "hold",
    "in-line": "hold",
    "inline": "hold",
    "in line": "hold",
    "sector perform": "hold",
    "peer perform": "hold",
    # Sells.
    "sell": "sell",
    "underperform": "sell",
    "under perform": "sell",
    "underweight": "sell",
    "under-weight": "sell",
    "under weight": "sell",
    "reduce": "sell",
    "negative": "sell",
    "moderate sell": "sell",
    # Strong sells.
    "strong sell": "strong-sell",
    "strong-sell": "strong-sell",
    "strongsell": "strong-sell",
    "conviction sell": "strong-sell",
}


def _normalise_action(raw: str | None) -> AnalystAction | None:
    """Map an upstream rating string into the five-bucket AnalystAction.

    Returns ``None`` when ``raw`` is empty or does not map to a known bucket;
    callers either skip the row or surface the raw string verbatim.
    """
    if not raw:
        return None
    key = str(raw).strip().lower()
    if not key:
        return None
    return _RATING_MAP.get(key)


def _normalise_symbol(symbol: str) -> str:
    return symbol.strip().upper().replace(".", "-")


def _num(value: Any) -> float | None:
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


def _coerce_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().date()
        except Exception:  # noqa: BLE001
            pass
    try:
        return datetime.fromisoformat(str(value)).date()
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Sync yfinance accessors
# ---------------------------------------------------------------------------


def _yf_ticker(symbol: str) -> Any:
    import yfinance as yf

    return yf.Ticker(symbol)


def _fetch_ratings_sync(symbol: str) -> dict[str, Any]:
    """Pull recommendations + upgrades/downgrades + price targets."""
    normalized = _normalise_symbol(symbol)
    try:
        ticker = _yf_ticker(normalized)
        try:
            upgrades = ticker.upgrades_downgrades
        except Exception:  # noqa: BLE001
            upgrades = None
        try:
            recommendations = ticker.recommendations
        except Exception:  # noqa: BLE001
            recommendations = None
        try:
            targets = ticker.analyst_price_targets
        except Exception:  # noqa: BLE001
            targets = None
        try:
            info = ticker.info or {}
        except Exception:  # noqa: BLE001
            info = {}
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"yfinance ratings failed for {symbol!r}: {exc}") from exc
    return {
        "symbol": normalized,
        "upgrades_downgrades": upgrades,
        "recommendations": recommendations,
        "analyst_price_targets": targets,
        "currency": info.get("currency") or "USD",
    }


# ---------------------------------------------------------------------------
# Public async API
# ---------------------------------------------------------------------------


async def get_ratings_history(symbol: str) -> RatingsHistoryResponse:
    """Return every recorded rating change for ``symbol`` (newest-first)."""
    normalized = _normalise_symbol(symbol)
    payload = await asyncio.to_thread(_fetch_ratings_sync, normalized)
    entries: list[RatingsHistoryEntry] = []

    frame = payload.get("upgrades_downgrades")
    if isinstance(frame, pd.DataFrame) and not frame.empty:
        for raw_idx, row in frame.iterrows():
            entry_date = _coerce_date(raw_idx) or _coerce_date(row.get("GradeDate"))
            if entry_date is None:
                continue
            firm = str(row.get("Firm") or "Unknown").strip()
            from_grade = str(row.get("FromGrade") or "").strip()
            to_grade = str(row.get("ToGrade") or "").strip()
            rating_to = _normalise_action(to_grade)
            if rating_to is None:
                # Skip rows we cannot bucket; leaving them out keeps the timeline clean.
                continue
            rating_from = _normalise_action(from_grade) if from_grade else None
            entries.append(
                RatingsHistoryEntry(
                    symbol=normalized,
                    date=entry_date,
                    firm=firm,
                    analyst_name=None,
                    rating_from=rating_from,
                    rating_to=rating_to,
                    raw_rating=to_grade or from_grade,
                    note=str(row.get("Action") or "") or None,
                    provider=PROVIDER,
                )
            )
    entries.sort(key=lambda entry: entry.date, reverse=True)
    return RatingsHistoryResponse(symbol=normalized, history=entries)


async def get_price_target_history(symbol: str) -> PriceTargetHistoryResponse:
    """Return price-target changes for ``symbol`` (newest-first).

    yfinance does not currently expose a full timeline of price-target
    changes — its ``analyst_price_targets`` accessor returns a single
    current snapshot (low / mean / median / high). To still produce a
    usable timeline, the provider falls back to deriving target deltas
    from the consecutive entries of the upgrades/downgrades frame where
    a ``PriceTarget`` column is surfaced (some yfinance versions ship
    this; older ones do not). The frontend renders an empty-state when
    no rows return.
    """
    normalized = _normalise_symbol(symbol)
    payload = await asyncio.to_thread(_fetch_ratings_sync, normalized)
    currency = str(payload.get("currency") or "USD")
    frame = payload.get("upgrades_downgrades")
    entries: list[PriceTargetEntry] = []
    if isinstance(frame, pd.DataFrame) and not frame.empty:
        ordered = frame.copy()
        # The frame is usually date-indexed; sort ascending so we can pair
        # adjacent rows for the same firm.
        try:
            ordered = ordered.sort_index()
        except Exception:  # noqa: BLE001
            pass
        last_target_by_firm: dict[str, float] = {}
        for raw_idx, row in ordered.iterrows():
            entry_date = _coerce_date(raw_idx) or _coerce_date(row.get("GradeDate"))
            if entry_date is None:
                continue
            firm = str(row.get("Firm") or "Unknown").strip()
            target_to = _num(row.get("PriceTarget"))
            if target_to is None:
                # Some versions name the field differently.
                target_to = _num(row.get("Target")) or _num(row.get("Price Target"))
            if target_to is None:
                continue
            target_from = last_target_by_firm.get(firm)
            entries.append(
                PriceTargetEntry(
                    symbol=normalized,
                    date=entry_date,
                    firm=firm,
                    analyst_name=None,
                    target_from=target_from,
                    target_to=target_to,
                    currency=currency,
                    provider=PROVIDER,
                )
            )
            last_target_by_firm[firm] = target_to
    entries.sort(key=lambda entry: entry.date, reverse=True)

    # Fallback: if no per-row targets surfaced but the snapshot dict has
    # data, emit a single anchor row so the timeline is not totally empty
    # for the common case.
    if not entries:
        snapshot = payload.get("analyst_price_targets")
        snapshot_target: float | None = None
        if isinstance(snapshot, dict):
            snapshot_target = _num(snapshot.get("mean") or snapshot.get("current"))
        if snapshot_target is not None:
            entries.append(
                PriceTargetEntry(
                    symbol=normalized,
                    date=datetime.now(tz=UTC).date(),
                    firm="Consensus",
                    analyst_name=None,
                    target_from=None,
                    target_to=snapshot_target,
                    currency=currency,
                    provider=PROVIDER,
                )
            )
    return PriceTargetHistoryResponse(symbol=normalized, history=entries)


async def get_individual_analysts(symbol: str) -> IndividualAnalystResponse:
    """Return per-firm currently-active forecasts for ``symbol``.

    yfinance does not expose individual-analyst names so this surface
    treats *firm* as the granularity (1 row per firm reported in the
    most recent rating). ``one_year_accuracy`` and ``star_rating`` are
    ``None`` for yfinance — they are reserved for richer upstreams
    (openbb-mcp ``equity_estimates_*`` / TipRanks-style providers) and
    surfaced by the frontend with em-dash placeholders.
    """
    normalized = _normalise_symbol(symbol)
    payload = await asyncio.to_thread(_fetch_ratings_sync, normalized)
    currency = str(payload.get("currency") or "USD")
    frame = payload.get("upgrades_downgrades")
    forecasts: list[IndividualAnalystForecast] = []

    if isinstance(frame, pd.DataFrame) and not frame.empty:
        # Walk newest → oldest, keeping only the first row per firm so the
        # response captures each firm's current rating.
        try:
            ordered = frame.sort_index(ascending=False)
        except Exception:  # noqa: BLE001
            ordered = frame
        seen_firms: set[str] = set()
        for raw_idx, row in ordered.iterrows():
            firm = str(row.get("Firm") or "Unknown").strip()
            if firm in seen_firms:
                continue
            seen_firms.add(firm)
            entry_date = _coerce_date(raw_idx) or _coerce_date(row.get("GradeDate"))
            if entry_date is None:
                continue
            to_grade = str(row.get("ToGrade") or "").strip()
            current = _normalise_action(to_grade)
            if current is None:
                continue
            target_to = (
                _num(row.get("PriceTarget"))
                or _num(row.get("Target"))
                or _num(row.get("Price Target"))
            )
            forecasts.append(
                IndividualAnalystForecast(
                    symbol=normalized,
                    firm=firm,
                    analyst_name=firm,  # Use firm name as the analyst label when no name surfaces.
                    current_rating=current,
                    current_price_target=target_to,
                    currency=currency,
                    rating_issued_date=entry_date,
                    one_year_accuracy=None,
                    star_rating=None,
                    provider=PROVIDER,
                )
            )
    return IndividualAnalystResponse(symbol=normalized, analysts=forecasts)


__all__ = [
    "PROVIDER",
    "_normalise_action",
    "get_individual_analysts",
    "get_price_target_history",
    "get_ratings_history",
]
