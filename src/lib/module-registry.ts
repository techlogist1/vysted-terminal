import type { FunctionComponent } from "react";

import type { CommandSpec, PanelSpec } from "../../types/plugin";

/**
 * A first-party module bundles panels, commands, and the React components that
 * render its panels. Phase 1's five data panels each ship as a module, plus a
 * "platform" module for workspace/settings commands.
 *
 * Modules are the in-app analogue of the `VystedPlugin` panel/command
 * capabilities — they reuse `PanelSpec` / `CommandSpec` from the frozen plugin
 * contract in `types/plugin.ts` and add the host-side concerns the serializable
 * contract deliberately omits: the React components and command handlers.
 */
export interface VystedModule {
  /** Stable module id, e.g. "chart", "watchlist", "platform". */
  id: string;
  /** Display name shown in the settings module-toggle list. */
  title: string;
  /** Panels this module contributes. */
  panels: PanelSpec[];
  /** cmd+K commands this module contributes. */
  commands: CommandSpec[];
  /**
   * Maps each `PanelSpec.component` id to the React component that renders it.
   * Components are plain props-less function components — the panel host adapts
   * them to dockview's panel signature.
   */
  panelComponents: Record<string, FunctionComponent>;
  /**
   * Handlers for this module's control-plane commands, keyed by
   * `CommandSpec.commandId`. Commands that only open a panel use
   * `CommandSpec.opensPanel` instead and need no handler.
   */
  commandHandlers?: Record<string, () => void>;
}

/** Flatten the panels contributed by a set of modules. */
export function collectPanels(modules: VystedModule[]): PanelSpec[] {
  return modules.flatMap((mod) => mod.panels);
}

/** Flatten the commands contributed by a set of modules. */
export function collectCommands(modules: VystedModule[]): CommandSpec[] {
  return modules.flatMap((mod) => mod.commands);
}

/** Build the panel-id → React component map for the panel host. */
export function collectPanelComponents(modules: VystedModule[]): Record<string, FunctionComponent> {
  const map: Record<string, FunctionComponent> = {};
  for (const mod of modules) {
    Object.assign(map, mod.panelComponents);
  }
  return map;
}

/** Build the commandId → handler map across a set of modules. */
export function collectCommandHandlers(modules: VystedModule[]): Record<string, () => void> {
  const map: Record<string, () => void> = {};
  for (const mod of modules) {
    if (mod.commandHandlers) {
      Object.assign(map, mod.commandHandlers);
    }
  }
  return map;
}
