/**
 * Per-asset-class default indicator presets.
 *
 * When a chart opens for a symbol whose asset class is known, the chart panel
 * seeds the indicator multi-select from these presets instead of an empty pane.
 * Keys are canonical indicator keys from `INDICATOR_CATALOG`
 * (`src/modules/chart/indicators.ts`) — the same keys the sidecar accepts at
 * `GET /indicators/{symbol}`. Presets are research-backed; see
 * PASS_B_RESEARCH.md §D.1.
 */

/** The asset classes that carry a tuned default indicator set in v1. */
export type AssetClass = "equity" | "etf" | "crypto";

/**
 * Equity, daily timeframe (1d / 1wk / 1mo).
 *
 * `ma` projects the SMA 20/50/200 trio in one overlay — the classic
 * trend-structure read — paired with volume confirmation and the
 * RSI + MACD momentum pair.
 */
export const EQUITY_DAILY: readonly string[] = ["ma", "volume", "rsi", "macd"] as const;

/**
 * Equity, intraday timeframe (1h and below).
 *
 * Intraday trend leans on the faster, single-line `ema` rather than the
 * 20/50/200 trio, and adds `vwap` as the session's fair-value anchor that
 * day traders mean-revert against.
 */
export const EQUITY_INTRADAY: readonly string[] = ["ema", "vwap", "rsi", "volume"] as const;

/**
 * ETF, daily timeframe.
 *
 * Mirrors the equity-daily structure read minus MACD to keep the pane light.
 *
 * Deferred enhancement: a relative-strength (RS) line versus a benchmark
 * (e.g. SPY) is the canonical ETF overlay, but it is NOT a shipped indicator
 * in `INDICATOR_CATALOG` (it needs a second symbol's series), so it is omitted
 * here until a comparison-series indicator ships.
 */
export const ETF_DAILY: readonly string[] = ["ma", "volume", "rsi"] as const;

/**
 * Crypto, any timeframe.
 *
 * Crypto trades 24/7 with no session boundaries, so the intraday-style
 * `ema` + `vwap` anchor applies across timeframes.
 *
 * Deferred-degrade (FR-092): open-interest and funding-rate overlays are the
 * crypto-native context indicators, but they require a derivatives feed that is
 * not yet wired, so they are omitted rather than shown empty.
 */
export const CRYPTO_DEFAULT: readonly string[] = ["ema", "vwap", "rsi", "volume"] as const;

/** Timeframes treated as intraday (1h and below); everything else is daily. */
const INTRADAY_TIMEFRAMES: ReadonlySet<string> = new Set(["1h", "30m", "15m", "5m", "1m"]);

/** True when the timeframe is 1h or shorter (intraday), false for daily+. */
function isIntraday(timeframe: string): boolean {
  return INTRADAY_TIMEFRAMES.has(timeframe);
}

/**
 * Resolve the default indicator key set for an asset class + timeframe.
 *
 * @param region accepted for future locale-anchoring (e.g. an India-specific
 *   benchmark for the deferred RS line); it does NOT change the key set in v1.
 */
export function presetFor(
  assetClass: AssetClass,
  timeframe: string,
  region?: "US" | "IN" | "GLOBAL",
): string[] {
  // region is intentionally unused in v1 — reserved for locale-anchoring.
  void region;

  switch (assetClass) {
    case "crypto":
      // Crypto is timeframe-agnostic: the ema/vwap anchor holds across all bars.
      return [...CRYPTO_DEFAULT];
    case "etf":
      return isIntraday(timeframe) ? [...EQUITY_INTRADAY] : [...ETF_DAILY];
    case "equity":
    default:
      return isIntraday(timeframe) ? [...EQUITY_INTRADAY] : [...EQUITY_DAILY];
  }
}
