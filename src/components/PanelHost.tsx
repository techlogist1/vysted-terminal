"use client";

import { DockviewReact, type DockviewReadyEvent } from "dockview";
import { useMemo } from "react";

import { applyDefaultLayout } from "@/config/default-layout";
import { collectPanelComponents } from "@/lib/module-registry";
import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * The dockview-backed panel host. Resolves each module's `PanelSpec.component`
 * id to its React component, hands the layout API to the workspace store, and
 * applies the first-launch layout (BLUEPRINT §5.1) on ready.
 *
 * `DockviewReact` is only mounted once modules have registered, which keeps the
 * static-export build SSR-safe (the prerender pass sees the loading state).
 */
export function PanelHost() {
  const modules = useModulesStore((state) => state.modules);

  // Built from all modules so the map is stable after registration. Props-less
  // function components satisfy dockview's panel signature directly.
  const components = useMemo(() => collectPanelComponents(modules), [modules]);

  function handleReady(event: DockviewReadyEvent) {
    useWorkspaceStore.getState().setDockviewApi(event.api);
    const enabledPanelIds = new Set(
      useModulesStore
        .getState()
        .enabledPanels()
        .map((panel) => panel.id),
    );
    applyDefaultLayout(event.api, enabledPanelIds);
  }

  if (modules.length === 0) {
    return (
      <div className="bg-charcoal-950 flex h-full w-full items-center justify-center">
        <p className="text-charcoal-400 font-mono text-xs">Loading modules…</p>
      </div>
    );
  }

  return (
    <div className="dockview-theme-dark dockview-theme-vysted h-full w-full">
      <DockviewReact components={components} onReady={handleReady} />
    </div>
  );
}
