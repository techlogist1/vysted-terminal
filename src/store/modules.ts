import { create } from "zustand";

import {
  collectCommandHandlers,
  collectCommands,
  collectPanels,
  type VystedModule,
} from "@/lib/module-registry";
import type { CommandSpec, PanelSpec } from "../../types/plugin";

interface ModulesState {
  /** Every registered module, in registry order. */
  modules: VystedModule[];
  /** Enabled flag per module id. A disabled module contributes nothing. */
  enabled: Record<string, boolean>;
  /** Register the module registry. Called once at startup; all modules start enabled. */
  registerModules: (modules: VystedModule[]) => void;
  /**
   * Append more modules to the registry without replacing the existing list.
   * Used by the plugin runtime (Phase 2) to surface plugin-contributed panels
   * and commands as runtime-added modules. New modules default to enabled;
   * pre-existing `enabled[id]` entries are preserved.
   */
  appendModules: (modules: VystedModule[]) => void;
  /** Toggle a single module on or off. */
  setModuleEnabled: (id: string, enabled: boolean) => void;
  /** Replace the whole enabled map (used when loading a workspace). */
  setEnabledMap: (enabled: Record<string, boolean>) => void;
  /** Modules that are currently enabled. */
  enabledModules: () => VystedModule[];
  /** Panels contributed by enabled modules. */
  enabledPanels: () => PanelSpec[];
  /** Commands contributed by enabled modules. */
  enabledCommands: () => CommandSpec[];
  /** Look up the `PanelSpec` for a panel id (searches all registered modules). */
  findPanel: (panelId: string) => PanelSpec | undefined;
  /** Look up a control-plane command handler by command id (enabled modules only). */
  commandHandler: (commandId: string) => (() => void) | undefined;
}

/**
 * The module registry store. Phase 1.A-2 ships the registry and the
 * enable/disable model; Teammate D (Phase 1.B) enriches it with the settings
 * toggle UI and workspace-driven persistence of the `enabled` map.
 */
export const useModulesStore = create<ModulesState>((set, get) => ({
  modules: [],
  enabled: {},
  registerModules: (modules) =>
    set({
      modules,
      enabled: Object.fromEntries(modules.map((module) => [module.id, true])),
    }),
  appendModules: (modules) =>
    set((state) => {
      // Append-only: filter out ids already in the registry so a re-register
      // of the same plugin (dev-server reload, runtime re-discovery) is a
      // no-op rather than duplicating the entry.
      const existingIds = new Set(state.modules.map((module) => module.id));
      const fresh = modules.filter((module) => !existingIds.has(module.id));
      if (fresh.length === 0) {
        return state;
      }
      return {
        modules: [...state.modules, ...fresh],
        // Preserve any pre-set `enabled[id]` (e.g. a workspace that flipped a
        // plugin off); default new entries to enabled.
        enabled: {
          ...Object.fromEntries(fresh.map((module) => [module.id, true])),
          ...state.enabled,
        },
      };
    }),
  setModuleEnabled: (id, enabled) =>
    set((state) => ({ enabled: { ...state.enabled, [id]: enabled } })),
  setEnabledMap: (enabled) => set({ enabled }),
  enabledModules: () => {
    const { modules, enabled } = get();
    return modules.filter((module) => enabled[module.id] !== false);
  },
  enabledPanels: () => collectPanels(get().enabledModules()),
  enabledCommands: () => collectCommands(get().enabledModules()),
  findPanel: (panelId) => collectPanels(get().modules).find((panel) => panel.id === panelId),
  commandHandler: (commandId) => collectCommandHandlers(get().enabledModules())[commandId],
}));
