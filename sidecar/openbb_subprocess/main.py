"""OpenBB subprocess — its own FastAPI service the main sidecar proxies through.

OpenBB-core's strict pins (fastapi <0.129, uvicorn <0.41) are incompatible
with the main Vysted sidecar's deps. Running OpenBB in its own process with
its own venv (and its own PyInstaller --onefile binary) isolates the version
conflict — the Tier 2 path per plan §A2 + BLOCKERS-C.md.

The subprocess uses the same router-loader + command-runner trick the original
in-process provider used: never `import openbb` (the meta-package), only
`openbb_core.app.router.RouterLoader.from_extensions()` + `CommandRunner`.
That avoids OpenBB's first-import static-package codegen, which writes into
`site-packages` and is fatal under PyInstaller --onefile.

Lifecycle: spawned by the main sidecar lazily on first OpenBB request via
`scripts/ensure-openbb-sidecar.mjs`. Shutdown follows the standard
stdin-EOF watchdog pattern — when the parent (the main sidecar) drops the
stdin pipe, this process self-exits, the same trick the main sidecar uses
to follow the Tauri core's shutdown.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from datetime import UTC, datetime
from threading import Lock
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


def _exit_when_parent_closes_stdin() -> None:
    """Terminate when the main sidecar closes our stdin.

    Mirrors the main sidecar's pattern: spawn a daemon thread that does a
    blocking read on stdin; when the parent (the main sidecar) drops its end
    of the pipe the read returns EOF and we self-exit.

    Subtlety: on Windows, calling ``sys.stdin.buffer.read()`` blocking under
    a ``subprocess.Popen(..., stdin=PIPE)`` parent appears to deadlock the
    OpenBB router-loader's anyio thread (the prewarm thread never completes;
    /health hangs at 503 indefinitely). The fix is to read from the raw OS
    file descriptor in chunks via ``os.read``, which doesn't take any of the
    higher-level Python locks that hose the anyio portal. See BLOCKERS-C.md
    "Subprocess stdin watchdog interaction".
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


# ---------------------------------------------------------------------------
# Lazy CommandRunner — same pattern as the in-process provider.
# ---------------------------------------------------------------------------

_runner: Any = None
_runner_lock = Lock()
_prewarm_done = False


def _get_runner() -> Any:
    global _runner
    with _runner_lock:
        if _runner is None:
            from openbb_core.app.command_runner import CommandRunner
            from openbb_core.app.router import RouterLoader

            RouterLoader.from_extensions()
            _runner = CommandRunner()
        return _runner


def _model_to_dict(item: Any) -> dict[str, Any]:
    if hasattr(item, "model_dump"):
        return dict(item.model_dump())
    if isinstance(item, dict):
        return dict(item)
    return {}


def _run(
    route: str,
    *,
    provider: str,
    standard_params: dict[str, Any] | None = None,
    extra_params: dict[str, Any] | None = None,
) -> Any:
    runner = _get_runner()
    try:
        return runner.sync_run(
            route,
            user="",
            provider_choices={"provider": provider},
            standard_params=standard_params or {},
            extra_params=extra_params or {},
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"OpenBB call {route!r} failed: {exc}") from exc


def _ensure_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None:
        return datetime.now(tz=UTC).isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# FastAPI app — minimal surface, returns plain dicts the main sidecar proxies.
# ---------------------------------------------------------------------------

