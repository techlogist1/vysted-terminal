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
      ? "bg-positive"
      : tone === "warn"
        ? "bg-warning"
        : tone === "error"
          ? "bg-negative"
          : "bg-charcoal-500";

  const modeClass =
    state?.bot_mode === "live"
      ? "bg-negative/15 text-negative border-negative/40"
      : "bg-charcoal-800 text-charcoal-300 border-charcoal-700";

  return (
    <div
      role="status"
      aria-label="Tradesa V2 bot status"
      data-tone={tone}
      data-testid="tradesa-status-strip"
      className="border-charcoal-700 bg-charcoal-925/80 text-charcoal-300 flex shrink-0 items-center gap-2 border-b px-3 py-2 text-xs"
    >
      <span aria-hidden className={`inline-block size-2 rounded-full ${dotClass}`} />
      <span className={`rounded border px-1.5 py-0.5 font-medium ${toneClasses(tone)}`}>
        {label}
      </span>

      {state?.bot_mode && (
        <span
          aria-label={`Mode: ${state.bot_mode}`}
          className={`text-micro rounded border px-1.5 py-0.5 font-semibold tracking-wide uppercase ${modeClass}`}
        >
          {state.bot_mode}
        </span>
      )}

      {state?.heartbeat_age_s !== null && state?.heartbeat_age_s !== undefined && (
        <span className="text-charcoal-500">
          heartbeat {formatRelativeSeconds(state.heartbeat_age_s)}
        </span>
      )}

      {state?.kill_switch_engaged === true && (
        <span className="border-negative bg-negative/15 text-negative text-micro rounded border px-1.5 py-0.5 font-semibold tracking-wide uppercase">
          Kill Switch
        </span>
      )}

      {state?.message && status !== "healthy" && (
        <span className="text-charcoal-500 hidden truncate sm:inline-block">{state.message}</span>
      )}

      <button
        type="button"
        aria-label="Reload bot status"
        onClick={() => void refresh()}
        className="text-charcoal-400 hover:bg-charcoal-700 hover:text-charcoal-200 ml-auto inline-flex size-6 items-center justify-center rounded transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
      >
        <RefreshCw className="size-3.5" />
      </button>
    </div>
  );
}

export default TradesaBotStatusStrip;
