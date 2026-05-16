/**
 * Tradesa V2 wrapper — bot status header strip (PLACEHOLDER, replaced by teammate T).
 *
 * Renders the always-visible bot-status banner at the top of every Tradesa
 * V2 panel. v0.6.5 lead-foundation ships this placeholder so the panel
 * imports resolve before teammate dispatch; the real strip lands in
 * deliverable B3 of the v0.6.5 plan.
 */

import { useTradesaConnectionState } from "../useTradesaConnectionState";
import { STATUS_LABEL, STATUS_TONE } from "../store";

export function TradesaBotStatusStrip() {
  const { status, state } = useTradesaConnectionState();
  const tone = STATUS_TONE[status];
  const label = STATUS_LABEL[status];
  return (
    <div
      role="status"
      aria-label="Tradesa V2 bot status"
      data-tone={tone}
      className="flex items-center gap-3 border-b border-zinc-800 bg-zinc-950/80 px-3 py-2 text-xs text-zinc-300"
    >
      <span className="font-medium">{label}</span>
      {state?.bot_mode && (
        <span className="rounded bg-zinc-800 px-1.5 py-0.5 uppercase tracking-wide">
          {state.bot_mode}
        </span>
      )}
      {state?.heartbeat_age_s !== null && state?.heartbeat_age_s !== undefined && (
        <span className="text-zinc-500">heartbeat {Math.round(state.heartbeat_age_s)}s ago</span>
      )}
      {state?.kill_switch_engaged === true && (
        <span className="rounded bg-red-900/50 px-1.5 py-0.5 text-red-200">KILL SWITCH</span>
      )}
    </div>
  );
}

export default TradesaBotStatusStrip;
