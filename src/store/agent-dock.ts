/**
 * Agent-dock store — the agent's primary-column layout state (FR-001).
 *
 * The agent is a co-equal primary surface, not a bolted-on sidebar: it occupies
 * a dominant, resizable left column beside the dockview cockpit, can collapse
 * to hand the full cockpit back, or maximize to take the full cockpit itself.
 * Width, collapsed and maximized ride the workspace blob so the arrangement
 * survives a relaunch.
 */

import { create } from "zustand";

export const AGENT_DOCK_MIN_WIDTH = 280;
export const AGENT_DOCK_MAX_WIDTH = 1200;
export const AGENT_DOCK_DEFAULT_WIDTH = 310;

interface AgentDockState {
  collapsed: boolean;
  /** Column width in pixels (clamped to [MIN, MAX]). Untouched while maximized,
   *  so it is the width un-maximizing restores. */
  width: number;
  /** The dock fills the whole cockpit (the only state the width clamp does not
   *  apply to); the dockview host stays mounted, hidden. */
  maximized: boolean;
  setCollapsed: (collapsed: boolean) => void;
  toggleCollapsed: () => void;
  setWidth: (width: number) => void;
  setMaximized: (maximized: boolean) => void;
  toggleMaximized: () => void;
}

function clampWidth(width: number): number {
  return Math.max(AGENT_DOCK_MIN_WIDTH, Math.min(width, AGENT_DOCK_MAX_WIDTH));
}

export const useAgentDockStore = create<AgentDockState>((set) => ({
  collapsed: false,
  width: AGENT_DOCK_DEFAULT_WIDTH,
  maximized: false,
  setCollapsed: (collapsed) => set({ collapsed }),
  toggleCollapsed: () => set((state) => ({ collapsed: !state.collapsed })),
  setWidth: (width) => set({ width: clampWidth(width) }),
  setMaximized: (maximized) => set({ maximized }),
  toggleMaximized: () => set((state) => ({ maximized: !state.maximized })),
}));

/** Test helper: reset the agent-dock store. */
export function resetAgentDockStoreForTests(): void {
  useAgentDockStore.setState({
    collapsed: false,
    width: AGENT_DOCK_DEFAULT_WIDTH,
    maximized: false,
  });
}
