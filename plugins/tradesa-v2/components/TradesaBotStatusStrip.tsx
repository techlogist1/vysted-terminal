/**
 * Tradesa V2 wrapper — bot status header strip.
 *
 * Renders the always-visible bot-status banner at the top of every Tradesa
 * V2 panel. Surfaces the connection-status tone, mode badge (paper/live),
 * heartbeat age (as a relative-time label, not raw seconds), kill-switch
 * indicator, and a small reload button that re-runs the status probe.
 *
 * The strip is rendered inside `PanelShell` (the central state-branch
 * container) — individual panels never mount it directly.
 */

import { RefreshCw } from "lucide-react";

import { useTradesaConnectionState } from "../useTradesaConnectionState";
import { STATUS_LABEL, STATUS_TONE } from "../store";

import { formatRelativeSeconds, toneClasses } from "./_utils";

export function TradesaBotStatusStrip() {
  const { status, state, refresh } = useTradesaConnectionState();
  const tone = STATUS_TONE[status];
  const label = STATUS_LABEL[status];

  const dotClass =
    tone === "ok"
      ? "bg-emerald-400"
      : tone === "warn"
        ? "bg-amber-400"
        : tone === "error"
          ? "bg-red-400"
          : "bg-zinc-500";

  const modeClass =
    state?.bot_mode === "live"
      ? "bg-red-900/60 text-red-200 border-red-800"
      : "bg-blue-900/60 text-blue-200 border-blue-800";

  return (
    <div
      role="status"
      aria-label="Tradesa V2 bot status"
      data-tone={tone}
      data-testid="tradesa-status-strip"
      className="flex shrink-0 items-center gap-2 border-b border-zinc-800 bg-zinc-950/80 px-3 py-2 text-xs text-zinc-300"
    >
      <span aria-hidden className={`inline-block size-2 rounded-full ${dotClass}`} />
      <span className={`rounded border px-1.5 py-0.5 font-medium ${toneClasses(tone)}`}>
        {label}
      </span>

      {state?.bot_mode && (
        <span
          aria-label={`Mode: ${state.bot_mode}`}
          className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase ${modeClass}`}
        >
          {state.bot_mode}
        </span>
      )}

      {state?.heartbeat_age_s !== null && state?.heartbeat_age_s !== undefined && (
        <span className="text-zinc-500">
          heartbeat {formatRelativeSeconds(state.heartbeat_age_s)}
        </span>
      )}

      {state?.kill_switch_engaged === true && (
        <span className="rounded border border-red-700 bg-red-900/60 px-1.5 py-0.5 text-[10px] font-semibold tracking-wide text-red-100 uppercase">
          Kill Switch
        </span>
      )}

      {state?.message && status !== "healthy" && (
        <span className="hidden truncate text-zinc-500 sm:inline-block">{state.message}</span>
      )}

      <button
        type="button"
        aria-label="Reload bot status"
        onClick={() => void refresh()}
        className="ml-auto inline-flex size-6 items-center justify-center rounded text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
      >
        <RefreshCw className="size-3.5" />
      </button>
    </div>
  );
}

export default TradesaBotStatusStrip;
