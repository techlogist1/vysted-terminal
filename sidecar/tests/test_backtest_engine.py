"""Tests for the backtest engine + agent_tools backtest_summary tool.

Foundation tests (concrete strategies + production bar loader are Teammate K).
A minimal in-test strategy ("buy-and-hold-on-day-2") exercises the engine
end-to-end.
"""

from __future__ import annotations

import pytest

from models.backtest import BacktestFeeModel, BacktestRequest
from services import agent_tools, backtest_engine, backtest_store
from services.backtest_engine import (
    BacktestEngineError,
    BacktestOrderIntent,
    BacktestStrategy,
    Bar,
    SimPortfolio,
)


@pytest.fixture(autouse=True)
def isolated_registries() -> None:
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    yield
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class BuyAndHoldDay2(BacktestStrategy):
    """Buy 100 shares of the first symbol on bar 2, hold to end."""

    NAME = "buy_and_hold_day2"

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._fired = False

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        if self._fired:
            return []
        if not portfolio.has_position(bar.symbol):
            # Trigger on day 2; we'll use whatever the second bar happens to be.
            if not hasattr(self, "_seen"):
                self._seen = 0  # type: ignore[attr-defined]
            self._seen += 1  # type: ignore[attr-defined]
            if self._seen == 2:  # type: ignore[attr-defined]
                self._fired = True
                return [BacktestOrderIntent(symbol=bar.symbol, quantity=100, reason="entry")]
        return []


class SellOnLast(BacktestStrategy):
    """Buy on bar 1, sell on the last bar — pairs with BuyAndHoldDay2 for full roundtrips."""

    NAME = "buy_sell_window"

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._bar_count = 0
        self._total_bars = params.get("total_bars", 3)

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        self._bar_count += 1
        if self._bar_count == 1 and not portfolio.has_position(bar.symbol):
            return [BacktestOrderIntent(symbol=bar.symbol, quantity=10, reason="enter")]
        if self._bar_count == self._total_bars and portfolio.has_position(bar.symbol):
            qty = portfolio.positions[bar.symbol].quantity
            return [BacktestOrderIntent(symbol=bar.symbol, quantity=-qty, reason="exit")]
        return []


def _bars(symbol: str = "AAPL") -> list[Bar]:
    return [
        Bar(timestamp="2025-01-02", symbol=symbol, open=100, high=102, low=99, close=101, volume=1),
        Bar(
            timestamp="2025-01-03", symbol=symbol, open=101, high=104, low=100, close=103, volume=1
        ),
        Bar(
            timestamp="2025-01-06", symbol=symbol, open=103, high=106, low=102, close=105, volume=1
        ),
        Bar(
            timestamp="2025-01-07", symbol=symbol, open=105, high=107, low=103, close=104, volume=1
        ),
        Bar(
            timestamp="2025-01-08", symbol=symbol, open=104, high=109, low=103, close=108, volume=1
        ),
    ]


