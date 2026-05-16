"""Extended analyst-ratings Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/analyst.ts``.

Phase 1 shipped a lightweight :class:`models.fundamentals.AnalystRating`
consensus snapshot. Phase 6 expands the surface in three directions:
ratings history, price-target history, individual analyst tracks. The
Phase 1 type stays in ``models/fundamentals.py``; the Phase 6 extensions
live here.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Standardised rating bucket
# ---------------------------------------------------------------------------

AnalystAction = Literal["strong-buy", "buy", "hold", "sell", "strong-sell"]


# ---------------------------------------------------------------------------
# Ratings history
# ---------------------------------------------------------------------------


class RatingsHistoryEntry(BaseModel):
    """One row in a symbol's ratings-history timeline."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    date: date
    firm: str
    analyst_name: str | None = None
    rating_from: AnalystAction | None = None
    rating_to: AnalystAction
    raw_rating: str
    note: str | None = None
    provider: str


class RatingsHistoryResponse(BaseModel):
    """Returned by ``GET /fundamentals/{symbol}/ratings/history``."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    history: list[RatingsHistoryEntry]


# ---------------------------------------------------------------------------
# Price-target history
# ---------------------------------------------------------------------------


class PriceTargetEntry(BaseModel):
    """One row in a symbol's price-target-history timeline."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    date: date
    firm: str
    analyst_name: str | None = None
    target_from: float | None = None
    target_to: float
    currency: str = "USD"
    provider: str


class PriceTargetHistoryResponse(BaseModel):
    """Returned by ``/fundamentals/{symbol}/ratings/price-target-history``."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    history: list[PriceTargetEntry]


# ---------------------------------------------------------------------------
# Individual analyst forecast
# ---------------------------------------------------------------------------


class IndividualAnalystForecast(BaseModel):
    """One analyst's active forecast + historical accuracy where exposed."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    firm: str
    analyst_name: str
    current_rating: AnalystAction
    current_price_target: float | None = None
    currency: str = "USD"
    rating_issued_date: date
    one_year_accuracy: float | None = None
    star_rating: float | None = None
    provider: str


class IndividualAnalystResponse(BaseModel):
    """Returned by ``GET /fundamentals/{symbol}/ratings/individual``."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    analysts: list[IndividualAnalystForecast]
