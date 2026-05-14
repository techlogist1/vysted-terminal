"""Tests for the /quotes router."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from models.market import Quote
from services.errors import ProviderError


def test_get_quote(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/quotes/AAPL").json()
    assert body["symbol"] == "AAPL"
    assert body["price"] == 192.5
    assert body["change"] == pytest.approx(2.5)
    assert body["change_percent"] == pytest.approx(2.5 / 190.0 * 100.0)
    assert body["provider"] == "yfinance"


def test_get_quotes_batch(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/quotes", params={"symbols": "AAPL,MSFT"}).json()
    assert len(body) == 2
    assert {q["symbol"] for q in body} == {"AAPL", "MSFT"}


def test_get_quotes_batch_skips_failures(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services import provider_registry

    def fake_get_quote(symbol: str, asset_class: str = "equity") -> Quote:
        if symbol == "BAD":
            raise ProviderError("symbol not found")
        return Quote(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            timestamp=datetime.now(tz=UTC),
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", fake_get_quote)
    body = client.get("/quotes", params={"symbols": "AAPL,BAD,MSFT"}).json()
    assert [q["symbol"] for q in body] == ["AAPL", "MSFT"]


def test_get_quote_provider_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_registry

    def boom(*_args: object, **_kwargs: object) -> Quote:
        raise ProviderError("upstream down")

    monkeypatch.setattr(provider_registry, "get_quote", boom)
    response = client.get("/quotes/AAPL")
    assert response.status_code == 502
    assert "upstream down" in response.json()["detail"]
