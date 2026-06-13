"""Vysted Terminal Python sidecar — a FastAPI service on localhost.

The Tauri core assigns a free port at app launch and passes it via ``--port``,
and resolves the per-OS application data directory and passes it via
``--data-dir``. The data directory is exported as the ``VYSTED_DATA_DIR``
environment variable so the persistence layer (portfolio SQLite, saved
workspaces) can find it — see ``config.py``.

Two entrypoint modes share this one binary (no extra ``externalBin``):

- **HTTP** (default) — ``--port <n>`` runs the FastAPI app under uvicorn; the
  FastMCP Streamable-HTTP transport is mounted at ``/mcp`` by ``app.create_app``.
- **MCP stdio** (FR-025) — ``--mcp-stdio`` runs the FastMCP server over stdio
  instead of binding a port, so an external MCP client can spawn this binary
  directly and speak JSON-RPC over stdin/stdout. ``--port`` is ignored in this
  mode and the stdin-EOF watchdog is disabled (the stdio transport owns stdin).
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

import uvicorn

from app import app
from config import DATA_DIR_ENV
from services import agent_tools, backtest_strategies, mcp_server, workflow_nodes
from services.workflow_nodes import registry_v0_6_0 as workflow_nodes_v0_6_0


def _register_runtime_extensions() -> None:
    """Wire the runtime tool/node registrations the production boot path needs.

    ``create_app`` already invokes the v0.5.0/v0.6.0/v0.6.5 extension hooks at
    app-build time; these re-calls are the documented production boot path and
    are idempotent (overwrites by stable id). The workflow node handlers are
    registered HERE (not in ``create_app``) so the pytest TestClient builds do
    not see them — workflow-engine tests reset the registry and register their
    own handlers. Shared by both the HTTP and ``--mcp-stdio`` entrypoints so the
    MCP surface exposes the identical catalog tool set on both transports.
    """
    # Built-in workflow node handlers against the workflow engine's registry.
    workflow_nodes.register_all()

    # FR-051: no broker is registered at boot — adapters register lazily via
    # ``brokers_registry.ensure_registered(...)`` on the marketplace/connect
    # path (``POST /brokers/{id}/connect``). The old eager bootstrap call here
    # is intentionally removed.

    # v0.5.0 runtime extensions — backtest strategy archetypes + the
    # price_data + fundamentals agent tools.
    backtest_strategies.register_all()
    agent_tools.register_v0_5_0_tools()

    # v0.6.0 (Phase 6) extensions — macro + SEC + earnings + analyst + quant +
    # screener agent tools and workflow nodes. Idempotent.
    agent_tools.register_v0_6_0_tools()
    workflow_nodes_v0_6_0.register_v0_6_0_nodes()

    # v0.6.5 phase extensions — empty aggregator; the function
    # stub registers no tools. The slot exists so v0.6.6+ write capability has a
    # per-release stamp matching v0.5.0 / v0.6.0 convention.
    from services.agent_tools import registry_v0_6_5 as _at_v0_6_5

    _at_v0_6_5.register_v0_6_5_tools()


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vysted Terminal sidecar")
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "Localhost port assigned by the Tauri core at launch. Required for "
            "the default HTTP transport; ignored when --mcp-stdio is set."
        ),
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Application data directory resolved by the Tauri core.",
    )
    parser.add_argument(
        "--mcp-stdio",
        action="store_true",
        help=(
            "Run the FastMCP server over stdio instead of uvicorn (FR-025). "
            "An external MCP client spawns this binary directly and speaks "
            "JSON-RPC over stdin/stdout. --port is ignored in this mode."
        ),
    )
    return parser


def run_mcp_stdio() -> None:
    """Serve the MCP surface over stdio (FR-025).

    Reuses the SAME runtime tool registrations and ``mcp_server.bind_app(app)``
    wiring the HTTP path performs (``app`` is built by ``app.create_app`` at
    import time, which calls ``bind_app``), then runs the FastMCP server on the
    stdio transport. The stdin-EOF watchdog is NOT started here — the stdio
    transport consumes stdin itself, so the watchdog would race it for EOF.

    ``show_banner=False`` keeps the FastMCP startup banner off stdout, which is
    the JSON-RPC channel in stdio mode.
    """
    _register_runtime_extensions()
    # Idempotent — ``create_app`` already bound the app reference; re-binding
    # documents that the stdio MCP tools call the same in-process app surface.
    mcp_server.bind_app(app)
    mcp_server.get_mcp_server().run(transport="stdio", show_banner=False)


def run_http(host: str, port: int) -> None:
    """Serve the FastAPI app (incl. the mounted /mcp transport) under uvicorn."""
    _register_runtime_extensions()
    threading.Thread(target=_exit_when_parent_closes_stdin, daemon=True).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    if args.data_dir:
        os.environ[DATA_DIR_ENV] = args.data_dir

    if args.mcp_stdio:
        run_mcp_stdio()
        return

    if args.port is None:
        _build_parser().error("--port is required unless --mcp-stdio is set")

    run_http(args.host, args.port)


if __name__ == "__main__":
    main()
