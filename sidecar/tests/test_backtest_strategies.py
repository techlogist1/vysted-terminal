"""Tests for the three concrete backtest strategy archetypes.

Each strategy is exercised against a deterministic in-memory bar fixture
so the assertions are about strategy logic, not provider behaviour. The
engine + registry surfaces are tested separately in
:mod:`test_backtest_engine`.

Three concerns per strategy:

1. The strategy registers under its documented id.
2. Given a price pattern that satisfies the entry condition, the
   strategy emits a buy intent of the configured size.
3. Given a follow-on price pattern that satisfies the exit condition,
   the strategy flatten the position.

Plus engine integration: ``run_backtest`` against each strategy produces
a non-empty equity curve and at least one closed trade in a synthetic
window long enough to trigger both legs.
"""

from __future__ import annotations

import math

import pytest

from models.backtest import BacktestRequest
from services import backtest_engine, backtest_store
from services.backtest_engine import Bar, SimPortfolio
from services.backtest_strategies import (
    STRATEGY_SPECS,
    MeanReversionStrategy,
    RegimeAwareStrategy,
    TrendFollowingStrategy,
    list_strategy_specs,
    register_all,
)


@pytest.fixture(autouse=True)
def isolated_registries() -> None:
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    yield
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()


# ---------------------------------------------------------------------------
# Spec catalogue + registry surface
# ---------------------------------------------------------------------------


def test_strategy_specs_catalog_has_three_archetypes() -> None:
    spec_ids = {spec["id"] for spec in STRATEGY_SPECS}
    assert spec_ids == {"mean_reversion", "trend_following", "regime_aware"}


def test_strategy_specs_carry_params_schema() -> None:
    for spec in list_strategy_specs():
        assert "paramsSchema" in spec
        schema = spec["paramsSchema"]
        assert isinstance(schema, dict)
        assert schema.get("type") == "object"
        assert "properties" in schema


def test_register_all_populates_engine_registry() -> None:
    register_all()
    registered = set(backtest_engine.registered_strategies())
    assert {"mean_reversion", "trend_following", "regime_aware"}.issubset(registered)


def test_register_all_is_idempotent() -> None:
    register_all()
    register_all()
    # Second register call must not duplicate or crash.
    assert backtest_engine.get_strategy_class("mean_reversion") is MeanReversionStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bar(timestamp: str, symbol: str, close: float) -> Bar:
    return Bar(
        timestamp=timestamp,
        symbol=symbol,
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1.0,
    )


# ---------------------------------------------------------------------------
# Mean reversion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mean_reversion_enters_on_negative_z_score() -> None:
    """A sudden one-bar drop after a flat run produces an entry."""
    strategy = MeanReversionStrategy(
        {"window": 5, "entry_z": -1.0, "exit_z": 0.0, "position_size": 10}
    )
    portfolio = SimPortfolio(cash=10_000.0)
    # Six flat bars to populate the window, then a sharp -5% bar.
    bars = [_bar(f"2025-01-0{i + 1}", "T", 100.0) for i in range(6)]
    bars.append(_bar("2025-01-07", "T", 95.0))  # ~-5% drop

    intents_acc: list = []
    for bar in bars:
        intents_acc.extend(await strategy.on_bar(bar, portfolio))
    assert any(intent.quantity == 10 for intent in intents_acc)


@pytest.mark.asyncio
async def test_mean_reversion_exits_on_z_recovery() -> None:
    """After being long, a recovery z above exit_z flattens."""
    strategy = MeanReversionStrategy(
        {"window": 5, "entry_z": -1.0, "exit_z": 0.0, "position_size": 10}
    )
    portfolio = SimPortfolio(cash=10_000.0)

    # Build the position manually to skip the engine-level fill logic.
    from services.backtest_engine import _OpenPosition

    portfolio.positions["T"] = _OpenPosition(
        trade_id="t1",
        symbol="T",
        quantity=10,
        entry_price=95.0,
        entered_at="2025-01-07",
    )

    # Seed window with mostly-flat returns then a strong recovery.
    bars = [_bar(f"2025-01-0{i + 1}", "T", 100.0) for i in range(6)]
    bars.append(_bar("2025-01-07", "T", 95.0))
    bars.append(_bar("2025-01-08", "T", 105.0))  # ~+10% recovery

    last_intent_qty: float | None = None
    for bar in bars:
        for intent in await strategy.on_bar(bar, portfolio):
            last_intent_qty = intent.quantity
    assert last_intent_qty is not None
    assert last_intent_qty < 0  # exit/flatten intent


