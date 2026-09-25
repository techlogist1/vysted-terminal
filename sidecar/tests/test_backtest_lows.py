"""Pinning tests for the P1/W1 backtest lows batch.

R15-AGENT-079, R15-CODE-PLATFORM-034, R15-CODE-PLATFORM-035,
R15-CODE-PLATFORM-036 — see docs/redesign/verification/vysted-r15-register.json.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from models.backtest import BacktestRequest
from services import backtest_dsl, backtest_engine, backtest_store
from services.backtest_dsl import CustomDslStrategy, compile_rule
from services.backtest_engine import BacktestOrderIntent, BacktestStrategy, Bar, SimPortfolio


@pytest.fixture(autouse=True)
def isolated_registries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VYSTED_DATA_DIR", str(tmp_path))
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    yield
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()


# ---------------------------------------------------------------------------
# R15-AGENT-079 — keyword case-folding
# ---------------------------------------------------------------------------


def test_uppercase_and_or_parse_like_lowercase() -> None:
    lower = compile_rule("sma(20) > 50 and close > 1")
    upper = compile_rule("SMA(20) > 50 AND close > 1")
    assert upper.indicators == lower.indicators
    assert upper.required_bars == lower.required_bars


# ---------------------------------------------------------------------------
# R15-CODE-PLATFORM-036 — CustomDslStrategy compiles each rule once
# ---------------------------------------------------------------------------


def test_each_rule_compiled_once(monkeypatch: pytest.MonkeyPatch) -> None:
    real_compile_rule = backtest_dsl.compile_rule
    calls = {"n": 0}

    def counting_compile_rule(source: str):
        calls["n"] += 1
        return real_compile_rule(source)

    monkeypatch.setattr(backtest_dsl, "compile_rule", counting_compile_rule)
    strategy = CustomDslStrategy({"entry": "sma(20) > sma(50)", "exit": "rsi(14) > 70"})

    assert calls["n"] == 2
    assert strategy.entry.source == "sma(20) > sma(50)"
    assert strategy.exit.source == "rsi(14) > 70"


# ---------------------------------------------------------------------------
# R15-CODE-PLATFORM-034 — walk-forward slices are half-open
# ---------------------------------------------------------------------------


class _NoOpStrategy(BacktestStrategy):
    NAME = "lows_noop"

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        return []


@pytest.mark.asyncio
async def test_each_bar_in_exactly_one_slice(monkeypatch: pytest.MonkeyPatch) -> None:
    backtest_engine.register_strategy("lows_noop", _NoOpStrategy)
    bars = [
        Bar(
            timestamp=f"2024-01-{day:02d}",
            symbol="AAPL",
            open=1,
            high=1,
            low=1,
            close=1,
            volume=1,
        )
        for day in range(1, 11)
    ]

    async def loader(_symbols: list[str], _start: str, _end: str) -> list[Bar]:
        return bars

    real_run_slice = backtest_engine._run_single_slice
    slice_bar_lists: list[list[Bar]] = []

    async def spying_run_slice(strategy, slice_bars, *args, **kwargs):
        slice_bar_lists.append(list(slice_bars))
        return await real_run_slice(strategy, slice_bars, *args, **kwargs)

    monkeypatch.setattr(backtest_engine, "_run_single_slice", spying_run_slice)

    request = BacktestRequest(
        strategyId="lows_noop",
        params={},
        symbols=["AAPL"],
        startDate="2024-01-01",
        endDate="2024-01-10",
        walkForwardSlices=3,
    )
    await backtest_engine.run_backtest(request, bar_loader=loader)

    # First call is the full unsliced run; the rest are the walk-forward slices.
    walk_forward_calls = slice_bar_lists[1:]
    assert walk_forward_calls, "expected at least one walk-forward slice"

    timestamp_hits: dict[str, int] = {}
    for slice_bars in walk_forward_calls:
        for bar in slice_bars:
            timestamp_hits[bar.timestamp] = timestamp_hits.get(bar.timestamp, 0) + 1

    assert all(count == 1 for count in timestamp_hits.values()), timestamp_hits
    assert sum(len(sb) for sb in walk_forward_calls) == len(bars)
