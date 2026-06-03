/**
 * Vysted Terminal — sidecar data-layer types.
 *
 * Hand-maintained TypeScript mirror of the Pydantic models in `sidecar/models/`.
 * When a Pydantic model changes, update the matching interface here in the same
 * commit (see CLAUDE.md Gotchas). Datetimes cross the wire as ISO-8601 strings.
 */

// --- market ---------------------------------------------------------------

/** Calendar-aware staleness label for a served market value (FR-041 / SC-019). */
export type Freshness = "live" | "eod" | "stale";

/** A point-in-time price quote for one instrument. */
export interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number | null;
  currency: string;
  market_state: string | null;
  timestamp: string;
  provider: string;
  /** Set by the quotes router so the UI never shows a stale value as live. */
  freshness?: Freshness | null;
}

/** A single open/high/low/close/volume bar. */
export interface OHLCVBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** An ordered series of OHLCV bars for one symbol and timeframe. */
export interface OHLCVSeries {
  symbol: string;
  timeframe: string;
  bars: OHLCVBar[];
  provider: string;
  /** Staleness of the LAST bar, set by the history router (FR-041 / SC-019). */
  freshness?: Freshness | null;
}

/** One dated observation within a macro series. */
export interface MacroObservation {
  date: string;
  value: number | null;
}

/** An economic/macro time series (FRED-style). */
export interface MacroSeries {
  series_id: string;
  title: string;
  units: string | null;
  observations: MacroObservation[];
  provider: string;
}

// --- fundamentals ---------------------------------------------------------

/**
 * Snapshot of valuation, profitability, health, and profile for one symbol.
 * Mirrors `sidecar/models/fundamentals.py` — keep in sync. Fraction fields
 * (`*_margin`, `roe`, `roa`, `*_growth`, `held_percent_*`, `fifty_two_week_change`,
 * `dividend_yield`) are 0.21 = 21%; `debt_to_equity` is a ratio (1.5 = 150%);
 * currency sizes (`revenue_ttm`/`net_income_ttm`/`free_cash_flow`/
 * `dividend_per_share`) are in `currency`.
 */
export interface Fundamentals {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  currency: string | null;
  // Valuation
  market_cap: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  peg_ratio: number | null;
  price_to_book: number | null;
  price_to_sales: number | null;
  ev_to_ebitda: number | null;
  book_value: number | null;
  dividend_yield: number | null;
  dividend_per_share: number | null;
  eps: number | null;
  beta: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  fifty_two_week_change: number | null;
  // Profitability (fractions)
  roe: number | null;
  roa: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  profit_margin: number | null;
  // Financial health
  debt_to_equity: number | null;
  current_ratio: number | null;
  quick_ratio: number | null;
  // Size & growth
  revenue_ttm: number | null;
  net_income_ttm: number | null;
  free_cash_flow: number | null;
  shares_outstanding: number | null;
  revenue_growth: number | null;
  earnings_growth: number | null;
  // Ownership (fractions)
  held_percent_insiders: number | null;
  held_percent_institutions: number | null;
  provider: string;
}

/** One labelled row of a financial statement, keyed by period label. */
export interface StatementLine {
  label: string;
  values: Record<string, number | null>;
}

/** Shared shape for the three financial statements. */
export interface FinancialStatement {
  symbol: string;
  periods: string[];
  lines: StatementLine[];
  provider: string;
}

/** Income statement excerpt. */
export type IncomeStatement = FinancialStatement;
/** Balance sheet excerpt. */
export type BalanceSheet = FinancialStatement;
/** Cash-flow statement excerpt. */
export type CashFlowStatement = FinancialStatement;

/** Aggregated analyst ratings and price targets for one symbol. */
export interface AnalystRating {
  symbol: string;
  consensus: string | null;
  target_mean: number | null;
  target_high: number | null;
  target_low: number | null;
  strong_buy: number;
  buy: number;
  hold: number;
  sell: number;
  strong_sell: number;
  provider: string;
}

// --- news -----------------------------------------------------------------

/**
 * A single news article. The `sentiment` / `sentiment_label` fields are
 * populated by the news service (Teammate C); the Phase 1.A provider layer
 * leaves them `null`.
 */
export interface NewsItem {
  id: string;
  title: string;
  summary: string | null;
  url: string;
  source: string;
  published_at: string;
  symbols: string[];
  sentiment: number | null;
  sentiment_label: string | null;
  provider: string;
}

// --- portfolio ------------------------------------------------------------

/** A single held position, persisted in the local SQLite database. */
export interface Position {
  id: number | null;
  symbol: string;
  quantity: number;
  cost_basis: number;
  asset_class: string;
  opened_at: string | null;
  note: string | null;
}

/** Payload for creating or updating a position (no server-assigned id). */
export interface PositionInput {
  symbol: string;
  quantity: number;
  cost_basis: number;
  asset_class: string;
  opened_at: string | null;
  note: string | null;
}

// --- indicators -----------------------------------------------------------
// Mirror of sidecar/models/indicators.py — the chart panel's overlay contract.

/** Which chart pane an indicator renders on. */
export type IndicatorPanel = "price" | "separate";

/**
 * A single `(time, value)` sample on an indicator line. `time` is an ISO-8601
 * timestamp mirrored from the source OHLCV bar; a `null` value marks a gap
 * where the indicator is undefined (e.g. a moving average's warm-up window).
 */
export interface IndicatorPoint {
  time: string;
  value: number | null;
}

/** One named line within an indicator (an indicator may plot several). */
export interface IndicatorLine {
  label: string;
  points: IndicatorPoint[];
}

/** The full result of computing one indicator over an OHLCV series. */
export interface IndicatorSeries {
  name: string;
  panel: IndicatorPanel;
  lines: IndicatorLine[];
}

/**
 * One price-bucket of a Volume Profile histogram — `price` is the bucket
 * centre and `volume` is the total traded volume that closed inside it.
 */
export interface VolumeProfileBucket {
  price: number;
  volume: number;
}

/**
 * A horizontal-histogram Volume Profile. Lives on its own contract because
 * its axes are price-keyed rather than time-keyed; the chart panel renders
 * it on the price pane via a custom series primitive.
 */
export interface VolumeProfile {
  buckets: VolumeProfileBucket[];
}

/** The `/indicators/{symbol}` payload — every requested indicator. */
export interface IndicatorResponse {
  symbol: string;
  timeframe: string;
  provider: string;
  indicators: IndicatorSeries[];
  volume_profile: VolumeProfile | null;
}
