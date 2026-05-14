"use client";

import { DockviewReact, type DockviewReadyEvent } from "dockview";
import { useMemo } from "react";

import { collectPanelComponents } from "@/lib/module-registry";
import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * The dockview-backed panel host. Resolves each module's `PanelSpec.component`
 * id to its React component, hands the layout API to the workspace store, and
 * — for the Phase 1.A-2 scaffold — opens every enabled panel on ready. The
 * curated first-launch layout (BLUEPRINT §5.1) is wired in Phase 1.C.
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
    for (const panel of useModulesStore.getState().enabledPanels()) {
      event.api.addPanel({
        id: panel.id,
        component: panel.component,
        title: panel.title,
      });
    }
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
