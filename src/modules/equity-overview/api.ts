/**
 * Equity-overview sidecar access.
 *
 * One symbol selection fans out to the five fundamentals endpoints plus a live
 * quote. The calls are independent, so a failure in one (e.g. analyst ratings
 * unavailable) does not blank the whole panel — `loadEquityOverview` returns a
 * `null` for any section that failed and an `error` only if every call failed.
 */

import { sidecarApi } from "@/lib/sidecar-client";
import type {
  AnalystRating,
  BalanceSheet,
  CashFlowStatement,
  Fundamentals,
  IncomeStatement,
  Quote,
} from "../../../types/data";

/** The assembled equity-overview payload for one symbol. */
export interface EquityOverview {
  symbol: string;
  quote: Quote | null;
  fundamentals: Fundamentals | null;
  income: IncomeStatement | null;
  balance: BalanceSheet | null;
  cashFlow: CashFlowStatement | null;
  ratings: AnalystRating | null;
  /** `true` when every section failed to load — the panel shows an error. */
  allFailed: boolean;
}

function settled<T>(result: PromiseSettledResult<T>): T | null {
  return result.status === "fulfilled" ? result.value : null;
}

/** Fetch every section for one symbol; partial failures degrade gracefully. */
export async function loadEquityOverview(symbol: string): Promise<EquityOverview> {
  const [quote, fundamentals, income, balance, cashFlow, ratings] = await Promise.allSettled([
    sidecarApi.quote(symbol),
    sidecarApi.fundamentals(symbol),
    sidecarApi.incomeStatement(symbol),
    sidecarApi.balanceSheet(symbol),
    sidecarApi.cashFlow(symbol),
    sidecarApi.analystRating(symbol),
  ]);

  const sections = [quote, fundamentals, income, balance, cashFlow, ratings];
  const allFailed = sections.every((section) => section.status === "rejected");

  return {
    symbol,
    quote: settled(quote),
    fundamentals: settled(fundamentals),
    income: settled(income),
    balance: settled(balance),
    cashFlow: settled(cashFlow),
    ratings: settled(ratings),
    allFailed,
  };
}
