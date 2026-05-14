"""Vysted Terminal Python sidecar — a FastAPI service on localhost.

Phase 0 scope: a single /health endpoint. The Tauri core assigns a free port
at app launch and passes it in via the --port CLI argument.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Vysted Terminal Sidecar", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe consumed by the Tauri core on app launch."""
    return {"status": "ok", "service": "vysted-sidecar", "version": "0.1.0"}


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
    args = parser.parse_args()

    threading.Thread(target=_exit_when_parent_closes_stdin, daemon=True).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
