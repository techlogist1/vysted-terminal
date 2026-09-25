"""Agent-tool registry — Phase 6 package refactor of v0.5.0's flat module.

Phase 3 shipped the ``AgentSpec.tools`` field on each agent JSON config
(e.g. ``strategy_critic.json`` lists ``["backtest_summary", "price_data",
"fundamentals"]``) and Phase 4 wired the registry so agents could call
backtest_summary against a real BacktestResult. Phase 6 splits the
v0.5.0 single-file module into a per-tool package so domain teams add
their own handlers in a dedicated file without contending on a shared
file at integration time.

The registry contract is unchanged from v0.5.0 — every consumer that
imports ``from services import agent_tools`` and calls
``agent_tools.register_tool(...)`` / ``agent_tools.invoke_tool(...)``
continues to work without modification. The submodule files are pulled
in lazily by :func:`register_v0_5_0_tools` and
:func:`register_v0_6_0_tools`.

Domain submodules (in order of registration):

  - :mod:`services.agent_tools.backtest_summary` — registers at import
    time (same as v0.5.0 behaviour).
  - :mod:`services.agent_tools.price_data` — registered by
    :func:`register_v0_5_0_tools`.
  - :mod:`services.agent_tools.fundamentals` — same.
  - :func:`register_v0_6_0_tools` below — the Phase 6 domain aggregator.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from services.errors import ProviderError

logger = logging.getLogger(__name__)

#: Tool-handler signature. Args are a JSON-shaped dict the model sent
#: (validated by the handler against its own expectation); return value
#: is any JSON-serialisable shape the runtime can feed back to the model.
AgentToolHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]

_TOOLS: dict[str, AgentToolHandler] = {}


def register_tool(tool_id: str, handler: AgentToolHandler) -> None:
    """Register a tool handler under ``tool_id``. Overwrites by id."""
    _TOOLS[tool_id] = handler
    logger.debug("agent_tools: registered %r", tool_id)


def registered_tools() -> list[str]:
    """List the currently-registered tool ids."""
    return sorted(_TOOLS)


def is_registered(tool_id: str) -> bool:
    """``True`` iff ``tool_id`` has a registered handler."""
    return tool_id in _TOOLS


async def invoke_tool(tool_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Invoke a registered tool. Raises ``KeyError`` on unknown id.

    A handler that lets a ``ProviderError`` (or any other exception) escape
    gets it converted to the tool's ``{"ok": False, "error": ...}`` envelope
    here, with one spelling, instead of every handler re-deriving its own
    copy of this try/except (R15-CODE-AGENT-014). A handler that already
    returns its own envelope — including one with extra fields, like
    ``fundamentals``'s ``reason`` classification — is unaffected: this only
    fires when the handler raises.
    """
    handler = _TOOLS.get(tool_id)
    if handler is None:
        raise KeyError(f"unknown tool {tool_id!r}; registered: {registered_tools()}")
    try:
        return await handler(args)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surface to the model, never crash the turn
        return {"ok": False, "error": f"unexpected error: {exc}"}


def reset_for_tests() -> None:
    """Clear the registry — used only from the test suite.

    Restores whatever registered itself at package-import time (a snapshot
    taken below, right after those imports run) — currently just
    ``backtest_summary``, but generically: any future module-level
    ``register_tool(...)`` call anywhere in the package survives a reset
    without this function needing to name it (R15-CODE-AGENT-027 — the old
    hardcoded ``backtest_summary`` re-registration silently dropped a second
    import-time tool, making tests that reset order-dependent).
    """
    _TOOLS.clear()
    _TOOLS.update(_IMPORT_TIME_TOOLS)


# ---------------------------------------------------------------------------
# Aggregator boot helpers
# ---------------------------------------------------------------------------
#
# Import-time side effects: the foundation tool ``backtest_summary`` registers
# itself at module import (as the v0.5.0 behaviour did from the flat file).
# The two v0.5.0 (Teammate K) tools — ``price_data`` and ``fundamentals`` —
# require an explicit ``register_v0_5_0_tools()`` call. v0.6.0 adds
# ``register_v0_6_0_tools()`` for the Phase 6 domain teammates.

