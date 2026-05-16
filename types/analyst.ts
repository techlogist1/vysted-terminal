/**
 * Vysted Terminal — analyst ratings expansion contracts (Phase 6).
 *
 * Hand-maintained TypeScript mirror of ``sidecar/models/analyst_extended.py``.
 *
 * Phase 1 shipped a lightweight ``AnalystRating`` consensus snapshot in
 * ``types/data.ts``. Phase 6 expands the surface in three directions:
 *   1. ratings history — every recorded ratings change with timestamp + firm
 *   2. price-target history — every price-target change with timestamp + firm
 *   3. individual analyst tracks — per-firm forecast accuracy where the
 *      upstream exposes it
 *
 * The Phase 1 consensus type stays in ``data.ts``; the Phase 6 extensions
 * live here and the Analyst Ratings panel imports both.
 */

// ---------------------------------------------------------------------------
// Standardised rating bucket
// ---------------------------------------------------------------------------

/**
 * The five-bucket standardised rating Vysted normalises every upstream
 * rating string into — handles the ``"strong buy" | "buy" | "outperform" |
 * "overweight"`` synonym set the upstream providers use unpredictably.
 */
export type AnalystAction = "strong-buy" | "buy" | "hold" | "sell" | "strong-sell";

// ---------------------------------------------------------------------------
// Ratings history (per-symbol timeline of rating CHANGES)
// ---------------------------------------------------------------------------

/**
 * One row in a symbol's ratings-history table — a rating change with the
 * firm + analyst that issued it.
 */
export interface RatingsHistoryEntry {
  symbol: string;
  /** ISO-8601 date the rating change was published. */
  date: string;
  /** Analyst firm / brokerage that published the change (e.g. ``"Morgan
   * Stanley"``). */
  firm: string;
  /** Specific analyst name, where the upstream exposes it. */
  analyst_name: string | null;
  /** Previous rating bucket — ``null`` when this is the firm's initial coverage. */
  rating_from: AnalystAction | null;
  /** New rating bucket. */
  rating_to: AnalystAction;
  /** The raw rating string the upstream returned (pre-normalisation). */
  raw_rating: string;
  /** Optional editorial commentary the firm published alongside the change. */
  note: string | null;
  provider: string;
}

/** Returned by ``/fundamentals/{symbol}/ratings/history``. */
export interface RatingsHistoryResponse {
  symbol: string;
  history: RatingsHistoryEntry[];
}

// ---------------------------------------------------------------------------
// Price-target history (per-symbol timeline)
// ---------------------------------------------------------------------------

/**
 * One row in a symbol's price-target-history table — a target-price change
 * from a specific firm.
 */
export interface PriceTargetEntry {
  symbol: string;
  date: string;
  firm: string;
  analyst_name: string | null;
  /** Previous price target — ``null`` when first issued. */
  target_from: number | null;
  /** New price target. */
  target_to: number;
  /** Reporting currency (e.g. ``"USD"``). */
  currency: string;
  provider: string;
}

/** Returned by ``/fundamentals/{symbol}/ratings/price-target-history``. */
export interface PriceTargetHistoryResponse {
  symbol: string;
  history: PriceTargetEntry[];
}

// ---------------------------------------------------------------------------
// Individual-analyst forecast & track
// ---------------------------------------------------------------------------

/**
 * One analyst's currently-active forecast for a symbol + their historical
 * accuracy where the upstream provider tracks it. Surfaces in the
 * IndividualAnalystTable panel.
 */
export interface IndividualAnalystForecast {
  symbol: string;
  firm: string;
  analyst_name: string;
  current_rating: AnalystAction;
  current_price_target: number | null;
  currency: string;
  /** Date the analyst issued their current rating. */
  rating_issued_date: string;
  /** Historical accuracy: fraction of past calls that beat the consensus
   * direction-wise over a rolling 12-month window. ``null`` when the
   * upstream does not score the analyst. */
  one_year_accuracy: number | null;
  /** Star rating, 1.0–5.0, normalised across upstream providers (TipRanks /
   * StarMine / similar). ``null`` when not available. */
  star_rating: number | null;
  provider: string;
}

/** Returned by ``/fundamentals/{symbol}/ratings/individual``. */
export interface IndividualAnalystResponse {
  symbol: string;
  analysts: IndividualAnalystForecast[];
}
