"use client";

import { useEffect, useState } from "react";

import { selectSeriesStatus, useMacroStore } from "@/store/macro";

import type { MacroProvider } from "../../../types/macro";
import { MacroChart } from "./MacroChart";
import { MacroSeriesPicker } from "./MacroSeriesPicker";

const DEFAULT_PROVIDER: MacroProvider = "fred";
const DEFAULT_SERIES_ID = "DGS10";

/**
 * Macro panel — picker on top, chart below.
 *
 * The panel mounts with FRED + ``DGS10`` (10-Year Treasury) loaded by
 * default so a populated-state screenshot is one click away. The user
 * switches provider via the picker tabs, types a query to search, or
 * picks from the curated "Featured" catalog. Selecting any result loads
 * the series via :mod:`store/macro` and renders it in :class:`MacroChart`.
 */
export function MacroPanel() {
  const [provider, setProvider] = useState<MacroProvider>(DEFAULT_PROVIDER);
  const [seriesId, setSeriesId] = useState<string>(DEFAULT_SERIES_ID);
  const loadSeries = useMacroStore((s) => s.loadSeries);
  const select = useMacroStore((s) => s.select);
  const status = useMacroStore((s) => selectSeriesStatus(s, provider, seriesId));

  // Load the default-on-mount series. Subsequent loads happen via the
  // picker's onSelect callback.
  useEffect(() => {
    select(provider, seriesId);
    void loadSeries(provider, seriesId);
  }, [provider, seriesId, loadSeries, select]);

  const onSelect = (nextProvider: MacroProvider, nextSeriesId: string) => {
    setProvider(nextProvider);
    setSeriesId(nextSeriesId);
  };

  return (
    <div
      className="flex h-full flex-col bg-charcoal-900 text-charcoal-100"
      data-testid="macro-panel"
    >
      <MacroSeriesPicker
        provider={provider}
        onProviderChange={setProvider}
        onSelect={onSelect}
      />
      <div className="flex-1 overflow-hidden">
        {status?.status === "loading" ? (
          <div className="flex h-full items-center justify-center font-mono text-[12px] text-charcoal-400">
            Loading {seriesId}…
          </div>
        ) : status?.status === "error" ? (
          <div
            className="flex h-full flex-col items-center justify-center px-4 text-center font-mono text-[12px] text-negative"
            data-testid="macro-error"
          >
            <div>Failed to load {seriesId}</div>
            <div className="mt-1 text-[10px] text-charcoal-400">{status.error}</div>
          </div>
        ) : status?.status === "ready" && status.series ? (
          <MacroChart series={status.series} />
        ) : (
          <div className="flex h-full items-center justify-center font-mono text-[12px] text-charcoal-500">
            Select a series.
          </div>
        )}
      </div>
    </div>
  );
}
