"""Phase 6 workflow nodes — screener / scanner.

Registers ``analysis.screener_query`` against the workflow engine. The
node consumes a universe id + criteria list (either as inputs from
upstream nodes or as static config) and emits the screener result rows
to downstream nodes — typically a Strategy Critic or a watchlist write
node.

Wire shape:

  - Inputs (override config when present):
      ``universe`` (str), ``criteria`` (list[dict]),
      ``custom_symbols`` (list[str], optional), ``limit`` (int, optional)
  - Config (fallback):
      same keys as the inputs.
  - Outputs:
      ``rows`` — the matched :class:`ScreenerResultRow` list (JSON-
      shaped), ``result_count`` — int, ``evaluated_count`` — int.

The node delegates to :func:`services.screener.run_screener`, so it
shares the universe resolution, fan-out, and AND-criteria semantics
the HTTP route uses. A misshapen criterion raises ``ValueError`` (the
engine maps that to a ``node-error`` event).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from services import workflow_engine

logger = logging.getLogger(__name__)


async def screener_query(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Run the screener against a universe + criteria pair.

    Inputs take precedence over config — workflows can wire an upstream
    node's output ("the macro screen criteria the Macro Thesis agent
    proposed") directly into the screener node.
    """
    from models.screener import ScreenerRequest
    from services import screener

    universe = inputs.get("universe") or config.get("universe")
    if not universe:
        raise ValueError(
            "analysis.screener_query: missing 'universe' (provide via input or config)"
        )

    criteria = inputs.get("criteria")
    if criteria is None:
        criteria = config.get("criteria")
    if criteria is None:
        raise ValueError(
            "analysis.screener_query: missing 'criteria' (provide via input or config)"
        )
    if not isinstance(criteria, list):
        raise ValueError("analysis.screener_query: 'criteria' must be a list")

    custom_symbols = inputs.get("custom_symbols") or config.get("custom_symbols")
    limit = inputs.get("limit") or config.get("limit") or 50

    try:
        request = ScreenerRequest.model_validate(
            {
                "universe": universe,
                "criteria": criteria,
                "custom_symbols": custom_symbols,
                "limit": limit,
            }
        )
    except ValidationError as exc:
        raise ValueError(f"analysis.screener_query: invalid request: {exc}") from exc

    result = await screener.run_screener(request)
    return {
        "rows": [row.model_dump(mode="json") for row in result.rows],
        "result_count": result.result_count,
        "evaluated_count": result.evaluated_count,
    }


def register() -> None:
    """Register every screener workflow node against the engine."""
    workflow_engine.register_node_type("analysis.screener_query", screener_query)
    logger.info("workflow_nodes: registered analysis.screener_query")


__all__ = ["register", "screener_query"]