@pytest.mark.asyncio
async def test_mean_reversion_zero_variance_window_emits_no_signal() -> None:
    """When the rolling stdev is zero, no z-score can be computed."""
    strategy = MeanReversionStrategy({"window": 5, "entry_z": -2.0})
    portfolio = SimPortfolio(cash=10_000.0)
    intents: list = []
    for i in range(10):
        intents.extend(await strategy.on_bar(_bar(f"2025-01-{i + 1:02d}", "T", 100.0), portfolio))
    assert intents == []


# ---------------------------------------------------------------------------
# Trend following
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trend_following_buys_on_golden_cross_above_200ma() -> None:
    """A sustained uptrend produces a golden-cross buy."""
    strategy = TrendFollowingStrategy({"short_window": 3, "long_window": 5, "position_size": 50})
    portfolio = SimPortfolio(cash=100_000.0)
    # Down-then-up pattern: short MA crosses above long MA.
    closes = [100, 99, 98, 97, 96, 102, 108, 115, 120]
    bars = [_bar(f"2025-01-{i + 1:02d}", "T", c) for i, c in enumerate(closes)]
    fired = False
    for bar in bars:
        for intent in await strategy.on_bar(bar, portfolio):
            if intent.quantity == 50:
                fired = True
    assert fired, "expected a golden-cross entry"


@pytest.mark.asyncio
async def test_trend_following_skips_until_enough_bars() -> None:
    """No signal until the long_window has filled."""
    strategy = TrendFollowingStrategy({"short_window": 3, "long_window": 5})
    portfolio = SimPortfolio(cash=100_000.0)
    intents: list = []
    for i in range(4):  # only 4 bars; long_window=5
        intents.extend(
            await strategy.on_bar(_bar(f"2025-01-{i + 1:02d}", "T", 100.0 + i), portfolio)
        )
    assert intents == []


@pytest.mark.asyncio
async def test_trend_following_death_cross_sells() -> None:
    """A death cross while long produces a sell intent."""
    strategy = TrendFollowingStrategy({"short_window": 3, "long_window": 5, "position_size": 50})
    portfolio = SimPortfolio(cash=100_000.0)

    from services.backtest_engine import _OpenPosition

    portfolio.positions["T"] = _OpenPosition(
        trade_id="t1",
        symbol="T",
        quantity=50,
        entry_price=120.0,
        entered_at="2025-01-09",
    )

    closes = [100, 105, 110, 115, 120, 118, 112, 105, 95, 88]
    bars = [_bar(f"2025-01-{i + 1:02d}", "T", c) for i, c in enumerate(closes)]
    saw_exit = False
    for bar in bars:
        for intent in await strategy.on_bar(bar, portfolio):
            if intent.quantity < 0:
                saw_exit = True
    assert saw_exit


# ---------------------------------------------------------------------------
# Regime-aware
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_regime_aware_uses_low_vol_size_in_calm_regime() -> None:
    strategy = RegimeAwareStrategy(
        {
            "vol_window": 5,
            "low_vol_size": 100,
            "high_vol_size": 25,
            "vol_threshold": 0.05,
        }
    )
    portfolio = SimPortfolio(cash=100_000.0)
    # Gentle uptrend — stdev of small positive returns is well below 0.05.
    closes = [100, 100.5, 101, 101.5, 102, 102.5, 103]
    sizes: list[float] = []
    for i, c in enumerate(closes):
        for intent in await strategy.on_bar(_bar(f"2025-01-{i + 1:02d}", "T", c), portfolio):
            sizes.append(intent.quantity)
    assert sizes and sizes[0] == 100  # low-vol size


@pytest.mark.asyncio
async def test_regime_aware_uses_high_vol_size_in_choppy_regime() -> None:
    strategy = RegimeAwareStrategy(
        {
            "vol_window": 5,
            "low_vol_size": 100,
            "high_vol_size": 25,
            "vol_threshold": 0.005,  # very low threshold so any chop trips it
        }
    )
    portfolio = SimPortfolio(cash=100_000.0)
    closes = [100, 105, 95, 110, 90, 115, 120]  # high stdev, ends positive
    sizes: list[float] = []
    for i, c in enumerate(closes):
        for intent in await strategy.on_bar(_bar(f"2025-01-{i + 1:02d}", "T", c), portfolio):
            sizes.append(intent.quantity)
    assert sizes and sizes[0] == 25  # high-vol size


