"""Process-global request pacing for the keyless T1 search tier (R7 Component 1).

Two small primitives the engine rotation in :mod:`services.search.keyless`
composes:

  * :class:`RequestQueue` — a per-engine min-interval throttle. All outbound
    hits to one engine are serialized through a per-engine :class:`asyncio.Lock`
    and spaced at least ``min_interval`` seconds apart, process-wide. This is
    PROACTIVE pacing: it dodges the soft burst thresholds (DDG's 202 "anomaly"
    page, Brave's CAPTCHA wall) before they fire, instead of only reacting to
    them. The first request to an engine is never delayed.

  * :func:`backoff_delay` — exponential backoff with multiplicative jitter for
    the bounded per-engine retry (2 attempts, then rotate to the next engine).
    Jitter prevents the lockstep re-hammering that turns one throttle response
    into a synchronized second one.

``clock``/``sleeper``/``rng`` are injectable purely for deterministic offline
tests; production uses ``time.monotonic`` / ``asyncio.sleep`` / ``random``.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable

#: Default seconds between two requests to the SAME engine (process-wide).
#: DDG ~3s mirrors the existing ~20/min token bucket in ``ddg.py``; the HTML
#: SERPs of Brave/Mojeek tolerate a slightly tighter cadence.
ENGINE_MIN_INTERVALS: dict[str, float] = {
    "ddg": 3.0,
    "brave": 2.0,
    "mojeek": 2.0,
}

#: Fallback spacing for an engine without an explicit entry.
DEFAULT_MIN_INTERVAL = 2.0

#: Bounded retry budget per engine before the chain rotates onward.
ATTEMPTS_PER_ENGINE = 2

#: Backoff shape: ``base * factor**attempt``, then +0..25% jitter.
_BACKOFF_BASE_SECS = 0.4
_BACKOFF_FACTOR = 2.0
_BACKOFF_JITTER = 0.25


def min_interval_for(engine_id: str) -> float:
    """The configured min-interval for ``engine_id`` (default for unknowns)."""
    return ENGINE_MIN_INTERVALS.get(engine_id, DEFAULT_MIN_INTERVAL)


def backoff_delay(
    attempt: int,
    *,
    base: float = _BACKOFF_BASE_SECS,
    factor: float = _BACKOFF_FACTOR,
    jitter: float = _BACKOFF_JITTER,
    rng: Callable[[], float] = random.random,
) -> float:
    """Exponential backoff for retry ``attempt`` (0-based) with +0..jitter%.

    attempt 0 → ~0.40-0.50s, attempt 1 → ~0.80-1.00s with the defaults — short
    enough that a keyless search never turns into a long stall, long enough to
    let a momentary throttle pass.
    """
    delay = base * (factor ** max(attempt, 0))
    return delay * (1.0 + jitter * rng())


class RequestQueue:
    """Per-engine min-interval throttle, serialized per engine.

    Concurrent searches share one queue: requests to the SAME engine line up
    on its lock and are spaced ``min_interval`` apart; requests to DIFFERENT
    engines proceed independently (rotating to Brave is never blocked by DDG
    pacing). ``acquire`` returns the seconds slept (``0.0`` when immediate)
    for observability and deterministic tests.
    """

    def __init__(
        self,
        *,
        intervals: dict[str, float] | None = None,
        default_interval: float = DEFAULT_MIN_INTERVAL,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._intervals = dict(ENGINE_MIN_INTERVALS if intervals is None else intervals)
        self._default = default_interval
        self._clock = clock
        self._sleeper = sleeper
        self._last: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, engine_id: str) -> asyncio.Lock:
        lock = self._locks.get(engine_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[engine_id] = lock
        return lock

    async def acquire(self, engine_id: str) -> float:
        """Wait for ``engine_id``'s next slot; returns the seconds slept."""
        interval = self._intervals.get(engine_id, self._default)
        async with self._lock_for(engine_id):
            now = self._clock()
            last = self._last.get(engine_id)
            wait = 0.0 if last is None else max(0.0, last + interval - now)
            if wait > 0:
                await self._sleeper(wait)
            # Stamp the SLOT time (not the post-sleep clock read) so back-to-back
            # acquires stay exactly one interval apart under a fake sleeper too.
            self._last[engine_id] = now + wait
            return wait


#: Process-global queue — lazily built on first use so no asyncio primitive is
#: created at import time before an event loop exists.
_QUEUE: RequestQueue | None = None


def get_queue() -> RequestQueue:
    """Return the process-global request queue, building it lazily."""
    global _QUEUE
    if _QUEUE is None:
        _QUEUE = RequestQueue()
    return _QUEUE


def reset_queue() -> None:
    """Drop the process-global queue (test isolation only)."""
    global _QUEUE
    _QUEUE = None


__all__ = [
    "ATTEMPTS_PER_ENGINE",
    "DEFAULT_MIN_INTERVAL",
    "ENGINE_MIN_INTERVALS",
    "RequestQueue",
    "backoff_delay",
    "get_queue",
    "min_interval_for",
    "reset_queue",
]
