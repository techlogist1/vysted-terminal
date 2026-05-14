/**
 * Vysted Terminal — sidecar data-layer types.
 *
 * Hand-maintained TypeScript mirror of the Pydantic models in `sidecar/models/`.
 * When a Pydantic model changes, update the matching interface here in the same
 * commit (see CLAUDE.md Gotchas). Datetimes cross the wire as ISO-8601 strings.
 */

// --- market ---------------------------------------------------------------

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

/** Snapshot of valuation ratios and company profile for one symbol. */
export interface Fundamentals {
  symbol: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  peg_ratio: number | null;
  price_to_book: number | null;
  dividend_yield: number | null;
  eps: number | null;
  beta: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
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
