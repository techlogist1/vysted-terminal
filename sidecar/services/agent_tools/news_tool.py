"""Agent tool — ``news``.

Lets the copilot (and any agent that allow-lists it) pull recent headlines +
sentiment for the names in play. Mirrors what ``GET /news`` serves, but is
reachable through the agentic tool loop AND projected to the external MCP
surface (FR-022 — news is one of the primary domains both consumers cover).

Read-only by design — no broker / order / safety-surface side effects (the §6.5
audit grep over the registry finds no forbidden substring in ``news``).

The ``/news`` router uses the app-state pooled ``httpx.AsyncClient``; an agent
tool has no request scope, so it opens a short-lived client for the single call
(not a hot loop — the pooled-client cold-start concern is about repeated rapid
requests, not one agent turn).
"""

from __future__ import annotations

from typing import Any

import httpx

from services.agent_tools import register_tool


async def _news(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch recent news, optionally filtered to ``symbols``."""
    symbols_arg = args.get("symbols")
    symbols: list[str]
    if isinstance(symbols_arg, str):
        symbols = [s.strip() for s in symbols_arg.split(",") if s.strip()]
    elif isinstance(symbols_arg, list):
        symbols = [str(s).strip() for s in symbols_arg if str(s).strip()]
    else:
        symbols = []
    try:
        limit = max(1, min(100, int(args.get("limit", 20) or 20)))
    except (TypeError, ValueError):
        limit = 20

    from services import news_provider
    from services.errors import ProviderError

    try:
        async with httpx.AsyncClient() as client:
            items = await news_provider.fetch_news(client, symbols, limit)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surface failures to the model
        return {"ok": False, "error": f"news fetch failed: {exc}"}

    return {
        "ok": True,
        "count": len(items),
        "news": [item.model_dump(mode="json") for item in items],
    }


def register() -> None:
    """Register the ``news`` tool in the package registry."""
    register_tool("news", _news)


__all__ = ["_news", "register"]
