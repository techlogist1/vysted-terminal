"""Phase 6 workflow-node aggregator — register_v0_6_0_nodes().

Mirrors :mod:`services.agent_tools.registry_v0_6_0`. Each Phase 6 domain
teammate ships their own ``services/workflow_nodes/<domain>_nodes.py``
file with a ``register()`` helper, and uncomments the matching line in
:func:`register_v0_6_0_nodes` below at integration time. Foundation
lands the stub with every entry commented out so additive teammate diffs
merge cleanly.

Naming convention:

  - File: ``services/workflow_nodes/<domain>_nodes.py``
  - Helper: ``<module>.register()`` — registers every node id for the
    domain via :func:`workflow_engine.register_node_type`.
  - Node ids prefixed by category — ``data.fetch_macro_series``,
    ``data.fetch_sec_filing``, ``quant.price_option``,
    ``analysis.screener_query``, etc. — matching the v0.5.0 builtins'
    ``<category>.<verb>`` style.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_v0_6_0_nodes() -> None:
    """Register every Phase 6 workflow node type.

    Idempotent. The order is M → F → Q → E → Sc — matching the v0.6.0
    plan's merge order so integration drift is easy to spot.
    """
    registered: list[str] = []

    # Teammate M — Macro Expansion.
    # from services.workflow_nodes import macro_nodes
    # macro_nodes.register()
    # registered.append("macro")

    # Teammate F — SEC Filings Reader.
    # from services.workflow_nodes import sec_nodes
    # sec_nodes.register()
    # registered.append("sec")

    # Teammate Q — QuantLib pricing modules.
    # from services.workflow_nodes import quant_nodes
    # quant_nodes.register()
    # registered.append("quant")

    # Teammate E — Earnings + Analyst Ratings expansion.
    # from services.workflow_nodes import research_nodes
    # research_nodes.register()
    # registered.append("research (earnings+analyst)")

    # Teammate Sc — Screener / Scanner.
    # from services.workflow_nodes import screener_nodes
    # screener_nodes.register()
    # registered.append("screener")

    if registered:
        logger.info("workflow_nodes: registered v0.6.0 domains: %s", ", ".join(registered))
    else:
        logger.debug(
            "workflow_nodes: register_v0_6_0_nodes() called with no domains uncommented"
        )


__all__ = ["register_v0_6_0_nodes"]
