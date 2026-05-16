"""Foundation agent tool — ``backtest_summary``.

Registers at module import so Strategy Critic's tools list
``["backtest_summary", "price_data", "fundamentals"]`` resolves the first
entry the moment :mod:`services.agent_tools` is imported. Migrated from
v0.5.0's flat ``agent_tools.py`` with no behaviour change.
"""

from __future__ import annotations

from typing import Any

from services import backtest_store
from services.agent_tools import register_tool


async def _backtest_summary(args: dict[str, Any]) -> dict[str, Any]:
    """Return a digest of a cached :class:`BacktestResult`.

    Args:
        run_id: stable id assigned by ``backtest_engine.run_backtest``.

    Returns the :class:`BacktestSummary` shape (compact — recent trades,
    best/worst trades, metrics, walk-forward slices — but NOT the raw
    equity curve, which is too long to feed to the model).
    """
    run_id = args.get("run_id") or args.get("runId")
    if not isinstance(run_id, str) or not run_id:
        return {
            "ok": False,
            "error": "missing or non-string run_id",
        }
    result = backtest_store.get(run_id)
    if result is None:
        return {
            "ok": False,
            "error": f"no cached backtest with run_id={run_id!r}",
        }

    # Top-N + bottom-N closed trades for outlier reasoning.
    closed = [t for t in result.trades if t.pnl is not None]
    closed_sorted = sorted(closed, key=lambda t: t.pnl or 0.0, reverse=True)
    best = closed_sorted[:3]
    worst = closed_sorted[-3:][::-1]
    recent = result.trades[-20:]

    return {
        "ok": True,
        "runId": result.run_id,
        "strategyId": result.strategy_id,
        "strategyParams": result.request.params,
        "symbols": result.request.symbols,
        "startDate": result.request.start_date,
        "endDate": result.request.end_date,
        "metrics": result.metrics.model_dump(by_alias=True),
        "recentTrades": [t.model_dump(by_alias=True) for t in recent],
        "bestTrades": [t.model_dump(by_alias=True) for t in best],
        "worstTrades": [t.model_dump(by_alias=True) for t in worst],
        "walkForwardSlices": (
            [s.model_dump(by_alias=True) for s in (result.walk_forward_slices or [])]
            if result.walk_forward_slices
            else None
        ),
    }


# Register at import time — preserves v0.5.0 behaviour: Strategy Critic's
# tools list sees ``backtest_summary`` resolved as soon as agent_tools is
# imported, without an explicit ``register_*`` call.
register_tool("backtest_summary", _backtest_summary)


__all__ = ["_backtest_summary"]
