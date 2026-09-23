"""Tests for the /crypto router — REST endpoints and the WebSocket stream."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_exchanges(client: TestClient) -> None:
    body = client.get("/crypto/exchanges").json()
    assert set(body["exchanges"]) == {"bybit", "binance", "kraken", "coinbase"}


def test_crypto_ticker(client: TestClient, mock_ccxt: None) -> None:
    body = client.get("/crypto/ticker", params={"exchange": "binance", "symbol": "BTC/USDT"}).json()
    assert body["symbol"] == "BTC/USDT"
    assert body["price"] == 67_000.0
    assert body["currency"] == "USDT"
    assert body["provider"] == "ccxt:binance"


def test_crypto_ticker_unsupported_exchange(client: TestClient, mock_ccxt: None) -> None:
    response = client.get("/crypto/ticker", params={"exchange": "notreal", "symbol": "BTC/USDT"})
    assert response.status_code == 502


def test_crypto_history(client: TestClient, mock_ccxt: None) -> None:
    body = client.get(
        "/crypto/history",
        params={"exchange": "kraken", "symbol": "BTC/USD", "timeframe": "1d"},
    ).json()
    assert body["symbol"] == "BTC/USD"
    assert body["provider"] == "ccxt:kraken"
    assert len(body["bars"]) == 2


def test_crypto_stream(client: TestClient, mock_ccxtpro: None) -> None:
    with client.websocket_connect("/crypto/stream?exchange=binance&symbol=BTC/USDT") as websocket:
        first = websocket.receive_json()
        second = websocket.receive_json()
    assert first["provider"] == "ccxt:binance"
    assert first["symbol"] == "BTC/USDT"
    assert second["price"] > first["price"]


_DAY_MS = 86_400_000


class _SinceExchange:
    """Serves one daily bar per day from ``since`` to now, ``limit`` per page."""

    calls: list[int] = []

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def fetch_ohlcv(self, symbol: str, timeframe: str, since: int, limit: int) -> list[list]:  # noqa: ARG002
        import math
        import time

        type(self).calls.append(since)
        now = int(time.time() * 1000)
        start = math.ceil(since / _DAY_MS) * _DAY_MS
        return [[t, 1.0, 2.0, 0.5, 1.5, 10.0] for t in range(start, now, _DAY_MS)][:limit]


def test_crypto_range_becomes_since_and_pages(monkeypatch) -> None:  # noqa: ANN001
    """R15-DATA-037: 1mo and 1y are different spans, and 5y pages past one call."""
    from types import SimpleNamespace

    from services import ccxt_provider

    monkeypatch.setattr(ccxt_provider, "ccxt", SimpleNamespace(binance=_SinceExchange))

    def bars(range_: str) -> int:
        _SinceExchange.calls = []
        return len(ccxt_provider.get_ohlcv("binance", "BTC/USDT", "1d", range_).bars)

    assert 29 <= bars("1mo") <= 31
    assert 364 <= bars("1y") <= 366
    assert 1824 <= bars("5y") <= 1827
    assert len(_SinceExchange.calls) == 2  # a full 1000-bar page, then the rest


def test_crypto_history_route_and_registry_forward_the_range(
    client: TestClient,
    monkeypatch,  # noqa: ANN001
) -> None:
    from types import SimpleNamespace

    from services import ccxt_provider, provider_registry

    monkeypatch.setattr(ccxt_provider, "ccxt", SimpleNamespace(binance=_SinceExchange))
    body = client.get(
        "/crypto/history",
        params={"exchange": "binance", "symbol": "BTC/USDT", "timeframe": "1d", "range": "3mo"},
    ).json()
    assert 90 <= len(body["bars"]) <= 92
    series = provider_registry.get_history("BTC/USDT", "1d", "6mo", asset_class="crypto")
    assert 181 <= len(series.bars) <= 183
