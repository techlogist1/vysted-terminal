/**
 * Vysted Terminal — QuantLib-backed pricing contracts (Phase 6).
 *
 * Hand-maintained TypeScript mirror of ``sidecar/models/quant.py``.
 *
 * All pricing is in-process via the QuantLib==1.42.1 Python wrapper bundled
 * into the main sidecar (Tier-3 architecture choice — see
 * ``docs/PHASE_6_HANDOFF.md`` and CHANGELOG v0.6.0). The wire shapes here
 * are deliberately framework-neutral — no QuantLib types leak into the
 * frontend.
 */

// ---------------------------------------------------------------------------
// Options
// ---------------------------------------------------------------------------

/** European or American exercise. v0.6.0 ships both. */
export type OptionExercise = "european" | "american";

/** Call or put. */
export type OptionPayoff = "call" | "put";

/**
 * Which numerical engine to use. ``black-scholes`` is closed-form European;
 * ``binomial`` is Cox-Ross-Rubinstein American; ``monte-carlo`` covers
 * path-dependent payoffs the Asian / Barrier engines also support.
 */
export type OptionPricingMethod = "black-scholes" | "binomial" | "monte-carlo";

/**
 * Inputs for an option-pricing call. Day-count + calendar are fixed
 * server-side (``Actual365Fixed`` + ``NullCalendar``) — the wire stays
 * minimal; advanced users get a custom-config endpoint later if needed.
 */
export interface OptionPricingRequest {
  exercise: OptionExercise;
  payoff: OptionPayoff;
  /** Spot price of the underlying at valuation time. */
  spot: number;
  /** Strike price. */
  strike: number;
  /** Risk-free rate, continuously compounded annualised (e.g. 0.05 for 5 %). */
  risk_free_rate: number;
  /** Continuous dividend yield (0.0 for non-dividend-paying). */
  dividend_yield: number;
  /** Annualised volatility (e.g. 0.30 for 30 %). */
  volatility: number;
  /** Valuation date (ISO-8601). */
  valuation_date: string;
  /** Expiry date (ISO-8601). Must be > valuation_date. */
  expiry_date: string;
  method: OptionPricingMethod;
  /** Binomial: tree steps (default 200). MC: ignored. */
  binomial_steps?: number;
  /** MC: number of sample paths (default 50000). Binomial/BS: ignored. */
  monte_carlo_paths?: number;
  /** MC: random seed for reproducible runs. */
  monte_carlo_seed?: number;
}

/**
 * The Greeks — first / second-order sensitivities. All values are per-unit
 * (delta in shares-per-option, gamma in per-spot, vega in per-vol-point /100,
 * theta in per-calendar-day, rho in per-rate-point /100). The Vysted UI
 * relabels into the standard display conventions before showing.
 */
export interface Greeks {
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
  rho: number;
}

/**
 * Output of an option-pricing call. Greeks are populated when the chosen
 * method supports them (Black-Scholes always; binomial via finite-difference;
 * Monte Carlo via pathwise derivative — ``null`` when not computed).
 */
export interface OptionPricingResult {
  price: number;
  greeks: Greeks | null;
  method: OptionPricingMethod;
  /** Standard error of the MC estimate (Monte Carlo only). */
  monte_carlo_std_error: number | null;
  /** Computation time on the sidecar (ms). */
  duration_ms: number;
}

// ---------------------------------------------------------------------------
// Bonds
// ---------------------------------------------------------------------------

/**
 * Inputs for a fixed-rate bond pricing call. Supports annual / semi-annual
 * / quarterly coupons. Day-count is ``Thirty360`` per the US convention;
 * compounding is ``Compounded`` and frequency follows the coupon frequency.
 */
export interface BondPricingRequest {
  /** Bond face value (default 1000.0). */
  face_value: number;
  /** Annual coupon rate (e.g. 0.05 for 5 %). */
  coupon_rate: number;
  /** Coupons per year — 1 (annual), 2 (semi-annual), 4 (quarterly). */
  coupons_per_year: 1 | 2 | 4;
  /** Issue date (ISO-8601). */
  issue_date: string;
  /** Maturity date (ISO-8601). */
  maturity_date: string;
  /** Settlement date (ISO-8601). Used as the valuation date. */
  settlement_date: string;
  /** Yield-to-maturity at which to price (annualised, decimal). */
  yield_to_maturity: number;
}

/** Output of a bond-pricing call. */
export interface BondPricingResult {
  /** Clean price (per 100 face). */
  clean_price: number;
  /** Dirty price (clean + accrued). */
  dirty_price: number;
  accrued_interest: number;
  /** Macaulay duration. */
  duration: number;
  /** Modified duration. */
  modified_duration: number;
  convexity: number;
  duration_ms: number;
}

// ---------------------------------------------------------------------------
// Yield curve
// ---------------------------------------------------------------------------

/**
 * One instrument used to bootstrap a yield curve. v0.6.0 supports ``deposit``
 * (money-market rate) + ``swap`` (interest-rate swap). The curve panel
 * lets the user paste a tenor-rate grid and bootstrap directly.
 */
export interface YieldCurveInstrument {
  /** Instrument type. */
  type: "deposit" | "swap";
  /** Tenor in months for deposits (e.g. 1, 3, 6) or years for swaps
   * (e.g. 2, 5, 10, 30) — the wire just carries the numeric tenor with a
   * ``unit`` field. */
  tenor: number;
  tenor_unit: "months" | "years";
  /** Rate (annualised, decimal). */
  rate: number;
}

/**
 * Bootstrap a yield curve from the given instruments + valuation date. The
 * curve is sampled at evenly-spaced node dates for the response — the panel
 * renders this as a line chart.
 */
export interface YieldCurveRequest {
  valuation_date: string;
  instruments: YieldCurveInstrument[];
  /** How many sample points to return (the bootstrapped curve is then
   * interpolated to those dates). */
  sample_count: number;
}

/** One sampled point on a bootstrapped curve. */
export interface YieldCurvePoint {
  /** ISO-8601 sample date. */
  date: string;
  /** Tenor in years (decimal). */
  tenor_years: number;
  /** Zero-rate at that tenor (continuously compounded, decimal). */
  zero_rate: number;
  /** Discount factor at that tenor. */
  discount_factor: number;
}

export interface YieldCurveResult {
  valuation_date: string;
  curve: YieldCurvePoint[];
  duration_ms: number;
}

// ---------------------------------------------------------------------------
// Greeks-only request (for the Greeks dashboard)
// ---------------------------------------------------------------------------

/** Subset of ``OptionPricingRequest`` for the standalone Greeks endpoint —
 * always uses Black-Scholes analytic engine. */
export interface GreeksRequest {
  payoff: OptionPayoff;
  spot: number;
  strike: number;
  risk_free_rate: number;
  dividend_yield: number;
  volatility: number;
  valuation_date: string;
  expiry_date: string;
}

export interface GreeksResult {
  greeks: Greeks;
  /** Black-Scholes price returned alongside the Greeks for free. */
  price: number;
  duration_ms: number;
}
