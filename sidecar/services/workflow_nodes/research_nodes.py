"""Phase 6 (Teammate E) workflow nodes — earnings + analyst research.

Registers four workflow node types so authors of the visual workflow
canvas can stitch earnings + analyst context into their pipelines:

* ``data.fetch_earnings_calendar`` — upcoming earnings events; outputs
  ``events: EarningsEvent[]``.
* ``data.fetch_earnings_history`` — past earnings results for a symbol;
  outputs ``history: EarningsHistoryEntry[]``.
* ``data.fetch_analyst_history`` — rating changes for a symbol; outputs
  ``history: RatingsHistoryEntry[]``.
* ``data.fetch_price_target_history`` — price-target timeline for a
  symbol; outputs ``history: PriceTargetEntry[]``.

The handlers follow the established :data:`NodeHandler` signature —
``async def(inputs, config) -> outputs`` — and shim into the existing
providers (:mod:`services.earnings_provider` and
:mod:`services.analyst_ratings_extended`). Configuration errors raise
``ValueError`` (the engine catches it and emits a node-error event);
provider errors propagate verbatim so the workflow run records them.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from services import analyst_ratings_extended, earnings_provider, workflow_engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# data.fetch_earnings_calendar
# ---------------------------------------------------------------------------


async def fetch_earnings_calendar(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Return upcoming earnings events in the requested window.

    Resolution order: ``inputs["days"]`` overrides ``config["days"]``;
    ``inputs["watchlist"]`` overrides ``config["watchlist"]``. Either
    accepts a comma-separated string or a list. ``days`` is clamped to
    ``[1, 60]``.
    """
    raw_days = inputs.get("days") or config.get("days") or 7
    try:
        days = int(raw_days)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"data.fetch_earnings_calendar: 'days' must be numeric; got {raw_days!r}"
        ) from exc
    if days < 1 or days > 60:
        raise ValueError("data.fetch_earnings_calendar: 'days' must be in [1, 60]")

    watchlist_value = inputs.get("watchlist") if "watchlist" in inputs else config.get("watchlist")
    watchlist: list[str] | None
    if isinstance(watchlist_value, str):
        watchlist = [s.strip() for s in watchlist_value.split(",") if s.strip()]
    elif isinstance(watchlist_value, list):
        watchlist = [str(s).strip() for s in watchlist_value if str(s).strip()]
    else:
        watchlist = None

    today = datetime.now(tz=UTC).date()
    response = await earnings_provider.get_upcoming(today, today + timedelta(days=days), watchlist)
    return {
        "events": [event.model_dump(mode="json") for event in response.events],
        "start_date": response.start_date.isoformat(),
        "end_date": response.end_date.isoformat(),
    }


# ---------------------------------------------------------------------------
# data.fetch_earnings_history
# ---------------------------------------------------------------------------


async def fetch_earnings_history(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Return past earnings reports for ``symbol``."""
    symbol = inputs.get("symbol") or config.get("symbol")
    if not symbol:
        raise ValueError(
            "data.fetch_earnings_history: missing 'symbol' (provide via input or config)"
        )
    response = await earnings_provider.get_history(str(symbol))
    return {
        "symbol": response.symbol,
        "history": [entry.model_dump(mode="json") for entry in response.history],
    }


# ---------------------------------------------------------------------------
# data.fetch_analyst_history
# ---------------------------------------------------------------------------


async def fetch_analyst_history(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Return rating changes for ``symbol`` (newest-first)."""
    symbol = inputs.get("symbol") or config.get("symbol")
    if not symbol:
        raise ValueError(
            "data.fetch_analyst_history: missing 'symbol' (provide via input or config)"
        )
    response = await analyst_ratings_extended.get_ratings_history(str(symbol))
    return {
        "symbol": response.symbol,
        "history": [entry.model_dump(mode="json") for entry in response.history],
    }


# ---------------------------------------------------------------------------
# data.fetch_price_target_history
# ---------------------------------------------------------------------------


async def fetch_price_target_history(
    inputs: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Return price-target timeline for ``symbol`` (newest-first)."""
    symbol = inputs.get("symbol") or config.get("symbol")
    if not symbol:
        raise ValueError(
            "data.fetch_price_target_history: missing 'symbol' (provide via input or config)"
        )
    response = await analyst_ratings_extended.get_price_target_history(str(symbol))
    return {
        "symbol": response.symbol,
        "history": [entry.model_dump(mode="json") for entry in response.history],
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register() -> None:
    """Register the four research node types with the workflow engine."""
    workflow_engine.register_node_type("data.fetch_earnings_calendar", fetch_earnings_calendar)
    workflow_engine.register_node_type("data.fetch_earnings_history", fetch_earnings_history)
    workflow_engine.register_node_type("data.fetch_analyst_history", fetch_analyst_history)
    workflow_engine.register_node_type(
        "data.fetch_price_target_history", fetch_price_target_history
    )


__all__ = [
    "fetch_analyst_history",
    "fetch_earnings_calendar",
    "fetch_earnings_history",
    "fetch_price_target_history",
    "register",
]
