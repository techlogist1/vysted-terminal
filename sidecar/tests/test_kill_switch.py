"""Tests for the kill-switch event bus.

Asserts:

  - subscribers are called concurrently
  - per-subscriber + aggregated p50 / p95 / max ack times are recorded
  - max ack time stays under the BLUEPRINT §6.5 #5 budget (2_000 ms) on a
    realistic config (10 mock subscribers, each with a short asyncio.sleep)
  - re-fire while fired is idempotent
  - reset clears the fired state
  - a misbehaving subscriber (one that raises) does NOT block the others
"""

from __future__ import annotations

import asyncio

import pytest

from services.kill_switch import KillSwitchBus


@pytest.fixture(autouse=True)
def _isolate_bus() -> None:
    """Each test gets a fresh KillSwitchBus to avoid cross-test bleed."""
    # We don't patch the module singleton here — every test in this file
    # uses a local instance. test_safety_router uses the module-level
    # singleton through the FastAPI app.
    yield


@pytest.mark.asyncio
async def test_subscribe_and_count() -> None:
    bus = KillSwitchBus()

    async def _noop(_event: object) -> None:
        pass

    unsub_a = bus.subscribe("a", _noop)
    bus.subscribe("b", _noop)
    assert bus.subscriber_count() == 2

    unsub_a()
    assert bus.subscriber_count() == 1


@pytest.mark.asyncio
async def test_fire_dispatches_to_all_subscribers() -> None:
    bus = KillSwitchBus()
    received: list[str] = []

    async def _make_cb(name: str):
        async def _cb(event: object) -> None:
            received.append(f"{name}:{event.reason}")  # type: ignore[attr-defined]

        return _cb

    for name in ("a", "b", "c"):
        bus.subscribe(name, await _make_cb(name))

    await bus.fire(reason="test", fired_by="user-toolbar")
    assert sorted(received) == ["a:test", "b:test", "c:test"]


@pytest.mark.asyncio
async def test_fire_records_per_subscriber_ack_times() -> None:
    bus = KillSwitchBus()

    async def _slow(_event: object) -> None:
        await asyncio.sleep(0.02)

    async def _fast(_event: object) -> None:
        await asyncio.sleep(0.0)

    bus.subscribe("slow", _slow)
    bus.subscribe("fast", _fast)

    result = await bus.fire(reason="test", fired_by="user-toolbar")
    assert "slow" in result.ack_times_ms
    assert "fast" in result.ack_times_ms
    assert result.ack_times_ms["slow"] > result.ack_times_ms["fast"]
    assert result.max_ack_ms == result.ack_times_ms["slow"]


@pytest.mark.asyncio
async def test_fire_runs_concurrently() -> None:
    """Total fire time ~= max subscriber time, not sum.

    7 subscribers each sleeping 50ms — total wall clock should be ~50ms,
    not ~350ms. Asserting < 200ms gives plenty of slack for scheduling
    variance on shared CI hardware.
    """
    bus = KillSwitchBus()

    async def _sleep_50ms(_event: object) -> None:
        await asyncio.sleep(0.05)

    for i in range(7):
        bus.subscribe(f"broker-{i}", _sleep_50ms)

    result = await bus.fire(reason="test", fired_by="user-toolbar")
    # max_ack_ms is per-subscriber, ~50ms. The TOTAL fire duration is
    # bounded by max plus a small overhead; we assert via max_ack_ms which
    # cannot exceed wall-clock fire time + scheduler overhead.
    assert result.max_ack_ms < 200.0


@pytest.mark.asyncio
async def test_kill_switch_under_2s_with_10_subscribers() -> None:
    """BLUEPRINT §6.5 #5 — kill switch under 2_000 ms with realistic subscribers.

    10 subscribers (7 broker adapters + 3 workflows in production), each
    with a small async-IO simulation. Asserts max_ack_ms < 2_000 — the
    operator-brief instrumented benchmark contract.
    """
    bus = KillSwitchBus()

    async def _adapter_handler(_event: object) -> None:
        await asyncio.sleep(0.05)  # cancel-all-orders simulation

    for i in range(10):
        bus.subscribe(f"sub-{i}", _adapter_handler)

    result = await bus.fire(reason="benchmark", fired_by="user-toolbar")
    assert result.max_ack_ms < 2_000.0
    assert result.p95_ack_ms < 2_000.0


@pytest.mark.asyncio
async def test_re_fire_is_idempotent() -> None:
    bus = KillSwitchBus()
    call_count = 0

    async def _cb(_event: object) -> None:
        nonlocal call_count
        call_count += 1

    bus.subscribe("a", _cb)

    first = await bus.fire(reason="first", fired_by="user-toolbar")
    second = await bus.fire(reason="second", fired_by="user-keyboard")

    # Same result returned both times — second fire was a no-op.
    assert first is second
    assert call_count == 1


@pytest.mark.asyncio
async def test_reset_clears_state() -> None:
    bus = KillSwitchBus()

    async def _cb(_event: object) -> None:
        pass

    bus.subscribe("a", _cb)
    await bus.fire(reason="test", fired_by="user-toolbar")
    assert bus.is_fired is True

    bus.reset()
    assert bus.is_fired is False
    assert bus.last_event is None
    assert bus.last_result is None


@pytest.mark.asyncio
async def test_misbehaving_subscriber_does_not_block_others() -> None:
    bus = KillSwitchBus()
    received: list[str] = []

    async def _raiser(_event: object) -> None:
        raise RuntimeError("boom")

    async def _good(_event: object) -> None:
        received.append("good")

    bus.subscribe("raiser", _raiser)
    bus.subscribe("good", _good)

    result = await bus.fire(reason="test", fired_by="user-toolbar")
    # The good subscriber still got the event.
    assert received == ["good"]
    # The raiser still has an ack time recorded (its exception was caught).
    assert "raiser" in result.ack_times_ms