@pytest.mark.asyncio
async def test_regime_aware_exits_on_negative_momentum() -> None:
    strategy = RegimeAwareStrategy({"vol_window": 3, "low_vol_size": 100, "vol_threshold": 1.0})
    portfolio = SimPortfolio(cash=100_000.0)
    from services.backtest_engine import _OpenPosition

    portfolio.positions["T"] = _OpenPosition(
        trade_id="t1",
        symbol="T",
        quantity=100,
        entry_price=100,
        entered_at="2025-01-01",
    )
    # Three-bar decline so the rolling mean turns negative.
    closes = [100, 99, 98, 97]
    saw_exit = False
    for i, c in enumerate(closes):
        for intent in await strategy.on_bar(_bar(f"2025-01-{i + 1:02d}", "T", c), portfolio):
            if intent.quantity < 0:
                saw_exit = True
    assert saw_exit


# ---------------------------------------------------------------------------
# Engine integration — each strategy round-trips through run_backtest
# ---------------------------------------------------------------------------


def _generate_zigzag_bars(start: int = 1, n: int = 60, base: float = 100.0) -> list[Bar]:
    """Synthetic zigzag — long enough to fire mean-reversion + momentum."""
    bars: list[Bar] = []
    for i in range(n):
        amplitude = 4.0 * math.sin(i / 3.0)
        close = base + i * 0.5 + amplitude
        day = ((start + i) % 28) + 1
        month = ((start + i) // 28) + 1
        bars.append(
            Bar(
                timestamp=f"2025-{month:02d}-{day:02d}",
                symbol="ZIG",
                open=close,
                high=close + 1,
                low=close - 1,
                close=close,
                volume=1000.0,
            )
        )
    return bars


@pytest.mark.asyncio
async def test_mean_reversion_runs_end_to_end_through_engine() -> None:
    register_all()
    bars = _generate_zigzag_bars(n=80)

    async def loader(_s: list[str], _start: str, _end: str) -> list[Bar]:
        return bars

    request = BacktestRequest(
        strategyId="mean_reversion",
        params={"window": 10, "entry_z": -0.5, "exit_z": 0.0, "position_size": 10},
        symbols=["ZIG"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=50_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=loader)
    assert len(result.equity_curve) == len(bars)
    assert len(result.trades) >= 1


@pytest.mark.asyncio
async def test_trend_following_runs_end_to_end_through_engine() -> None:
    register_all()
    # First 100 bars trend down, next 200 trend up — guarantees a
    # below → above transition once both MAs have filled.
    down = list(range(200, 100, -1))  # 100 → 100
    up = list(range(100, 100 + 200))  # 100 → 299
    closes = down + up
    bars = [
        Bar(
            timestamp=f"2025-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}",
            symbol="UP",
            open=c,
            high=c + 1,
            low=c - 1,
            close=float(c),
            volume=1.0,
        )
        for i, c in enumerate(closes)
    ]

    async def loader(_s: list[str], _start: str, _end: str) -> list[Bar]:
        return bars

    request = BacktestRequest(
        strategyId="trend_following",
        params={"short_window": 10, "long_window": 50, "position_size": 5},
        symbols=["UP"],
        startDate="2025-01-01",
        endDate="2026-12-31",
        initialCapital=100_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=loader)
    assert len(result.equity_curve) == len(bars)
    assert any(t.side == "buy" for t in result.trades)


@pytest.mark.asyncio
async def test_regime_aware_runs_end_to_end_through_engine() -> None:
    register_all()
    bars = _generate_zigzag_bars(n=40)

    async def loader(_s: list[str], _start: str, _end: str) -> list[Bar]:
        return bars

    request = BacktestRequest(
        strategyId="regime_aware",
        params={
            "vol_window": 5,
            "low_vol_size": 10,
            "high_vol_size": 5,
            "vol_threshold": 0.01,
        },
        symbols=["ZIG"],
        startDate="2025-01-01",
        endDate="2025-12-31",
        initialCapital=50_000.0,
    )
    result = await backtest_engine.run_backtest(request, bar_loader=loader)
    assert len(result.equity_curve) == len(bars)
