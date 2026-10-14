"""Agent tool — ``run_custom_backtest`` (R7 hackability Pillar 2).

Lets the agent AUTHOR a strategy as a declarative entry/exit DSL definition
and EXECUTE it server-side in the simulated backtest engine, in one call.
The definition is parsed by :mod:`services.backtest_dsl`'s restricted
recursive-descent grammar — no eval/exec of arbitrary code, ever. §6.5: the
backtest engine never touches order paths; this tool only simulates.

The result is cached in :mod:`services.backtest_store` under the returned
``runId`` — exactly where UI-started runs land — so ``backtest_summary``
resolves it and the frontend renders the full result in BacktestResultView
via ``GET /backtest/runs/{run_id}``.

Exposes :func:`register` (the ``price_data`` convention). NOT registered at
import time on purpose: ``test_capability_catalog.py``'s SC-006 gate requires
every registered handler to carry a catalog ``Capability``, and catalog.py is
owned by another track — the lead wires BOTH the catalog entry and the one
``register()`` call together. Exact paste-ready entries:
``docs/redesign/INTEGRATION_NOTES_R7_HACK.md``.
"""

from __future__ import annotations

from typing import Any

from models.backtest import BacktestRequest
from services import backtest_engine, backtest_store
from services.agent_tools import register_tool
from services.backtest_dsl import validate_definition
from services.bar_loader import load_bars

_MAX_TRADES_RETURNED = 20


def _digest(result: Any) -> dict[str, Any]:
    """The compact BacktestSummary-shaped digest (mirrors backtest_summary)."""
    closed = [t for t in result.trades if t.pnl is not None]
    closed_sorted = sorted(closed, key=lambda t: t.pnl or 0.0, reverse=True)
    return {
        "runId": result.run_id,
        "strategyId": result.strategy_id,
        "strategyParams": result.request.params,
        "symbols": result.request.symbols,
        "startDate": result.request.start_date,
        "endDate": result.request.end_date,
        "metrics": result.metrics.model_dump(by_alias=True),
        "warnings": result.warnings,
        "recentTrades": [
            t.model_dump(by_alias=True) for t in result.trades[-_MAX_TRADES_RETURNED:]
        ],
        "bestTrades": [t.model_dump(by_alias=True) for t in closed_sorted[:3]],
        "worstTrades": [t.model_dump(by_alias=True) for t in closed_sorted[-3:][::-1]],
        "walkForwardSlices": (
            [s.model_dump(by_alias=True) for s in (result.walk_forward_slices or [])]
            if result.walk_forward_slices
            else None
        ),
    }


async def _run_custom_backtest(args: dict[str, Any]) -> dict[str, Any]:
    """Author + run a custom-DSL backtest; return the run digest.

    Args:
        entry: entry rule, e.g. ``"sma(20) > sma(50)"`` (required).
        exit: exit rule, e.g. ``"rsi(14) > 70"`` (required).
        symbols: tickers to trade (required, non-empty).
        start_date / end_date: ISO ``YYYY-MM-DD`` (required).
        position_size: shares per trade (default 100).
        initial_capital: starting cash (default 100_000).
        walk_forward_slices: 1..10 (default 1).
    """
    definition: dict[str, Any] = {
        "entry": args.get("entry"),
        "exit": args.get("exit"),
    }
    if "position_size" in args:
        definition["position_size"] = args.get("position_size")
    report = validate_definition(definition)
    if not report["ok"]:
        return {
            "ok": False,
            "error": "invalid strategy definition",
            "errors": report["errors"],
        }

    symbols = args.get("symbols")
    if not isinstance(symbols, list) or not symbols or not all(isinstance(s, str) for s in symbols):
        return {"ok": False, "error": "symbols must be a non-empty list of strings"}
    start_date = args.get("start_date") or args.get("startDate")
    end_date = args.get("end_date") or args.get("endDate")
    if not isinstance(start_date, str) or not isinstance(end_date, str):
        return {"ok": False, "error": "start_date and end_date are required (YYYY-MM-DD)"}

    try:
        request = BacktestRequest(
            strategyId="custom",
            params={
                "entry": definition["entry"],
                "exit": definition["exit"],
                "position_size": definition.get("position_size", 100),
            },
            symbols=[s.strip().upper() for s in symbols],
            startDate=start_date,
            endDate=end_date,
            initialCapital=float(args.get("initial_capital", 100_000.0)),
            walkForwardSlices=int(args.get("walk_forward_slices", 1)),
        )
    except (ValueError, TypeError) as exc:
        return {"ok": False, "error": f"invalid backtest request: {exc}"}

    try:
        result = await backtest_engine.run_backtest(request, bar_loader=load_bars)
    except backtest_engine.BacktestEngineError as exc:
        return {"ok": False, "error": str(exc)}
    backtest_store.put(result)

    return {
        "ok": True,
        "indicators": report["indicators"],
        "requiredBars": report["requiredBars"],
        **_digest(result),
    }


def register() -> None:
    """Register the handler. The lead calls this alongside the catalog entry
    (SC-006 parity: a registered handler without a Capability fails the gate,
    and vice versa for ``read_handler`` entries)."""
    register_tool("run_custom_backtest", _run_custom_backtest)


__all__ = ["_run_custom_backtest", "register"]
