"use client";

import { DockviewReact, type DockviewReadyEvent, type IDockviewPanel } from "dockview";
import { useEffect, useMemo, useRef } from "react";

import { collectPanelComponents } from "@/lib/module-registry";
import { autosaveLayout, restoreLastSessionOrDefault } from "@/lib/workspace";
import { useModulesStore } from "@/store/modules";
import { usePanelContextBus } from "@/store/panel-context";
import { useWorkspaceStore } from "@/store/workspace";

/** Debounce window for persisting the cockpit to the autosave slot. */
const AUTOSAVE_DEBOUNCE_MS = 1500;

/**
 * Host-side minimum panel sizes (px), keyed by `PanelSpec.component`. Enforced
 * via dockview's per-panel `setConstraints` so a squeezed cockpit can never
 * collapse a panel into overlapping/illegible content — content-heavy panels
 * (chart, settings, marketplace) get a wider floor; rail panels a tighter one.
 *
 * This lives in the HOST, not in `PanelSpec` (`types/plugin.ts` is Tier-1
 * LOCKED), so the plugin contract stays byte-for-byte untouched. Anything not
 * listed gets `DEFAULT_PANEL_MIN_SIZE`.
 */
const PANEL_MIN_SIZE: Record<string, { minimumWidth: number; minimumHeight: number }> = {
  "chart-panel": { minimumWidth: 360, minimumHeight: 220 },
  "equity-overview-panel": { minimumWidth: 340, minimumHeight: 200 },
  "watchlist-panel": { minimumWidth: 264, minimumHeight: 140 },
  "news-panel": { minimumWidth: 280, minimumHeight: 160 },
  "portfolio-panel": { minimumWidth: 300, minimumHeight: 160 },
};
const DEFAULT_PANEL_MIN_SIZE = { minimumWidth: 300, minimumHeight: 180 };

/** Clamp a panel's minimum size so it can't be dragged into overlap. */
function applyPanelConstraints(panel: IDockviewPanel): void {
  const size = PANEL_MIN_SIZE[panel.api.component] ?? DEFAULT_PANEL_MIN_SIZE;
  panel.api.setConstraints(size);
}

/**
 * Re-affirm constraints AND grow any panel a saved blob restored below its
 * minimum (dockview's `fromJSON` restores exact sizes, and constraints only
 * clamp *future* sash drags — they don't retroactively grow an under-min
 * panel). Run once after restore so a layout saved before min-sizes existed (or
 * a legacy sub-min blob) snaps up to a legible size.
 */
function enforceConstraintsAfterRestore(panel: IDockviewPanel): void {
  const size = PANEL_MIN_SIZE[panel.api.component] ?? DEFAULT_PANEL_MIN_SIZE;
  panel.api.setConstraints(size);
  if (panel.api.width > 0 && panel.api.width < size.minimumWidth) {
    panel.api.setSize({ width: size.minimumWidth });
  }
}

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
    // Dev-only handle for the test-automation rig (dead-stripped in the
    // production static export). Lets the rig inspect/drive the live layout.
    if (process.env.NODE_ENV !== "production") {
      (window as unknown as { __vystedDockview?: typeof api }).__vystedDockview = api;
    }
    // Clamp minimum sizes for every panel — those placed by the default layout,
    // restored from a saved blob, opened from the palette, or proposed by the
    // agent. Subscribing before the restore means restored/default panels are
    // caught as they're added; the post-restore sweep re-affirms the set.
    const constraintsSub = api.onDidAddPanel((panel) => applyPanelConstraints(panel));
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
        constraintsSub.dispose();
        return;
      }
      // Re-affirm constraints + grow any panel restored below its minimum.
      // Deferred until after dockview's initial layout settles: setting
      // constraints mid-restore (before the gridview branch nodes exist)
      // silently no-ops. We use setTimeout, NOT requestAnimationFrame — rAF is
      // throttled to a halt on an unfocused/occluded WKWebView, which would
      // leave the constraints unapplied whenever the window isn't frontmost.
      let constraintTimer: ReturnType<typeof setTimeout> | null = setTimeout(() => {
        constraintTimer = null;
        if (!mountedRef.current || useWorkspaceStore.getState().dockviewApi !== api) {
          return;
        }
        api.panels.forEach((panel) => enforceConstraintsAfterRestore(panel));
      }, 80);
      let timer: ReturnType<typeof setTimeout> | null = null;
      const subscription = api.onDidLayoutChange(() => {
        if (timer) {
          clearTimeout(timer);
        }
        timer = setTimeout(() => void autosaveLayout(), AUTOSAVE_DEBOUNCE_MS);
      });
      // Track the focused panel into the shared context bus so the agent knows
      // what the user is "looking at" (FR-002/FR-007 — the deixis "this"/"it"
      // resolves to the focused panel; hand focus updates the agent's next turn).
      const focusSub = api.onDidActivePanelChange((panel) => {
        usePanelContextBus.getState().setFocusedSource(panel?.id ?? null);
      });
      cleanupRef.current = () => {
        if (timer) {
          clearTimeout(timer);
        }
        if (constraintTimer !== null) {
          clearTimeout(constraintTimer);
        }
        subscription.dispose();
        focusSub.dispose();
        constraintsSub.dispose();
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
