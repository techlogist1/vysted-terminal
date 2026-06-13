"""Phase 6.5 agent-tool aggregator — register_v0_6_5_tools().

An intentionally empty per-phase aggregator: v0.6.5 registers no agent tools.
The stub maintains the v0.6.0 F4 refactor convention (one aggregator per phase)
so a future phase has a slot to fill, and keeps the §6.5 audit grep
(``test_safety_end_to_end.py::test_audit_6_ai_order_gate``) returning zero
forbidden ``place_*`` / ``submit_*`` / ``execute_*`` / ``auto_approve`` matches
across the agent_tools package — this file is deliberately empty.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_v0_6_5_tools() -> None:
    """Register every Phase 6.5 (v0.6.5) agent tool.

    Idempotent. No tools are registered — the stub exists only to maintain the
    per-phase aggregator convention from v0.6.0's F4 refactor.
    """
    logger.debug("agent_tools: register_v0_6_5_tools() — no tools in this phase.")


__all__ = ["register_v0_6_5_tools"]
