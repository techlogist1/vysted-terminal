"use client";

import { useCallback, useState } from "react";
import { TrendingUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useRetryOnSidecarReady } from "@/lib/use-sidecar-retry";
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
  // picker's onSelect callback. The load auto-retries on a cold-boot sidecar
  // bind (and re-arms on reconnect) so a panel mounted before the sidecar was
  // ready self-heals instead of latching a permanent error. `loadSeries`
  // swallows its error into store state, so re-throw on the error status to
  // signal the retry hook.
  const loadDefault = useCallback(async () => {
    select(provider, seriesId);
    await loadSeries(provider, seriesId);
    const status = selectSeriesStatus(useMacroStore.getState(), provider, seriesId);
    if (status?.status === "error") {
      throw new Error(status.error ?? "macro load failed");
    }
  }, [provider, seriesId, loadSeries, select]);
  useRetryOnSidecarReady(loadDefault, [provider, seriesId]);

  const onSelect = (nextProvider: MacroProvider, nextSeriesId: string) => {
    setProvider(nextProvider);
    setSeriesId(nextSeriesId);
  };

  return (
    <div
      className="bg-charcoal-900 text-charcoal-100 flex h-full flex-col"
      data-testid="macro-panel"
    >
      <MacroSeriesPicker provider={provider} onProviderChange={setProvider} onSelect={onSelect} />
      <div className="flex-1 overflow-hidden">
        {status?.status === "loading" ? (
          <div className="text-charcoal-400 text-caption flex h-full items-center justify-center font-mono">
            <div className="flex items-center gap-2">
              <div className="border-charcoal-600 size-3 animate-spin rounded-full border-2 border-t-amber-400" />
              Loading {seriesId}…
            </div>
          </div>
        ) : status?.status === "error" ? (
          <div
            className="text-negative text-caption flex h-full flex-col items-center justify-center px-4 text-center font-mono"
            data-testid="macro-error"
          >
            <div>Could not load {seriesId}</div>
            <div className="text-charcoal-400 text-micro mt-1">{status.error}</div>
            <Button
              size="xs"
              variant="ghost"
              className="mt-3 text-amber-300 hover:text-amber-200"
              onClick={() => void loadSeries(provider, seriesId)}
              data-testid="macro-retry"
            >
              Retry
            </Button>
          </div>
        ) : status?.status === "ready" && status.series ? (
          <MacroChart series={status.series} />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
            <TrendingUp className="text-charcoal-600 size-8" />
            <p className="text-charcoal-300 text-caption font-mono">No series loaded</p>
            <p className="text-charcoal-500 text-micro font-mono">
              Browse Featured or search above to load a FRED, ECB, IMF, or World Bank time series.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
