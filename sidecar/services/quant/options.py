"""Option pricing — Black-Scholes analytic, Cox-Ross-Rubinstein binomial, Monte Carlo.

Three engines under one dispatcher (:func:`price`).

Black-Scholes (``"black-scholes"``)
   Analytic ``ql.AnalyticEuropeanEngine`` on a flat BSM process. Greeks are
   produced for free by the engine.

Binomial (``"binomial"``)
   ``ql.BinomialVanillaEngine`` with the Cox-Ross-Rubinstein tree.
   Defaults to 200 steps when ``binomial_steps`` is None. Supports both
   European and American exercise. Greeks come from finite-difference
   re-pricing (perturb spot ±1 %, vol ±0.5pt, rate ±0.5pt) via the
   :func:`_greeks_fd` helper.

Monte Carlo (``"monte-carlo"``)
   ``ql.MCEuropeanEngine`` with antithetic variance reduction.
   Defaults to 50000 paths and seed=42. The standard error of the MC
   estimate is captured into ``OptionPricingResult.monte_carlo_std_error``.
   MC Greeks are not computed in v0.6.0 — the Greeks dashboard endpoint
   uses the analytic engine separately, which is the right Tier-3 trade-off.
"""

from __future__ import annotations

import time

import QuantLib as ql

from models.quant import Greeks, OptionPricingRequest, OptionPricingResult

from ._common import build_bsm_process, ql_option_type, to_ql_date

#: Default number of CRR binomial tree steps when caller omits.
DEFAULT_BINOMIAL_STEPS = 200

#: Default number of Monte Carlo sample paths when caller omits.
DEFAULT_MC_PATHS = 50_000

#: Default Monte Carlo random seed for reproducible runs.
DEFAULT_MC_SEED = 42


# ---------------------------------------------------------------------------
# Black-Scholes analytic
# ---------------------------------------------------------------------------


def price_european_bs(req: OptionPricingRequest) -> OptionPricingResult:
    """Price a European option with the analytic Black-Scholes engine.

    Greeks are always populated.
    """
    if req.exercise != "european":
        raise ValueError(
            f"black-scholes engine only supports european exercise, got {req.exercise!r}"
        )
    started = time.perf_counter()

    process = build_bsm_process(
        req.spot,
        req.risk_free_rate,
        req.dividend_yield,
        req.volatility,
        req.valuation_date,
    )

    payoff = ql.PlainVanillaPayoff(ql_option_type(req.payoff), req.strike)
    exercise = ql.EuropeanExercise(to_ql_date(req.expiry_date))
    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))

    price = option.NPV()
    greeks = Greeks(
        delta=option.delta(),
        gamma=option.gamma(),
        vega=option.vega(),
        theta=option.theta(),
        rho=option.rho(),
    )

    return OptionPricingResult(
        price=price,
        greeks=greeks,
        method="black-scholes",
        monte_carlo_std_error=None,
        duration_ms=(time.perf_counter() - started) * 1000.0,
    )


# ---------------------------------------------------------------------------
# Cox-Ross-Rubinstein binomial
# ---------------------------------------------------------------------------


def _price_binomial_npv(req: OptionPricingRequest, steps: int) -> float:
    """Price ``req`` on a fresh CRR binomial tree of ``steps`` nodes.

    Builds a new process per call — the global QL settings (evaluation
    date, market data quote handles) are rebuilt inside
    :func:`build_bsm_process`, so :func:`_greeks_fd` perturbations are
    isolated by construction.
    """
    process = build_bsm_process(
        req.spot,
        req.risk_free_rate,
        req.dividend_yield,
        req.volatility,
        req.valuation_date,
    )
    payoff = ql.PlainVanillaPayoff(ql_option_type(req.payoff), req.strike)
    if req.exercise == "european":
        exercise = ql.EuropeanExercise(to_ql_date(req.expiry_date))
    else:
        exercise = ql.AmericanExercise(to_ql_date(req.valuation_date), to_ql_date(req.expiry_date))
    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(ql.BinomialVanillaEngine(process, "crr", steps))
    return option.NPV()


