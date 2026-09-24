import { currencyAffix } from "@/lib/format";

import type { Greeks } from "../../../types/quant";

/** Display currencies for the option panels, the Bond pricer's set (R15-DATA-100).
 *  A display label only: the pricing request stays currency-free. */
export const DISPLAY_CURRENCIES = ["USD", "INR", "EUR", "GBP", "JPY"] as const;

export interface MarketGreek {
  value: number;
  unit: string | null;
}

/** QuantLib returns vega per unit of volatility (1.00 = 100 vol points) and
 *  theta per year. A desk reads vega per 1 vol point and theta per calendar day
 *  (R15-UI-028, R15-UI-051). */
export function toMarketUnits({ vega, theta }: Pick<Greeks, "vega" | "theta">): {
  vega: MarketGreek;
  theta: MarketGreek;
} {
  return {
    vega: { value: vega / 100, unit: "per 1 vol pt" },
    theta: { value: theta / 365, unit: "per day" },
  };
}

/** One greek as a panel shows it: vega and theta in market units, the rest as served. */
export function greekForDisplay(greeks: Greeks, key: keyof Greeks): MarketGreek {
  if (key === "vega" || key === "theta") return toMarketUnits(greeks)[key];
  return { value: greeks[key], unit: null };
}

/** An option price at pricer precision (4 dp) with the display currency's symbol. */
export function formatOptionPrice(value: number, currency: string): string {
  const { prefix, suffix } = currencyAffix(currency);
  return `${prefix}${value.toFixed(4)}${suffix}`;
}
