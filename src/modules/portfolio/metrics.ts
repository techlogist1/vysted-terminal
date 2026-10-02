/**
 * Portfolio metrics — computed client-side by joining stored positions with
 * live quotes. The sidecar persists only the manually entered facts; P&L,
 * weight, and basic risk metrics are derived here so no extra sidecar model is
 * needed (per the Phase 1.B brief).
 */

import type { Holding } from "@/store/portfolios";

import type { Quote } from "../../../types/data";

/** A holding joined with its live quote and derived per-position metrics. */
export interface PositionRow {
  position: Holding;
  quote: Quote | null;
  /** Cost basis × quantity. */
  costValue: number;
  /** Live price × quantity, or `null` when the quote did not resolve. */
  marketValue: number | null;
  /** Market value − cost value, or `null` without a quote. */
  pnl: number | null;
  /** P&L as a percentage of cost value, or `null` without a quote. */
  pnlPercent: number | null;
  /**
   * Share of total portfolio market value (0–1), or `null` without a quote
   * OR when the resolved positions span more than one quote currency
   * (R15-DATA-042 / R15-CODE-PLATFORM-053 — a weight computed against a
   * cross-currency sum is a fabricated ratio, not just a display concern).
   */
  weight: number | null;
}

/**
 * Per-currency roll-up (R11 / D57). A portfolio can hold instruments quoted in
 * different currencies; summing their raw values is a fabricated number
 * (₹64,650 + $1,200 is not 65,850 of anything). Each resolved position lands
 * in the bucket of its QUOTE's currency; the UI renders one subtotal per
 * bucket and never a cross-currency aggregate.
 */
export interface CurrencySubtotal {
  /** Normalized quote currency code ("" when the quote carried none — such a
   *  bucket formats with the region fallback, exactly as before D57). */
  currency: string;
  /** Sum of resolved market values quoted in this currency. */
  marketValue: number;
  /** Unrealised P&L of the resolved positions in this currency. */
  pnl: number;
  /** Cost of the RESOLVED positions in this currency (denominator-matched). */
  resolvedCost: number;
  /** P&L as a percentage of {@link resolvedCost} (0 when that cost is 0). */
  pnlPercent: number;
}

/** Portfolio-level roll-up across every position. */
export interface PortfolioSummary {
  rows: PositionRow[];
  /** Sum of cost values across ALL positions (resolved or not). */
  totalCost: number;
  /** Sum of cost values across only positions with a resolved quote. */
  resolvedCost: number;
  /**
   * Sum of resolved market values. HONEST ONLY when {@link mixedCurrencies}
   * is false — a cross-currency sum is a fabricated number (D57); when mixed,
   * render {@link byCurrency} instead and never publish this as a total.
   */
  totalMarketValue: number;
  /** Total unrealised P&L across resolved positions — same D57 caveat as
   *  {@link totalMarketValue} when currencies are mixed. */
  totalPnl: number;
  /**
   * Total P&L as a percentage of the cost of the RESOLVED positions only.
   * Denominator-matched to {@link totalPnl} — counting unresolved positions'
   * cost into the denominator (while their P&L is necessarily excluded from the
   * numerator) produced a misleading percentage (Phase 9.5 F-GUI-1).
   */
  totalPnlPercent: number;
  /**
   * Largest single-position weight (0–1) — a basic concentration metric.
   * `null` when {@link mixedCurrencies} — it would be computed from
   * cross-currency weights and carry no marker that it is meaningless
   * (R15-CODE-PLATFORM-053).
   */
  concentration: number | null;
  /** Count of positions whose live quote failed to resolve. */
  unresolvedCount: number;
  /** Per-currency subtotals across the RESOLVED positions, in first-seen
   *  order (R11 / D57). Empty when nothing resolved. */
  byCurrency: CurrencySubtotal[];
  /** True when the resolved positions span more than one quote currency —
   *  the aggregate totals above are then fabricated; use {@link byCurrency}. */
  mixedCurrencies: boolean;
}

/** Normalize a quote's currency for bucketing ("usd " → "USD"; absent → ""). */
function currencyKey(quote: Quote | null): string {
  return (quote?.currency ?? "").trim().toUpperCase();
}

/** Join holdings to quotes and compute per-holding + portfolio-level metrics.
 *  Rows carry the real {@link Holding.id} — no synthetic index-based id and
 *  no re-join by array position required of the caller. */
