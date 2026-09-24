import { currencyAffix } from "@/lib/format";

import type { Greeks } from "../../../types/quant";

/** Display currencies for the option panels, the Bond pricer's set (R15-DATA-100).
 *  A display label only: the pricing request stays currency-free. */
export const DISPLAY_CURRENCIES = ["USD", "INR", "EUR", "GBP", "JPY"] as const;

export interface MarketGreek {
  value: number;
  unit: string | null;
}

/** QuantLib returns vega and rho per unit rate (1.00 = a full 100-point move)
 *  and theta per year. A desk reads vega/rho per 1-point move and theta per
 *  calendar day (R15-UI-028, R15-UI-051). */
export function toMarketUnits({ vega, theta, rho }: Pick<Greeks, "vega" | "theta" | "rho">): {
  vega: MarketGreek;
  theta: MarketGreek;
  rho: MarketGreek;
} {
  return {
    vega: { value: vega / 100, unit: "per 1 vol pt" },
    theta: { value: theta / 365, unit: "per day" },
    rho: { value: rho / 100, unit: "per 1%" },
  };
}

/** One greek as a panel shows it: vega/theta/rho in market units, the rest as served. */
export function greekForDisplay(greeks: Greeks, key: keyof Greeks): MarketGreek {
  if (key === "vega" || key === "theta" || key === "rho") return toMarketUnits(greeks)[key];
  return { value: greeks[key], unit: null };
}

/** An option price at pricer precision (4 dp) with the display currency's symbol. */
export function formatOptionPrice(value: number, currency: string): string {
  const { prefix, suffix } = currencyAffix(currency);
  return `${prefix}${value.toFixed(4)}${suffix}`;
}
