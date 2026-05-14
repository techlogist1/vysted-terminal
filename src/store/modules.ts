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
