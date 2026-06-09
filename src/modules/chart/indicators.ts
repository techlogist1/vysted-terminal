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

import { INDICATOR_PALETTE } from "@/lib/chart-theme";

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
  /** Terse label for toolbar chips ("RSI", "MA (20/50/200)"). */
  label: string;
  /** Spelled-out name for the Indicators popover ("Relative Strength Index"). */
  menuLabel: string;
  /** Pane the indicator renders on — `price` overlays, `separate` oscillators. */
  panel: IndicatorPanel;
  /** Catalog category for the selector grouping. */
  category: IndicatorCategory;
}

/** Every indicator the chart panel can request, in display order. */
export const INDICATOR_CATALOG: readonly IndicatorDef[] = [
  // --- Moving Averages -----------------------------------------------------
  {
    key: "ma",
    label: "MA (20/50/200)",
    menuLabel: "Moving Average (20/50/200)",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "sma",
    label: "SMA",
    menuLabel: "Simple Moving Average",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "ema",
    label: "EMA",
    menuLabel: "Exponential Moving Average",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "wma",
    label: "WMA",
    menuLabel: "Weighted Moving Average",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "hma",
    label: "Hull MA",
    menuLabel: "Hull Moving Average",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "dema",
    label: "DEMA",
    menuLabel: "Double Exponential Moving Average",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "tema",
    label: "TEMA",
    menuLabel: "Triple Exponential Moving Average",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "kama",
    label: "KAMA",
    menuLabel: "Kaufman Adaptive Moving Average",
    panel: "price",
    category: "moving-average",
  },
  {
    key: "vwap",
    label: "VWAP",
    menuLabel: "Volume-Weighted Average Price",
    panel: "price",
    category: "moving-average",
  },

  // --- Momentum ------------------------------------------------------------
  {
    key: "rsi",
    label: "RSI",
    menuLabel: "Relative Strength Index",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "macd",
    label: "MACD",
    menuLabel: "Moving Average Convergence Divergence",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "stochastic",
    label: "Stochastic",
    menuLabel: "Stochastic Oscillator",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "williams_r",
    label: "Williams %R",
    menuLabel: "Williams Percent Range",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "cci",
    label: "CCI",
    menuLabel: "Commodity Channel Index",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "roc",
    label: "ROC",
    menuLabel: "Rate of Change",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "tsi",
    label: "TSI",
    menuLabel: "True Strength Index",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "kst",
    label: "KST",
    menuLabel: "Know Sure Thing",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "awesome_oscillator",
    label: "Awesome Osc",
    menuLabel: "Awesome Oscillator",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "ppo",
    label: "PPO",
    menuLabel: "Percentage Price Oscillator",
    panel: "separate",
    category: "momentum",
  },
  {
    key: "ultimate_oscillator",
    label: "Ultimate Osc",
    menuLabel: "Ultimate Oscillator",
    panel: "separate",
    category: "momentum",
  },

  // --- Volatility ----------------------------------------------------------
  {
    key: "bollinger",
    label: "Bollinger Bands",
    menuLabel: "Bollinger Bands",
    panel: "price",
    category: "volatility",
  },
  {
    key: "keltner",
    label: "Keltner Channels",
    menuLabel: "Keltner Channels",
    panel: "price",
    category: "volatility",
  },
  {
    key: "atr",
    label: "ATR",
    menuLabel: "Average True Range",
    panel: "separate",
    category: "volatility",
  },
  {
    key: "std_dev",
    label: "Std Dev",
    menuLabel: "Standard Deviation",
    panel: "separate",
    category: "volatility",
  },
  {
    key: "bollinger_bandwidth",
    label: "Bollinger Bandwidth",
    menuLabel: "Bollinger Bandwidth",
    panel: "separate",
    category: "volatility",
  },
  {
    key: "donchian",
    label: "Donchian",
    menuLabel: "Donchian Channels",
    panel: "price",
    category: "volatility",
  },
  {
    key: "chaikin_volatility",
    label: "Chaikin Volatility",
    menuLabel: "Chaikin Volatility",
    panel: "separate",
    category: "volatility",
  },

  // --- Volume --------------------------------------------------------------
  { key: "volume", label: "Volume", menuLabel: "Volume", panel: "separate", category: "volume" },
  {
    key: "volume_profile",
    label: "Volume Profile",
    menuLabel: "Volume Profile",
    panel: "price",
    category: "volume",
  },
  {
    key: "obv",
    label: "OBV",
    menuLabel: "On-Balance Volume",
    panel: "separate",
    category: "volume",
  },
  {
    key: "mfi",
    label: "MFI",
    menuLabel: "Money Flow Index",
    panel: "separate",
    category: "volume",
  },
  {
    key: "ad_line",
    label: "A/D Line",
    menuLabel: "Accumulation/Distribution Line",
    panel: "separate",
    category: "volume",
  },
  {
    key: "chaikin_money_flow",
    label: "CMF",
    menuLabel: "Chaikin Money Flow",
    panel: "separate",
    category: "volume",
  },
  {
    key: "force_index",
    label: "Force Index",
    menuLabel: "Force Index",
    panel: "separate",
    category: "volume",
  },
  {
    key: "ease_of_movement",
    label: "EOM",
    menuLabel: "Ease of Movement",
    panel: "separate",
    category: "volume",
  },
  {
    key: "vpt",
    label: "VPT",
    menuLabel: "Volume-Price Trend",
    panel: "separate",
    category: "volume",
  },

  // --- Trend ---------------------------------------------------------------
  {
    key: "ichimoku",
    label: "Ichimoku Cloud",
    menuLabel: "Ichimoku Cloud",
    panel: "price",
    category: "trend",
  },
  {
    key: "parabolic_sar",
    label: "Parabolic SAR",
    menuLabel: "Parabolic SAR",
    panel: "price",
    category: "trend",
  },
  {
    key: "adx",
    label: "ADX",
    menuLabel: "Average Directional Index",
    panel: "separate",
    category: "trend",
  },
  { key: "aroon", label: "Aroon", menuLabel: "Aroon", panel: "separate", category: "trend" },
  {
    key: "aroon_oscillator",
    label: "Aroon Osc",
    menuLabel: "Aroon Oscillator",
    panel: "separate",
    category: "trend",
  },
  { key: "vortex", label: "Vortex", menuLabel: "Vortex", panel: "separate", category: "trend" },
  {
    key: "mass_index",
    label: "Mass Index",
    menuLabel: "Mass Index",
    panel: "separate",
    category: "trend",
  },
  {
    key: "pivot_points",
    label: "Pivot Points",
    menuLabel: "Pivot Points",
    panel: "price",
    category: "trend",
  },
  {
    key: "supertrend",
    label: "SuperTrend",
    menuLabel: "SuperTrend",
    panel: "price",
    category: "trend",
  },

  // --- Statistical ---------------------------------------------------------
  {
    key: "linreg",
    label: "Linear Regression",
    menuLabel: "Linear Regression",
    panel: "price",
    category: "statistical",
  },
  {
    key: "std_error_bands",
    label: "Std Error Bands",
    menuLabel: "Standard Error Bands",
    panel: "price",
    category: "statistical",
  },
  {
    key: "hlc3",
    label: "HLC/3",
    menuLabel: "Typical Price (HLC/3)",
    panel: "price",
    category: "statistical",
  },
  {
    key: "ohlc4",
    label: "OHLC/4",
    menuLabel: "Average Price (OHLC/4)",
    panel: "price",
    category: "statistical",
  },
  {
    key: "median_price",
    label: "Median Price",
    menuLabel: "Median Price",
    panel: "price",
    category: "statistical",
  },
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
export const INDICATOR_COLORS: readonly string[] = INDICATOR_PALETTE;
