"""Tests for the Yahoo-family circuit breaker (R11, D53).

The tracker is process-global (reset by the autouse conftest fixture); time
is controlled by monkeypatching ``time.monotonic`` inside the module so the
cooldown math is deterministic.
"""

from __future__ import annotations

import pytest

from services import provider_health


def test_closed_until_threshold_then_opens() -> None:
    assert provider_health.is_open() is False
    provider_health.record_rate_limited()
    provider_health.record_rate_limited()
    assert provider_health.is_open() is False  # streak 2 < threshold 3
    provider_health.record_rate_limited()
    assert provider_health.is_open() is True
    status = provider_health.status()
    assert status["open"] is True
    assert status["opens_total"] == 1
    assert status["cooldown_remaining"] > 0


def test_weight_reports_a_batch_storm_as_multiple_events() -> None:
    provider_health.record_rate_limited(weight=3.0)
    assert provider_health.is_open() is True


def test_success_closes_and_resets() -> None:
    provider_health.record_rate_limited(weight=5.0)
    assert provider_health.is_open() is True
    provider_health.record_success()
    assert provider_health.is_open() is False
    assert provider_health.status()["consecutive_throttles"] == 0
    # A fresh streak must again need the full threshold.
    provider_health.record_rate_limited()
    assert provider_health.is_open() is False


def test_cooldown_lapses_half_open_then_reopens_longer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"now": 1000.0}
    monkeypatch.setattr(provider_health.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(provider_health.random, "uniform", lambda a, b: 0.0)  # no jitter

    provider_health.record_rate_limited(weight=3.0)
    assert provider_health.is_open() is True
    first_cooldown = provider_health.cooldown_remaining()
    assert first_cooldown == pytest.approx(60.0)

    # While open, further throttle reports do not extend the window.
    clock["now"] += 10.0
    provider_health.record_rate_limited(weight=10.0)
    assert provider_health.cooldown_remaining() == pytest.approx(50.0)

    # Cooldown lapses — half-open: callers may probe again.
    clock["now"] += 60.0
    assert provider_health.is_open() is False

    # The probe fails again: the second open is geometrically longer.
    provider_health.record_rate_limited(weight=3.0)
    assert provider_health.is_open() is True
    assert provider_health.cooldown_remaining() == pytest.approx(120.0)

    # A healthy probe after THAT cooldown fully resets the ladder.
    clock["now"] += 120.0
    provider_health.record_success()
    provider_health.record_rate_limited(weight=3.0)
    assert provider_health.cooldown_remaining() == pytest.approx(60.0)


def test_families_are_independent() -> None:
    provider_health.record_rate_limited("yahoo", weight=3.0)
    assert provider_health.is_open("yahoo") is True
    assert provider_health.is_open("some-other-upstream") is False
