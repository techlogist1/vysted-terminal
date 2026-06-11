"""Agent-vs-engine backtest parity (R10 — the E5 capability is REAL, not listed).

E5's symptom was the copilot claiming "I don't have a direct backtesting tool";
the toolbelt-integrity test proves the tool is GRANTED — this one proves the
granted tool produces EXACTLY what the engine produces: fixed synthetic bars →
``backtest_engine.run_backtest`` directly vs ``invoke_tool("run_custom_backtest")``
through the agent registry → identical results minus the run_id, and the
``backtest_summary`` digest resolves the same numbers. No network: the bar
loader is a fixture in both lanes.
"""

from __future__ import annotations

from typing import Any

import pytest

from models.backtest import BacktestRequest
from services import agent_tools, backtest_engine, backtest_store, backtest_strategies
from services.agent_tools import run_custom_backtest as run_custom_backtest_mod
from services.backtest_engine import Bar

ENTRY = "close > sma(3)"
EXIT = "close < sma(3)"
SYMBOLS = ["AAPL"]
START, END = "2025-01-01", "2025-01-12"
POSITION_SIZE = 10
INITIAL_CAPITAL = 50_000.0

#: Fixed synthetic closes — two clean round trips through the sma(3) cross.
_CLOSES = [100.0, 100.0, 100.0, 110.0, 112.0, 90.0, 85.0, 99.0, 120.0, 80.0]


def _bars() -> list[Bar]:
    return [
        Bar(
            timestamp=f"2025-01-{day + 1:02d}",
            symbol="AAPL",
            open=close,
            high=close + 1,
            low=close - 1,
            close=close,
            volume=1000,
        )
        for day, close in enumerate(_CLOSES)
    ]


async def _fixed_loader(_symbols: list[str], _start: str, _end: str) -> list[Bar]:
    return _bars()


@pytest.fixture(autouse=True)
def _isolated() -> Any:
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    backtest_strategies.register_all()
    agent_tools.reset_for_tests()
    agent_tools.register_v0_5_0_tools()
    agent_tools.register_v0_6_0_tools()
    yield
    backtest_engine.reset_registry_for_tests()
    backtest_store.reset_for_tests()
    agent_tools.reset_for_tests()


def _request() -> BacktestRequest:
    return BacktestRequest(
        strategyId="custom",
        params={"entry": ENTRY, "exit": EXIT, "position_size": POSITION_SIZE},
        symbols=SYMBOLS,
        startDate=START,
        endDate=END,
        initialCapital=INITIAL_CAPITAL,
        walkForwardSlices=1,
    )


def _strip_run_ids(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # ``id`` is the per-trade uuid minted per run — like run_id it is the only
    # legitimate difference between two identical executions.
    return [{k: v for k, v in t.items() if k not in ("runId", "run_id", "id")} for t in trades]


@pytest.mark.asyncio
async def test_agent_tool_matches_direct_engine_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct engine vs the agent's registry tool on the SAME fixed bars:
    metrics + the full trade log are identical (run_id aside)."""
    direct = await backtest_engine.run_backtest(_request(), bar_loader=_fixed_loader)

    monkeypatch.setattr(run_custom_backtest_mod, "load_bars", _fixed_loader)
    via_agent = await agent_tools.invoke_tool(
        "run_custom_backtest",
        {
            "entry": ENTRY,
            "exit": EXIT,
            "symbols": SYMBOLS,
            "start_date": START,
            "end_date": END,
            "position_size": POSITION_SIZE,
            "initial_capital": INITIAL_CAPITAL,
        },
    )
    assert via_agent["ok"] is True
    assert via_agent["runId"] != direct.run_id  # two runs, two ids — the ONE allowed diff

    # Metrics identical.
    assert via_agent["metrics"] == direct.metrics.model_dump(by_alias=True)
    # The agent run landed in the shared store with the SAME trade log.
    cached = backtest_store.get(via_agent["runId"])
    assert cached is not None
    direct_trades = [t.model_dump(by_alias=True) for t in direct.trades]
    agent_trades = [t.model_dump(by_alias=True) for t in cached.trades]
    assert _strip_run_ids(agent_trades) == _strip_run_ids(direct_trades)
    # Equity curves identical point-for-point.
    assert [p.model_dump(by_alias=True) for p in cached.equity_curve] == [
        p.model_dump(by_alias=True) for p in direct.equity_curve
    ]
    # The request the engine saw is the request the tool authored.
    assert cached.request.params["entry"] == ENTRY
    assert cached.request.symbols == SYMBOLS
    assert via_agent["metrics"]["tradeCount"] >= 1, "fixture must produce real trades"


@pytest.mark.asyncio
async def test_backtest_summary_digest_matches_the_tool_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``backtest_summary`` over the agent run's id digests the SAME metrics and
    trades the tool returned — one cached result, two consistent reads."""
    monkeypatch.setattr(run_custom_backtest_mod, "load_bars", _fixed_loader)
    via_agent = await agent_tools.invoke_tool(
        "run_custom_backtest",
        {
            "entry": ENTRY,
            "exit": EXIT,
            "symbols": SYMBOLS,
            "start_date": START,
            "end_date": END,
            "position_size": POSITION_SIZE,
            "initial_capital": INITIAL_CAPITAL,
        },
    )
    assert via_agent["ok"] is True

    summary = await agent_tools.invoke_tool("backtest_summary", {"run_id": via_agent["runId"]})
    assert summary["ok"] is True
    digest = summary["summary"] if "summary" in summary else summary
    # The digest's headline numbers match the tool's own return.
    assert digest["metrics"] == via_agent["metrics"]
    assert digest["runId"] == via_agent["runId"]
    assert _strip_run_ids(digest["recentTrades"]) == _strip_run_ids(via_agent["recentTrades"])
    assert _strip_run_ids(digest["bestTrades"]) == _strip_run_ids(via_agent["bestTrades"])
    assert _strip_run_ids(digest["worstTrades"]) == _strip_run_ids(via_agent["worstTrades"])
