"""Tests for the v0.6.0 macro dispatcher's ``data_cache`` integration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from models.macro_extended import MacroCatalog, MacroSearchResult, MacroSeriesExtended
from models.market import MacroObservation
from services import data_cache
from services.macro import macro_router as macro_dispatcher


def _stub_series() -> MacroSeriesExtended:
    return MacroSeriesExtended(
        series_id="DGS10",
        title="10-Year Treasury",
        units="Percent",
        observations=[MacroObservation(date=datetime(2026, 5, 14, tzinfo=UTC), value=4.25)],
        provider="fred",
        frequency="daily",
        last_updated=datetime(2026, 5, 14, tzinfo=UTC),
        seasonal_adjustment="not-adjusted",
        source_url="https://fred.stlouisfed.org/series/DGS10",
        notes=None,
    )


def _stub_search() -> list[MacroSearchResult]:
    return [
        MacroSearchResult(
            provider="fred",
            series_id="DGS10",
            title="10-Year",
            frequency="daily",
            units="Percent",
            score=0.95,
        )
    ]


def _stub_catalog() -> MacroCatalog:
    return MacroCatalog(provider="fred", entries=[])


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Per-test isolated cache db."""
    data_cache.reset_for_tests(tmp_path / "test_cache.db")
    yield
    data_cache.reset_for_tests(None)


@pytest.fixture
def _fred_stubs(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Count how many times each provider entry point is called."""
    counts = {"get_series": 0, "search": 0, "catalog": 0}

    from services.macro import fred_provider

    def fake_get_series(series_id: str) -> MacroSeriesExtended:
        counts["get_series"] += 1
        return _stub_series()

    def fake_search(query: str, limit: int = 25) -> list[MacroSearchResult]:
        counts["search"] += 1
        return _stub_search()

    def fake_catalog(limit: int = 25) -> MacroCatalog:
        counts["catalog"] += 1
        return _stub_catalog()

    monkeypatch.setattr(fred_provider, "get_series", fake_get_series)
    monkeypatch.setattr(fred_provider, "search", fake_search)
    monkeypatch.setattr(fred_provider, "catalog", fake_catalog)
    return counts


@pytest.mark.asyncio
async def test_get_series_caches_subsequent_reads(_fred_stubs: dict[str, int]) -> None:
    s1 = await macro_dispatcher.get_series("DGS10", "fred")
    s2 = await macro_dispatcher.get_series("DGS10", "fred")
    assert s1.series_id == "DGS10"
    assert s2.series_id == "DGS10"
    # Cache hit on second read.
    assert _fred_stubs["get_series"] == 1


@pytest.mark.asyncio
async def test_get_series_bypasses_stale_cache(_fred_stubs: dict[str, int]) -> None:
    # TTL=0 → every read is treated as a miss.
    await macro_dispatcher.get_series("DGS10", "fred", ttl_seconds=0)
    await macro_dispatcher.get_series("DGS10", "fred", ttl_seconds=0)
    assert _fred_stubs["get_series"] == 2


@pytest.mark.asyncio
async def test_search_caches_results(_fred_stubs: dict[str, int]) -> None:
    a = await macro_dispatcher.search("treasury", "fred")
    b = await macro_dispatcher.search("treasury", "fred")
    assert len(a) == len(b) == 1
    assert _fred_stubs["search"] == 1


@pytest.mark.asyncio
async def test_catalog_caches_results(_fred_stubs: dict[str, int]) -> None:
    await macro_dispatcher.get_catalog("fred")
    await macro_dispatcher.get_catalog("fred")
    assert _fred_stubs["catalog"] == 1


@pytest.mark.asyncio
async def test_unknown_provider_raises() -> None:
    from services.errors import ProviderError

    with pytest.raises(ProviderError, match="Unknown macro provider"):
        await macro_dispatcher.get_series("X", "fictional")


@pytest.mark.asyncio
async def test_get_series_rejects_empty_id() -> None:
    from services.errors import ProviderError

    with pytest.raises(ProviderError, match="series_id is required"):
        await macro_dispatcher.get_series("", "fred")
