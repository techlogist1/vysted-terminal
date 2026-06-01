/**
 * Agent autonomy — how much the agent's cockpit-driving act-path asks before it
 * applies (Claude-Code-style). ORTHOGONAL to the four intent modes
 * (Ask/Edit/Build/Delegate in `agent-mode`): autonomy governs the CONFIRMATION
 * friction, not the intent.
 *
 *   - **ask**  (default) — every proposed change waits in the diff/accept gate.
 *   - **auto** — UI/layout/chart/watchlist changes apply WITHOUT a per-action
 *                confirmation (still shown in the transcript as a record).
 *
 * HARD SAFETY LINE (never crossed in any mode): `auto` only skips the per-change
 * accept for the read-only-app host-actions (panel / chart / watchlist). It is
 * NEVER a path around §6.5 for an order — `propose_order` ALWAYS routes through
 * the confirm-before-place dialog, in every autonomy mode (enforced in
 * `proposed-changes` by excluding `kind === "order"` from the auto-apply path,
 * and again by `accept()` routing orders to the §6.5 dialog regardless). Brokers
 * stay read-only; autonomy changes friction, not safety enforcement.
 */

import { create } from "zustand";

/** The autonomy axis. `auto` is the "bypass per-action confirmation" mode. */
export type AgentAutonomy = "ask" | "auto";

const AUTONOMY_VALUES: readonly AgentAutonomy[] = ["ask", "auto"];

/** Type guard for restoring a persisted autonomy value (older/garbled blobs). */
export function isAgentAutonomy(value: unknown): value is AgentAutonomy {
  return typeof value === "string" && (AUTONOMY_VALUES as readonly string[]).includes(value);
}

interface AgentAutonomyState {
  autonomy: AgentAutonomy;
  setAutonomy: (autonomy: AgentAutonomy) => void;
}

export const useAgentAutonomyStore = create<AgentAutonomyState>((set) => ({
  autonomy: "ask",
  setAutonomy: (autonomy) => set({ autonomy }),
}));

/** Test helper: reset the autonomy store to the default ask gate. */
export function resetAgentAutonomyStoreForTests(): void {
  useAgentAutonomyStore.setState({ autonomy: "ask" });
}
