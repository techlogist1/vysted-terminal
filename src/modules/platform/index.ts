import { SettingsPanel } from "@/components/SettingsPanel";
import type { VystedModule } from "@/lib/module-registry";
import { useWorkspaceDialog } from "./workspace-dialog-store";

/**
 * Platform module — settings + workspace persistence. Owned by Teammate D
 * (Phase 1.B).
 *
 * Contributes the Settings panel (per-module enable/disable) and three cmd+K
 * commands: "Open Settings" opens the panel; "Save Workspace" / "Load Workspace"
 * are control-plane commands whose handlers open `WorkspaceDialog` to collect a
 * name. The handlers only flip the dialog store — the actual save/load goes
 * through `src/lib/workspace.ts` once the user confirms.
 *
 * This module is intentionally not user-disableable: Settings is the only way to
 * re-enable a module, so `SettingsPanel` locks the `platform` toggle on. The
 * module id, the `settings-panel` component id, and the `settings` panel id are
 * kept stable.
 */

/** Stable id of the platform module — exported so `SettingsPanel` can lock its toggle. */
export const PLATFORM_MODULE_ID = "platform";

export const platformModule: VystedModule = {
  id: PLATFORM_MODULE_ID,
  title: "Platform",
  panels: [
    {
      id: "settings",
      title: "Settings",
      icon: "settings",
      component: "settings-panel",
      singleton: true,
      defaultSize: { w: 4, h: 5 },
    },
  ],
  commands: [
    {
      id: "platform.open-settings",
      trigger: "settings",
      title: "Open Settings",
      description: "Enable or disable modules",
      icon: "settings",
      opensPanel: "settings",
    },
    {
      id: "platform.save-workspace",
      trigger: "save workspace",
      title: "Save Workspace",
      description: "Save the current panel layout and enabled modules",
      icon: "save",
      commandId: "platform.save-workspace",
    },
    {
      id: "platform.load-workspace",
      trigger: "load workspace",
      title: "Load Workspace",
      description: "Restore a saved workspace",
      icon: "folder-open",
      commandId: "platform.load-workspace",
    },
  ],
  panelComponents: {
    "settings-panel": SettingsPanel,
  },
  commandHandlers: {
    "platform.save-workspace": () => useWorkspaceDialog.getState().openSave(),
    "platform.load-workspace": () => useWorkspaceDialog.getState().openLoad(),
  },
};
