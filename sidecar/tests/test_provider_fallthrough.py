"""R15-LIFECYCLE-021: a provider the registry keeps falling through is visible.

Fall-throughs are counted per (provider, model_key) on /system/provider-health
(C14), /health stops naming a failing provider as primary, and a provider that
merely does not list the instrument (``not_found``) is not counted.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from models.fundamentals import Fundamentals
from models.market import Quote
from services import (
    bse_provider,
    india_provider,
    nse_provider,
    openbb_mcp_provider,
    provider_registry,
    yfinance_provider,
)
from services.errors import ProviderError


def _bse_quote(symbol: str) -> Quote:
    return Quote(
        symbol=symbol.removesuffix(".NS"),
        price=2950.0,
        change=0.0,
        change_percent=0.0,
        currency="INR",
        timestamp=datetime.now(tz=UTC),
        provider="bse",
    )


@pytest.fixture
def nse_down(monkeypatch: pytest.MonkeyPatch) -> None:
    """nse_direct's host refuses; jugaad does not list the name; BSE serves."""

    def refused(_symbol: str) -> Quote:
        raise ProviderError("nse_direct: transport failure on /api/quote-equity")

    def unlisted(symbol: str) -> Quote:
        raise ProviderError(f"nse: {symbol!r} is not listed", kind="not_found")

    for module in (nse_provider, india_provider, bse_provider):
        monkeypatch.setattr(module, "is_available", lambda: True)
    monkeypatch.setattr(nse_provider, "get_quote", refused)
    monkeypatch.setattr(india_provider, "get_quote", unlisted)
    monkeypatch.setattr(bse_provider, "get_quote", _bse_quote)


def test_three_nse_direct_failures_surface_with_a_count_of_three(
    client: TestClient, nse_down: None
) -> None:
    for _ in range(3):
        assert provider_registry.get_quote("RELIANCE.NS").provider == "bse"

    rows = client.get("/system/provider-health").json()["fallthroughs"]
    assert [(r["provider"], r["model_key"], r["count"]) for r in rows] == [
        ("nse_direct", "quote", 3)
    ]
    assert "transport failure" in rows[0]["last_error"]
    assert rows[0]["last_at"] > 0
    # /health no longer names the failing lane as a live source.
    assert "nse_direct failing" in client.get("/health").json()["providers"]["quote"]


def test_a_served_call_ends_the_run(
    client: TestClient, nse_down: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider_registry.get_quote("RELIANCE.NS")
    monkeypatch.setattr(nse_provider, "get_quote", _bse_quote)
    provider_registry.get_quote("RELIANCE.NS")
    assert client.get("/system/provider-health").json()["fallthroughs"] == []


def test_openbb_to_yfinance_fallthrough_is_counted_the_same_way(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Class pin on the async resolver and a non-IN lane."""

    async def openbb_down(_symbol: str) -> Fundamentals:
        raise ProviderError("openbb-mcp: connection refused", kind="network")

    monkeypatch.setattr(openbb_mcp_provider, "is_available", lambda: True)
    monkeypatch.setattr(openbb_mcp_provider, "get_fundamentals", openbb_down)
    monkeypatch.setattr(
        yfinance_provider,
        "get_fundamentals",
        lambda _s: Fundamentals(symbol="AAPL", provider="yfinance", roe=0.3),
    )
    for _ in range(3):
        asyncio.run(provider_registry.get_fundamentals("AAPL"))

    rows = client.get("/system/provider-health").json()["fallthroughs"]
    assert [(r["provider"], r["model_key"], r["count"]) for r in rows] == [
        ("openbb-mcp", "fundamentals", 3)
    ]
