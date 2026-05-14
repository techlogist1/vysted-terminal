"""Vysted Terminal Python sidecar — a FastAPI service on localhost.

Phase 0 scope: a single /health endpoint. The Tauri core assigns a free port
at app launch and passes it in via the --port CLI argument.
"""

from __future__ import annotations

import argparse

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Vysted Terminal Sidecar", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe consumed by the Tauri core on app launch."""
    return {"status": "ok", "service": "vysted-sidecar", "version": "0.1.0"}


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

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
