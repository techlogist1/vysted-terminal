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