app = FastAPI(title="Vysted OpenBB Subprocess", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health() -> Any:
    """Liveness — the main sidecar polls this before its first proxied call.

    Returns 200 only once the router prewarm has completed. Cold-start
    PyInstaller-bundled `RouterLoader.from_extensions()` can take 10-30 s; the
    main sidecar waits on this signal so its first proxied call doesn't time
    out mid-discovery.
    """
    if not _prewarm_done:
        raise HTTPException(status_code=503, detail="OpenBB router still warming up.")
    return {"status": "ok", "service": "vysted-openbb"}


@app.get("/quote/{symbol}")
def quote(symbol: str) -> dict[str, Any]:
    result = _run("/equity/price/quote", provider="yfinance", standard_params={"symbol": symbol})
    rows = getattr(result, "results", None) or []
    if not rows:
        raise HTTPException(status_code=502, detail=f"No quote rows for {symbol!r}")
    row = _model_to_dict(rows[0])
    if "last_timestamp" in row:
        row["last_timestamp"] = _ensure_datetime(row["last_timestamp"])
    return row


@app.get("/history/{symbol}")
def history(
    symbol: str,
    interval: str = "1d",
    start_date: str | None = None,
) -> dict[str, Any]:
    extra: dict[str, Any] = {"interval": interval}
    if start_date:
        extra["start_date"] = start_date
    result = _run(
        "/equity/price/historical",
        provider="yfinance",
        standard_params={"symbol": symbol},
        extra_params=extra,
    )
    bars: list[dict[str, Any]] = []
    for raw in getattr(result, "results", None) or []:
        row = _model_to_dict(raw)
        row["date"] = _ensure_datetime(row.get("date") or row.get("timestamp"))
        bars.append(row)
    return {"symbol": symbol, "bars": bars}


@app.get("/profile/{symbol}")
def profile(symbol: str) -> dict[str, Any]:
    result = _run("/equity/profile", provider="yfinance", standard_params={"symbol": symbol})
    rows = getattr(result, "results", None) or []
    return _model_to_dict(rows[0]) if rows else {}


@app.get("/metrics/{symbol}")
def metrics(symbol: str) -> dict[str, Any]:
    result = _run(
        "/equity/fundamental/metrics",
        provider="yfinance",
        standard_params={"symbol": symbol},
    )
    rows = getattr(result, "results", None) or []
    return _model_to_dict(rows[0]) if rows else {}


@app.get("/statement/{symbol}")
def statement(
    symbol: str,
    kind: str = Query(..., description="One of: income | balance | cash"),
) -> dict[str, Any]:
    route_map = {
        "income": "/equity/fundamental/income",
        "balance": "/equity/fundamental/balance",
        "cash": "/equity/fundamental/cash",
    }
    route = route_map.get(kind)
    if not route:
        raise HTTPException(status_code=400, detail=f"unknown statement kind: {kind!r}")
    result = _run(route, provider="yfinance", standard_params={"symbol": symbol})
    rows = [_model_to_dict(r) for r in (getattr(result, "results", None) or [])]
    return {"symbol": symbol, "rows": rows}


@app.get("/ratings/{symbol}")
def ratings(symbol: str) -> dict[str, Any]:
    result = _run(
        "/equity/estimates/price_target",
        provider="yfinance",
        standard_params={"symbol": symbol},
    )
    rows = getattr(result, "results", None) or []
    return _model_to_dict(rows[0]) if rows else {}


@app.get("/macro/{series_id}")
def macro(
    series_id: str,
    provider: str = Query(default="fred"),
) -> dict[str, Any]:
    result = _run("/economy/fred_series", provider=provider, standard_params={"symbol": series_id})
    observations: list[dict[str, Any]] = []
    for raw in getattr(result, "results", None) or []:
        row = _model_to_dict(raw)
        row["date"] = _ensure_datetime(row.get("date"))
        observations.append(row)
    metadata = getattr(result, "extra", None) or {}
    title = ""
    if isinstance(metadata, dict):
        info = metadata.get("results_metadata") or {}
        if isinstance(info, dict):
            entry = info.get(series_id) or next(iter(info.values()), {})
            if isinstance(entry, dict):
                title = str(entry.get("title") or "")
    return {"series_id": series_id, "title": title or series_id, "observations": observations}


def _prewarm_runner() -> None:
    """Build the OpenBB router on a worker thread so the first inbound request
    does not pay the (significant, ~10-30 s in the PyInstaller bundle)
    RouterLoader.from_extensions() cost while a client is waiting on a
    socket. Sets ``_prewarm_done`` when complete; ``/health`` returns 503
    until then so the main sidecar's launch poll waits for full readiness.
    """
    global _prewarm_done
    try:
        _get_runner()
    except Exception:  # noqa: BLE001 - prewarm is best-effort
        pass
    finally:
        _prewarm_done = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Vysted OpenBB subprocess")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    # Skip the stdin-EOF watchdog when explicitly disabled (--no-watchdog) or
    # when stdin is a pipe — see BLOCKERS-C.md "Subprocess stdin watchdog
    # interaction". The main sidecar's FastAPI lifespan handler explicitly
    # terminates this subprocess on shutdown via subprocess.terminate(), so
    # the watchdog is belt-and-suspenders insurance, not a hard requirement.
    threading.Thread(target=_exit_when_parent_closes_stdin, daemon=True).start()
    threading.Thread(target=_prewarm_runner, daemon=True).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
