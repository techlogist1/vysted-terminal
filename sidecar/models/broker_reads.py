"""Granular broker read models — net-new shapes for FR-042 (SC-012).

``models/broker.py`` is Tier-1 LOCKED (the §6.5 surface), so the genuine
granular reads live here. Today ``GET /brokers/{id}/positions``, ``/holdings``,
and ``/margins`` all alias ``account_info()`` → the same ``AccountSummary``;
these models back the *distinct* reads each broker SDK actually exposes:

  * :class:`BrokerPositionsResult` — net + day position lists (intraday/F&O),
    each with per-leg unrealized + realized P&L.
  * :class:`BrokerHoldingsResult` — settled long-term holdings.
  * :class:`BrokerMarginsResult` — per-segment available / used / net funds.

Every result carries the FR-041 provenance label — ``synthetic: bool`` +
``mode: "paper" | "live"`` + ``provider: str`` — so a paper / disconnected
value is plainly marked and never presented to the user as a real position.

Mirrored by hand in ``types/broker-reads.ts`` — keep the two in sync (CLAUDE.md
Gotchas).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.broker import BrokerId, BrokerMode


class BrokerReadProvenance(BaseModel):
    """FR-041 label shared by every granular read result.

    ``synthetic`` is ``True`` whenever the value is a paper-mode / disconnected
    placeholder — the UI must badge it so a fabricated figure is never read as a
    real broker position.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    broker: BrokerId
    account_id: str = Field(alias="accountId")
    #: True when the figures are paper-mode placeholders, not a real broker read.
    synthetic: bool
    mode: BrokerMode
    #: Provenance — which adapter / SDK produced these figures (e.g. "kite").
    provider: str
    captured_at: int = Field(alias="capturedAt")


class BrokerLegPosition(BaseModel):
    """One leg of a granular positions read (net or day)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: str
    quantity: float
    average_cost: float = Field(alias="averageCost")
    last_price: float = Field(alias="lastPrice")
    unrealized_pnl: float | None = Field(default=None, alias="unrealizedPnl")
    realized_pnl: float | None = Field(default=None, alias="realizedPnl")
    product: str | None = None


class BrokerPositionsResult(BrokerReadProvenance):
    """Intraday / F&O positions — the broker's distinct ``positions()`` call.

    ``net`` is the net open position per instrument; ``day`` is the intraday
    leg. These are NOT the settled holdings (see :class:`BrokerHoldingsResult`).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    net: list[BrokerLegPosition] = Field(default_factory=list)
    day: list[BrokerLegPosition] = Field(default_factory=list)


class BrokerHolding(BaseModel):
    """One settled long-term holding."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: str
    quantity: float
    average_cost: float = Field(alias="averageCost")
    last_price: float = Field(alias="lastPrice")
    market_value: float = Field(alias="marketValue")
    unrealized_pnl: float | None = Field(default=None, alias="unrealizedPnl")


class BrokerHoldingsResult(BrokerReadProvenance):
    """Settled long-term holdings — the broker's distinct ``holdings()`` call."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    holdings: list[BrokerHolding] = Field(default_factory=list)


class BrokerSegmentMargin(BaseModel):
    """Funds for one trading segment (e.g. equity, commodity)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    segment: str
    currency: str
    available: float
    used: float
    net: float


class BrokerMarginsResult(BrokerReadProvenance):
    """Per-segment funds — the broker's distinct ``margins()`` call."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    segments: list[BrokerSegmentMargin] = Field(default_factory=list)


#: Union surfaced by the granular read routes — each route narrows to one.
GranularBrokerRead = Literal["positions", "holdings", "margins"]


__all__ = [
    "BrokerHolding",
    "BrokerHoldingsResult",
    "BrokerLegPosition",
    "BrokerMarginsResult",
    "BrokerPositionsResult",
    "BrokerReadProvenance",
    "BrokerSegmentMargin",
    "GranularBrokerRead",
]
