"""FastAPI route tests for the v0.6.0 macro endpoints (Teammate M).

Tests the provider-aware ``GET /macro/{series_id}?provider=...`` dispatch,
the new discovery endpoints ``/macro/search`` + ``/macro/catalog``, and
the legacy Phase-1/3 fallback when no provider literal is supplied.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from models.macro_extended import MacroCatalog, MacroSearchResult, MacroSeriesExtended
from models.market import MacroObservation
from services import data_cache
from services.errors import ProviderError


def _series_stub(provider: str, series_id: str) -> MacroSeriesExtended:
    return MacroSeriesExtended(
        series_id=series_id,
        title=f"{series_id} title",
        units="Percent",
        observations=[
            MacroObservation(date=datetime(2026, 5, 14, tzinfo=UTC), value=4.25),
        ],
        provider=provider,  # type: ignore[arg-type]
        frequency="daily",
        last_updated=None,
        seasonal_adjustment=None,
        source_url=f"https://example.com/{series_id}",
        notes=None,
    )


def _search_stub(provider: str, query: str) -> list[MacroSearchResult]:
    return [
        MacroSearchResult(
            provider=provider,  # type: ignore[arg-type]
            series_id=f"{provider.upper()}-X",
            title=f"{query} {provider}",
            frequency="daily",
            units=None,
            score=0.5,
        )
    ]


def _catalog_stub(provider: str) -> MacroCatalog:
    return MacroCatalog(provider=provider, entries=[])  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Per-test isolated cache db so no test pollutes another."""
    data_cache.reset_for_tests(tmp_path / "macro_router_cache.db")
    yield
    data_cache.reset_for_tests(None)


@pytest.fixture
def patch_all_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch every macro provider's three callables with deterministic stubs."""
    from services.macro import (
        ecb_provider,
        fred_provider,
        imf_provider,
        world_bank_provider,
    )

    for provider_name, mod in (
        ("fred", fred_provider),
        ("ecb", ecb_provider),
        ("imf", imf_provider),
        ("world-bank", world_bank_provider),
    ):
        monkeypatch.setattr(mod, "get_series", lambda sid, _p=provider_name: _series_stub(_p, sid))
        monkeypatch.setattr(
            mod, "search", lambda q, limit=25, _p=provider_name: _search_stub(_p, q)
        )
        monkeypatch.setattr(mod, "catalog", lambda limit=25, _p=provider_name: _catalog_stub(_p))


# ---------------------------------------------------------------------------
# /macro/{series_id}
# ---------------------------------------------------------------------------


def test_get_series_dispatches_to_fred(client: TestClient, patch_all_providers: None) -> None:
    res = client.get("/macro/DGS10", params={"provider": "fred"})
    assert res.status_code == 200
    body = res.json()
    assert body["series_id"] == "DGS10"
    assert body["provider"] == "fred"
    assert body["source_url"].endswith("DGS10")


def test_get_series_dispatches_to_ecb(client: TestClient, patch_all_providers: None) -> None:
    res = client.get("/macro/FM.D.U2.EUR.4F.KR.MRR_FR.LEV", params={"provider": "ecb"})
    assert res.status_code == 200
    assert res.json()["provider"] == "ecb"


def test_get_series_dispatches_to_imf(client: TestClient, patch_all_providers: None) -> None:
    # IMF series ids use ``/`` to separate dataflow from key; the path parameter
    # accepts the dot-prefixed legacy form too (``IFS.A.US.NGDP_R_K_IX``) which
    # the IMF provider's id parser handles either way.
    res = client.get("/macro/IFS.A.US.NGDP_R_K_IX", params={"provider": "imf"})
    assert res.status_code == 200
    assert res.json()["provider"] == "imf"


def test_get_series_dispatches_to_world_bank(client: TestClient, patch_all_providers: None) -> None:
    res = client.get("/macro/NY.GDP.PCAP.CD", params={"provider": "world-bank"})
    assert res.status_code == 200
    assert res.json()["provider"] == "world-bank"


def test_get_series_returns_502_on_provider_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.macro import fred_provider

    def boom(_sid: str) -> MacroSeriesExtended:
        raise ProviderError("no API key")

    monkeypatch.setattr(fred_provider, "get_series", boom)
    res = client.get("/macro/X", params={"provider": "fred"})
    assert res.status_code == 502
    assert "no API key" in res.json()["detail"]


def test_get_series_legacy_path_when_provider_not_v0_6_0(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No provider param → legacy Phase-1/3 path returns 501 in the test build."""
    res = client.get("/macro/DGS10")
    # The Phase-1/3 path raises ProviderError → 501.
    assert res.status_code == 501


# ---------------------------------------------------------------------------
# /macro/search
# ---------------------------------------------------------------------------


def test_search_returns_results(client: TestClient, patch_all_providers: None) -> None:
    res = client.get("/macro/search", params={"q": "treasury", "provider": "fred"})
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert body[0]["provider"] == "fred"


def test_search_requires_query(client: TestClient, patch_all_providers: None) -> None:
    res = client.get("/macro/search", params={"provider": "fred"})
    assert res.status_code == 422  # FastAPI validation


def test_search_rejects_unknown_provider(client: TestClient, patch_all_providers: None) -> None:
    res = client.get(
        "/macro/search",
        params={"q": "x", "provider": "yodlee"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# /macro/catalog
# ---------------------------------------------------------------------------


def test_catalog_returns_entries(client: TestClient, patch_all_providers: None) -> None:
    res = client.get("/macro/catalog", params={"provider": "fred"})
    assert res.status_code == 200
    assert res.json()["provider"] == "fred"


def test_catalog_rejects_unknown_provider(client: TestClient, patch_all_providers: None) -> None:
    res = client.get("/macro/catalog", params={"provider": "alpha-vantage"})
    assert res.status_code == 422
