"""Phase 6 agent tool — ``screener_run``.

Lets the v0.5.0 Strategy Critic + the v0.6.0 macro/research agents pull a
populated screener result into their context. The tool re-validates the
request payload through the same :class:`ScreenerRequest` Pydantic model
the router uses, so the agent's invocation is contract-aligned with the
HTTP surface (a misformatted criterion is a clean ``{"ok": False, ...}``
return, not a crash).

Read-only by design — the §6.5 audit (``test_safety_end_to_end::test_safety_audit_6_no_bypass``)
greps the registered tool ids for ``place_order|submit_order|execute_order``
patterns; ``screener_run`` is data-only and stays well clear of that surface.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from services.agent_tools import register_tool

logger = logging.getLogger(__name__)


async def _screener_run(args: dict[str, Any]) -> dict[str, Any]:
    """Run the screener with criteria the calling agent supplies.

    Args (passed via the model's tool-call payload):

      - ``universe`` (str, required) — one of ``"sp500" | "nifty50" |
        "crypto-top50" | "custom"``.
      - ``criteria`` (list[dict], required) — discriminated-union
        criterion list. Each entry is shaped as the corresponding
        :class:`ScreenerCriterion` variant.
      - ``custom_symbols`` (list[str], optional) — required when
        ``universe == "custom"``.
      - ``limit`` (int, optional, default 50) — agent-friendly default;
        the router default of 200 is fine for the UI but produces a
        chunky context blob for agents.

    Returns ``{"ok": True, "result": ScreenerResult-as-JSON}`` on
    success; ``{"ok": False, "error": "..."}`` on validation /
    provider failure.
    """
    from models.screener import ScreenerRequest
    from services import screener
    from services.errors import ProviderError

    payload = dict(args)
    payload.setdefault("limit", 50)

    try:
        request = ScreenerRequest.model_validate(payload)
    except ValidationError as exc:
        return {"ok": False, "error": f"invalid screener request: {exc}"}

    try:
        result = await screener.run_screener(request)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        logger.exception("screener_run unexpected error")
        return {"ok": False, "error": f"unexpected error: {exc}"}

    return {
        "ok": True,
        "result": result.model_dump(mode="json"),
    }


def register() -> None:
    """Register the ``screener_run`` tool in the package registry."""
    register_tool("screener_run", _screener_run)


__all__ = ["_screener_run", "register"]
