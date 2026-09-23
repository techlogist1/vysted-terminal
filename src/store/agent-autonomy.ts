/**
 * Agent autonomy — how much the agent's cockpit-driving act-path asks before it
 * applies (Claude-Code-style). ORTHOGONAL to the four intent modes
 * (Ask/Edit/Build/Delegate in `agent-mode`): autonomy governs the CONFIRMATION
 * friction, not the intent.
 *
 *   - **ask**  (default) — every proposed change waits in the diff/accept gate.
 *   - **auto** — every host action (panel / chart / watchlist / data-write /
 *                settings) applies WITHOUT a per-action confirmation (still
 *                shown in the transcript as a record).
 *
 * Vysted has no brokerage connection, so no host action can place, stage or
 * simulate a trade in any mode; autonomy changes confirmation friction only.
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
