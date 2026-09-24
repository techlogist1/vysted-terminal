/**
 * The Equity Overview's fundamentals rows — ONE list shared by the panel (which
 * renders a row per field) and the `open_company_overview` host action (which
 * may spotlight a row). Because both read this table, the action can only claim
 * to spotlight a metric the panel really shows (R15-AGENT-081).
 */

import type { Fundamentals } from "../../../types/data";

export type FieldKind = "ratio" | "price" | "fraction" | "money" | "count";

export interface FieldDef {
  label: string;
  key: keyof Fundamentals;
  kind: FieldKind;
  /** Headline metrics read at the primary tier; supporting ratios at secondary. */
  headline?: boolean;
  /** A statement-denominated size (revenue, net income, FCF): formatted in the
   *  statement currency (`financial_currency ?? currency`, C2), which differs
   *  from the trading currency for a foreign reporter (SIFY: USD ADR, INR books). */
  statementSize?: boolean;
}

export interface FieldGroup {
  title: string;
  fields: FieldDef[];
}

// Screener-grade fundamentals, grouped the way a trader reads a stock page. Labels
// are curated (never snake_case). Every group ALWAYS renders (R13) — a group that
// happens to be all-null (e.g. ownership for an index fund) still shows its field
// rows, each with an honest em-dash + reason chip, never a silently-hidden section.
export const FIELD_GROUPS: FieldGroup[] = [
  {
    title: "Valuation",
    fields: [
      { label: "Market cap", key: "market_cap", kind: "money", headline: true },
      { label: "P/E", key: "pe_ratio", kind: "ratio", headline: true },
      { label: "Fwd P/E", key: "forward_pe", kind: "ratio" },
      { label: "PEG", key: "peg_ratio", kind: "ratio" },
      { label: "P/B", key: "price_to_book", kind: "ratio" },
      { label: "P/S", key: "price_to_sales", kind: "ratio" },
      { label: "EV/EBITDA", key: "ev_to_ebitda", kind: "ratio" },
      { label: "Book value", key: "book_value", kind: "price" },
    ],
  },
  {
    title: "Profitability",
    fields: [
      { label: "ROE", key: "roe", kind: "fraction", headline: true },
      { label: "ROA", key: "roa", kind: "fraction" },
      { label: "Gross margin", key: "gross_margin", kind: "fraction" },
      { label: "Operating margin", key: "operating_margin", kind: "fraction" },
      { label: "Net margin", key: "profit_margin", kind: "fraction", headline: true },
    ],
  },
  {
    title: "Financial health",
    fields: [
      { label: "Debt / equity", key: "debt_to_equity", kind: "ratio", headline: true },
      { label: "Current ratio", key: "current_ratio", kind: "ratio" },
      { label: "Quick ratio", key: "quick_ratio", kind: "ratio" },
      {
        label: "Free cash flow",
        key: "free_cash_flow",
        kind: "money",
        headline: true,
        statementSize: true,
      },
    ],
  },
  {
    title: "Growth & size",
    fields: [
      {
        label: "Revenue (TTM)",
        key: "revenue_ttm",
        kind: "money",
        headline: true,
        statementSize: true,
      },
      {
        label: "Net income (TTM)",
        key: "net_income_ttm",
        kind: "money",
        headline: true,
        statementSize: true,
      },
      { label: "Revenue growth", key: "revenue_growth", kind: "fraction" },
      { label: "Earnings growth", key: "earnings_growth", kind: "fraction" },
      { label: "Shares outstanding", key: "shares_outstanding", kind: "count" },
    ],
  },
  {
    title: "Per share & dividend",
    fields: [
      { label: "EPS", key: "eps", kind: "price", headline: true },
      { label: "Dividend / share", key: "dividend_per_share", kind: "price" },
      { label: "Dividend yield", key: "dividend_yield", kind: "fraction" },
      { label: "Beta", key: "beta", kind: "ratio" },
      { label: "1Y change", key: "fifty_two_week_change", kind: "fraction" },
    ],
  },
  {
    title: "Ownership",
    fields: [
      { label: "Insiders (Yahoo)", key: "held_percent_insiders", kind: "fraction" },
      { label: "Institutions (Yahoo)", key: "held_percent_institutions", kind: "fraction" },
    ],
  },
];

/** The highlightable metric ids (every row key) → the row's label. */
export const METRIC_LABELS: ReadonlyMap<string, string> = new Map(
  FIELD_GROUPS.flatMap((group) => group.fields.map((f) => [f.key as string, f.label])),
);

/** Resolve an agent-supplied metric name ("pe_ratio", "Market cap") to the key
 *  of a row the panel renders, or `null` when the panel has no such metric. */
export function resolveMetric(name: string | undefined): string | null {
  const key = (name ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  return METRIC_LABELS.has(key) ? key : null;
}
