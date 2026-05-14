"""Shared fixtures for sidecar tests.

Every provider is mocked here — no test makes a live network call. The fakes
return deterministic, canned data shaped like the real upstream responses so the
provider mapping code is genuinely exercised.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client() -> TestClient:
    """A TestClient bound to a freshly built app instance."""
    return TestClient(create_app())


# --------------------------------------------------------------------------
# yfinance fakes
# --------------------------------------------------------------------------


class _FakeFastInfo:
    last_price = 192.5
    previous_close = 190.0
    last_volume = 51_000_000
    currency = "USD"


def _statement_df() -> pd.DataFrame:
    columns = pd.to_datetime(["2025-09-30", "2024-09-30"])
    return pd.DataFrame(
        {columns[0]: [400_000.0, 100_000.0], columns[1]: [380_000.0, 95_000.0]},
        index=["Total Revenue", "Net Income"],
    )


class _FakeTicker:
    """Stand-in for ``yfinance.Ticker`` with canned, deterministic data."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    def fast_info(self) -> _FakeFastInfo:
        return _FakeFastInfo()

    def history(self, period: str, interval: str) -> pd.DataFrame:  # noqa: ARG002
        index = pd.to_datetime(["2026-05-12", "2026-05-13", "2026-05-14"])
        return pd.DataFrame(
            {
                "Open": [188.0, 190.0, 191.0],
                "High": [191.0, 192.0, 193.5],
                "Low": [187.0, 189.0, 190.5],
                "Close": [190.0, 191.0, 192.5],
                "Volume": [48_000_000.0, 49_500_000.0, 51_000_000.0],
            },
            index=index,
        )

    @property
    def info(self) -> dict:
        return {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3_000_000_000_000,
            "trailingPE": 31.2,
            "forwardPE": 28.4,
            "trailingPegRatio": 2.1,
            "priceToBook": 47.0,
            "dividendYield": 0.0044,
            "trailingEps": 6.17,
            "beta": 1.25,
            "fiftyTwoWeekHigh": 220.0,
            "fiftyTwoWeekLow": 160.0,
        }

    @property
    def income_stmt(self) -> pd.DataFrame:
        return _statement_df()

    @property
    def balance_sheet(self) -> pd.DataFrame:
        return _statement_df()

    @property
    def cashflow(self) -> pd.DataFrame:
        return _statement_df()

    @property
    def recommendations(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "period": "0m",
                    "strongBuy": 12,
                    "buy": 20,
                    "hold": 8,
                    "sell": 1,
                    "strongSell": 0,
                }
            ]
        )

    @property
    def analyst_price_targets(self) -> dict:
        return {"current": 192.5, "low": 170.0, "high": 260.0, "mean": 225.0}


@pytest.fixture
def mock_yfinance(monkeypatch: pytest.MonkeyPatch) -> type[_FakeTicker]:
    """Patch ``yfinance.Ticker`` with the canned fake."""
    from services import yfinance_provider

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _FakeTicker)
    return _FakeTicker


# --------------------------------------------------------------------------
# ccxt fakes
# --------------------------------------------------------------------------


class _FakeCcxtExchange:
    """Stand-in for a synchronous ccxt exchange instance."""

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def fetch_ticker(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "last": 67_000.0,
            "close": 67_000.0,
            "previousClose": 66_000.0,
            "change": 1_000.0,
            "percentage": 1.515,
            "baseVolume": 12_345.0,
            "timestamp": 1_747_200_000_000,
        }

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int) -> list[list[float]]:  # noqa: ARG002
        return [
            [1_747_000_000_000, 66_000.0, 66_500.0, 65_500.0, 66_200.0, 1_000.0],
            [1_747_086_400_000, 66_200.0, 67_200.0, 66_100.0, 67_000.0, 1_500.0],
        ]


class _FakeCcxtProExchange:
    """Stand-in for a ccxt.pro async exchange instance."""

    def __init__(self, *_args, **_kwargs) -> None:
        self.has = {"watchTicker": True}
        self._n = 0

    async def watch_ticker(self, symbol: str) -> dict:
        await asyncio.sleep(0)
        self._n += 1
        return {
            "symbol": symbol,
            "last": 67_000.0 + self._n,
            "close": 67_000.0,
            "previousClose": 66_000.0,
            "change": 1_000.0,
            "percentage": 1.5,
            "baseVolume": 100.0,
            "timestamp": 1_747_200_000_000,
        }

    async def close(self) -> None:
        pass


@pytest.fixture
def mock_ccxt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the synchronous ccxt module with fake exchange factories."""
    from services import ccxt_provider

    fake = SimpleNamespace(
        **{name: _FakeCcxtExchange for name in ccxt_provider.SUPPORTED_EXCHANGES}
    )
    monkeypatch.setattr(ccxt_provider, "ccxt", fake)


@pytest.fixture
def mock_ccxtpro(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the ccxt.pro module with fake async exchange factories."""
    from services import ccxt_provider

    fake = SimpleNamespace(
        **{name: _FakeCcxtProExchange for name in ccxt_provider.SUPPORTED_EXCHANGES}
    )
    monkeypatch.setattr(ccxt_provider, "ccxtpro", fake)