async def _loader(_symbols: list[str], _start: str, _end: str) -> list[Bar]:
    return _bars()


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_strategy_raises() -> None:
    request = BacktestRequest(
        strategyId="not_registered",
        params={},
        symbols=["AAPL"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=100_000.0,
    )
    with pytest.raises(BacktestEngineError, match="unknown strategy"):
        await backtest_engine.run_backtest(request, bar_loader=_loader)


@pytest.mark.asyncio
async def test_buy_and_hold_runs_end_to_end() -> None:
    backtest_engine.register_strategy("buy_and_hold", BuyAndHoldDay2)
    request = BacktestRequest(
        strategyId="buy_and_hold",
        params={},
        symbols=["AAPL"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=100_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=_loader)
    assert result.metrics.trade_count == 0  # never closed → trade_count of CLOSED trades is 0
    assert len(result.trades) == 1  # one open trade
    assert len(result.equity_curve) == 5


@pytest.mark.asyncio
async def test_buy_sell_records_closed_trade_with_pnl() -> None:
    backtest_engine.register_strategy("buy_sell", SellOnLast)
    request = BacktestRequest(
        strategyId="buy_sell",
        params={"total_bars": 5},
        symbols=["AAPL"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=100_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=_loader)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_price is not None
    assert trade.pnl is not None
    # Bought at 101 (≈), sold at 108 (≈) — fees nibble but P&L stays positive.
    assert trade.pnl > 0
    assert result.metrics.win_rate == 1.0
    assert result.metrics.trade_count == 1


@pytest.mark.asyncio
async def test_walk_forward_produces_slices() -> None:
    backtest_engine.register_strategy("buy_sell", SellOnLast)
    request = BacktestRequest(
        strategyId="buy_sell",
        params={"total_bars": 2},
        symbols=["AAPL"],
        startDate="2025-01-02",
        endDate="2025-01-08",
        initialCapital=100_000.0,
        walkForwardSlices=2,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=_loader)
    assert result.walk_forward_slices is not None
    assert len(result.walk_forward_slices) == 2


# ---------------------------------------------------------------------------
# agent_tools.backtest_summary — registered at import time
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backtest_summary_tool_registered() -> None:
    assert agent_tools.is_registered("backtest_summary")


@pytest.mark.asyncio
async def test_backtest_summary_returns_error_for_missing_run() -> None:
    summary = await agent_tools.invoke_tool("backtest_summary", {"run_id": "ghost"})
    assert summary["ok"] is False
    assert "no cached backtest" in summary["error"]


@pytest.mark.asyncio
async def test_backtest_summary_returns_digest_for_real_run() -> None:
    backtest_engine.register_strategy("buy_sell", SellOnLast)
    request = BacktestRequest(
        strategyId="buy_sell",
        params={"total_bars": 5},
        symbols=["AAPL"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=100_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=_loader)
    backtest_store.put(result)

    summary = await agent_tools.invoke_tool("backtest_summary", {"run_id": result.run_id})
    assert summary["ok"] is True
    assert summary["strategyId"] == "buy_sell"
    assert "metrics" in summary
    assert "recentTrades" in summary
    assert "bestTrades" in summary
    assert "worstTrades" in summary
    # No raw equity_curve — keep the agent prompt compact.
    assert "equityCurve" not in summary


@pytest.mark.asyncio
async def test_unaffordable_position_surfaces_warning_not_silent_zero() -> None:
    """D65 (R12): entries the portfolio cannot afford must be DISCLOSED.

    A position size costing more than initial capital used to produce a
    confident all-zero result (logger-only warning). The result now carries
    a ``warnings`` entry with the skip count and shortfall.
    """
    backtest_engine.register_strategy("buy_and_hold_poor", BuyAndHoldDay2)
    request = BacktestRequest(
        strategyId="buy_and_hold_poor",
        params={},
        symbols=["AAPL"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=100.0,  # 100 shares @ ~100 needs ~10,000 — never affordable
    )
    result = await backtest_engine.run_backtest(request, bar_loader=_loader)
    assert result.metrics.trade_count == 0
    assert result.trades == []
    assert result.warnings is not None and len(result.warnings) == 1
    assert "skipped" in result.warnings[0]
    assert "position size" in result.warnings[0]


@pytest.mark.asyncio
async def test_clean_run_carries_no_warnings() -> None:
    backtest_engine.register_strategy("buy_sell_clean", SellOnLast)
    request = BacktestRequest(
        strategyId="buy_sell_clean",
        params={"total_bars": 5},
        symbols=["AAPL"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=100_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=_loader)
    assert result.warnings is None


# ---------------------------------------------------------------------------
# R15-DATA-009: one equity-curve point per timestamp, not per bar
# ---------------------------------------------------------------------------


class BuyAllInOnce(BacktestStrategy):
    """Buy a fixed quantity of every symbol on the first bar it sees, then hold."""

    NAME = "buy_all_in_once"

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._bought: set[str] = set()
        self._quantity = params["quantity"]

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        if bar.symbol in self._bought:
            return []
        self._bought.add(bar.symbol)
        return [BacktestOrderIntent(symbol=bar.symbol, quantity=self._quantity, reason="entry")]


def _identical_path_bars(symbols: list[str], prices: list[float]) -> list[Bar]:
    """N symbols, each following the SAME price path across the same dates."""
    dates = [f"2025-01-{2 + i:02d}" for i in range(len(prices))]
    bars: list[Bar] = []
    for bar_date, price in zip(dates, prices, strict=True):
        for symbol in symbols:
            bars.append(
                Bar(
                    timestamp=bar_date,
                    symbol=symbol,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=1,
                )
            )
    return bars


_ZERO_FEES = BacktestFeeModel(feeBps=0, slippageBps=0)


@pytest.mark.asyncio
async def test_multi_symbol_equity_curve_has_one_point_per_timestamp() -> None:
    """R15-DATA-009: N symbols sharing a date must not yield N equity points."""
    prices = [100.0, 102.0, 101.0, 105.0, 104.0, 108.0, 107.0, 110.0]

    for n in (1, 2, 4):
        symbols = [f"SYM{i}" for i in range(n)]
        strategy_name = f"buy_all_in_once_curve_{n}"
        backtest_engine.register_strategy(strategy_name, BuyAllInOnce)

        async def loader(
            _symbols: list[str],
            _start: str,
            _end: str,
            _symbols_list: list[str] = symbols,
            _prices: list[float] = prices,
        ) -> list[Bar]:
            return _identical_path_bars(_symbols_list, _prices)

        request = BacktestRequest(
            strategyId=strategy_name,
            params={"quantity": 100_000.0 / n / prices[0]},
            symbols=symbols,
            startDate="2025-01-01",
            endDate="2025-12-31",
            initialCapital=100_000.0,
            feeModel=_ZERO_FEES,
        )
        result = await backtest_engine.run_backtest(request, bar_loader=loader)
        assert len(result.equity_curve) == len(prices), f"n={n}"


@pytest.mark.asyncio
async def test_multi_symbol_sharpe_does_not_scale_with_symbol_count() -> None:
    """R15-DATA-009: the Sharpe must not inflate with the number of symbols.

    N symbols following an identical price path, with the initial capital
    split evenly and fully invested at t0 (no idle cash), produce the SAME
    per-date percentage returns regardless of N. Before the fix, N symbols
    emitted N equity-curve points per date, so ``_compute_metrics`` treated
    them as N separate trading days and inflated Sharpe by roughly sqrt(N).
    """
    prices = [100.0, 102.0, 101.0, 105.0, 104.0, 108.0, 107.0, 110.0, 109.0, 113.0]
    sharpes: dict[int, float] = {}

    for n in (1, 2, 4):
        symbols = [f"SYM{i}" for i in range(n)]
        strategy_name = f"buy_all_in_once_sharpe_{n}"
        backtest_engine.register_strategy(strategy_name, BuyAllInOnce)

        async def loader(
            _symbols: list[str],
            _start: str,
            _end: str,
            _symbols_list: list[str] = symbols,
            _prices: list[float] = prices,
        ) -> list[Bar]:
            return _identical_path_bars(_symbols_list, _prices)

        request = BacktestRequest(
            strategyId=strategy_name,
            params={"quantity": 100_000.0 / n / prices[0]},
            symbols=symbols,
            startDate="2025-01-01",
            endDate="2025-12-31",
            initialCapital=100_000.0,
            feeModel=_ZERO_FEES,
        )
        result = await backtest_engine.run_backtest(request, bar_loader=loader)
        sharpes[n] = result.metrics.sharpe

    assert sharpes[1] != 0.0
    assert sharpes[1] == pytest.approx(sharpes[2], rel=1e-9)
    assert sharpes[1] == pytest.approx(sharpes[4], rel=1e-9)
