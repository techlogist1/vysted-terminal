/**
 * Tradesa V2 wrapper — shared placeholder panel body (foundation only).
 *
 * v0.6.5 lead-foundation ships this so the seven panel components render
 * a graceful-degradation-aware shell before teammate dispatch. Teammate T
 * replaces each per-panel component (B5-B11) with the real
 * UX-grade implementation; this file gets deleted at integration.
 */

import { useTradesaConnectionState } from "../useTradesaConnectionState";
import { STATUS_LABEL } from "../store";

import { TradesaBotStatusStrip } from "./TradesaBotStatusStrip";

export interface PlaceholderPanelProps {
  panelTitle: string;
  panelDescription: string;
}

export function PlaceholderPanel({
  panelTitle,
  panelDescription,
}: PlaceholderPanelProps) {
  const { status, state } = useTradesaConnectionState();
  return (
    <div className="flex h-full flex-col bg-zinc-950 text-zinc-100">
      <TradesaBotStatusStrip />
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
        <h2 className="text-base font-semibold text-zinc-200">{panelTitle}</h2>
        <p className="max-w-md text-sm text-zinc-400">{panelDescription}</p>
        <p className="text-xs text-zinc-500">
          {STATUS_LABEL[status]}
          {state?.message ? ` — ${state.message}` : ""}
        </p>
        <p className="text-[11px] uppercase tracking-wide text-zinc-600">
          v0.6.5 placeholder — full UX lands in teammate-T deliverable
        </p>
      </div>
    </div>
  );
}