export function buildPortfolioSummary(
  holdings: Holding[],
  quotes: Map<string, Quote>,
): PortfolioSummary {
  const partials = holdings.map((position) => {
    const quote = quotes.get(position.symbol.toUpperCase()) ?? null;
    const costValue = position.costBasis * position.quantity;
    const marketValue = quote !== null ? quote.price * position.quantity : null;
    const pnl = marketValue !== null ? marketValue - costValue : null;
    // P&L% is undefined for a zero cost basis (vested shares / RSUs are a valid
    // cost_basis=0 case) — return null so the UI shows "—" rather than a
    // misleading "+0.00%" on a real gain (hunt-state-logic).
    const pnlPercent = pnl !== null && costValue !== 0 ? (pnl / costValue) * 100 : null;
    return { position, quote, costValue, marketValue, pnl, pnlPercent };
  });

  const totalCost = partials.reduce((sum, row) => sum + row.costValue, 0);
  // Resolved cost = cost of the positions whose quote resolved — the only cost
  // that can legitimately back the resolved P&L numerator.
  const resolvedCost = partials.reduce(
    (sum, row) => sum + (row.marketValue !== null ? row.costValue : 0),
    0,
  );
  const totalMarketValue = partials.reduce((sum, row) => sum + (row.marketValue ?? 0), 0);
  const totalPnl = partials.reduce((sum, row) => sum + (row.pnl ?? 0), 0);
  const totalPnlPercent = resolvedCost !== 0 ? (totalPnl / resolvedCost) * 100 : 0;

  // Per-currency buckets (D57) — resolved positions only, keyed by the QUOTE's
  // currency (positions are entered in the listing currency; the quote is the
  // instrument-truth for what unit the numbers are in).
  const buckets = new Map<string, CurrencySubtotal>();
  for (const row of partials) {
    if (row.marketValue === null) {
      continue;
    }
    const key = currencyKey(row.quote);
    const bucket = buckets.get(key) ?? {
      currency: key,
      marketValue: 0,
      pnl: 0,
      resolvedCost: 0,
      pnlPercent: 0,
    };
    bucket.marketValue += row.marketValue;
    bucket.pnl += row.pnl ?? 0;
    bucket.resolvedCost += row.costValue;
    buckets.set(key, bucket);
  }
  const byCurrency = [...buckets.values()].map((b) => ({
    ...b,
    pnlPercent: b.resolvedCost !== 0 ? (b.pnl / b.resolvedCost) * 100 : 0,
  }));
  const mixedCurrencies = byCurrency.length > 1;

  // R15-DATA-042 / R15-CODE-PLATFORM-053: weight and concentration are a
  // share of the SUMMED market value, which is fabricated (D57) once the
  // resolved positions span more than one currency — null them in the
  // CONTRACT, not just in the panel that happens to read it.
  const rows: PositionRow[] = partials.map((row) => ({
    ...row,
    weight:
      row.marketValue !== null && totalMarketValue !== 0 && !mixedCurrencies
        ? row.marketValue / totalMarketValue
        : null,
  }));

  // R15-UI-005: reduce only over positions with a RESOLVED weight — starting
  // the max from 0 fabricated a real "0.0%" concentration when nothing
  // resolved (no signal is not the same as no concentration).
  const resolvedWeights = rows
    .map((row) => row.weight)
    .filter((weight): weight is number => weight !== null);
  const concentration =
    mixedCurrencies || resolvedWeights.length === 0 ? null : Math.max(...resolvedWeights);
  const unresolvedCount = rows.filter((row) => row.quote === null).length;

  return {
    rows,
    totalCost,
    resolvedCost,
    totalMarketValue,
    totalPnl,
    totalPnlPercent,
    concentration,
    unresolvedCount,
    byCurrency,
    mixedCurrencies,
  };
}

// --- Risk analytics (R15-CODE-PLATFORM-023) --------------------------------
//
// Sharpe/Sortino/Calmar/max-drawdown existed only inside the backtest engine,
// against a simulated equity curve — never against the user's actual tracked
// portfolio. These are pure functions over DAILY CLOSE price history (fetched
// via the existing `/history` sidecar client, 1y range), computed once per
// CURRENCY BUCKET (never cross-currency — D57, same rule as the P&L totals
// above): a fabricated ₹+$ blend is not a real return series either.
//
// Trading days across symbols rarely line up 1:1 (holidays, listing gaps), so
// every function here operates on an already ALIGNED daily-return array — the
// caller (computeCurrencyRisk) intersects each holding's price-by-date map
// down to the common trading days first.

