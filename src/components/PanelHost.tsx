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
  // --- Default-cockpit panels ---
  // chart: the always-present indicator selector (max-h-56 = 224px) + two
  // flex-wrap toolbars (~80px) sit BELOW the chart canvas; at the old 220px
  // floor the `flex-1` canvas collapsed to 0px and lightweight-charts rendered
  // a 0-height surface. 480px = ~200px usable canvas + ~80px toolbars + the
  // 200px indicator-section floor, so the canvas keeps a legible height.
  "chart-panel": { minimumWidth: 360, minimumHeight: 480 },
  "equity-overview-panel": { minimumWidth: 340, minimumHeight: 200 },
  "watchlist-panel": { minimumWidth: 264, minimumHeight: 140 },
  "news-panel": { minimumWidth: 280, minimumHeight: 160 },
  // portfolio: a named-portfolio header (~48px) + the flex-wrap add-holding form
  // (~150px) sit above the holdings table / empty state, so a low floor squeezed
  // the content (and the empty-state CTA) into a sliver in the default rail.
  "portfolio-panel": { minimumWidth: 520, minimumHeight: 320 },

  // --- Wide content panels (fixed-width aside / canvas + a results floor) ---
  // Each width = the panel's hardcoded fixed column(s) + a usable second pane,
  // so the `flex-1` results/canvas section never collapses to 0 at the min.
  "node-editor-panel": { minimumWidth: 560, minimumHeight: 320 }, // palette 224 + props 256 + 80 canvas
  "option-pricer-panel": { minimumWidth: 640, minimumHeight: 320 }, // w-80 aside (320) + 320 results
  "bond-pricer-panel": { minimumWidth: 640, minimumHeight: 300 }, // w-80 aside (320) + 320 results
  "yield-curve-panel": { minimumWidth: 640, minimumHeight: 360 }, // w-80 aside (320) + 320 chart
  "greeks-dashboard-panel": { minimumWidth: 600, minimumHeight: 280 }, // w-72 aside (288) + 312 heatmap
  "backtest-panel": { minimumWidth: 680, minimumHeight: 340 }, // w-72 aside (288) + 392 results
  "screener-panel": { minimumWidth: 580, minimumHeight: 360 }, // 384px criteria grid + padding + remove
  "sec-filings-panel": { minimumWidth: 480, minimumHeight: 300 },
  "earnings-calendar-panel": { minimumWidth: 560, minimumHeight: 240 },
  "analyst-ratings-panel": { minimumWidth: 420, minimumHeight: 260 },
  "macro-panel": { minimumWidth: 400, minimumHeight: 300 },
  "audit-log-viewer": { minimumWidth: 440, minimumHeight: 200 },

  // --- Primary-content / config panels (opened from the palette) ---
  "settings-panel": { minimumWidth: 480, minimumHeight: 300 },
  "marketplace-panel": { minimumWidth: 380, minimumHeight: 300 },
  "agent-builder-panel": { minimumWidth: 380, minimumHeight: 280 },
  "plugin-manager-panel": { minimumWidth: 340, minimumHeight: 200 },

  // --- Rail / narrow companion panels ---
  // chat-sidebar is a narrow companion; the generic 300px default snaps it 56%
  // wider than its declared defaultSize, so give it a tighter, usable floor.
  // 280px matches the new AGENT_DOCK_MIN_WIDTH so the composer never gets squeezed
  // when the dock is dragged to its minimum.
  "chat-sidebar": { minimumWidth: 280, minimumHeight: 160 },
  "broker-connect-panel": { minimumWidth: 320, minimumHeight: 200 },
  "broker-order-entry": { minimumWidth: 280, minimumHeight: 200 },
};
const DEFAULT_PANEL_MIN_SIZE = { minimumWidth: 300, minimumHeight: 180 };

/** Clamp a panel's minimum size so it can't be dragged into overlap. Guarded:
 *  a dockview throw on one panel (e.g. a disposed/edge state) must not abort a
 *  whole-layout sweep, leaving later panels unconstrained. */
function applyPanelConstraints(panel: IDockviewPanel): void {
  try {
    const size = PANEL_MIN_SIZE[panel.api.component] ?? DEFAULT_PANEL_MIN_SIZE;
    panel.api.setConstraints(size);
  } catch {
    // best-effort; a single panel failing to clamp must not break the others.
  }
}

/**
 * Re-affirm constraints AND grow any panel a saved blob restored below its
 * minimum (dockview's `fromJSON` restores exact sizes, and constraints only
 * clamp *future* sash drags — they don't retroactively grow an under-min
 * panel). Run once after restore so a layout saved before min-sizes existed (or
 * a legacy sub-min blob) snaps up to a legible size.
 */
function enforceConstraintsAfterRestore(panel: IDockviewPanel): void {
  try {
    const size = PANEL_MIN_SIZE[panel.api.component] ?? DEFAULT_PANEL_MIN_SIZE;
    panel.api.setConstraints(size);
    // Grow a panel restored below its minimum on BOTH axes — `setConstraints`
    // only clamps future sash drags, it doesn't retroactively grow an under-min
    // panel a saved blob restored too small (e.g. a blob saved before min-sizes
    // existed, or one saved while the panel was squeezed).
    if (panel.api.width > 0 && panel.api.width < size.minimumWidth) {
      panel.api.setSize({ width: size.minimumWidth });
    }
    if (panel.api.height > 0 && panel.api.height < size.minimumHeight) {
      panel.api.setSize({ height: size.minimumHeight });
    }
  } catch {
    // best-effort; one panel throwing must not abort the post-restore sweep.
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
