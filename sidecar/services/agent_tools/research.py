"""Agent tool — ``research`` (fast, single-pass research gather).

Wires the fast research service (``services.research.fast.gather_fast``) into the
agent loop. The handler hands the service the active region and the agent-tool
``invoke_tool`` seam so the service can fan out to existing read-only data tools
(news, quotes, fundamentals, web search) and return a single grounded bundle the
model can summarise — one round, no inner LLM loop (that is ``deep_research``).

The research/deep-research service is built in parallel; this handler imports it
lazily inside the call so the module imports cleanly even before the service
lands, and so the test suite can monkeypatch the service in place.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool


async def _research(args: dict[str, Any]) -> dict[str, Any]:
    """Gather grounded research context for ``query`` in one pass.

    Calls :func:`services.research.fast.gather_fast` with the active region and
    the agent-tool ``invoke_tool`` seam, and returns the service bundle. On a
    missing/blank query returns ``{"ok": False, "message": <human reason>}`` —
    never a raw error blob.
    """
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "message": "Research needs a query — tell me what to look into.",
        }

    import config
    from services import agent_tools
    from services.research import fast

    return await fast.gather_fast(
        query.strip(),
        region=config.get_region(),
        tool_call=agent_tools.invoke_tool,
        # Forward steps LIVE to the runtime sink (Track A) so even the default
        # FAST mode animates a working trace; ``None`` outside an agent run.
        on_step=config.get_step_sink(),
    )


def register() -> None:
    """Register the ``research`` tool in the package registry."""
    register_tool("research", _research)


__all__ = ["_research", "register"]
