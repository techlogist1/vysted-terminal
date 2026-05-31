/**
 * Agent-dock store — the agent's primary-column layout state (FR-001).
 *
 * The agent is a co-equal primary surface, not a bolted-on sidebar: it occupies
 * a dominant, resizable left column beside the dockview cockpit, and can collapse
 * to hand the full cockpit back. Width + collapsed ride the workspace blob so the
 * arrangement survives a relaunch.
 */

import { create } from "zustand";

export const AGENT_DOCK_MIN_WIDTH = 320;
export const AGENT_DOCK_MAX_WIDTH = 1200;
export const AGENT_DOCK_DEFAULT_WIDTH = 460;

interface AgentDockState {
  collapsed: boolean;
  /** Column width in pixels (clamped to [MIN, MAX]). */
  width: number;
  setCollapsed: (collapsed: boolean) => void;
  toggleCollapsed: () => void;
  setWidth: (width: number) => void;
}

function clampWidth(width: number): number {
  return Math.max(AGENT_DOCK_MIN_WIDTH, Math.min(width, AGENT_DOCK_MAX_WIDTH));
}

export const useAgentDockStore = create<AgentDockState>((set) => ({
  collapsed: false,
  width: AGENT_DOCK_DEFAULT_WIDTH,
  setCollapsed: (collapsed) => set({ collapsed }),
  toggleCollapsed: () => set((state) => ({ collapsed: !state.collapsed })),
  setWidth: (width) => set({ width: clampWidth(width) }),
}));

/** Test helper: reset the agent-dock store. */
export function resetAgentDockStoreForTests(): void {
  useAgentDockStore.setState({ collapsed: false, width: AGENT_DOCK_DEFAULT_WIDTH });
}
