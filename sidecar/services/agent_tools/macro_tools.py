"""v0.6.0 agent tools — macro data (Teammate M).

Registers two tools agents can call once :func:`register` runs from
:mod:`services.agent_tools.registry_v0_6_0`:

  - ``macro_series`` — fetch one series from a named provider.
  - ``macro_search`` — search a provider's catalog by free-text query.

Both tools surface the same provider literal the REST contract uses:
``"fred" | "ecb" | "imf" | "world-bank"``. Tools are read-only — no
broker / order / safety-surface side effects.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool
from services.errors import ProviderError
from services.macro import macro_router as macro_dispatcher

_VALID_PROVIDERS = {"fred", "ecb", "imf", "world-bank"}


async def _macro_series(args: dict[str, Any]) -> dict[str, Any]:
    """Fetch one macro series for an agent prompt.

    Args:
        series_id: provider-native id (e.g. ``"DGS10"`` for FRED).
        provider: one of ``"fred"``, ``"ecb"``, ``"imf"``, ``"world-bank"``.

    Returns ``{"ok": True, "series": <MacroSeriesExtended-shaped dict>}`` on
    success; ``{"ok": False, "error": ...}`` on provider failure.
    """
    series_id = args.get("series_id")
    provider = args.get("provider")
    if not isinstance(series_id, str) or not series_id:
        return {"ok": False, "error": "missing or non-string series_id"}
    if not isinstance(provider, str) or provider.lower() not in _VALID_PROVIDERS:
        return {
            "ok": False,
            "error": f"provider must be one of {sorted(_VALID_PROVIDERS)}",
        }
    try:
        series = await macro_dispatcher.get_series(series_id, provider.lower())
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}
    return {"ok": True, "series": series.model_dump(mode="json")}


async def _macro_search(args: dict[str, Any]) -> dict[str, Any]:
    """Search a macro provider's catalog by free-text query.

    Args:
        q: free-text query.
        provider: one of ``"fred"``, ``"ecb"``, ``"imf"``, ``"world-bank"``.
        limit: max results, defaults to 10.
    """
    query = args.get("q") or args.get("query")
    provider = args.get("provider")
    limit_raw = args.get("limit", 10)
    if not isinstance(query, str) or not query:
        return {"ok": False, "error": "missing or non-string query"}
    if not isinstance(provider, str) or provider.lower() not in _VALID_PROVIDERS:
        return {
            "ok": False,
            "error": f"provider must be one of {sorted(_VALID_PROVIDERS)}",
        }
    try:
        limit = max(1, min(50, int(limit_raw)))
    except (TypeError, ValueError):
        limit = 10
    try:
        results = await macro_dispatcher.search(query, provider.lower(), limit=limit)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}
    return {
        "ok": True,
        "results": [r.model_dump(mode="json") for r in results],
    }


def register() -> None:
    """Register the macro_* tools in the package registry."""
    register_tool("macro_series", _macro_series)
    register_tool("macro_search", _macro_search)


__all__ = ["_macro_search", "_macro_series", "register"]
