/**
 * Chart panel — the 50-indicator catalog.
 *
 * Mirrors `sidecar/services/indicators.SUPPORTED_INDICATORS` by hand: the
 * canonical key the sidecar accepts, a display label, the pane the indicator
 * renders on, and the catalog category that groups it in the selector UI.
 *
 * The category is a UI-only concern — the wire payload does not carry it. Six
 * categories keep the 50-entry selector scannable without scrolling: Moving
 * Averages, Momentum, Volatility, Volume, Trend, Statistical.
 */

import type { IndicatorPanel } from "../../../types/data";

/** UI-only catalog grouping for the indicator selector. */
export type IndicatorCategory =
  | "moving-average"
  | "momentum"
  | "volatility"
  | "volume"
  | "trend"
  | "statistical";

/** Display order + label for each category in the selector UI. */
export const CATEGORY_LABELS: Record<IndicatorCategory, string> = {
  "moving-average": "Moving Averages",
  momentum: "Momentum",
  volatility: "Volatility",
  volume: "Volume",
  trend: "Trend",
  statistical: "Statistical",
} as const;

/** Order in which the category sections appear in the selector. */
export const CATEGORY_ORDER: readonly IndicatorCategory[] = [
  "moving-average",
  "momentum",
  "volatility",
  "volume",
  "trend",
  "statistical",
] as const;

/** One selectable indicator in the chart panel's multi-select. */
export interface IndicatorDef {
  /** Canonical key sent to `GET /indicators/{symbol}`. */
  key: string;
  /** Human label shown in the selector. */
  label: string;
  /** Pane the indicator renders on — `price` overlays, `separate` oscillators. */
  panel: IndicatorPanel;
  /** Catalog category for the selector grouping. */
  category: IndicatorCategory;
}

