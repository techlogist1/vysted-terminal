"""Tests for the v0.6.0 macro workflow node (Teammate M).

Covers ``data.fetch_macro_series`` invocation in isolation and through
``workflow_engine.register_node_type`` registration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from models.macro_extended import MacroSeriesExtended
from models.market import MacroObservation
from services import data_cache, workflow_engine
from services.macro import fred_provider
from services.workflow_nodes import macro_nodes


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    data_cache.reset_for_tests(tmp_path / "nodes_cache.db")
    yield
    data_cache.reset_for_tests(None)


@pytest.fixture(autouse=True)
def _isolated_registry() -> None:
    workflow_engine.reset_registry_for_tests()
    yield
    workflow_engine.reset_registry_for_tests()


def _series_stub() -> MacroSeriesExtended:
    return MacroSeriesExtended(
        series_id="DGS10",
        title="10-Year",
        units="Percent",
        observations=[MacroObservation(date=datetime(2026, 5, 14, tzinfo=UTC), value=4.25)],
        provider="fred",
        frequency="daily",
        last_updated=None,
        seasonal_adjustment=None,
        source_url=None,
        notes=None,
    )


def test_register_installs_node_type() -> None:
    macro_nodes.register()
    assert "data.fetch_macro_series" in workflow_engine.registered_node_types()


@pytest.mark.asyncio
async def test_fetch_macro_series_via_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fred_provider, "get_series", lambda sid: _series_stub())
    out = await macro_nodes.fetch_macro_series(
        inputs={}, config={"series_id": "DGS10", "provider": "fred"}
    )
    assert out["series"]["series_id"] == "DGS10"
    assert out["series"]["provider"] == "fred"


@pytest.mark.asyncio
async def test_fetch_macro_series_via_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fred_provider, "get_series", lambda sid: _series_stub())
    out = await macro_nodes.fetch_macro_series(
        inputs={"series_id": "DGS10", "provider": "fred"}, config={}
    )
    assert out["series"]["series_id"] == "DGS10"


@pytest.mark.asyncio
async def test_fetch_macro_series_missing_series_id_raises() -> None:
    with pytest.raises(ValueError, match="series_id"):
        await macro_nodes.fetch_macro_series(inputs={}, config={"provider": "fred"})


@pytest.mark.asyncio
async def test_fetch_macro_series_missing_provider_raises() -> None:
    with pytest.raises(ValueError, match="provider"):
        await macro_nodes.fetch_macro_series(inputs={}, config={"series_id": "DGS10"})


@pytest.mark.asyncio
async def test_fetch_macro_series_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="unknown provider"):
        await macro_nodes.fetch_macro_series(
            inputs={}, config={"series_id": "X", "provider": "yodlee"}
        )
