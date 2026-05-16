"""Phase 6.5 agent-tool aggregator — register_v0_6_5_tools().

v0.6.5 (Tradesa V2 wrapper plugin) ships READ-ONLY by operator decision —
no Vysted-side agent tools that can act on Tradesa V2 are registered.
This stub maintains the v0.6.0 F4 refactor convention (one aggregator
per phase) so v0.6.6+ has a slot to fill when write capability is added.

Specifically, v0.6.5 deliberately does NOT register any of:

  - ``tradesa_v2_fire_kill_switch``
  - ``tradesa_v2_close_position``
  - ``tradesa_v2_pause_bot``
  - ``tradesa_v2_approve_proposal``

…or any other tool that lets an AI agent take action on the bot. The
operator brief is explicit: v0.6.5 is observation-only. The §6.5
defense-in-depth audit (``test_safety_end_to_end.py::test_audit_6_ai_order_gate``)
greps every agent-tool registry for forbidden placement-ish patterns;
this file is intentionally empty so that grep continues to return zero
matches for ``place_*`` / ``submit_*`` / ``execute_*`` / ``auto_approve``
across the agent_tools package.

When write capability ships (v0.6.6+), the corresponding tools land here
as a ``tradesa_v2_tools`` submodule and a ``tradesa_v2_tools.register()``
call. Each new tool ID must (a) pass the §6.5 audit grep, (b) route
through the propose→confirm flow (no direct broker calls), and
(c) audit-log every invocation per BLUEPRINT §6.5 #4.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_v0_6_5_tools() -> None:
    """Register every Phase 6.5 (v0.6.5) agent tool.

    Idempotent. v0.6.5 ships READ-ONLY by operator decision — no tools
    are registered. The stub exists to maintain the per-phase aggregator
    convention from v0.6.0's F4 refactor; v0.6.6+ fills it in.
    """
    logger.debug(
        "agent_tools: register_v0_6_5_tools() — read-only wrapper release, "
        "no Tradesa V2 agent tools registered (v0.6.5 brief)."
    )


__all__ = ["register_v0_6_5_tools"]
