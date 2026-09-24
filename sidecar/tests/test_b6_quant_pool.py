"""QuantLib holds the GIL, so pricing must leave the process, not just the
event-loop thread (R15-CODE-PLATFORM-018)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from services.quant.pool import run_quant

SIDECAR_DIR = Path(__file__).resolve().parents[1]


def _pid(_req: object) -> int:
    return os.getpid()


@pytest.mark.asyncio
async def test_run_quant_executes_in_a_worker_process() -> None:
    assert await run_quant(_pid, None) != os.getpid()


# A real sidecar-shaped parent: imports main (the app + the stdin watchdog),
# prices once through the pool, reports readiness, then either runs the
# watchdog (stdin EOF -> os._exit) or just sleeps until it is killed.
_CHILD = """
import asyncio, sys, time
import main
from models.quant import OptionPricingRequest
from services.quant import options
from services.quant.pool import run_quant

req = OptionPricingRequest(
    exercise="american", payoff="put", spot=100.0, strike=100.0,
    risk_free_rate=0.05, dividend_yield=0.02, volatility=0.2,
    valuation_date="2026-05-16", expiry_date="2027-05-16",
    method="binomial", binomial_steps=50,
)
asyncio.run(run_quant(options.price, req))
print("priced", flush=True)
if sys.argv[1] == "watchdog":
    main._exit_when_parent_closes_stdin()
else:
    time.sleep(600)
"""


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _orphans_after(exit_parent: str, tmp_path: Path) -> list[int]:
    """Children (pool workers + resource_tracker) still alive 5 s after the parent exits."""
    env = {**os.environ, "VYSTED_DATA_DIR": str(tmp_path)}
    child = subprocess.Popen(
        [sys.executable, "-c", _CHILD, exit_parent],
        cwd=SIDECAR_DIR,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    try:
        assert child.stdout is not None and child.stdout.readline() == b"priced\n"
        out = subprocess.run(["pgrep", "-P", str(child.pid)], capture_output=True, text=True)
        pids = [int(p) for p in out.stdout.split()]
        assert pids, "pricing must have spawned pool workers"
        if exit_parent == "watchdog":
            child.stdin.close()  # type: ignore[union-attr]
        else:
            child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and any(_alive(p) for p in pids):
            time.sleep(0.1)
        return [p for p in pids if _alive(p)]
    finally:
        child.kill()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process tree (pgrep)")
def test_watchdog_exit_leaves_no_pool_processes(tmp_path: Path) -> None:
    """The stdin-EOF watchdog's os._exit skips the lifespan finally; the pool
    workers and resource_tracker must not be orphaned (R15-CODE-PLATFORM-018)."""
    leaked = _orphans_after("watchdog", tmp_path)
    for pid in leaked:
        os.kill(pid, signal.SIGKILL)
    assert leaked == []


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process tree (pgrep)")
def test_pool_workers_die_with_a_killed_parent(tmp_path: Path) -> None:
    """Tauri's RunEvent::Exit kills the sidecar outright; workers must follow."""
    leaked = _orphans_after("kill", tmp_path)
    for pid in leaked:
        os.kill(pid, signal.SIGKILL)
    assert leaked == []
