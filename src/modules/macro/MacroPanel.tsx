"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { TrendingUp } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { useRetryOnSidecarReady } from "@/lib/use-sidecar-retry";
import { selectSeriesStatus, useMacroStore } from "@/store/macro";
import { usePanelContextBus } from "@/store/panel-context";

import type { MacroProvider } from "../../../types/macro";
import { MacroChart } from "./MacroChart";
import { MacroSeriesPicker } from "./MacroSeriesPicker";

const DEFAULT_PROVIDER: MacroProvider = "fred";
const DEFAULT_SERIES_ID = "DGS10";

/** What a provider tab opens on: the head of that provider's featured catalog,
 *  so a tab switch never asks one provider for another provider's id. */
const TAB_DEFAULT_SERIES: Record<MacroProvider, string> = {
  fred: DEFAULT_SERIES_ID,
  ecb: "FM.D.U2.EUR.4F.KR.MRR_FR.LEV",
  imf: "WEO/USA.NGDP_RPCH.A",
  "world-bank": "NY.GDP.PCAP.CD",
};

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

  // Once the user picks a tab or series, the mount default goes inert so a
  // reconnect re-fire never overrides an explicit choice.
  const userInteractedRef = useRef(false);

  // Load the default-on-mount series. The load auto-retries on a cold-boot
  // sidecar bind (and re-arms on reconnect) so a panel mounted before the
  // sidecar was ready self-heals instead of latching a permanent error.
  // `loadSeries` swallows its error into store state, so re-throw the kept
  // original error: the hook retries only a not-ready engine, never a keyless
  // 502. Only the mount default rides the hook (R15-UI-030).
  const loadDefault = useCallback(async () => {
    if (userInteractedRef.current) {
      return;
    }
    select(DEFAULT_PROVIDER, DEFAULT_SERIES_ID);
    await loadSeries(DEFAULT_PROVIDER, DEFAULT_SERIES_ID);
    const status = selectSeriesStatus(
      useMacroStore.getState(),
      DEFAULT_PROVIDER,
      DEFAULT_SERIES_ID,
    );
    if (status?.status === "error") {
      throw status.cause;
    }
  }, [loadSeries, select]);
  useRetryOnSidecarReady(loadDefault, []);

  // A user choice is one explicit request; a failure shows its Retry.
  const onSelect = (nextProvider: MacroProvider, nextSeriesId: string) => {
    userInteractedRef.current = true;
    setProvider(nextProvider);
    setSeriesId(nextSeriesId);
    select(nextProvider, nextSeriesId);
    void loadSeries(nextProvider, nextSeriesId);
  };
  const onProviderChange = (nextProvider: MacroProvider) =>
    onSelect(nextProvider, TAB_DEFAULT_SERIES[nextProvider]);

  // R15-AGENT-053: publish the active provider + series id so the copilot
  // can see what's on screen.
  const publishPanelContext = usePanelContextBus((s) => s.publish);
  const unregisterPanelContext = usePanelContextBus((s) => s.unregisterSource);

  useEffect(() => {
    publishPanelContext({
      source: "macro",
      kind: "snapshot",
      payload: { provider, seriesId },
      emittedAt: Date.now(),
    });
  }, [publishPanelContext, provider, seriesId]);

  useEffect(() => {
    return () => {
      unregisterPanelContext("macro");
    };
  }, [unregisterPanelContext]);

  return (
    <div
      className="bg-charcoal-900 text-charcoal-100 flex h-full flex-col"
      data-testid="macro-panel"
    >
      <MacroSeriesPicker
        provider={provider}
        onProviderChange={onProviderChange}
        onSelect={onSelect}
      />
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
