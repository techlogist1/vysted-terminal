"use client";

import { DockviewReact, type DockviewReadyEvent } from "dockview";
import {
  Component,
  Fragment,
  type FunctionComponent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
} from "react";

import { Button } from "@/components/ui/button";
import { collectPanelComponents } from "@/lib/module-registry";
import { applyPanelConstraints, enforceConstraintsAfterRestore } from "@/lib/panel-sizing";
import { autosaveLayout, loadWorkspace, restoreLastSessionOrDefault } from "@/lib/workspace";
import { useModulesStore } from "@/store/modules";
import { usePanelContextBus } from "@/store/panel-context";
import { useSettingsStore } from "@/store/settings";
import { useWorkspaceStore } from "@/store/workspace";

/**
 * Keeps one panel's render throw inside that panel (R15-LIFECYCLE-023): without
 * it React unmounts the whole root and the cockpit goes blank. "Reload panel"
 * remounts the panel's subtree; the error reaches the diagnostics log through
 * the root's `onCaughtError` (`main.tsx`).
 */
class PanelErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null; attempt: number }
> {
  state = { error: null as Error | null, attempt: 0 };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    const { error, attempt } = this.state;
    if (error === null) {
      return <Fragment key={attempt}>{this.props.children}</Fragment>;
    }
    return (
      <div role="alert" className="flex h-full flex-col items-start gap-3 p-4">
        <p className="text-charcoal-100 text-body">This panel crashed.</p>
        <p className="text-charcoal-400 text-caption break-all">{error.message}</p>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => this.setState({ error: null, attempt: attempt + 1 })}
          >
            Reload panel
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() =>
              void navigator.clipboard?.writeText(error.stack ?? error.message).catch(() => {})
            }
          >
            Copy error
          </Button>
        </div>
      </div>
    );
  }
}

/** The panel-component map with every panel behind its own error boundary. */
export function withPanelErrorBoundaries(
  components: Record<string, FunctionComponent>,
): Record<string, FunctionComponent> {
  return Object.fromEntries(
    Object.entries(components).map(([id, Panel]) => {
      function GuardedPanel(props: object) {
        return (
          <PanelErrorBoundary>
            <Panel {...props} />
          </PanelErrorBoundary>
        );
      }
      return [id, GuardedPanel];
    }),
  );
}

/**
 * The "Start with" preference (FR-038, R15-UI-087): after the launch restore
 * (which also restores the settings), a named start layout loads over the last
 * session through the ordinary layout loader. A layout that no longer loads
 * leaves the last session in place.
 */
export async function applyStartLayout(api: DockviewReadyEvent["api"]): Promise<void> {
  const name = useSettingsStore.getState().startLayout;
  if (name === null || useWorkspaceStore.getState().dockviewApi !== api) {
    return;
  }
  try {
    await loadWorkspace(name);
  } catch (error) {
    console.warn(`[workspace] start layout "${name}" did not load; kept the last session.`, error);
  }
}

/**
 * The dockview-backed panel host. Resolves each module's `PanelSpec.component`
 * id to its React component, hands the layout API to the workspace store, and
 * on launch restores the auto-saved "last session" cockpit (Track C) — falling
 * back to the bundled default layout (BLUEPRINT §5.1) when none exists. Layout
 * changes autosave (debounced inside `autosaveLayout`) so a customised cockpit
 * survives a relaunch.
 *
 * `DockviewReact` is only mounted once modules have registered, which keeps the
 * static-export build SSR-safe (the prerender pass sees the loading state).
 */
export function PanelHost() {
  const modules = useModulesStore((state) => state.modules);

  // Built from all modules so the map is stable after registration. Props-less
  // function components satisfy dockview's panel signature directly.
  const components = useMemo(
    () => withPanelErrorBoundaries(collectPanelComponents(modules)),
    [modules],
  );

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
    // Re-affirm constraints + grow any panel restored below its minimum, after
    // EVERY fromJSON (the boot restore and a named layout load alike) and once
    // the restore settles. Deferred until dockview's layout settles: setting
    // constraints mid-restore (before the gridview branch nodes exist) silently
    // no-ops. setTimeout, NOT requestAnimationFrame — rAF is throttled to a halt
    // on an unfocused/occluded WKWebView.
    let sweepTimer: ReturnType<typeof setTimeout> | null = null;
    const scheduleSweep = () => {
      if (sweepTimer !== null) {
        clearTimeout(sweepTimer);
      }
      sweepTimer = setTimeout(() => {
        sweepTimer = null;
        if (!mountedRef.current || useWorkspaceStore.getState().dockviewApi !== api) {
          return;
        }
        api.panels.forEach((panel) => enforceConstraintsAfterRestore(panel));
      }, 80);
    };
    const fromJSONSub = api.onDidLayoutFromJSON(scheduleSweep);
    const enabledPanelIds = new Set(
      useModulesStore
        .getState()
        .enabledPanels()
        .map((panel) => panel.id),
    );
    // Restore the last session (or default), THEN wire the layout autosave.
    // `autosaveLayout` itself is gated on the restore settling.
    void restoreLastSessionOrDefault(api, enabledPanelIds)
      .then(() => applyStartLayout(api))
      .finally(() => {
        // If StrictMode/HMR unmounted us or replaced the dockview api while the
        // restore awaited, this api is disposed — do not wire autosave to it (also
        // closes the subscription/timer leak when unmount lands mid-restore).
        if (!mountedRef.current || useWorkspaceStore.getState().dockviewApi !== api) {
          if (sweepTimer !== null) {
            clearTimeout(sweepTimer);
          }
          constraintsSub.dispose();
          fromJSONSub.dispose();
          return;
        }
        scheduleSweep();
        const subscription = api.onDidLayoutChange(() => autosaveLayout());
        // Track the focused panel into the shared context bus so the agent knows
        // what the user is "looking at" (FR-002/FR-007 — the deixis "this"/"it"
        // resolves to the focused panel; hand focus updates the agent's next turn).
        const focusSub = api.onDidActivePanelChange((panel) => {
          usePanelContextBus.getState().setFocusedSource(panel?.id ?? null);
        });
        cleanupRef.current = () => {
          if (sweepTimer !== null) {
            clearTimeout(sweepTimer);
          }
          subscription.dispose();
          focusSub.dispose();
          constraintsSub.dispose();
          fromJSONSub.dispose();
        };
      });
  }

  if (modules.length === 0) {
    return (
      <div className="bg-charcoal-950 flex h-full w-full items-center justify-center">
        <p className="text-charcoal-400 text-caption">Loading modules…</p>
      </div>
    );
  }

  return (
    <div className="dockview-theme-dark dockview-theme-vysted h-full w-full">
      <DockviewReact components={components} onReady={handleReady} />
    </div>
  );
}
