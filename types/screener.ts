/**
 * Vysted Terminal — screener / scanner contracts (Phase 6).
 *
 * Hand-maintained TypeScript mirror of ``sidecar/models/screener.py``.
 *
 * Filter criteria are a discriminated union by operator — the criteria
 * builder UI maps each operator to a different input shape (numeric ranges,
 * string-eq for sector / industry, set-membership for the watchlist
 * universe).
 */

// ---------------------------------------------------------------------------
// Universe
// ---------------------------------------------------------------------------

/** Curated universe id. Custom universes are pasted by the user as a
 * ticker list and don't get an id. */
export type ScreenerUniverseId = "sp500" | "nifty50" | "crypto-top50" | "custom";

/**
 * A universe definition. ``"sp500"`` and ``"nifty50"`` are curated server-side
 * (refreshed daily); ``"custom"`` is constructed from a pasted ticker list
 * the request carries.
 */
export interface ScreenerUniverse {
  id: ScreenerUniverseId;
  label: string;
  /** Tickers in the universe (always present; for ``"custom"`` it's the
   * user's pasted list). */
  symbols: string[];
  /** Asset class — the screener fans out to the right provider per asset
   * class. */
  asset_class: "equity" | "crypto";
}

// ---------------------------------------------------------------------------
// Criterion (discriminated union by operator)
// ---------------------------------------------------------------------------

/**
 * One filter criterion. The discriminator is ``operator``; the field shape
 * varies by operator:
 *   - ``"gt" | "lt" | "gte" | "lte"`` carry a single numeric threshold.
 *   - ``"eq"`` for sector / industry / currency carries a string.
 *   - ``"between"`` carries a (min, max) numeric range.
 *   - ``"in"`` carries a string array (e.g. for tickers).
 */
export type ScreenerCriterion =
  | { field: ScreenerNumericField; operator: "gt" | "lt" | "gte" | "lte"; value: number }
  | {
      field: ScreenerNumericField;
      operator: "between";
      value: { min: number; max: number };
    }
  | { field: ScreenerStringField; operator: "eq"; value: string }
  | { field: "symbol" | "sector" | "industry"; operator: "in"; value: string[] };

/** The fields a numeric operator may target. Tracks the
 * ``Fundamentals`` shape's numeric columns plus a few price-derived columns. */
export type ScreenerNumericField =
  // Valuation
  | "market_cap"
  | "pe_ratio"
  | "forward_pe"
  | "peg_ratio"
  | "price_to_book"
  | "price_to_sales"
  | "ev_to_ebitda"
  | "book_value"
  | "dividend_yield"
  | "eps"
  | "beta"
  // Profitability (fractions: 0.20 = 20%)
  | "roe"
  | "roa"
  | "gross_margin"
  | "operating_margin"
  | "profit_margin"
  // Financial health
  | "debt_to_equity"
  | "current_ratio"
  | "quick_ratio"
  // Growth (fractions)
  | "revenue_growth"
  | "earnings_growth"
  // Range / ownership
  | "fifty_two_week_high"
  | "fifty_two_week_low"
  | "fifty_two_week_change"
  | "held_percent_insiders"
  | "held_percent_institutions"
  // Price-derived (from the live quote)
  | "price"
  | "change_percent_1d"
  | "volume";

/** The fields an ``"eq"`` operator may target. */
export type ScreenerStringField = "sector" | "industry" | "currency";

// ---------------------------------------------------------------------------
// Request / response
// ---------------------------------------------------------------------------

/** Request shape for ``POST /screener/run``. */
export interface ScreenerRequest {
  /** Universe id; for ``"custom"`` the ``custom_symbols`` field must be set. */
  universe: ScreenerUniverseId;
  /** Custom tickers when ``universe = "custom"``. Otherwise ignored. */
  custom_symbols?: string[];
  /** AND-combined criteria. v0.6.0 doesn't support OR / nested grouping. */
  criteria: ScreenerCriterion[];
  /** Maximum rows to return (default 200, max 1000). */
  limit: number;
}

/** One row in the screener results table. */
export interface ScreenerResultRow {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  // Optional in the TS mirror (the sidecar always sends them, but older blobs /
  // test fixtures may omit them) — the table + CSV treat absent as "—".
  forward_pe?: number | null;
  peg_ratio?: number | null;
  price_to_book?: number | null;
  /** Dividend yield as a fraction (0.012 = 1.2%). */
  dividend_yield?: number | null;
  /** Return on equity as a fraction (0.20 = 20%). */
  roe?: number | null;
  /** Debt-to-equity ratio (1.5 = 150%). */
  debt_to_equity?: number | null;
  price: number | null;
  change_percent_1d: number | null;
  /** Volume (most recent close). */
  volume: number | null;
  /** Per-criterion match scores keyed by criterion index — surfaced in the
   * results table for column hover-explain. */
  matched_criteria: number[];
}

/** Response shape from ``POST /screener/run``. */
export interface ScreenerResult {
  universe: ScreenerUniverseId;
  /** Total candidates evaluated before criteria filtered them. */
  evaluated_count: number;
  /** Symbols dropped (timeout / provider error) before evaluation. */
  skipped_count: number;
  /** Total rows returned (≤ ``limit``). */
  result_count: number;
  rows: ScreenerResultRow[];
  duration_ms: number;
}
