"""Technical-indicator Pydantic models — the chart panel's overlay contract.

These shapes are mirrored by hand in ``types/data.ts``; keep the two in sync
(see CLAUDE.md Gotchas). The chart panel renders each ``IndicatorSeries`` either
on the price pane (``panel="price"``) as an overlay or in its own pane below the
price chart (``panel="separate"``).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

IndicatorPanel = Literal["price", "separate"]


class IndicatorPoint(BaseModel):
    """A single ``(time, value)`` sample on an indicator line.

    ``time`` is an ISO-8601 timestamp mirrored from the source OHLCV bar. A
    ``None`` value marks a gap where the indicator is undefined (e.g. the warm-up
    window of a moving average).
    """

    time: str
    value: float | None


class IndicatorLine(BaseModel):
    """One named line within an indicator (an indicator may plot several)."""

    label: str
    points: list[IndicatorPoint]


class IndicatorSeries(BaseModel):
    """The full result of computing one indicator over an OHLCV series."""

    name: str
    panel: IndicatorPanel
    lines: list[IndicatorLine]


class IndicatorResponse(BaseModel):
    """The ``/indicators/{symbol}`` payload — every requested indicator."""

    symbol: str
    timeframe: str
    provider: str
    indicators: list[IndicatorSeries]
