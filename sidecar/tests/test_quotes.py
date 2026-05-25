"""Tests for the /quotes router."""

from __future__ import annotations

import time
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


def test_get_quotes_batch_fans_out_concurrently(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each blocking provider call sleeps; concurrent fan-out keeps wall time ≈ one call.

    Sequential execution of N sleepy calls would take ~N * delay; the
    ``asyncio.to_thread`` + ``asyncio.gather`` fan-out runs them in parallel on
    worker threads so the batch finishes in roughly one call's time.
    """
    from services import provider_registry

    delay = 0.2
    n_symbols = 10

    def slow_get_quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        time.sleep(delay)
        return Quote(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            timestamp=datetime.now(tz=UTC),
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", slow_get_quote)
    symbols = ",".join(f"SYM{i}" for i in range(n_symbols))

    start = time.perf_counter()
    body = client.get("/quotes", params={"symbols": symbols}).json()
    elapsed = time.perf_counter() - start

    assert len(body) == n_symbols
    # Sequential would be ~n_symbols * delay (= 2.0s). Concurrent must be well
    # under half that even allowing for thread-pool + scheduling overhead.
    assert elapsed < (n_symbols * delay) / 2, f"batch was not concurrent: {elapsed:.3f}s"


def test_get_quote_provider_error(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_registry

    def boom(*_args: object, **_kwargs: object) -> Quote:
        raise ProviderError("upstream down")

    monkeypatch.setattr(provider_registry, "get_quote", boom)
    response = client.get("/quotes/AAPL")
    assert response.status_code == 502
    assert "upstream down" in response.json()["detail"]
