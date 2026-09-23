"""QuantLib's evaluation date is process-global: overlapping pricings must not
see each other's date, and the async quant lanes must wait for the QuantLib
lock off the event loop (R15-CODE-PLATFORM-005)."""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from collections.abc import Callable
from datetime import date
from typing import Any

import pytest

from models.quant import (
    BondPricingRequest,
    OptionPricingRequest,
    YieldCurveInstrument,
    YieldCurveRequest,
)
from services.quant import _common, bonds, options, yield_curve
from services.workflow_nodes import quant_nodes

_RACE_SECONDS = 0.5


def _race(fn_a: Callable[[], Any], fn_b: Callable[[], Any]) -> tuple[list[Any], list[Any]]:
    """Call each callable repeatedly on two threads for the same wall window.

    A raised exception is recorded as that call's result (a swapped date can
    make QuantLib raise), so it compares unequal to the serial value.
    """
    out_a: list[Any] = []
    out_b: list[Any] = []
    barrier = threading.Barrier(2)
    deadline = time.monotonic() + _RACE_SECONDS

    def loop(fn: Callable[[], Any], out: list[Any]) -> None:
        barrier.wait()
        while time.monotonic() < deadline:
            try:
                out.append(fn())
            except Exception as exc:  # noqa: BLE001 — the result under test
                out.append(exc)

    threads = [
        threading.Thread(target=loop, args=(fn_a, out_a)),
        threading.Thread(target=loop, args=(fn_b, out_b)),
    ]
    # Switch threads often so the interleaving lands between set-date and NPV.
    interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(interval)
    return out_a, out_b


def _option(valuation: date, expiry: date) -> OptionPricingRequest:
    return OptionPricingRequest(
        exercise="european",
        payoff="call",
        spot=100.0,
        strike=95.0,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        volatility=0.2,
        valuation_date=valuation,
        expiry_date=expiry,
        method="black-scholes",
    )


def test_overlapping_option_pricings_keep_their_own_valuation_date() -> None:
    early = _option(date(2026, 5, 16), date(2027, 5, 16))
    # Thread B's valuation date is after A's expiry: under a swapped date A
    # prices as already expired (0.0).
    late = _option(date(2030, 1, 2), date(2031, 1, 2))
    serial_early = options.price(early).price
    serial_late = options.price(late).price

    got_early, got_late = _race(
        lambda: options.price(early).price, lambda: options.price(late).price
    )

    assert all(p == pytest.approx(serial_early) for p in got_early)
    assert all(p == pytest.approx(serial_late) for p in got_late)


def test_overlapping_bond_and_curve_bootstrap_keep_their_own_dates() -> None:
    bond = BondPricingRequest(
        face_value=1000.0,
        coupon_rate=0.05,
        coupons_per_year=2,
        issue_date=date(2026, 5, 16),
        maturity_date=date(2036, 5, 16),
        settlement_date=date(2029, 3, 1),
        yield_to_maturity=0.04,
    )
    curve = YieldCurveRequest(
        valuation_date=date(2031, 7, 1),
        instruments=[
            YieldCurveInstrument(type="deposit", tenor=3, tenor_unit="months", rate=0.043),
            YieldCurveInstrument(type="swap", tenor=2, tenor_unit="years", rate=0.045),
            YieldCurveInstrument(type="swap", tenor=10, tenor_unit="years", rate=0.05),
        ],
        sample_count=10,
    )
    serial_bond = bonds.price_bond(bond).model_dump(exclude={"duration_ms"})
    serial_curve = yield_curve.bootstrap_curve(curve).model_dump(exclude={"duration_ms"})

    got_bond, got_curve = _race(
        lambda: bonds.price_bond(bond).model_dump(exclude={"duration_ms"}),
        lambda: yield_curve.bootstrap_curve(curve).model_dump(exclude={"duration_ms"}),
    )

    assert all(b == serial_bond for b in got_bond)
    assert all(c == serial_curve for c in got_curve)


@pytest.mark.asyncio
async def test_quant_node_waits_for_the_quantlib_lock_off_the_event_loop() -> None:
    # Another pricing (a threadpool /quant route) holds the QuantLib lock.
    held = threading.Event()
    release = threading.Event()

    def other_pricing() -> None:
        with _common._QL_LOCK:
            held.set()
            release.wait(timeout=2)  # bounded, so a blocked loop fails instead of hanging

    holder = threading.Thread(target=other_pricing)
    holder.start()
    held.wait()
    config = _option(date(2026, 5, 16), date(2027, 5, 16)).model_dump(mode="json")
    pricing = asyncio.create_task(quant_nodes.price_option({}, config))

    loop = asyncio.get_running_loop()
    started = loop.time()
    for _ in range(20):
        await asyncio.sleep(0.001)
    # The loop kept turning while the node waited for the lock in a worker thread.
    assert loop.time() - started < 1.0
    assert not pricing.done()

    release.set()
    result = await asyncio.wait_for(pricing, timeout=5)
    holder.join()
    assert result["result"]["price"] > 0
