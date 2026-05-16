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


# ---------------------------------------------------------------------------
# v0.5.0 (Teammate K) tools — price_data + fundamentals
# ---------------------------------------------------------------------------
#
# Both are registered by :func:`register_v0_5_0_tools` at sidecar
# startup (called from ``main.py`` and from ``app.create_app``). Import
# time stays light — heavy provider modules are pulled in lazily inside
# the handlers. Tests can call ``register_v0_5_0_tools`` directly after
# a :func:`reset_for_tests` to exercise the dispatch wiring.


async def _price_data(args: dict[str, Any]) -> dict[str, Any]:
    """Return a recent OHLCV slice + the latest quote for ``symbol``.

    The Strategy Critic queries this tool to corroborate (or refute)
    claims a strategy backtest implicitly makes about the symbol's
    behaviour — e.g. "is this really a low-vol name?".

    Args:
        symbol: Ticker. Required.
        timeframe: One of the yfinance-mapped timeframes. Defaults to ``"1d"``.
        range_: Provider-native range string (e.g. ``"6mo"``, ``"1y"``).
            Defaults to ``"6mo"`` — six months is enough for vol /
            drawdown context without bloating the model prompt.
        asset_class: ``"equity"`` (default) or ``"crypto"``.

    Returns the most recent 90 bars (compact for the model) plus the
    latest quote. On provider failure returns ``{"ok": False, ...}``.
    """
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    timeframe = str(args.get("timeframe", "1d"))
    range_ = args.get("range") or args.get("range_") or "6mo"
    asset_class = str(args.get("asset_class", "equity"))

    # Provider registry is sync for equity/crypto history; run on a
    # thread so the event loop stays responsive. Imports are lazy to
    # keep import-time light.
    import asyncio

    from services import provider_registry
    from services.errors import ProviderError

    try:
        series = await asyncio.to_thread(
            provider_registry.get_history,
            symbol,
            timeframe,
            str(range_),
            asset_class,
        )
        quote = await asyncio.to_thread(provider_registry.get_quote, symbol, asset_class)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}

    recent_bars = list(series.bars)[-90:]
    return {
        "ok": True,
        "symbol": series.symbol,
        "timeframe": series.timeframe,
        "provider": series.provider,
        "quote": quote.model_dump(by_alias=True, mode="json"),
        "bars": [
            {
                "timestamp": bar.timestamp.isoformat()
                if hasattr(bar.timestamp, "isoformat")
                else str(bar.timestamp),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
            for bar in recent_bars
        ],
    }


async def _fundamentals(args: dict[str, Any]) -> dict[str, Any]:
    """Return valuation ratios + a company profile for ``symbol``.

    The Strategy Critic uses fundamentals to challenge value/growth
    strategy assumptions — e.g. flagging that a "value" backtest is
    really a high-beta backtest because the universe's average P/B
    ratio is sky-high.

    Args:
        symbol: Ticker. Required.

    Falls back through the same registry path as ``GET /fundamentals``;
    openbb-mcp when bundled, yfinance otherwise. The registry's
    fundamentals path is async (it awaits the openbb-mcp client).
    """
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    from services import provider_registry
    from services.errors import ProviderError

    try:
        fundamentals = await provider_registry.get_fundamentals(symbol)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}

    return {
        "ok": True,
        "fundamentals": fundamentals.model_dump(by_alias=True, mode="json"),
    }


def register_v0_5_0_tools() -> None:
    """Register the v0.5.0 (Teammate K) production tools.

    Called from ``main.py`` at sidecar startup and from
    ``app.create_app`` so TestClient paths converge. Idempotent — the
    underlying :func:`register_tool` overwrites by tool id.
    """
    register_tool("price_data", _price_data)
    register_tool("fundamentals", _fundamentals)
    logger.info("agent_tools: registered v0.5.0 tools (price_data, fundamentals)")
