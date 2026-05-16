"""sec-edgar-mcp subprocess entry point.

Hosts the stock ``sec-edgar-mcp`` package (1.0.8) on a port picked by the
Tauri Rust core. The main Vysted sidecar connects to this subprocess as
an MCP client (Streamable-HTTP transport) and proxies its tool surface
via :mod:`services.sec_filings_provider`.

This entry point is what ``scripts/ensure-sec-edgar-mcp-sidecar.mjs``
bundles into a PyInstaller ``--onefile`` binary
(``vysted-sec-edgar-mcp-sidecar-<triple>[.exe]``). The binary is spawned by
``src-tauri/src/sec_edgar_mcp.rs`` — Tauri Rust ``Command::new`` rather
than Python ``subprocess.Popen``, which is the architectural fix for the
Phase-2 Windows deadlock (CLAUDE.md Gotcha; precedent
``sidecar/openbb_mcp_subprocess/`` v0.4.0).

Like the openbb-mcp subprocess, this child implements the stdin-EOF
watchdog so the Tauri core can shut it down cleanly: when the parent
drops the stdin pipe, the watchdog reads EOF and ``os._exit(0)``.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading


def _exit_when_parent_closes_stdin() -> None:
    """Terminate when the parent closes our stdin (clean-shutdown signal).

    Mirrors the openbb-mcp subprocess: ``os.read`` rather than the
    higher-level ``sys.stdin.buffer.read`` to avoid the Windows-specific
    deadlock documented in the v0.3.0 BLOCKERS and the CLAUDE.md Gotcha
    on PyInstaller ``_MEIPASS`` interactions.
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
    parser = argparse.ArgumentParser(description="Vysted sec-edgar-mcp subprocess")
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

    # sec-edgar-mcp's server module reads ``--transport`` / ``--port`` /
    # ``--host`` from ``sys.argv``. Streamable-HTTP is the transport the
    # Vysted MCP client speaks (matches the openbb-mcp pattern).
    sys.argv = [
        sys.argv[0],
        "--transport",
        "streamable-http",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]

    # sec-edgar-mcp respects the standard SEC fair-access guidance and
    # requires a User-Agent header. The upstream package reads it from
    # the ``SEC_EDGAR_USER_AGENT`` env var if not otherwise configured;
    # set a sane default here so the subprocess never 403s SEC EDGAR.
    os.environ.setdefault(
        "SEC_EDGAR_USER_AGENT",
        "Vysted Terminal (contact: support@vysted.com)",
    )

    # Defer the import until argv is set so the upstream server sees the
    # rewritten argv. The exact public entry point lives at
    # ``sec_edgar_mcp.server`` per the package's docs.
    from sec_edgar_mcp.server import main as sec_edgar_main  # type: ignore[import-not-found]

    sec_edgar_main()


if __name__ == "__main__":
    main()
