"""v0.6.0 workflow nodes — macro data (Teammate M).

One node type registered:

  - ``data.fetch_macro_series`` — fetch one macro series via the dispatched
    provider. Inputs: ``{series_id, provider}``; outputs:
    ``{series: <MacroSeriesExtended dict>}``.

Either input may come via the upstream ``inputs`` dict (so a previous node
emits the id / provider for this node) or via the static node ``config``
block. Missing both raises ``ValueError`` matching the v0.5.0 built-in
nodes' error contract.
"""

from __future__ import annotations

from typing import Any

from services import workflow_engine
from services.macro import macro_router as macro_dispatcher

_VALID_PROVIDERS = {"fred", "ecb", "imf", "world-bank"}


async def fetch_macro_series(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Fetch one macro time series for the workflow run."""
    series_id = inputs.get("series_id") or config.get("series_id")
    provider = inputs.get("provider") or config.get("provider")
    if not series_id:
        raise ValueError(
            "data.fetch_macro_series: missing 'series_id' (provide via input or config)"
        )
    if not provider:
        raise ValueError(
            "data.fetch_macro_series: missing 'provider' "
            f"(supply one of {sorted(_VALID_PROVIDERS)})"
        )
    if str(provider).lower() not in _VALID_PROVIDERS:
        raise ValueError(
            f"data.fetch_macro_series: unknown provider {provider!r}; "
            f"supported: {sorted(_VALID_PROVIDERS)}"
        )
    series = await macro_dispatcher.get_series(str(series_id), str(provider).lower())
    return {"series": series.model_dump(mode="json")}


def register() -> None:
    """Register the macro workflow node types against the engine."""
    workflow_engine.register_node_type("data.fetch_macro_series", fetch_macro_series)


__all__ = ["fetch_macro_series", "register"]
