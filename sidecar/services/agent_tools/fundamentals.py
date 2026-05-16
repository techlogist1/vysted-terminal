"""v0.5.0 agent tool — ``fundamentals``.

Migrated from v0.5.0's flat ``agent_tools.py`` with no behaviour change.
Registered via :func:`register` from
:func:`services.agent_tools.register_v0_5_0_tools` at sidecar startup
and from ``app.create_app``.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool


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


def register() -> None:
    """Register the ``fundamentals`` tool in the package registry."""
    register_tool("fundamentals", _fundamentals)


__all__ = ["_fundamentals", "register"]
