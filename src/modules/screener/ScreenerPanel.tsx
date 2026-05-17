"use client";

import { useEffect } from "react";
import { Play, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useScreenerStore } from "@/store/screener";

import type { ScreenerUniverseId } from "../../../types/screener";
import { ScreenerCriteriaBuilder } from "./ScreenerCriteriaBuilder";
import { ScreenerResultsTable } from "./ScreenerResultsTable";

const UNIVERSE_LABELS: Record<ScreenerUniverseId, string> = {
  sp500: "S&P 500",
  nifty50: "NIFTY 50",
  "crypto-top50": "Crypto top 50",
  custom: "Custom tickers",
};

/**
 * Screener panel — Phase 6 (Teammate Sc backend / lead-completed frontend).
 *
 * Layout: universe picker (top row) + criteria builder (middle) +
 * "Run screener" action + results table (bottom). Default criteria
 * (P/E < 20 AND market cap > 100B AND sector = "Technology") are seeded
 * so the panel renders in a populated-state shape on first mount.
 */
export function ScreenerPanel() {
  const universe = useScreenerStore((s) => s.universe);
  const setUniverse = useScreenerStore((s) => s.setUniverse);
  const customSymbols = useScreenerStore((s) => s.customSymbols);
  const setCustomSymbols = useScreenerStore((s) => s.setCustomSymbols);
  const universeMeta = useScreenerStore((s) => s.universeMeta);
  const loadUniverse = useScreenerStore((s) => s.loadUniverse);
  const runScreener = useScreenerStore((s) => s.runScreener);
  const status = useScreenerStore((s) => s.status);
  const error = useScreenerStore((s) => s.error);

  useEffect(() => {
    if (universe !== "custom") {
      void loadUniverse(universe);
    }
  }, [universe, loadUniverse]);

  const universeInfo = universeMeta[universe];

  return (
    <div className="flex h-full flex-col gap-3 overflow-auto p-3">
      <div className="border-border flex flex-wrap items-end gap-3 border-b pb-3">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="screener-universe"
            className="text-muted-foreground text-xs tracking-wide uppercase"
          >
            Universe
          </label>
          <select
            id="screener-universe"
            aria-label="universe"
            value={universe}
            onChange={(e) => setUniverse(e.target.value as ScreenerUniverseId)}
            className="border-border bg-background rounded-md border px-2 py-1.5 text-sm"
          >
            {(Object.keys(UNIVERSE_LABELS) as ScreenerUniverseId[]).map((id) => (
              <option key={id} value={id}>
                {UNIVERSE_LABELS[id]}
              </option>
            ))}
          </select>
          {universeInfo && universe !== "custom" && (
            <span className="text-muted-foreground text-[10px]">
              {universeInfo.symbols.length} tickers · {universeInfo.asset_class}
            </span>
          )}
        </div>
        {universe === "custom" && (
          <div className="flex min-w-[16rem] flex-1 flex-col gap-1">
            <label
              htmlFor="screener-custom-symbols"
              className="text-muted-foreground text-xs tracking-wide uppercase"
            >
              Symbols (comma or space)
            </label>
            <input
              id="screener-custom-symbols"
              type="text"
              value={customSymbols}
              onChange={(e) => setCustomSymbols(e.target.value)}
              placeholder="AAPL MSFT NVDA"
              className="border-border bg-background rounded-md border px-2 py-1.5 text-sm"
            />
          </div>
        )}
        <div className="ml-auto">
          <Button
            onClick={() => void runScreener()}
            disabled={status === "loading"}
            data-testid="run-screener-button"
          >
            <Play className="mr-1.5 size-4" />
            {status === "loading" ? "Running…" : "Run screener"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="border-destructive/40 bg-destructive/10 text-destructive flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
          <AlertCircle className="size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <ScreenerCriteriaBuilder />
      <div className="min-h-0 flex-1">
        <ScreenerResultsTable />
      </div>
    </div>
  );
}
