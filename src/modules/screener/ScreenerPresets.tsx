"use client";

import { Sparkles } from "lucide-react";

import { useScreenerStore } from "@/store/screener";

import type { ScreenerCriterion, ScreenerUniverseId } from "../../../types/screener";

interface ScreenerPreset {
  id: string;
  label: string;
  description: string;
  universe: ScreenerUniverseId;
  criteria: ScreenerCriterion[];
}

/**
 * Curated starter screens (the screener.in "clone-and-modify" workflow). Each
 * applies a universe + a criteria set and runs immediately; the user then tweaks
 * the criteria below and drills into any result (row-click loads it in the
 * cockpit). Fraction fields (roe / margins / growth / yield) use fractions
 * (0.20 = 20%) to match the Fundamentals contract.
 */
const PRESETS: ScreenerPreset[] = [
  {
    id: "quality",
    label: "Quality compounders",
    description: "High ROE + net margin + revenue growth, low debt, large cap",
    universe: "sp500",
    criteria: [
      { field: "roe", operator: "gt", value: 0.18 },
      { field: "profit_margin", operator: "gt", value: 0.12 },
      { field: "revenue_growth", operator: "gt", value: 0.1 },
      { field: "debt_to_equity", operator: "lt", value: 1.0 },
      { field: "market_cap", operator: "gt", value: 10_000_000_000 },
    ],
  },
  {
    id: "value",
    label: "Sound value",
    description: "Low P/E, profitable (ROE > 12%), low leverage",
    universe: "sp500",
    criteria: [
      { field: "pe_ratio", operator: "gt", value: 0 },
      { field: "pe_ratio", operator: "lt", value: 15 },
      { field: "roe", operator: "gt", value: 0.12 },
      { field: "debt_to_equity", operator: "lt", value: 1.0 },
    ],
  },
  {
    id: "garp",
    label: "GARP",
    description: "Growth at a reasonable price — PEG < 1 with real growth + returns",
    universe: "sp500",
    criteria: [
      { field: "peg_ratio", operator: "gt", value: 0 },
      { field: "peg_ratio", operator: "lt", value: 1 },
      { field: "revenue_growth", operator: "gt", value: 0.12 },
      { field: "roe", operator: "gt", value: 0.15 },
    ],
  },
  {
    id: "dividend",
    label: "Dividend + low debt",
    description: "Yield > 3%, low leverage, profitable",
    universe: "sp500",
    criteria: [
      { field: "dividend_yield", operator: "gt", value: 0.03 },
      { field: "debt_to_equity", operator: "lt", value: 0.6 },
      { field: "profit_margin", operator: "gt", value: 0.08 },
    ],
  },
  {
    id: "margins",
    label: "High-margin leaders",
    description: "Fat gross + operating margins, strong returns",
    universe: "sp500",
    criteria: [
      { field: "gross_margin", operator: "gt", value: 0.5 },
      { field: "operating_margin", operator: "gt", value: 0.25 },
      { field: "roe", operator: "gt", value: 0.15 },
    ],
  },
  {
    id: "deep-value",
    label: "Deep value",
    description: "Cheap on book + sales, still earning",
    universe: "sp500",
    criteria: [
      { field: "price_to_book", operator: "gt", value: 0 },
      { field: "price_to_book", operator: "lt", value: 1.5 },
      { field: "price_to_sales", operator: "lt", value: 2 },
      { field: "pe_ratio", operator: "gt", value: 0 },
      { field: "pe_ratio", operator: "lt", value: 18 },
    ],
  },
  {
    id: "megacap",
    label: "Megacap quality",
    description: "Giants ($200B+) with elite returns + margins",
    universe: "sp500",
    criteria: [
      { field: "market_cap", operator: "gt", value: 200_000_000_000 },
      { field: "roe", operator: "gt", value: 0.2 },
      { field: "profit_margin", operator: "gt", value: 0.15 },
    ],
  },
  {
    id: "promoter",
    label: "Founder-aligned (NSE)",
    description: "High insider/promoter holding, sound balance sheet (NIFTY 50)",
    universe: "nifty50",
    criteria: [
      { field: "held_percent_insiders", operator: "gt", value: 0.4 },
      { field: "roe", operator: "gt", value: 0.12 },
      { field: "debt_to_equity", operator: "lt", value: 1.0 },
    ],
  },
];

export function ScreenerPresets() {
  const setUniverse = useScreenerStore((s) => s.setUniverse);
  const setCriteria = useScreenerStore((s) => s.setCriteria);
  const setCombinator = useScreenerStore((s) => s.setCombinator);
  const runScreener = useScreenerStore((s) => s.runScreener);

  const apply = (preset: ScreenerPreset) => {
    setUniverse(preset.universe);
    setCriteria(preset.criteria);
    // Every preset is AND-semantics — reset the combinator so a prior "Match
    // ANY" selection doesn't silently turn the preset into an OR sweep.
    setCombinator("and");
    void runScreener();
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-muted-foreground text-micro inline-flex shrink-0 items-center gap-1 tracking-wide uppercase">
        <Sparkles className="size-3 text-amber-400" /> Screens
      </span>
      {PRESETS.map((preset) => (
        <button
          key={preset.id}
          type="button"
          onClick={() => apply(preset)}
          title={preset.description}
          className="border-border bg-charcoal-850 text-muted-foreground rounded-control text-micro border px-2 py-0.5 transition-colors hover:border-amber-500 hover:text-amber-300"
        >
          {preset.label}
        </button>
      ))}
    </div>
  );
}
