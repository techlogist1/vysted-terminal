/**
 * Vysted Terminal — earnings calendar + estimates + surprises (Phase 6).
 *
 * Hand-maintained TypeScript mirror of ``sidecar/models/earnings.py``.
 */

// ---------------------------------------------------------------------------
// Event identity
// ---------------------------------------------------------------------------

/** When during the trading day a company reports — used by the calendar UI
 * to lay out the day strip (before-open / during / after-close / unknown). */
export type EarningsTimeOfDay = "before-open" | "during-market" | "after-close" | "unknown";

/** Fiscal-period label — e.g. ``"Q1 2026"``, ``"FY 2025"``. */
export interface FiscalPeriod {
  /** ``"Q1" | "Q2" | "Q3" | "Q4" | "FY"``. */
  quarter: "Q1" | "Q2" | "Q3" | "Q4" | "FY";
  /** Fiscal year (calendar-year integer). */
  year: number;
}

/**
 * One scheduled earnings event in the upcoming-calendar view. Past events
 * are returned by the surprises endpoint, not this one.
 */
export interface EarningsEvent {
  symbol: string;
  company_name: string | null;
  /** ISO-8601 date the company is expected to report. */
  scheduled_date: string;
  time_of_day: EarningsTimeOfDay;
  fiscal_period: FiscalPeriod;
  /** Consensus EPS estimate (analyst-mean), in the reporting currency. */
  eps_estimate_mean: number | null;
  /** Estimate dispersion (standard deviation of analyst forecasts). */
  eps_estimate_stddev: number | null;
  /** Number of contributing analysts. */
  estimate_analyst_count: number;
  /** Currency for the estimates (e.g. ``"USD"``). */
  currency: string;
  provider: string;
}

// ---------------------------------------------------------------------------
// Surprise (post-report)
// ---------------------------------------------------------------------------

/**
 * The actual reported result paired with the consensus estimate, computed
 * once the earnings report lands. Surfaces in the surprises chart + history
 * grid.
 */
export interface EarningsSurprise {
  symbol: string;
  /** ISO-8601 date the company reported (may differ from the originally
   * scheduled date if rescheduled). */
  reported_date: string;
  fiscal_period: FiscalPeriod;
  /** Actual reported EPS. */
  eps_actual: number;
  /** Pre-report consensus mean. */
  eps_estimate_mean: number;
  /** ``eps_actual - eps_estimate_mean``. */
  eps_surprise: number;
  /** ``eps_surprise / |eps_estimate_mean|`` (decimal — UI multiplies by 100). */
  eps_surprise_pct: number | null;
  /** Total revenue actual + estimate, in the reporting currency. */
  revenue_actual: number | null;
  revenue_estimate_mean: number | null;
  revenue_surprise_pct: number | null;
  currency: string;
  provider: string;
}

// ---------------------------------------------------------------------------
// Estimate detail (pre-report)
// ---------------------------------------------------------------------------

/**
 * Detailed estimate breakdown for one upcoming earnings event — surfaces in
 * the EpsEstimateGrid alongside the calendar.
 */
export interface EarningsEstimateDetail {
  symbol: string;
  fiscal_period: FiscalPeriod;
  eps_estimate_mean: number;
  eps_estimate_median: number | null;
  eps_estimate_high: number;
  eps_estimate_low: number;
  eps_estimate_stddev: number | null;
  estimate_analyst_count: number;
  /** Same fields for revenue. */
  revenue_estimate_mean: number | null;
  revenue_estimate_median: number | null;
  revenue_estimate_high: number | null;
  revenue_estimate_low: number | null;
  revenue_analyst_count: number;
  currency: string;
  provider: string;
  /** ISO-8601 timestamp of the most recent estimate refresh from the
   * upstream provider. */
  as_of: string;
}

// ---------------------------------------------------------------------------
// Response envelopes
// ---------------------------------------------------------------------------

/** Returned by ``/earnings/upcoming``. */
export interface EarningsUpcomingResponse {
  /** Start of the requested window (inclusive). */
  start_date: string;
  /** End of the requested window (inclusive). */
  end_date: string;
  events: EarningsEvent[];
}

/** Returned by ``/earnings/{symbol}/surprises``. */
export interface EarningsSurprisesResponse {
  symbol: string;
  surprises: EarningsSurprise[];
}

/** Returned by ``/earnings/{symbol}/history``. */
export interface EarningsHistoryEntry {
  fiscal_period: FiscalPeriod;
  reported_date: string;
  eps_actual: number;
  eps_estimate_mean: number | null;
  revenue_actual: number | null;
  revenue_estimate_mean: number | null;
  currency: string;
}

export interface EarningsHistoryResponse {
  symbol: string;
  history: EarningsHistoryEntry[];
}
