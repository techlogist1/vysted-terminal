/**
 * Active-agent store — the single source of truth for which agent persona the
 * chat surface is focused on.
 *
 * Until R7 this was ChatSidebar-local useState, which made every external
 * "switch to agent X" affordance (the ⌘K agent rows, deep links) silently
 * dead: they could reveal the dock but not change the persona. The palette
 * now writes here and the chat surface subscribes.
 */

import { create } from "zustand";

export const DEFAULT_AGENT_ID = "copilot";

interface ActiveAgentState {
  /** Active agent id (a first-party or custom agent), or null for direct chat. */
  activeAgentId: string | null;
  setActiveAgent: (id: string | null) => void;
}

export const useActiveAgentStore = create<ActiveAgentState>((set) => ({
  activeAgentId: DEFAULT_AGENT_ID,
  setActiveAgent: (id) => set({ activeAgentId: id }),
}));
