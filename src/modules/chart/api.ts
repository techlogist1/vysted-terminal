/**
 * Chart panel — indicators API.
 *
 * Thin wrapper over the low-level `sidecarGet` for the chart panel's only
 * non-shared endpoint, `GET /indicators/{symbol}`. The shared data-layer
 * endpoints (history, quotes, ...) are reached via `sidecarApi`; this module
 * owns just the indicator call so `sidecar-client.ts` stays untouched.
 */

import { sidecarGet } from "@/lib/sidecar-client";
import type { IndicatorResponse } from "../../../types/data";

/**
 * Fetch the requested technical indicators for `symbol`, computed server-side
 * against that symbol's OHLCV history at the given timeframe.
 *
 * @param symbol      Ticker symbol, e.g. `SPY`.
 * @param indicators  Canonical indicator keys, e.g. `["rsi", "macd"]`.
 * @param timeframe   Bar interval; must match the chart's history timeframe.
 * @param assetClass  `equity` (default) or `crypto`.
 * @param region      The picked listing's region (R15-DATA-002), so the
 *                    indicators compute on the same listing the candles show.
 */
export function fetchIndicators(
  symbol: string,
  indicators: string[],
  timeframe = "1d",
  assetClass = "equity",
  region?: string,
): Promise<IndicatorResponse> {
  return sidecarGet<IndicatorResponse>(
    `/indicators/${encodeURIComponent(symbol)}`,
    {
      indicators: indicators.join(","),
      timeframe,
      asset_class: assetClass,
    },
    { "X-Vysted-Region": region },
  );
}
