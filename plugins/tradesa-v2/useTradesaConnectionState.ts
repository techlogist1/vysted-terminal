/**
 * Tradesa V2 wrapper — connection-state hook.
 *
 * Every Tradesa V2 panel calls this hook to learn what UX state to
 * render. The hook:
 *
 *   1. Triggers an initial connection probe on mount (if no probe in the
 *      last 30s).
 *   2. Runs a 30s poll while the panel is mounted (matching
 *      POLL_CADENCE_MS.status).
 *   3. Returns the latest probe result + a typed status enum so panels
 *      can switch on a known set of states without inspecting the
 *      message string.
 *
 * The hook returns the same reference across renders when the underlying
 * state hasn't changed, so panel re-renders only happen on actual state
 * transitions (healthy → bot-offline → healthy etc.).
 */

import { useEffect, useMemo } from "react";

import { POLL_CADENCE_MS, useTradesaStore } from "./store";

import type { TradesaConnectionState, TradesaConnectionStatus } from "../../types/tradesa_v2";

export interface ConnectionStateHookResult {
  /** Current status — drives the panel UX switch. */
  status: TradesaConnectionStatus;
  /** Full state snapshot (or null until first probe lands). */
  state: TradesaConnectionState | null;
  /** Manually trigger a re-probe (panels expose this from the header strip). */
  refresh: () => Promise<void>;
}

/** Default state — used until the first probe completes. */
const CONNECTING_FALLBACK: TradesaConnectionState = {
  status: "connecting",
  message: "Probing Tradesa V2…",
  checked_at: 0,
  last_heartbeat_at: null,
  heartbeat_age_s: null,
  bot_mode: null,
  kill_switch_engaged: null,
};

/**
 * Subscribe to the connection-state slice of the Tradesa V2 store + run
 * a 30s poll while mounted. Returns the current state and a refresh()
 * callback the panel header strip can wire to a "retry" button.
 */
export function useTradesaConnectionState(): ConnectionStateHookResult {
  const connection = useTradesaStore((s) => s.connection);
  const refresh = useTradesaStore((s) => s.refreshConnection);

  useEffect(() => {
    // Trigger an immediate probe on mount if we have no recent reading.
    void refresh();
    const handle = window.setInterval(() => {
      void refresh();
    }, POLL_CADENCE_MS.status);
    return () => window.clearInterval(handle);
  }, [refresh]);

  return useMemo(() => {
    const state = connection ?? CONNECTING_FALLBACK;
    return {
      status: state.status,
      state: connection,
      refresh,
    };
  }, [connection, refresh]);
}