# Pull in backtest_summary's import-time registration. This must run after
# ``register_tool`` is defined above; the submodule imports it from this
# package's __init__.
from services.agent_tools import backtest_summary as _backtest_summary_mod  # noqa: E402, F401

#: Snapshot of whatever registered at package-import time (above), so
#: :func:`reset_for_tests` can restore it generically instead of naming
#: ``backtest_summary`` by hand (R15-CODE-AGENT-027).
_IMPORT_TIME_TOOLS: dict[str, AgentToolHandler] = dict(_TOOLS)


def register_v0_5_0_tools() -> None:
    """Register the v0.5.0 (Teammate K) production tools.

    Called from ``main.py`` at sidecar startup and from
    ``app.create_app`` so TestClient paths converge. Idempotent — the
    underlying :func:`register_tool` overwrites by tool id.
    """
    from services.agent_tools import fundamentals, price_data

    price_data.register()
    fundamentals.register()
    logger.info("agent_tools: registered v0.5.0 tools (price_data, fundamentals)")


def register_v0_6_0_tools() -> None:
    """Register every Phase 6 (v0.6.0) agent tool.

    Idempotent. Calls each domain's ``register()`` helper. Inlined from the
    former ``registry_v0_6_0`` module (R15-CODE-AGENT-028): that module was a
    pure pass-through with no callers besides this function.
    """
    registered: list[str] = []

    # Teammate M — Macro Expansion (FRED + ECB + IMF + World Bank).
    from services.agent_tools import macro_tools

    macro_tools.register()
    registered.append("macro")

    # Teammate F — SEC Filings Reader.
    from services.agent_tools import sec_tools

    sec_tools.register()
    registered.append("sec")

    # Teammate Q — QuantLib pricing modules.
    from services.agent_tools import quant_tools

    quant_tools.register()
    registered.append("quant")

    # Teammate E — Earnings + Analyst Ratings expansion.
    from services.agent_tools import analyst_tools, earnings_tools

    earnings_tools.register()
    analyst_tools.register()
    registered.append("earnings+analyst")

    # Teammate Sc — Screener / Scanner.
    from services.agent_tools import screener_tools

    screener_tools.register()
    registered.append("screener")

    # News — headlines + sentiment (also projected to the external MCP surface).
    from services.agent_tools import news_tool

    news_tool.register()
    registered.append("news")

    # Market overview — locale-aware market-state snapshot (indices + headlines)
    # for a broad "how's the market today" question. Read-only; reuses the
    # provider_registry quote path + the news provider (no new data fetching).
    from services.agent_tools import market_overview

    market_overview.register()
    registered.append("market_overview")

    # Pass B (B1) — locale-aware symbol resolution (name/ticker -> instrument).
    from services.agent_tools import resolve_symbol

    resolve_symbol.register()
    registered.append("resolve_symbol")

    # Pass B (B2) — multi-symbol comparison (quote + fundamentals + relative perf).
    from services.agent_tools import compare_symbols

    compare_symbols.register()
    registered.append("compare_symbols")

    # Pass B (B3) — web search (BYOK Exa / local SearXNG; native rides the adapter).
    from services.agent_tools import web_search

    web_search.register()
    registered.append("web_search")

    # Pass B (B4) — the ONE research engine (FR-115): a single ``research`` tool
    # that escalates in place from a fast bundle (depth=quick) to the DEEP
    # budget-bounded loop (depth=deep/heavy). ``deep_research`` is no longer a
    # registered tool — its engine is called internally by ``research``.
    from services.agent_tools import research

    research.register()
    registered.append("research")

    # R7 Component 3 — India corporate disclosures (merged BSE+NSE announcements
    # + quarterly shareholding patterns), read-only.
    from services.agent_tools import disclosure_tools

    disclosure_tools.register()
    registered.append("disclosures")

    # R7 Track N — custom-DSL backtest authoring.
    from services.agent_tools import run_custom_backtest

    run_custom_backtest.register()
    registered.append("backtest-custom")

    logger.info("agent_tools: registered v0.6.0 domains: %s", ", ".join(registered))


__all__ = [
    "AgentToolHandler",
    "invoke_tool",
    "is_registered",
    "register_tool",
    "register_v0_5_0_tools",
    "register_v0_6_0_tools",
    "registered_tools",
    "reset_for_tests",
]
