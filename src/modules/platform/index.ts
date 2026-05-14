import { createPlaceholderPanel } from "@/components/PlaceholderPanel";
import type { VystedModule } from "@/lib/module-registry";

/**
 * Platform module — placeholder. Owned by Teammate D (Phase 1.B).
 *
 * Teammate D replaces `panelComponents["settings-panel"]` with the real settings
 * panel (per-module enable/disable) and adds workspace save/load commands —
 * these use `commandId` + `commandHandlers` (not `opensPanel`). Note: the
 * platform module should not be user-disableable, since Settings is how modules
 * are re-enabled — Teammate D enforces that in the toggle UI. Keep the module
 * id, the `settings-panel` component id, and the `settings` panel id stable.
 */
export const platformModule: VystedModule = {
  id: "platform",
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
  ],
  panelComponents: {
    "settings-panel": createPlaceholderPanel("Settings"),
  },
};
