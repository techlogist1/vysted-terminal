import { create } from "zustand";

/**
 * Which workspace operation the dialog is collecting input for. `null` means the
 * dialog is closed. `"research-space"` prompts for a ticker to spin up a per-stock
 * research space (chart + overview + brief + scoped notes, saved as a workspace).
 */
export type WorkspaceDialogMode = "save" | "load" | "research-space" | null;

interface WorkspaceDialogState {
  /** Active dialog mode, or `null` when closed. */
  mode: WorkspaceDialogMode;
  /** Open the dialog in save mode (prompts for a name to save under). */
  openSave: () => void;
  /** Open the dialog in load mode (lists saved workspaces to pick from). */
  openLoad: () => void;
  /** Open the dialog to create a per-stock research space (prompts for a ticker). */
  openResearchSpace: () => void;
  /** Close the dialog. */
  close: () => void;
}

/**
 * UI state for the workspace save/load dialog. The platform module's cmd+K
 * command handlers are plain `() => void` functions, so they cannot render a
 * dialog directly — they flip this store instead, and `WorkspaceDialog`
 * (mounted once in `page.tsx`) renders in response.
 */
export const useWorkspaceDialog = create<WorkspaceDialogState>((set) => ({
  mode: null,
  openSave: () => set({ mode: "save" }),
  openLoad: () => set({ mode: "load" }),
  openResearchSpace: () => set({ mode: "research-space" }),
  close: () => set({ mode: null }),
}));
