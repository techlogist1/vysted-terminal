"""Phase 6 agent-tool aggregator — register_v0_6_0_tools().

Each domain teammate adds their submodule under
``services/agent_tools/<domain>_tools.py`` and a registration call to the
list below. Foundation lands the stub with all five teammates' entries
commented out; teammates uncomment their entry when wiring their domain.

Convention each teammate follows:

  1. Add a file ``services/agent_tools/<domain>_tools.py`` exporting a
     ``register()`` function that calls ``register_tool(<id>, <handler>)``
     for each tool the domain ships.
  2. Uncomment the matching line in ``register_v0_6_0_tools()`` below.

The line ordering below matches the merge order from the v0.6.0 plan
(M → F → Q → E → Sc) so the integration audit can spot drift.
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

    if registered:
        logger.info("agent_tools: registered v0.6.0 domains: %s", ", ".join(registered))
    else:
        logger.debug("agent_tools: register_v0_6_0_tools() called with no domains uncommented")


__all__ = ["register_v0_6_0_tools"]
