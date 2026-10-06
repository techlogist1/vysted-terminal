"""QuantLib pricing in a worker process, off the sidecar event loop.

QuantLib's SWIG calls hold the GIL, so ``asyncio.to_thread`` still froze every
route for the length of a pricing (a 20k-step binomial blocked ``/health`` for
6.4 s — R15-CODE-PLATFORM-018). Every async pricing lane (workflow nodes, agent
tools, the ``/quant`` routes) goes through :func:`run_quant` instead. Inside a
worker the per-process ``_QL_LOCK`` still guards the evaluation date.
"""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import threading
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor

_pool: ProcessPoolExecutor | None = None


def _exit_with_parent() -> None:
    """Pool initializer: the worker exits when the sidecar dies.

    A SIGKILLed sidecar (Tauri's RunEvent::Exit) never runs :func:`shutdown`;
    without this its workers reparent to PID 1 and live forever. The spawn
    parent sentinel is the stdlib's parent-death signal (a pipe EOF on POSIX,
    the parent's process handle on Windows).
    """
    parent = multiprocessing.parent_process()
    if parent is not None:
        threading.Thread(target=lambda: (parent.join(), os._exit(0)), daemon=True).start()


def _get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        # spawn, not fork: a forked child of a threaded asyncio server can
        # inherit held locks. The frozen binary needs freeze_support() (main.py).
        _pool = ProcessPoolExecutor(
            max_workers=2,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=_exit_with_parent,
        )
    return _pool


async def run_quant[Req, Res](fn: Callable[[Req], Res], req: Req) -> Res:
    """Run ``fn(req)`` in the pricing pool; ``fn`` must be a module-level function."""
    # ponytail: a running pricing cannot be cancelled mid-flight; a node timeout
    # abandons the result while the worker finishes. Kill-and-respawn the worker
    # if abandoned pricings ever starve the pool.
    return await asyncio.get_running_loop().run_in_executor(_get_pool(), fn, req)


def shutdown() -> None:
    """Stop the pool now, even mid-pricing (lifespan ``finally`` and the stdin-EOF
    watchdog before its ``os._exit``); a later pricing recreates it."""
    global _pool
    pool, _pool = _pool, None
    if pool is None:
        return
    # ponytail: private _processes; Python 3.14's terminate_workers() replaces it.
    workers = list(pool._processes.values())
    pool.shutdown(wait=False, cancel_futures=True)
    for worker in workers:
        worker.terminate()
    for worker in workers:
        worker.join(timeout=2)


__all__ = ["run_quant", "shutdown"]
