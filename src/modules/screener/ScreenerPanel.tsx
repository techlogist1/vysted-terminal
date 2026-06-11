"use client";

import { useCallback } from "react";
import { Play, AlertCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useRetryOnSidecarReady } from "@/lib/use-sidecar-retry";
import { useScreenerStore } from "@/store/screener";

import type { ScreenerUniverseId } from "../../../types/screener";
import { ScreenerCriteriaBuilder } from "./ScreenerCriteriaBuilder";
import { ScreenerPresets } from "./ScreenerPresets";
import { ScreenerResultsTable } from "./ScreenerResultsTable";

const UNIVERSE_LABELS: Record<ScreenerUniverseId, string> = {
  sp500: "S&P 500",
  nifty50: "NIFTY 50",
  "crypto-top50": "Crypto top 50",
  custom: "Custom tickers",
  "nse-all": "NSE — full market",
  "bse-all": "BSE — full market",
  "india-all": "India — NSE + BSE",
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
  const universeStatus = useScreenerStore((s) => s.universeStatus);
  const loadUniverse = useScreenerStore((s) => s.loadUniverse);
  const runScreener = useScreenerStore((s) => s.runScreener);
  const status = useScreenerStore((s) => s.status);
  const error = useScreenerStore((s) => s.error);

  // Load the selected universe's ticker metadata. Auto-retries on a cold-boot
  // sidecar bind (and re-arms on reconnect) so a panel mounted before the
  // sidecar was ready self-heals instead of latching a dead universe count.
  // Re-arms per `universe` so switching universe loads the new one. The
  // "custom" universe has no metadata to fetch, so it always resolves. The
  // user-driven "Run screener" stays a separate explicit action.
  // `loadUniverse` swallows its error into `universeStatus[id]` — re-throw on
  // the error status to drive the retry hook.
  const loadDefault = useCallback(async () => {
    if (universe === "custom") {
      return;
    }
    await loadUniverse(universe);
    if (useScreenerStore.getState().universeStatus[universe] === "error") {
      throw new Error(`Failed to load universe ${universe}`);
    }
  }, [universe, loadUniverse]);
  useRetryOnSidecarReady(loadDefault, [universe]);

  const universeInfo = universeMeta[universe];

  return (
    <div className="flex h-full flex-col gap-3 overflow-hidden p-3">
      <div className="border-border flex flex-wrap items-end gap-3 border-b pb-3">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="screener-universe"
            className="text-muted-foreground text-caption tracking-wide uppercase"
          >
            Universe
          </label>
          <select
            id="screener-universe"
            aria-label="universe"
            value={universe}
            onChange={(e) => setUniverse(e.target.value as ScreenerUniverseId)}
            className="border-border bg-charcoal-850 rounded-control text-body h-8 border px-2"
          >
            {(Object.keys(UNIVERSE_LABELS) as ScreenerUniverseId[]).map((id) => (
              <option key={id} value={id}>
                {UNIVERSE_LABELS[id]}
              </option>
            ))}
          </select>
          {universe !== "custom" &&
            (universeStatus[universe] === "loading" ? (
              <span className="text-muted-foreground text-micro animate-pulse">
                Loading universe…
              </span>
            ) : universeStatus[universe] === "error" ? (
              <span className="text-destructive text-micro">Failed to load universe</span>
            ) : universeInfo ? (
              <span className="text-muted-foreground text-micro">
                {universeInfo.symbols.length} tickers · {universeInfo.asset_class}
              </span>
            ) : null)}
        </div>
        {universe === "custom" && (
          <div className="flex min-w-[16rem] flex-1 flex-col gap-1">
            <label
              htmlFor="screener-custom-symbols"
              className="text-muted-foreground text-caption tracking-wide uppercase"
            >
              Symbols (comma or space)
            </label>
            <input
              id="screener-custom-symbols"
              type="text"
              value={customSymbols}
              onChange={(e) => setCustomSymbols(e.target.value)}
              placeholder="AAPL MSFT NVDA"
              className="border-border bg-charcoal-850 rounded-control text-body h-8 border px-2"
            />
          </div>
        )}
        {universe === "custom" && customSymbols.trim() === "" && (
          <span className="text-warning text-micro">Enter at least one ticker to screen.</span>
        )}
        <div className="ml-auto">
          <Button
            onClick={() => void runScreener()}
            disabled={
              status === "loading" || (universe === "custom" && customSymbols.trim() === "")
            }
            data-testid="run-screener-button"
          >
            <Play className="mr-1" />
            {status === "loading" ? "Running…" : "Run screener"}
          </Button>
        </div>
      </div>

      {error && (
        // Design law: signal colors are text + a 1px marker, never a filled
        // background — the destructive tone rides the border and the copy only.
        <div className="border-destructive/40 text-destructive text-body flex items-center gap-2 rounded-none border px-3 py-2">
          <AlertCircle className="size-4 shrink-0" />
          <span className="flex-1">
            {error.startsWith("POST /screener/run failed")
              ? "Screener failed: " +
                error.replace(/^POST \/screener\/run failed \(\d+\):\s*/, "").slice(0, 120)
              : error.slice(0, 120)}
          </span>
          <button
            type="button"
            className="text-caption ml-auto shrink-0 underline"
            onClick={() => void runScreener()}
          >
            Retry
          </button>
        </div>
      )}

      <div className="shrink-0">
        <ScreenerPresets />
      </div>
      <div className="shrink-0">
        <ScreenerCriteriaBuilder />
      </div>
      <div className="min-h-0 flex-1">
        <ScreenerResultsTable />
      </div>
    </div>
  );
}
