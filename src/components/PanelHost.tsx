"use client";

import { DockviewReact, type DockviewReadyEvent } from "dockview";
import { useEffect, useMemo, useRef } from "react";

import { collectPanelComponents } from "@/lib/module-registry";
import { autosaveLayout, restoreLastSessionOrDefault } from "@/lib/workspace";
import { useModulesStore } from "@/store/modules";
import { useWorkspaceStore } from "@/store/workspace";

/** Debounce window for persisting the cockpit to the autosave slot. */
const AUTOSAVE_DEBOUNCE_MS = 1500;

/**
 * The dockview-backed panel host. Resolves each module's `PanelSpec.component`
 * id to its React component, hands the layout API to the workspace store, and
 * on launch restores the auto-saved "last session" cockpit (Track C) — falling
 * back to the bundled default layout (BLUEPRINT §5.1) when none exists. Layout
 * changes are debounce-autosaved so a customised cockpit survives a relaunch.
 *
 * `DockviewReact` is only mounted once modules have registered, which keeps the
 * static-export build SSR-safe (the prerender pass sees the loading state).
 */
export function PanelHost() {
  const modules = useModulesStore((state) => state.modules);

  // Built from all modules so the map is stable after registration. Props-less
  // function components satisfy dockview's panel signature directly.
  const components = useMemo(() => collectPanelComponents(modules), [modules]);

  // Cleanup for the autosave subscription, set once the layout is ready.
  const cleanupRef = useRef<(() => void) | null>(null);
  // Whether this component is currently mounted. Set true on (re)mount, false on
  // unmount — combined with the dockview-api-identity check below, it stops an
  // in-flight async restore from a disposed mount (StrictMode/HMR) from wiring
  // autosave to (or mutating) a disposed dockview api. Written only (never read)
  // in cleanup, so it sidesteps the stale-ref-in-cleanup lint heuristic.
  const mountedRef = useRef(false);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cleanupRef.current?.();
      cleanupRef.current = null;
    };
  }, []);

  function handleReady(event: DockviewReadyEvent) {
    const api = event.api;
    useWorkspaceStore.getState().setDockviewApi(api);
    const enabledPanelIds = new Set(
      useModulesStore
        .getState()
        .enabledPanels()
        .map((panel) => panel.id),
    );
    // Restore the last session (or default), THEN begin autosaving — so the
    // first autosave reflects a genuine user change, not the restore itself.
    void restoreLastSessionOrDefault(api, enabledPanelIds).finally(() => {
      // If StrictMode/HMR unmounted us or replaced the dockview api while the
      // restore awaited, this api is disposed — do not wire autosave to it (also
      // closes the subscription/timer leak when unmount lands mid-restore).
      if (!mountedRef.current || useWorkspaceStore.getState().dockviewApi !== api) {
        return;
      }
      let timer: ReturnType<typeof setTimeout> | null = null;
      const subscription = api.onDidLayoutChange(() => {
        if (timer) {
          clearTimeout(timer);
        }
        timer = setTimeout(() => void autosaveLayout(), AUTOSAVE_DEBOUNCE_MS);
      });
      cleanupRef.current = () => {
        if (timer) {
          clearTimeout(timer);
        }
        subscription.dispose();
      };
    });
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
