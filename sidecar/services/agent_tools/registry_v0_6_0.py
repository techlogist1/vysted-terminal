"""Phase 6 agent-tool aggregator — register_v0_6_0_tools().

As of v0.6.0 all five Phase 6 domain registrations are live (M / F / Q /
E / Sc). Each ``services/agent_tools/<domain>_tools.py`` exports a
``register()`` function that calls ``register_tool(<id>, <handler>)`` for
its domain. The line ordering below matches the merge order from the
v0.6.0 plan so the integration audit can spot drift.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_v0_6_0_tools() -> None:
    """Register every Phase 6 (v0.6.0) agent tool.

    Idempotent. Calls each domain's ``register()`` helper. Teammates
    uncomment their line when integrating.
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

    if registered:
        logger.info("agent_tools: registered v0.6.0 domains: %s", ", ".join(registered))
    else:
        logger.debug("agent_tools: register_v0_6_0_tools() called with no domains uncommented")


__all__ = ["register_v0_6_0_tools"]
