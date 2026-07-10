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
from services import provider_health


@pytest.fixture(autouse=True)
def _reset_provider_health() -> None:
    """The Yahoo-family circuit breaker (R11/D53) is process-global state —
    a 429 storm simulated by one test must never leak an open circuit into
    the next."""
    provider_health.reset_for_tests()
    yield
    provider_health.reset_for_tests()


@pytest.fixture
def client() -> TestClient:
    """A TestClient bound to a freshly built app instance."""
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _no_network_dividend_history(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the R11/D56 dividend-history cross-check off the network.

    ``snapshot_structured`` now calls ``dividend_history.get_dividend_ttm`` on
    every research snapshot (a yfinance ``.dividends`` pull); the research tests
    inject a fake ``tool_call`` but not a fake yfinance, so without this the new
    seam would reach the live network. Stub it to ``None`` (no cross-check card)
    for every test EXCEPT ``test_dividend_history`` — the module that exercises
    the real function with ``yf.Ticker`` mocked directly."""
    if request.module.__name__.rsplit(".", 1)[-1] == "test_dividend_history":
        return
    from services import dividend_history

    async def _stub(_symbol: str) -> None:
        return None

    monkeypatch.setattr(dividend_history, "get_dividend_ttm", _stub)


@pytest.fixture(autouse=True)
def _no_network_growth_check(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the R12/D66 quarterly-growth cross-check off the network.

    ``snapshot_structured`` calls ``growth_check.get_quarterly_yoy`` (a
    yfinance ``.quarterly_income_stmt`` pull) whenever the fundamentals leg
    carries provider growth scalars — same seam-vs-network shape as the D56
    dividend stub above. Stub it to ``None`` (no computed figure, no conflict)
    for every test EXCEPT ``test_growth_check`` — the module that exercises the
    real function with ``yf.Ticker`` mocked directly."""
    if request.module.__name__.rsplit(".", 1)[-1] == "test_growth_check":
        return
    from services import growth_check

    async def _stub(_symbol: str) -> None:
        return None

    monkeypatch.setattr(growth_check, "get_quarterly_yoy", _stub)


@pytest.fixture(autouse=True)
def _no_network_ownership_check(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the R13/D68 exchange-ownership cross-check off the network.

    ``snapshot_structured`` calls ``ownership_check.get_exchange_ownership`` when
    the fundamentals leg carries a provider ownership scalar — same seam-vs-
    network shape as the D56/D66 stubs above. Stub it to ``None`` (no exchange
    facts) for every test EXCEPT ``test_ownership_check`` — the module that
    exercises the real function with ``corporate_disclosures.get_shareholding``
    mocked directly."""
    if request.module.__name__.rsplit(".", 1)[-1] == "test_ownership_check":
        return
    from services import ownership_check

    async def _stub(_symbol: str) -> None:
        return None

    monkeypatch.setattr(ownership_check, "get_exchange_ownership", _stub)


@pytest.fixture(autouse=True)
def _no_network_dividend_actions(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the R13/D57 declared-unpaid-dividend cross-check off the network.

    ``snapshot_structured`` calls ``dividend_actions.get_declared_unpaid_dividend``
    on every research snapshot (an NSE corporate-actions pull) — same seam-vs-
    network shape as the D56/D66 stubs above. Stub it to ``None`` (no declared
    figure) for every test EXCEPT ``test_dividend_actions`` — the module that
    exercises the real function with ``nse_provider.get_corporate_actions``
    mocked directly."""
    if request.module.__name__.rsplit(".", 1)[-1] == "test_dividend_actions":
        return
    from services import dividend_actions

    async def _stub(_symbol: str) -> None:
        return None

    monkeypatch.setattr(dividend_actions, "get_declared_unpaid_dividend", _stub)


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
            # yfinance 1.3.0 returns ``dividendYield`` as a percentage number
            # (e.g. ``0.36`` for AAPL). The provider divides by 100 so the
            # ``Fundamentals.dividend_yield`` field carries a true fraction.
            "dividendYield": 0.44,
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