def _greeks_fd(req: OptionPricingRequest, steps: int) -> Greeks:
    """Finite-difference Greeks for the binomial engine.

    Perturbations are absolute around the input point so the FD is stable
    across reasonable input ranges:

    * Delta — central difference, ``ΔS = 1 % of spot``.
    * Gamma — three-point stencil, ``ΔS = 1 % of spot``.
    * Vega  — central difference, ``Δσ = 0.005`` (0.5 vol points).
              Returned per unit-vol matching the QuantLib convention (so
              the panel divides by 100 to show per-1 % move).
    * Theta — forward difference, ``Δt = 1 day``; sign flipped to match
              QuantLib's convention (option value drops as expiry nears).
    * Rho   — central difference, ``Δr = 0.005`` (0.5 rate points).
    """
    spot_bump = 0.01 * req.spot
    base = req
    up_s = base.model_copy(update={"spot": base.spot + spot_bump})
    dn_s = base.model_copy(update={"spot": base.spot - spot_bump})

    price_base = _price_binomial_npv(base, steps)
    price_up_s = _price_binomial_npv(up_s, steps)
    price_dn_s = _price_binomial_npv(dn_s, steps)

    delta = (price_up_s - price_dn_s) / (2.0 * spot_bump)
    gamma = (price_up_s - 2.0 * price_base + price_dn_s) / (spot_bump * spot_bump)

    vol_bump = 0.005
    up_v = base.model_copy(update={"volatility": base.volatility + vol_bump})
    dn_v = base.model_copy(update={"volatility": base.volatility - vol_bump})
    vega = (_price_binomial_npv(up_v, steps) - _price_binomial_npv(dn_v, steps)) / (2.0 * vol_bump)

    rate_bump = 0.005
    up_r = base.model_copy(update={"risk_free_rate": base.risk_free_rate + rate_bump})
    dn_r = base.model_copy(update={"risk_free_rate": base.risk_free_rate - rate_bump})
    rho = (_price_binomial_npv(up_r, steps) - _price_binomial_npv(dn_r, steps)) / (2.0 * rate_bump)

    # Theta — forward difference in valuation date by 1 calendar day.
    from datetime import timedelta

    fwd = base.model_copy(update={"valuation_date": base.valuation_date + timedelta(days=1)})
    price_fwd = _price_binomial_npv(fwd, steps)
    # QuantLib's theta convention is "rate of change with respect to t",
    # which is negative as expiry approaches. Match that sign so the
    # binomial Greeks line up with the analytic Greeks.
    theta = -(price_fwd - price_base) * 365.0

    return Greeks(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho)


def price_american_binomial(req: OptionPricingRequest) -> OptionPricingResult:
    """Price an option on a Cox-Ross-Rubinstein binomial tree.

    Defaults to 200 steps if the request omits ``binomial_steps``.
    Greeks are computed via finite-difference re-pricing.
    """
    started = time.perf_counter()
    steps = req.binomial_steps if req.binomial_steps is not None else DEFAULT_BINOMIAL_STEPS
    if steps < 3:
        raise ValueError(f"binomial steps must be at least 3, got {steps}")
    price = _price_binomial_npv(req, steps)
    greeks = _greeks_fd(req, steps)
    return OptionPricingResult(
        price=price,
        greeks=greeks,
        method="binomial",
        monte_carlo_std_error=None,
        duration_ms=(time.perf_counter() - started) * 1000.0,
    )


# ---------------------------------------------------------------------------
# Monte Carlo European
# ---------------------------------------------------------------------------


def price_european_mc(req: OptionPricingRequest) -> OptionPricingResult:
    """Price a European option with antithetic-variate Monte Carlo.

    Defaults to 50000 paths, seed=42. The standard error of the MC
    estimate is surfaced as ``OptionPricingResult.monte_carlo_std_error``
    so the panel can show ±1 SE bands alongside the point estimate.
    """
    if req.exercise != "european":
        raise ValueError(
            f"monte-carlo engine only supports european exercise in v0.6.0, got {req.exercise!r}"
        )
    started = time.perf_counter()

    paths = req.monte_carlo_paths if req.monte_carlo_paths is not None else DEFAULT_MC_PATHS
    seed = req.monte_carlo_seed if req.monte_carlo_seed is not None else DEFAULT_MC_SEED
    if paths < 100:
        raise ValueError(f"monte carlo paths must be at least 100, got {paths}")

    process = build_bsm_process(
        req.spot,
        req.risk_free_rate,
        req.dividend_yield,
        req.volatility,
        req.valuation_date,
    )
    payoff = ql.PlainVanillaPayoff(ql_option_type(req.payoff), req.strike)
    exercise = ql.EuropeanExercise(to_ql_date(req.expiry_date))
    option = ql.VanillaOption(payoff, exercise)

    # 1 time step is sufficient for a Black-Scholes Geometric Brownian
    # Motion European pricer — the analytic terminal distribution is
    # known. timeSteps=1 + antithetic variates is the standard
    # variance-reduction recipe.
    engine = ql.MCEuropeanEngine(
        process,
        "PseudoRandom",
        timeSteps=1,
        antitheticVariate=True,
        requiredSamples=paths,
        seed=seed,
    )
    option.setPricingEngine(engine)

    price = option.NPV()
    std_error = option.errorEstimate()

    return OptionPricingResult(
        price=price,
        greeks=None,
        method="monte-carlo",
        monte_carlo_std_error=std_error,
        duration_ms=(time.perf_counter() - started) * 1000.0,
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def price(req: OptionPricingRequest) -> OptionPricingResult:
    """Dispatch an option-pricing request to the engine named by ``req.method``."""
    if req.method == "black-scholes":
        return price_european_bs(req)
    if req.method == "binomial":
        return price_american_binomial(req)
    if req.method == "monte-carlo":
        return price_european_mc(req)
    raise ValueError(f"unknown pricing method {req.method!r}")


__all__ = [
    "DEFAULT_BINOMIAL_STEPS",
    "DEFAULT_MC_PATHS",
    "DEFAULT_MC_SEED",
    "price",
    "price_american_binomial",
    "price_european_bs",
    "price_european_mc",
]