/** Every indicator the chart panel can request, in display order. */
export const INDICATOR_CATALOG: readonly IndicatorDef[] = [
  // --- Moving Averages -----------------------------------------------------
  { key: "ma", label: "MA (20/50/200)", panel: "price", category: "moving-average" },
  { key: "sma", label: "SMA", panel: "price", category: "moving-average" },
  { key: "ema", label: "EMA", panel: "price", category: "moving-average" },
  { key: "wma", label: "WMA", panel: "price", category: "moving-average" },
  { key: "hma", label: "Hull MA", panel: "price", category: "moving-average" },
  { key: "dema", label: "DEMA", panel: "price", category: "moving-average" },
  { key: "tema", label: "TEMA", panel: "price", category: "moving-average" },
  { key: "kama", label: "KAMA", panel: "price", category: "moving-average" },
  { key: "vwap", label: "VWAP", panel: "price", category: "moving-average" },

  // --- Momentum ------------------------------------------------------------
  { key: "rsi", label: "RSI", panel: "separate", category: "momentum" },
  { key: "macd", label: "MACD", panel: "separate", category: "momentum" },
  { key: "stochastic", label: "Stochastic", panel: "separate", category: "momentum" },
  { key: "williams_r", label: "Williams %R", panel: "separate", category: "momentum" },
  { key: "cci", label: "CCI", panel: "separate", category: "momentum" },
  { key: "roc", label: "ROC", panel: "separate", category: "momentum" },
  { key: "tsi", label: "TSI", panel: "separate", category: "momentum" },
  { key: "kst", label: "KST", panel: "separate", category: "momentum" },
  { key: "awesome_oscillator", label: "Awesome Osc", panel: "separate", category: "momentum" },
  { key: "ppo", label: "PPO", panel: "separate", category: "momentum" },
  { key: "ultimate_oscillator", label: "Ultimate Osc", panel: "separate", category: "momentum" },

  // --- Volatility ----------------------------------------------------------
  { key: "bollinger", label: "Bollinger Bands", panel: "price", category: "volatility" },
  { key: "keltner", label: "Keltner Channels", panel: "price", category: "volatility" },
  { key: "atr", label: "ATR", panel: "separate", category: "volatility" },
  { key: "std_dev", label: "Std Dev", panel: "separate", category: "volatility" },
  {
    key: "bollinger_bandwidth",
    label: "Bollinger Bandwidth",
    panel: "separate",
    category: "volatility",
  },
  { key: "donchian", label: "Donchian", panel: "price", category: "volatility" },
  {
    key: "chaikin_volatility",
    label: "Chaikin Volatility",
    panel: "separate",
    category: "volatility",
  },

  // --- Volume --------------------------------------------------------------
  { key: "volume", label: "Volume", panel: "separate", category: "volume" },
  { key: "volume_profile", label: "Volume Profile", panel: "price", category: "volume" },
  { key: "obv", label: "OBV", panel: "separate", category: "volume" },
  { key: "mfi", label: "MFI", panel: "separate", category: "volume" },
  { key: "ad_line", label: "A/D Line", panel: "separate", category: "volume" },
  { key: "chaikin_money_flow", label: "CMF", panel: "separate", category: "volume" },
  { key: "force_index", label: "Force Index", panel: "separate", category: "volume" },
  { key: "ease_of_movement", label: "EOM", panel: "separate", category: "volume" },
  { key: "vpt", label: "VPT", panel: "separate", category: "volume" },

  // --- Trend ---------------------------------------------------------------
  { key: "ichimoku", label: "Ichimoku Cloud", panel: "price", category: "trend" },
  { key: "parabolic_sar", label: "Parabolic SAR", panel: "price", category: "trend" },
  { key: "adx", label: "ADX", panel: "separate", category: "trend" },
  { key: "aroon", label: "Aroon", panel: "separate", category: "trend" },
  { key: "aroon_oscillator", label: "Aroon Osc", panel: "separate", category: "trend" },
  { key: "vortex", label: "Vortex", panel: "separate", category: "trend" },
  { key: "mass_index", label: "Mass Index", panel: "separate", category: "trend" },
  { key: "pivot_points", label: "Pivot Points", panel: "price", category: "trend" },
  { key: "supertrend", label: "SuperTrend", panel: "price", category: "trend" },

  // --- Statistical ---------------------------------------------------------
  { key: "linreg", label: "Linear Regression", panel: "price", category: "statistical" },
  { key: "std_error_bands", label: "Std Error Bands", panel: "price", category: "statistical" },
  { key: "hlc3", label: "HLC/3", panel: "price", category: "statistical" },
  { key: "ohlc4", label: "OHLC/4", panel: "price", category: "statistical" },
  { key: "median_price", label: "Median Price", panel: "price", category: "statistical" },
] as const;

/** Indicators that draw on the price pane (overlays). */
export const PRICE_INDICATORS: readonly IndicatorDef[] = INDICATOR_CATALOG.filter(
  (indicator) => indicator.panel === "price",
);

/** Indicators that draw in their own pane below the price chart. */
export const SEPARATE_INDICATORS: readonly IndicatorDef[] = INDICATOR_CATALOG.filter(
  (indicator) => indicator.panel === "separate",
);

/** Look up an indicator definition by its canonical key. */
export function indicatorByKey(key: string): IndicatorDef | undefined {
  return INDICATOR_CATALOG.find((indicator) => indicator.key === key);
}

/** Group the catalog by category in `CATEGORY_ORDER`, preserving entry order within. */
export function indicatorsByCategory(): readonly {
  category: IndicatorCategory;
  label: string;
  indicators: readonly IndicatorDef[];
}[] {
  return CATEGORY_ORDER.map((category) => ({
    category,
    label: CATEGORY_LABELS[category],
    indicators: INDICATOR_CATALOG.filter((indicator) => indicator.category === category),
  }));
}

/** A stable palette of distinct line colors for indicator series. */
export const INDICATOR_COLORS: readonly string[] = [
  "#e9a94d", // amber-400
  "#8fa67c", // sage-400
  "#c9c2b2", // charcoal-200
  "#f4c87a", // amber-300
  "#b6c4a8", // sage-300
];