/** Trading days of daily-return history a bucket needs before its risk
 *  metrics are computed — below this, every metric is `null` rather than a
 *  number derived from too little signal. */
export const MIN_RISK_HISTORY_DAYS = 30;

/** Trading days in a year, for annualizing a daily statistic. */
const TRADING_DAYS_PER_YEAR = 252;

/** Day-over-day simple returns from an ordinal (date-ascending) close series.
 *  `n` closes produce `n - 1` returns. */
export function dailyReturns(closes: readonly number[]): number[] {
  const returns: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    returns.push(closes[i] / closes[i - 1] - 1);
  }
  return returns;
}

function mean(values: readonly number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/** Sample standard deviation (ddof = 1). */
function stdev(values: readonly number[]): number {
  if (values.length < 2) return 0;
  const m = mean(values);
  const sumSq = values.reduce((sum, v) => sum + (v - m) ** 2, 0);
  return Math.sqrt(sumSq / (values.length - 1));
}

/** Annualized volatility of a daily-return series (stdev × √252). */
export function annualizedVolatility(returns: readonly number[]): number {
  return stdev(returns) * Math.sqrt(TRADING_DAYS_PER_YEAR);
}

/** Sharpe ratio, risk-free rate = 0 (annualized mean / annualized vol). */
export function sharpeRatio(returns: readonly number[]): number {
  const vol = annualizedVolatility(returns);
  if (vol === 0) return 0;
  return (mean(returns) * TRADING_DAYS_PER_YEAR) / vol;
}

/** Sortino ratio — like Sharpe, but the denominator only penalizes downside
 *  deviation below the 0 target (MAR = 0, matching the Sharpe rf = 0). */
export function sortinoRatio(returns: readonly number[]): number {
  const downsideSumSq = returns.reduce((sum, r) => sum + Math.min(r, 0) ** 2, 0);
  const downsideDeviation =
    Math.sqrt(downsideSumSq / returns.length) * Math.sqrt(TRADING_DAYS_PER_YEAR);
  if (downsideDeviation === 0) return 0;
  return (mean(returns) * TRADING_DAYS_PER_YEAR) / downsideDeviation;
}

/** Max drawdown of the equity curve implied by a daily-return series, as a
 *  negative fraction (e.g. -0.2 = a 20% peak-to-trough decline). */
export function maxDrawdown(returns: readonly number[]): number {
  let value = 1;
  let peak = 1;
  let worst = 0;
  for (const r of returns) {
    value *= 1 + r;
    peak = Math.max(peak, value);
    worst = Math.min(worst, value / peak - 1);
  }
  return worst;
}

/** Calmar ratio — annualized return over the magnitude of max drawdown. */
export function calmarRatio(returns: readonly number[]): number {
  const dd = maxDrawdown(returns);
  if (dd === 0) return 0;
  return (mean(returns) * TRADING_DAYS_PER_YEAR) / Math.abs(dd);
}

/** 1-day historical Value-at-Risk at 95% confidence: the magnitude of loss at
 *  the 5th percentile of the historical return distribution (positive number
 *  — "you'd expect to lose at least this much on 1 day in 20"). Uses linear
 *  interpolation between order statistics (the standard / numpy-default
 *  percentile method) so it is exactly reproducible by hand. */
export function historicalVaR95(returns: readonly number[]): number {
  const sorted = [...returns].sort((a, b) => a - b);
  const h = 0.05 * (sorted.length - 1);
  const lo = Math.floor(h);
  const hi = Math.ceil(h);
  const p05 = lo === hi ? sorted[lo] : sorted[lo] + (h - lo) * (sorted[hi] - sorted[lo]);
  return -p05;
}

function covariance(a: readonly number[], b: readonly number[]): number {
  const ma = mean(a);
  const mb = mean(b);
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += (a[i] - ma) * (b[i] - mb);
  return sum / (a.length - 1);
}

/** Pearson correlation of two equal-length, date-aligned return series. */
export function correlation(a: readonly number[], b: readonly number[]): number {
  const sa = stdev(a);
  const sb = stdev(b);
  if (sa === 0 || sb === 0) return 0;
  return covariance(a, b) / (sa * sb);
}

/** Beta of a return series against a benchmark's (Cov / Var, date-aligned). */
export function beta(returns: readonly number[], benchmarkReturns: readonly number[]): number {
  const benchVar = stdev(benchmarkReturns) ** 2;
  if (benchVar === 0) return 0;
  return covariance(returns, benchmarkReturns) / benchVar;
}

/** One holding's close-by-date price history, ascending by date. */
export interface HoldingPriceHistory {
  symbol: string;
  /** ISO date -> close. */
  closesByDate: Map<string, number>;
  /** Share of the bucket's resolved market value (0-1); weighted portfolio
   *  return = Σ weight_i × return_i on each aligned trading day. */
  weight: number;
}

export interface CorrelationMatrix {
  symbols: string[];
  /** `matrix[i][j]` = correlation of `symbols[i]` and `symbols[j]`. */
  matrix: number[][];
}

export interface CurrencyRiskMetrics {
  currency: string;
  /** Aligned trading days the metrics were computed over. */
  days: number;
  annualizedVolatility: number;
  /** Risk-free rate = 0. */
  sharpeRatio: number;
  sortinoRatio: number;
  maxDrawdown: number;
  calmarRatio: number;
  valueAtRisk95: number;
  /** `null` when the benchmark's own history didn't overlap the holdings'
   *  by {@link MIN_RISK_HISTORY_DAYS} days. */
  beta: number | null;
  correlation: CorrelationMatrix;
}

/** Intersect every date key present in ALL of the given maps, ascending. */
function intersectDates(maps: readonly Map<string, number>[]): string[] {
  if (maps.length === 0) return [];
  let common = new Set(maps[0].keys());
  for (const m of maps.slice(1)) {
    common = new Set([...common].filter((d) => m.has(d)));
  }
  return [...common].sort();
}

/** The value-weighted portfolio daily-return series over `dates` (ascending),
 *  Σ weight_i × return_i on each aligned trading day. */
function weightedPortfolioReturns(
  dates: readonly string[],
  holdings: readonly HoldingPriceHistory[],
  weights: readonly number[],
): number[] {
  const returnsBySymbol = holdings.map((h) =>
    dailyReturns(dates.map((d) => h.closesByDate.get(d)!)),
  );
  const days = dates.length - 1;
  return Array.from({ length: days }, (_, t) =>
    returnsBySymbol.reduce((sum, r, i) => sum + weights[i] * r[t], 0),
  );
}

/**
 * Risk metrics for one currency bucket's resolved holdings, over their
 * aligned trading-day history. `null` when fewer than
 * {@link MIN_RISK_HISTORY_DAYS} days of returns overlap across every holding
 * — never a metric computed from a handful of mismatched points (D57 sibling
 * rule: honesty over a fabricated number).
 */
export function computeCurrencyRisk(
  currency: string,
  holdings: readonly HoldingPriceHistory[],
  benchmarkCloses: Map<string, number> | null,
): CurrencyRiskMetrics | null {
  if (holdings.length === 0) return null;
  const dates = intersectDates(holdings.map((h) => h.closesByDate));
  if (dates.length < MIN_RISK_HISTORY_DAYS + 1) return null;

  const weights = holdings.map((h) => h.weight);
  const portfolioReturns = weightedPortfolioReturns(dates, holdings, weights);
  const returnsBySymbol = holdings.map((h) =>
    dailyReturns(dates.map((d) => h.closesByDate.get(d)!)),
  );
  const days = portfolioReturns.length;

  let betaValue: number | null = null;
  if (benchmarkCloses) {
    const benchDates = intersectDates([benchmarkCloses, ...holdings.map((h) => h.closesByDate)]);
    if (benchDates.length >= MIN_RISK_HISTORY_DAYS + 1) {
      const benchReturns = dailyReturns(benchDates.map((d) => benchmarkCloses.get(d)!));
      // Re-weight the portfolio return series onto the benchmark-aligned date
      // set (may be a subset of `dates` when the benchmark's calendar is
      // sparser than the holdings').
      const alignedPortfolio = weightedPortfolioReturns(benchDates, holdings, weights);
      betaValue = beta(alignedPortfolio, benchReturns);
    }
  }

  return {
    currency,
    days,
    annualizedVolatility: annualizedVolatility(portfolioReturns),
    sharpeRatio: sharpeRatio(portfolioReturns),
    sortinoRatio: sortinoRatio(portfolioReturns),
    maxDrawdown: maxDrawdown(portfolioReturns),
    calmarRatio: calmarRatio(portfolioReturns),
    valueAtRisk95: historicalVaR95(portfolioReturns),
    beta: betaValue,
    correlation: {
      symbols: holdings.map((h) => h.symbol),
      matrix: returnsBySymbol.map((a) => returnsBySymbol.map((b) => correlation(a, b))),
    },
  };
}
