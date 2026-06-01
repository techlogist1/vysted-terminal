"""Tests for the /quotes router."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

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


def test_get_quote_carries_freshness(client: TestClient, mock_yfinance: object) -> None:
    """Every served quote carries a calendar-aware freshness label (SC-019).

    The recent mock-quote is never labelled ``stale`` — a legitimate close is
    ``live`` or ``eod``, never shown as a stale value (nor a stale value as live).
    """
    body = client.get("/quotes/AAPL").json()
    assert body["freshness"] in {"live", "eod"}


def test_get_quote_old_value_is_labeled_stale(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A quote dated well past the staleness tolerance is labelled ``stale`` — it
    is never presented as a live tick (SC-019, the 'no stale-as-live' invariant)."""
    from services import provider_registry

    def stale_quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        return Quote(
            symbol=symbol,
            price=100.0,
            change=1.0,
            change_percent=1.0,
            timestamp=datetime.now(tz=UTC) - timedelta(days=45),
            provider="yfinance",
        )

    monkeypatch.setattr(provider_registry, "get_quote", stale_quote)
    body = client.get("/quotes/AAPL").json()
    assert body["freshness"] == "stale"


def test_crypto_quote_is_live(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Crypto trades 24/7, so a fresh crypto fetch is always labelled ``live``."""
    from services import provider_registry

    def crypto_quote(symbol: str, asset_class: str = "equity") -> Quote:  # noqa: ARG001
        return Quote(
            symbol=symbol,
            price=65000.0,
            change=500.0,
            change_percent=0.7,
            currency="USD",
            timestamp=datetime.now(tz=UTC) - timedelta(days=10),
            provider="ccxt",
        )

    monkeypatch.setattr(provider_registry, "get_quote", crypto_quote)
    # Batch endpoint avoids the encoded-slash path-routing issue of crypto pairs.
    body = client.get("/quotes", params={"symbols": "BTC/USDT", "asset_class": "crypto"}).json()
    assert len(body) == 1
    assert body[0]["freshness"] == "live"


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
