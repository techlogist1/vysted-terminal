/**
 * Chart panel — the 20-indicator catalog.
 *
 * Mirrors `sidecar/services/indicators.SUPPORTED_INDICATORS` by hand: the
 * canonical key the sidecar accepts, a display label, and which pane the
 * indicator renders on. The sidecar is authoritative for `panel` — this table
 * drives the selector UI and lets the panel group overlays vs. oscillators
 * before any network round-trip.
 */

import type { IndicatorPanel } from "../../../types/data";

/** One selectable indicator in the chart panel's multi-select. */
export interface IndicatorDef {
  /** Canonical key sent to `GET /indicators/{symbol}`. */
  key: string;
  /** Human label shown in the selector. */
  label: string;
  /** Pane the indicator renders on — `price` overlays, `separate` oscillators. */
  panel: IndicatorPanel;
}

/** Every indicator the chart panel can request, in display order. */
export const INDICATOR_CATALOG: readonly IndicatorDef[] = [
  // --- price-pane overlays ---
  { key: "ma", label: "MA (20/50/200)", panel: "price" },
  { key: "sma", label: "SMA", panel: "price" },
  { key: "ema", label: "EMA", panel: "price" },
  { key: "bollinger", label: "Bollinger Bands", panel: "price" },
  { key: "ichimoku", label: "Ichimoku Cloud", panel: "price" },
  { key: "keltner", label: "Keltner Channels", panel: "price" },
  { key: "vwap", label: "VWAP", panel: "price" },
  { key: "parabolic_sar", label: "Parabolic SAR", panel: "price" },
  // --- separate-pane oscillators / volume ---
  { key: "rsi", label: "RSI", panel: "separate" },
  { key: "macd", label: "MACD", panel: "separate" },
  { key: "adx", label: "ADX", panel: "separate" },
  { key: "stochastic", label: "Stochastic", panel: "separate" },
  { key: "atr", label: "ATR", panel: "separate" },
  { key: "obv", label: "OBV", panel: "separate" },
  { key: "mfi", label: "MFI", panel: "separate" },
  { key: "cci", label: "CCI", panel: "separate" },
  { key: "williams_r", label: "Williams %R", panel: "separate" },
  { key: "roc", label: "ROC", panel: "separate" },
  { key: "volume", label: "Volume", panel: "separate" },
  { key: "volume_profile", label: "Volume Profile", panel: "separate" },
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

/** A stable palette of distinct line colors for indicator series. */
export const INDICATOR_COLORS: readonly string[] = [
  "#e9a94d", // amber-400
  "#8fa67c", // sage-400
  "#c9c2b2", // charcoal-200
  "#f4c87a", // amber-300
  "#b6c4a8", // sage-300
];
