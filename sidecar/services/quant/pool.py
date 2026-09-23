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
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor

_pool: ProcessPoolExecutor | None = None


def _get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        # spawn, not fork: a forked child of a threaded asyncio server can
        # inherit held locks. The frozen binary needs freeze_support() (main.py).
        _pool = ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn"))
    return _pool


async def run_quant[Req, Res](fn: Callable[[Req], Res], req: Req) -> Res:
    """Run ``fn(req)`` in the pricing pool; ``fn`` must be a module-level function."""
    # ponytail: a running pricing cannot be cancelled mid-flight; a node timeout
    # abandons the result while the worker finishes. Kill-and-respawn the worker
    # if abandoned pricings ever starve the pool.
    return await asyncio.get_running_loop().run_in_executor(_get_pool(), fn, req)


def shutdown() -> None:
    """Stop the pool (app lifespan ``finally``); a later pricing recreates it."""
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


__all__ = ["run_quant", "shutdown"]
