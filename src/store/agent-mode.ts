/**
 * Agent-mode store — the current four-mode intent (FR-003).
 *
 * Holds the active mode (Ask / Edit / Build / Delegate). The mode is shown in
 * the agent surface and switchable by keyboard (⌥1–⌥4). It rides the workspace
 * blob so a cockpit reopens in the mode the user left it in. The read-only vs
 * mutating enforcement is server-side (the sidecar filters Ask to read-only
 * tools); this store is the frontend's display + dispatch state.
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
