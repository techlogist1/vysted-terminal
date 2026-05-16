"""Agent tool registry + the v0.5.0 foundation tools.

Phase 3 shipped the AgentSpec.tools field on each agent JSON config
(e.g. strategy_critic.json lists ``["backtest_summary", "price_data",
"fundamentals"]``) but the runtime did not actually dispatch tool calls
— provider adapters streamed text only. Phase 4 wires the registry so
agents can call backtest_summary against a real BacktestResult.

The contract:

  - ``register_tool(tool_id, handler)`` — keys an ``AgentToolHandler``
    into a module-level registry; plugin-contributed tools register
    through the same surface in future phases.
  - ``invoke_tool(tool_id, args)`` — called by the agent runtime when a
    provider emits a tool_use block; returns a JSON-serialisable result
    the runtime feeds back to the model as a tool result.

v0.5.0 foundation ships ``backtest_summary`` only; Teammate K registers
``price_data`` + ``fundamentals`` against the Phase-1 provider registry
when wiring the end-to-end Strategy Critic demo. The registry is
deliberately tool-flat — when an agent's tools list contains a tool id
that is not registered, the runtime substitutes a one-line "tool not
available in this build" reply rather than raising.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from services import backtest_store

logger = logging.getLogger(__name__)

#: Tool-handler signature. Args are a JSON-shaped dict the model sent
#: (validated by the handler against its own expectation); return value
#: is any JSON-serialisable shape the runtime can feed back to the model.
AgentToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

_TOOLS: dict[str, AgentToolHandler] = {}


def register_tool(tool_id: str, handler: AgentToolHandler) -> None:
    """Register a tool handler under ``tool_id``."""
    _TOOLS[tool_id] = handler
    logger.debug("agent_tools: registered %r", tool_id)


def registered_tools() -> list[str]:
    return sorted(_TOOLS)


def is_registered(tool_id: str) -> bool:
    return tool_id in _TOOLS


async def invoke_tool(tool_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a registered tool. Raises KeyError on unknown id."""
    handler = _TOOLS.get(tool_id)
    if handler is None:
        raise KeyError(f"unknown tool {tool_id!r}; registered: {registered_tools()}")
    return await handler(args)


def reset_for_tests() -> None:
    _TOOLS.clear()


# ---------------------------------------------------------------------------
# Foundation tool: backtest_summary
# ---------------------------------------------------------------------------


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


# Register the foundation tool at import time; Strategy Critic's tools
# list ``["backtest_summary", "price_data", "fundamentals"]`` will see
# this one resolved.
register_tool("backtest_summary", _backtest_summary)
