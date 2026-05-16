"""Path-dependent Monte Carlo pricing — Asian arithmetic + barrier knock-out.

v0.6.0 ships two payoffs beyond the European MC engine that lives in
:mod:`.options`:

* Asian arithmetic-average price option — via
  :class:`ql.MCDiscreteArithmeticAPEngine` over a daily-fixing grid.
* Barrier knock-out (up-and-out / down-and-out, call / put) — via
  :class:`ql.MCBarrierEngine`.

Both functions use plain-primitive inputs (no Pydantic model) — these
are utility surfaces the workflow nodes + agent tools can reach into
when a path-dependent payoff is requested. The HTTP router stays
focused on the three main option engines from :mod:`.options` plus
Greeks / bonds / yield curves; if a future phase wires path-dependent
options into the wire, a dedicated `OptionPricingRequest` discriminant
union extension is the right move.
"""

from __future__ import annotations

import time
from datetime import date, timedelta

import QuantLib as ql

from models.quant import OptionPayoff

from ._common import build_bsm_process, ql_option_type, to_ql_date

#: Default Monte Carlo paths for path-dependent engines (variance is
#: higher than the analytic-collapse European path so we raise the floor).
DEFAULT_PATH_DEPENDENT_PATHS = 50_000

#: Default RNG seed.
DEFAULT_SEED = 42


def price_asian_mc(
    spot: float,
    strike: float,
    r: float,
    q: float,
    vol: float,
    valuation_date: date,
    expiry_date: date,
    paths: int = DEFAULT_PATH_DEPENDENT_PATHS,
    seed: int = DEFAULT_SEED,
    payoff_type: OptionPayoff = "call",
    fixing_days: int | None = None,
) -> dict[str, float]:
    """Price an arithmetic-average Asian option via Monte Carlo.

    Fixings are sampled daily by default — the engine takes a list of
    fixing dates; we synthesise a daily schedule from ``valuation_date``
    through ``expiry_date`` (inclusive). Pass ``fixing_days`` to override
    with a coarser grid (e.g. ``fixing_days=21`` for monthly fixings).

    Returns ``{"price": ..., "std_error": ..., "duration_ms": ...}``.
    """
    started = time.perf_counter()

    if expiry_date <= valuation_date:
        raise ValueError("expiry_date must be after valuation_date")
    if paths < 100:
        raise ValueError(f"paths must be at least 100, got {paths}")

    process = build_bsm_process(spot, r, q, vol, valuation_date)

    # Build a daily fixing schedule (or coarser if fixing_days specified).
    step = fixing_days if fixing_days is not None and fixing_days > 0 else 1
    fixings: list[ql.Date] = []
    cursor = valuation_date + timedelta(days=step)
    while cursor <= expiry_date:
        fixings.append(to_ql_date(cursor))
        cursor += timedelta(days=step)
    if not fixings:
        # Degenerate input — at minimum sample the expiry.
        fixings = [to_ql_date(expiry_date)]

    payoff = ql.PlainVanillaPayoff(ql_option_type(payoff_type), strike)
    exercise = ql.EuropeanExercise(to_ql_date(expiry_date))

    # DiscreteAveragingAsianOption: averaging type "Arithmetic", initial
    # past-fixings 0, running-accumulator 0.0, fixing dates from above.
    option = ql.DiscreteAveragingAsianOption(
        ql.Average.Arithmetic,
        0.0,  # running accumulator (no past fixings)
        0,  # past fixings count
        fixings,
        payoff,
        exercise,
    )
    engine = ql.MCDiscreteArithmeticAPEngine(
        process,
        "PseudoRandom",
        brownianBridge=False,
        antitheticVariate=True,
        controlVariate=False,
        requiredSamples=paths,
        seed=seed,
    )
    option.setPricingEngine(engine)

    price = option.NPV()
    std_error = option.errorEstimate()

    return {
        "price": price,
        "std_error": std_error,
        "duration_ms": (time.perf_counter() - started) * 1000.0,
    }


def price_barrier_mc(
    spot: float,
    strike: float,
    barrier: float,
    barrier_type: str,
    rebate: float,
    r: float,
    q: float,
    vol: float,
    valuation_date: date,
    expiry_date: date,
    paths: int = DEFAULT_PATH_DEPENDENT_PATHS,
    seed: int = DEFAULT_SEED,
    payoff_type: OptionPayoff = "call",
    time_steps: int = 252,
) -> dict[str, float]:
    """Price a barrier knock-out / knock-in option via Monte Carlo.

    ``barrier_type`` is one of ``"up-and-out"``, ``"down-and-out"``,
    ``"up-and-in"``, ``"down-and-in"``. ``rebate`` is the cash paid if
    the option knocks out — pass ``0.0`` for a vanilla knock-out.

    Returns ``{"price": ..., "std_error": ..., "duration_ms": ...}``.
    """
    started = time.perf_counter()

    barrier_map = {
        "up-and-out": ql.Barrier.UpOut,
        "down-and-out": ql.Barrier.DownOut,
        "up-and-in": ql.Barrier.UpIn,
        "down-and-in": ql.Barrier.DownIn,
    }
    if barrier_type not in barrier_map:
        raise ValueError(
            f"unknown barrier_type {barrier_type!r}; expected one of {sorted(barrier_map)}"
        )
    if paths < 100:
        raise ValueError(f"paths must be at least 100, got {paths}")

    process = build_bsm_process(spot, r, q, vol, valuation_date)
    payoff = ql.PlainVanillaPayoff(ql_option_type(payoff_type), strike)
    exercise = ql.EuropeanExercise(to_ql_date(expiry_date))

    option = ql.BarrierOption(barrier_map[barrier_type], barrier, rebate, payoff, exercise)
    engine = ql.MCBarrierEngine(
        process,
        "PseudoRandom",
        timeSteps=time_steps,
        antitheticVariate=True,
        requiredSamples=paths,
        seed=seed,
    )
    option.setPricingEngine(engine)

    price = option.NPV()
    std_error = option.errorEstimate()

    return {
        "price": price,
        "std_error": std_error,
        "duration_ms": (time.perf_counter() - started) * 1000.0,
    }


__all__ = [
    "DEFAULT_PATH_DEPENDENT_PATHS",
    "DEFAULT_SEED",
    "price_asian_mc",
    "price_barrier_mc",
]
