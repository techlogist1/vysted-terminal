"use client";

import { useCallback, useState } from "react";
import { TrendingUp } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
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
          // Chart-shaped pulse skeleton + an honest meta line — never a bare
          // spinner standing in for the surface.
          <div className="flex h-full flex-col gap-3 p-3" data-testid="macro-skeleton">
            <div className="bg-charcoal-850 h-3 w-48 animate-pulse rounded-none" />
            <div className="bg-charcoal-850 min-h-0 flex-1 animate-pulse rounded-none" />
            <p className="text-charcoal-500 text-caption">Loading {seriesId}…</p>
          </div>
        ) : status?.status === "error" ? (
          <div data-testid="macro-error">
            <EmptyState
              icon={TrendingUp}
              headline={`Could not load ${seriesId}`}
              hint={status.error ?? "The macro provider request failed."}
              cta={{
                label: "Retry",
                primary: true,
                onClick: () => void loadSeries(provider, seriesId),
              }}
            />
          </div>
        ) : status?.status === "ready" && status.series ? (
          <MacroChart series={status.series} />
        ) : (
          <EmptyState
            icon={TrendingUp}
            headline="No series loaded"
            hint="Browse Featured or search above to load a FRED, ECB, IMF, or World Bank time series."
          />
        )}
      </div>
    </div>
  );
}
