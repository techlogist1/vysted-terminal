"""Read-only agent tool — ``broker_portfolio``.

Lets a persona analyse the user's REAL connected-broker account (positions,
equity, buying power, per-position unrealized P&L) — e.g. "is my Zerodha
portfolio overexposed to one sector?".

SAFETY: this is a READ tool. It calls ``adapter.account_info()`` which is
audit-free (``broker_base.py``) and never touches the order path. The AI has no
way to place an order through it; any broker-mutating action must go through the
locked ``propose_order -> confirm_and_place`` two-step, which this does not call.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool
from services.broker_base import BrokerError


async def _broker_portfolio(args: dict[str, Any]) -> dict[str, Any]:
    """Return the connected broker's account summary. ``broker`` defaults to
    ``kite``; unknown/unconnected brokers return a typed error the model
    recovers from."""
    broker = str(args.get("broker") or "kite")
    from services.brokers import registry as brokers_registry

    try:
        adapter = brokers_registry.get(broker)
    except KeyError:
        return {"ok": False, "error": f"broker {broker!r} is not available"}
    try:
        summary = await adapter.account_info()
    except BrokerError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "broker": broker, "account": summary.model_dump(by_alias=True)}


def register() -> None:
    """Register the ``broker_portfolio`` tool in the package registry."""
    register_tool("broker_portfolio", _broker_portfolio)
