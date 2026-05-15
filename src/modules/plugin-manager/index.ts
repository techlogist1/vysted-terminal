import type { VystedModule } from "@/lib/module-registry";

import { PluginManagerPanel } from "@/components/PluginManagerPanel";

/**
 * Plugin Manager module — exposes the runtime supervisor's view of every
 * loaded plugin (state, health history, metadata, enable/disable) as a
 * dockview panel reachable via cmd+K (`/plugins`).
 *
 * The host bootstraps a `PluginRuntime` once at startup and attaches it to
 * `usePluginsStore` via `attachRuntime()`; this module's panel is the
 * React-facing projection of that store.
 */
export const pluginManagerModule: VystedModule = {
  id: "plugin-manager",
  title: "Plugin Manager",
  panels: [
    {
      id: "plugin-manager",
      title: "Plugins",
      icon: "puzzle",
      component: "plugin-manager-panel",
      singleton: true,
      defaultSize: { w: 4, h: 5 },
    },
  ],
  commands: [
    {
      id: "plugin-manager.open",
      trigger: "plugins",
      title: "Open Plugin Manager",
      description: "Loaded plugins, lifecycle state, and health history",
      icon: "puzzle",
      opensPanel: "plugin-manager",
    },
  ],
  panelComponents: {
    "plugin-manager-panel": PluginManagerPanel,
  },
};
