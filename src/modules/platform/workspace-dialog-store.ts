import { create } from "zustand";

/**
 * Which workspace operation the dialog is collecting a name for. `null` means
 * the dialog is closed.
 */
export type WorkspaceDialogMode = "save" | "load" | null;

interface WorkspaceDialogState {
  /** Active dialog mode, or `null` when closed. */
  mode: WorkspaceDialogMode;
  /** Open the dialog in save mode (prompts for a name to save under). */
  openSave: () => void;
  /** Open the dialog in load mode (lists saved workspaces to pick from). */
  openLoad: () => void;
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
  close: () => set({ mode: null }),
}));
