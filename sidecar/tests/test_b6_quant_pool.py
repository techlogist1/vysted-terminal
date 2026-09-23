"""QuantLib holds the GIL, so pricing must leave the process, not just the
event-loop thread (R15-CODE-PLATFORM-018)."""

from __future__ import annotations

import os

import pytest

from services.quant.pool import run_quant


def _pid(_req: object) -> int:
    return os.getpid()


@pytest.mark.asyncio
async def test_run_quant_executes_in_a_worker_process() -> None:
    assert await run_quant(_pid, None) != os.getpid()
