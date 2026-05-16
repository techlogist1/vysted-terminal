"""Vysted Terminal Python sidecar — a FastAPI service on localhost.

The Tauri core assigns a free port at app launch and passes it via ``--port``,
and resolves the per-OS application data directory and passes it via
``--data-dir``. The data directory is exported as the ``VYSTED_DATA_DIR``
environment variable so the persistence layer (portfolio SQLite, saved
workspaces) can find it — see ``config.py``.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

import uvicorn

from app import app
from config import DATA_DIR_ENV
from services import agent_tools, backtest_strategies, workflow_nodes
from services.brokers import registry as brokers_registry
from services.workflow_nodes import registry_v0_6_0 as workflow_nodes_v0_6_0


def _exit_when_parent_closes_stdin() -> None:
    """Terminate when the Tauri core closes our stdin.

    The sidecar is bundled with PyInstaller --onefile, whose bootloader process
    re-execs the real worker as a child. Killing the bootloader (what the Tauri
    core spawns) would otherwise orphan this worker. Watching stdin for EOF is a
    reliable, cross-platform shutdown signal: when the Tauri core exits it drops
    its end of the stdin pipe, we read EOF, and we exit too.
    """
    if sys.stdin is None:
        return
    try:
        sys.stdin.buffer.read()
    except Exception:
        # Any stdin failure means the parent is gone — nothing to recover.
        pass
    os._exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vysted Terminal sidecar")
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Localhost port assigned by the Tauri core at launch.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Application data directory resolved by the Tauri core.",
    )
    args = parser.parse_args()

    if args.data_dir:
        os.environ[DATA_DIR_ENV] = args.data_dir

    # Register the ten built-in workflow node handlers against the
    # workflow engine's registry. This is done in ``main`` (not in
    # ``app.create_app``) so the pytest suite's TestClient builds do
    # not see them — workflow engine tests reset the registry between
    # cases and register their own handlers.
    workflow_nodes.register_all()

    # India broker adapters (Teammate I — Dhan + Angel One + Kite).
    # ``create_app`` already bootstrapped these when ``app`` was imported
    # above; the explicit re-call here documents the production boot path
    # and is idempotent (re-registering replaces the prior instance).
    brokers_registry.bootstrap_default_adapters()

    # v0.5.0 runtime extensions — backtest strategy archetypes + the
    # price_data + fundamentals agent tools. ``create_app`` already
    # invokes these via ``_register_v0_5_0_runtime_extensions`` at app
    # build time; the explicit re-call here is the documented
    # production boot path and is idempotent (overwrites by id).
    backtest_strategies.register_all()
    agent_tools.register_v0_5_0_tools()

    # v0.6.0 (Phase 6) extensions — macro + SEC + earnings + analyst +
    # quant + screener agent tools and workflow nodes. The aggregators
    # below currently no-op when no Phase 6 teammate has registered
    # their domain; they become live as each teammate's submodule
    # uncomments its entry in
    # ``services/agent_tools/registry_v0_6_0.py`` and
    # ``services/workflow_nodes/registry_v0_6_0.py``. Idempotent.
    agent_tools.register_v0_6_0_tools()
    workflow_nodes_v0_6_0.register_v0_6_0_nodes()

    threading.Thread(target=_exit_when_parent_closes_stdin, daemon=True).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
