/**
 * Agent-mode store — the current two-mode intent + autonomy-axis model
 * (FR-003; see REBUILD_SPEC.md:179 for the collapse from the old four modes).
 *
 * Holds the active mode (Agent / Delegate, `types/agent-modes.ts`). Mode is
 * shown in the agent surface and switchable by keyboard (⌥1–⌥2). It rides the
 * workspace blob so a cockpit reopens in the mode the user left it in. Read vs
 * edit vs build is an inferred intent within "Agent" mode, classified and
 * gated server-side (`classify_intent` in the sidecar); autonomy (ask/auto) is
 * the orthogonal "how much confirmation" axis. This store is the frontend's
 * display + dispatch state for mode only.
 */

import { create } from "zustand";

import { DEFAULT_AGENT_MODE, isAgentMode, type AgentMode } from "../../types/agent-modes";

interface AgentModeState {
  mode: AgentMode;
  setMode: (mode: AgentMode) => void;
}

export const useAgentModeStore = create<AgentModeState>((set) => ({
  mode: DEFAULT_AGENT_MODE,
  setMode: (mode) => set({ mode: isAgentMode(mode) ? mode : DEFAULT_AGENT_MODE }),
}));

/** Test helper: reset the agent-mode store to its default. */
export function resetAgentModeStoreForTests(): void {
  useAgentModeStore.setState({ mode: DEFAULT_AGENT_MODE });
}
