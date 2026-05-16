"""Generate the Bybit testnet paper-trade audit-trail JSON artefact.

Runs the same flow as
``tests/test_brokers_ccxt_exec.py::test_bybit_testnet_paper_trade_end_to_end``
against a real-shaped audit-log DB in a temp dir, then dumps the resulting
audit rows as JSON to
``docs/screenshots/v0.5.0/teammate-x/paper-trade-audit-trail.json``.

This is the pre-integration evidence artefact for Teammate X's plan
deliverable #2 — the v0.5.0 plan requires a populated audit-log
screenshot rendered by Teammate S's `AuditLogViewer.tsx`, which is not
yet in this worktree. The JSON artefact proves the audit-log trail
shape regardless of UI presence; the screenshot pass re-runs after
the Teammate S merge.

Usage::

    cd sidecar
    python tests/gen_audit_trail.py

Standalone — never imported by the test suite.
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any


class _FakeCcxtExchange:
    """Stand-in for a ccxt exchange — enough for the paper-mode flow."""

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        self.options = options or {}

    def set_sandbox_mode(self, _enabled: bool) -> None:
        pass

    def fetch_balance(self) -> dict[str, Any]:
        return {
            "USDT": {"free": 1_000.0, "used": 0.0, "total": 1_000.0},
            "info": {},
        }


async def main() -> None:
    here = Path(__file__).resolve().parent
    sidecar_root = here.parent
    out_path = (
        sidecar_root.parent
        / "docs"
        / "screenshots"
        / "v0.5.0"
        / "teammate-x"
        / "paper-trade-audit-trail.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        os.environ["VYSTED_DATA_DIR"] = tmp_dir

        # Imports happen AFTER the env var is set so the audit-log DB
        # lands under tmp_dir, not the user's data dir.
        import sys

        if str(sidecar_root) not in sys.path:
            sys.path.insert(0, str(sidecar_root))

        from services import audit_log, kill_switch
        from services.brokers import ccxt_exec

        kill_switch.reset_bus_for_tests()

        # Patch the ccxt module to avoid any chance of touching the network.
        ccxt_exec.ccxt = SimpleNamespace(  # type: ignore[attr-defined]
            bybit=_FakeCcxtExchange,
            binance=_FakeCcxtExchange,
            kraken=_FakeCcxtExchange,
            coinbase=_FakeCcxtExchange,
        )

        adapter = ccxt_exec.CcxtExecutionAdapter("bybit", testnet=True)
        await adapter.connect({"api_key": "test", "secret": "test"})
        proposal = adapter.propose_order(
            symbol="BTC/USDT",
            side="buy",
            order_type="limit",
            quantity=0.01,
            limit_price=50_000.0,
            currency="USDT",
        )
        result = await adapter.confirm_and_place(proposal, human_confirmed=True)
        assert result.broker_order_id is not None
        await adapter.cancel_order(result.broker_order_id)

        rows = audit_log.tail(limit=20)
        rows_chrono = list(reversed(rows))

        payload = {
            "generated_by": "sidecar/tests/gen_audit_trail.py",
            "scope": "Bybit testnet paper trade — propose -> confirm -> place -> cancel",
            "broker_id": adapter.BROKER_ID,
            "proposal_id": proposal.proposal_id,
            "broker_order_id": result.broker_order_id,
            "row_count": len(rows_chrono),
            "rows": [r.model_dump(by_alias=True, mode="json") for r in rows_chrono],
        }

        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print(f"Wrote {out_path} ({len(rows_chrono)} rows)")  # noqa: T201
        for r in rows_chrono:
            print(f"  {r.action:<24}  broker={r.broker}  source={r.source}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
