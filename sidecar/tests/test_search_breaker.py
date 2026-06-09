"""Tests for the per-engine circuit breaker (``services.search.breaker``)."""

from __future__ import annotations

from services.search.breaker import (
    STATE_CLOSED,
    STATE_HALF_OPEN,
    STATE_OPEN,
    CircuitBreaker,
    breaker_for,
    breaker_status,
    reset_breakers,
)


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, secs: float) -> None:
        self.now += secs


def _breaker(clock: _Clock, *, threshold: int = 2, cooldown: float = 45.0) -> CircuitBreaker:
    return CircuitBreaker(fail_threshold=threshold, cooldown_secs=cooldown, clock=clock)


def test_starts_closed_and_allows() -> None:
    br = _breaker(_Clock())
    assert br.state == STATE_CLOSED
    assert br.allow() is True
    assert br.cooldown_remaining() == 0.0


def test_single_failure_stays_closed() -> None:
    br = _breaker(_Clock())
    br.record_failure()
    assert br.state == STATE_CLOSED
    assert br.allow() is True


def test_threshold_failures_trip_open() -> None:
    clock = _Clock()
    br = _breaker(clock)
    br.record_failure()
    br.record_failure()
    assert br.state == STATE_OPEN
    assert br.allow() is False
    assert br.cooldown_remaining() == 45.0


def test_success_resets_failure_count() -> None:
    br = _breaker(_Clock())
    br.record_failure()
    br.record_success()
    br.record_failure()  # only one consecutive failure now
    assert br.state == STATE_CLOSED


def test_cooldown_counts_down_with_clock() -> None:
    clock = _Clock()
    br = _breaker(clock)
    br.record_failure()
    br.record_failure()
    clock.advance(21.0)
    assert br.state == STATE_OPEN
    assert br.cooldown_remaining() == 24.0  # the honest "cooling down (24s)" number


def test_half_open_after_cooldown_allows_single_probe() -> None:
    clock = _Clock()
    br = _breaker(clock)
    br.record_failure()
    br.record_failure()
    clock.advance(45.0)
    assert br.state == STATE_HALF_OPEN
    assert br.allow() is True  # the one probe
    assert br.allow() is False  # no second request while the probe is in flight


def test_probe_success_closes() -> None:
    clock = _Clock()
    br = _breaker(clock)
    br.record_failure()
    br.record_failure()
    clock.advance(45.0)
    assert br.allow() is True
    br.record_success()
    assert br.state == STATE_CLOSED
    assert br.allow() is True


def test_probe_failure_reopens_with_fresh_cooldown() -> None:
    clock = _Clock()
    br = _breaker(clock)
    br.record_failure()
    br.record_failure()
    clock.advance(45.0)
    assert br.allow() is True
    br.record_failure()
    assert br.state == STATE_OPEN
    assert br.cooldown_remaining() == 45.0  # fresh bench, not the stale one
    assert br.allow() is False


def test_breaker_for_is_process_global_per_engine() -> None:
    reset_breakers()
    try:
        assert breaker_for("ddg") is breaker_for("ddg")
        assert breaker_for("ddg") is not breaker_for("brave")
    finally:
        reset_breakers()


def test_breaker_status_shape() -> None:
    reset_breakers()
    try:
        status = breaker_status("mojeek")
        assert status["id"] == "mojeek"
        assert status["state"] == STATE_CLOSED
        assert status["cooldown_remaining_s"] == 0.0
    finally:
        reset_breakers()
