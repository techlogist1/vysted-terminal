"""Extended macro Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/macro.ts``. When a TypeScript
interface in that file changes, update the matching ``BaseModel`` here in the
same commit (see CLAUDE.md Gotchas).

Phase 1 shipped a minimal :class:`models.market.MacroSeries`; Phase 6 lights
up the multi-provider macro contract that the FRED / ECB / IMF / World Bank
upstreams all need. The Phase 1 shape stays in ``models/market.py`` for
backwards compatibility; the v0.6.0 macro layer consumes
:class:`MacroSeriesExtended` here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .market import MacroObservation

# ---------------------------------------------------------------------------
# Provider identity
# ---------------------------------------------------------------------------

MacroProvider = Literal["fred", "ecb", "imf", "world-bank"]
"""The four macro upstreams Vysted supports as of v0.6.0."""

MacroFrequency = Literal[
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
    "other",
]
"""Frequency labels common across the four providers."""

SeasonalAdjustment = Literal[
    "seasonally-adjusted",
    "not-adjusted",
    "not-applicable",
]


# ---------------------------------------------------------------------------
# Series shape
# ---------------------------------------------------------------------------


class MacroSeriesExtended(BaseModel):
    """Economic / macro time series with provider-aware metadata.

    Phase 6 extension over :class:`models.market.MacroSeries`:
      - ``provider`` is a narrow literal, not a free string;
      - ``frequency``, ``last_updated``, ``seasonal_adjustment`` are new;
      - ``source_url`` lets the UI link out to the upstream's series page.
    """

    model_config = ConfigDict(extra="forbid")

    series_id: str
    title: str
    units: str | None = None
    observations: list[MacroObservation]
    provider: MacroProvider
    frequency: MacroFrequency | None = None
    last_updated: datetime | None = None
    seasonal_adjustment: SeasonalAdjustment | None = None
    source_url: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Discovery — search + catalog
# ---------------------------------------------------------------------------


class MacroSearchResult(BaseModel):
    """One result from ``GET /macro/search?q=``."""

    model_config = ConfigDict(extra="forbid")

    provider: MacroProvider
    series_id: str
    title: str
    frequency: MacroFrequency | None = None
    units: str | None = None
    score: float


class MacroCatalogEntry(BaseModel):
    """One entry in a provider's curated catalog."""

    model_config = ConfigDict(extra="forbid")

    provider: MacroProvider
    series_id: str
    title: str
    category: str | None = None
    frequency: MacroFrequency | None = None
    units: str | None = None


class MacroCatalog(BaseModel):
    """Per-provider catalog payload returned by ``GET /macro/catalog``."""

    model_config = ConfigDict(extra="forbid")

    provider: MacroProvider
    entries: list[MacroCatalogEntry]
