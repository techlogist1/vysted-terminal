"""Global kill switch — BLUEPRINT §6.5 #5.

A prominent always-visible "Halt All Trading" control in the main UI
immediately disables order placement across every broker plugin at once.
The runtime side of that promise is this async event broadcaster.

Every broker adapter subscribes on construction (forced in
``BrokerAdapter.__init__`` — see ``services/broker_base.py``). When the
user fires the kill switch via the toolbar / keyboard shortcut / system
tray / slash command, :func:`fire` dispatches the event to every
subscriber concurrently and aggregates ack times. The dedicated safety
audit suite (Teammate S) asserts ``max_ack_ms < 2000`` on a real run
with 7 brokers + 3 workflows + 2 pending paper proposals — instrumented,
not approximated.

The bus is module-singleton; lifecycle handled by the FastAPI lifespan
in ``app.py``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from models.safety import KillSwitchEvent, KillSwitchFireResult

logger = logging.getLogger(__name__)

KillSwitchCallback = Callable[[KillSwitchEvent], Awaitable[None]]
Unsubscribe = Callable[[], None]

#: Subscriber-ack budget — the dedicated safety audit suite hard-fails when
#: any subscriber exceeds this on the real-config run.
ACK_BUDGET_NS = 2_000_000_000


class KillSwitchBus:
    """Async event broadcaster + subscriber registry.

    Single fire-and-forget semantics: ``fire`` records ``perf_counter_ns``
    at fire time, dispatches to subscribers via ``asyncio.gather``,
    captures per-subscriber ack time, returns aggregated result.

    Re-fire while already fired is a no-op (idempotent). Reset is gated
    behind a dedicated route + re-acknowledgment in the UI; it is NOT an
    everyday toggle.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, KillSwitchCallback] = {}
        self._fired: bool = False
        self._last_event: KillSwitchEvent | None = None
        self._last_result: KillSwitchFireResult | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def subscribe(self, name: str, callback: KillSwitchCallback) -> Unsubscribe:
        """Register a kill-switch callback, return an unsubscribe function.

        ``name`` is the subscriber identifier — broker id for adapters,
        ``workflow:<id>`` for workflow runs, etc. Duplicate names overwrite
        (so re-registering an adapter on reconnect is safe).
        """
        self._subscribers[name] = callback
        logger.debug("kill_switch: subscribed %s (total=%d)", name, len(self._subscribers))

        def _unsubscribe() -> None:
            self._subscribers.pop(name, None)
            logger.debug("kill_switch: unsubscribed %s (total=%d)", name, len(self._subscribers))

        return _unsubscribe

    def subscriber_count(self) -> int:
        """Return the current subscriber count (test helper)."""
        return len(self._subscribers)

    # ------------------------------------------------------------------
    # Fire + reset
    # ------------------------------------------------------------------

    @property
    def is_fired(self) -> bool:
        """Whether the kill switch is currently in the fired state."""
        return self._fired

    @property
    def last_event(self) -> KillSwitchEvent | None:
        """The event from the most-recent fire, or None if never fired."""
        return self._last_event

    @property
    def last_result(self) -> KillSwitchFireResult | None:
        """The aggregated ack result from the most-recent fire."""
        return self._last_result

    async def fire(self, reason: str, fired_by: str) -> KillSwitchFireResult:
        """Broadcast a kill-switch event and return ack timing aggregates.

        Idempotent: if already fired, returns the previously-captured
        result without re-dispatching. Otherwise gathers subscriber acks
        concurrently and computes p50 / p95 / max ack time.
        """
        async with self._lock:
            if self._fired and self._last_result is not None:
                logger.info("kill_switch: fire while already fired — returning prior result")
                return self._last_result

            event = KillSwitchEvent(
                firedAt=int(time.time() * 1000),
                reason=reason,
                firedBy=fired_by,  # type: ignore[arg-type]
            )
            subscribers_snapshot = dict(self._subscribers)
            ack_times: dict[str, float] = {}

            async def _dispatch(name: str, cb: KillSwitchCallback) -> None:
                start = time.perf_counter_ns()
                try:
                    await cb(event)
                except Exception as exc:  # noqa: BLE001 — never block the kill switch
                    logger.exception("kill_switch: subscriber %s raised %s", name, exc)
                elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
                ack_times[name] = elapsed_ms

            await asyncio.gather(
                *(_dispatch(name, cb) for name, cb in subscribers_snapshot.items())
            )

            self._fired = True
            self._last_event = event
            self._last_result = _aggregate_ack_times(event, ack_times)
            logger.warning(
                "kill_switch: FIRED by=%s reason=%r max_ack_ms=%.2f",
                fired_by,
                reason,
                self._last_result.max_ack_ms,
            )
            return self._last_result

    def reset(self) -> None:
        """Reset the fired state. Gated by a re-ack at the route layer."""
        if self._fired:
            logger.warning("kill_switch: RESET requested")
        self._fired = False
        self._last_event = None
        self._last_result = None


def _percentile(values: list[float], pct: float) -> float:
    """Linear-interpolated percentile; matches numpy.percentile for our sample sizes."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    frac = rank - lower
    return sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower])


def _aggregate_ack_times(
    event: KillSwitchEvent, ack_times: dict[str, float]
) -> KillSwitchFireResult:
    """Compute p50/p95/max from raw ack times."""
    values = list(ack_times.values())
    if not values:
        return KillSwitchFireResult(
            event=event,
            ackTimesMs={},
            p50AckMs=0.0,
            p95AckMs=0.0,
            maxAckMs=0.0,
        )
    return KillSwitchFireResult(
        event=event,
        ackTimesMs=ack_times,
        p50AckMs=_percentile(values, 50),
        p95AckMs=_percentile(values, 95),
        maxAckMs=max(values),
    )


# ---------------------------------------------------------------------------
# Module-singleton bus
# ---------------------------------------------------------------------------

#: The single shared kill-switch bus. Broker adapters, workflow runs, and
#: the safety router all use this instance. Tests construct a fresh
#: :class:`KillSwitchBus` and patch this attribute when isolation is needed.
bus = KillSwitchBus()


def get_bus() -> KillSwitchBus:
    """Return the module-singleton bus. Importable from routers + tests."""
    return bus


def reset_bus_for_tests() -> None:
    """Test helper — drops all subscribers and clears fired state.

    Real code should never call this; tests do because the module-singleton
    bus is shared across the FastAPI test client.
    """
    global bus
    bus = KillSwitchBus()


def _unused() -> Any:  # pragma: no cover - keeps Any import for future
    return None
