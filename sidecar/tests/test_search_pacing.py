"""Tests for the per-engine request queue + backoff (``services.search.pacing``)."""

from __future__ import annotations

import asyncio

from services.search.pacing import (
    ATTEMPTS_PER_ENGINE,
    RequestQueue,
    backoff_delay,
    get_queue,
    min_interval_for,
    reset_queue,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, secs: float) -> None:
        self.now += secs


def _queue(clock: _Clock, slept: list[float]) -> RequestQueue:
    async def _sleeper(secs: float) -> None:
        slept.append(secs)
        clock.advance(secs)  # a fake sleep still advances the fake clock

    return RequestQueue(
        intervals={"ddg": 3.0, "brave": 2.0}, default_interval=1.5, clock=clock, sleeper=_sleeper
    )


def _run(coro):
    return asyncio.run(coro)


def test_first_request_is_immediate() -> None:
    slept: list[float] = []
    q = _queue(_Clock(), slept)
    assert _run(q.acquire("ddg")) == 0.0
    assert slept == []


def test_back_to_back_requests_are_spaced_by_min_interval() -> None:
    clock = _Clock()
    slept: list[float] = []
    q = _queue(clock, slept)

    async def _two() -> tuple[float, float]:
        first = await q.acquire("ddg")
        second = await q.acquire("ddg")
        return first, second

    first, second = _run(_two())
    assert first == 0.0
    assert second == 3.0  # paced to the ddg min-interval
    assert slept == [3.0]


def test_elapsed_time_reduces_the_wait() -> None:
    clock = _Clock()
    slept: list[float] = []
    q = _queue(clock, slept)

    async def _go() -> float:
        await q.acquire("ddg")
        clock.advance(2.0)  # 2s of real work elapsed since the last hit
        return await q.acquire("ddg")

    assert _run(_go()) == 1.0  # only the 1s deficit is slept


def test_engines_are_throttled_independently() -> None:
    clock = _Clock()
    slept: list[float] = []
    q = _queue(clock, slept)

    async def _go() -> float:
        await q.acquire("ddg")
        return await q.acquire("brave")  # different engine — no ddg pacing applies

    assert _run(_go()) == 0.0


def test_unknown_engine_uses_default_interval() -> None:
    clock = _Clock()
    slept: list[float] = []
    q = _queue(clock, slept)

    async def _go() -> float:
        await q.acquire("newengine")
        return await q.acquire("newengine")

    assert _run(_go()) == 1.5


def test_concurrent_acquires_serialize_per_engine() -> None:
    clock = _Clock()
    slept: list[float] = []
    q = _queue(clock, slept)

    async def _go() -> list[float]:
        return list(await asyncio.gather(q.acquire("ddg"), q.acquire("ddg"), q.acquire("ddg")))

    waits = sorted(_run(_go()))
    assert waits == [0.0, 3.0, 3.0]  # one immediate, each follower waits one slot


def test_backoff_grows_exponentially_with_bounded_jitter() -> None:
    # rng pinned to 0 → pure exponential base; rng pinned to 1 → +25% ceiling.
    assert backoff_delay(0, rng=lambda: 0.0) == 0.4
    assert backoff_delay(1, rng=lambda: 0.0) == 0.8
    assert backoff_delay(0, rng=lambda: 1.0) == 0.5
    assert backoff_delay(1, rng=lambda: 1.0) == 1.0


def test_retry_budget_is_two_attempts_per_engine() -> None:
    assert ATTEMPTS_PER_ENGINE == 2


def test_min_interval_for_known_and_unknown_engines() -> None:
    assert min_interval_for("ddg") == 3.0
    assert min_interval_for("never-heard-of-it") == 2.0


def test_global_queue_is_lazy_singleton() -> None:
    reset_queue()
    try:
        assert get_queue() is get_queue()
    finally:
        reset_queue()
