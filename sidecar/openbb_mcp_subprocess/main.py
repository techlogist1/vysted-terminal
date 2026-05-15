"""openbb-mcp subprocess entry point.

Hosts the stock ``openbb-mcp-server`` package (1.4.0) on a port picked by the
Tauri Rust core. The main Vysted sidecar connects to this subprocess as an
MCP client (Streamable-HTTP transport) and proxies its tool surface via
:mod:`services.openbb_mcp_provider`.

This entry point is what ``scripts/ensure-openbb-mcp-sidecar.mjs`` bundles
into a PyInstaller ``--onefile`` binary
(``vysted-openbb-mcp-sidecar-<triple>[.exe]``). The binary is spawned by
``src-tauri/src/openbb_mcp.rs`` — Tauri Rust ``Command::new`` rather than
Python ``subprocess.Popen``, which is the architectural fix for the
Phase-2 Windows deadlock (CLAUDE.md Gotcha).

Like the main sidecar, this subprocess implements the stdin-EOF watchdog
so the Tauri core can shut it down cleanly: when the parent (the Tauri
core, or its supervising helper) drops the stdin pipe, the watchdog
reads EOF and ``os._exit(0)``.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading


def _exit_when_parent_closes_stdin() -> None:
    """Terminate when the parent closes our stdin (clean-shutdown signal).

    Reads in chunks via ``os.read`` rather than the higher-level
    ``sys.stdin.buffer.read`` to avoid the same Windows-specific deadlock
    documented in the v0.3.0 BLOCKERS — that pattern hung the original
    OpenBB subprocess. ``os.read`` does not take the higher-level Python
    locks that interact badly with anyio under PyInstaller ``_MEIPASS``.
    """
    if sys.stdin is None:
        return
    try:
        fd = sys.stdin.fileno()
    except Exception:  # noqa: BLE001
        return
    try:
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
    except Exception:  # noqa: BLE001
        pass
    os._exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vysted openbb-mcp subprocess")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--no-watchdog",
        action="store_true",
        help="Skip the stdin-EOF watchdog (useful when running standalone for tests).",
    )
    args = parser.parse_args()

    if not args.no_watchdog:
        threading.Thread(target=_exit_when_parent_closes_stdin, daemon=True).start()

    # Delegate to openbb-mcp-server's own ``main`` after rewriting ``sys.argv``
    # so its argparse picks up the host/port we want. openbb-mcp-server expects
    # ``--transport streamable-http --host H --port P``; we always speak the
    # Streamable-HTTP transport (matches what the main sidecar's MCP client
    # connects to).
    sys.argv = [
        sys.argv[0],
        "--transport",
        "streamable-http",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]

    from openbb_mcp_server.app.app import main as openbb_main  # type: ignore[import-not-found]

    openbb_main()


if __name__ == "__main__":
    main()
