import type { DockviewApi, IDockviewPanel } from "dockview";
import { create } from "zustand";

import { applyDefaultLayout } from "@/config/default-layout";
import { useChartDrawingsStore } from "@/store/chart-drawings";
import { useModulesStore } from "@/store/modules";

/**
 * Grid-units → px seed for `PanelSpec.defaultSize`. dockview redistributes
 * sizes proportionally as panels are added, so this is a starting ratio, not a
 * hard pixel lock — it just makes the contract's `defaultSize` field meaningful
 * (it was previously dead metadata that every module filled in with no effect).
 */
const GRID_UNIT_PX = 64;

/**
 * Reserved layout name for the auto-saved "last session" cockpit (Track C).
 * Persisted to the sidecar like any layout, but hidden from the user-facing
 * layout list and restored automatically on launch so a customised cockpit
 * survives a relaunch.
 */
export const AUTOSAVE_LAYOUT_NAME = "__autosave__";

/** Reserved layout names are internal slots, hidden from the Layouts UI. */
export function isReservedLayoutName(name: string): boolean {
  return name.startsWith("__");
}

interface WorkspaceState {
  /** Name of the active workspace. */
  name: string;
  /** The dockview layout API, set by `PanelHost` once the layout mounts. */
  dockviewApi: DockviewApi | null;
  setName: (name: string) => void;
  setDockviewApi: (api: DockviewApi | null) => void;
  /** Open a panel by its `PanelSpec` id, or focus it if already open. */
  openPanel: (panelId: string) => void;
  /** Close a panel by id, if open. */
  closePanel: (panelId: string) => void;
  /** Clear the cockpit and re-apply the bundled default layout. */
  resetToDefaultLayout: () => void;
}

/**
 * Workspace store — the active workspace name and a handle to the dockview
 * layout. Phase 1.A-2 ships the open/close/focus plumbing; Teammate D
 * (Phase 1.B) enriches it with `.vysted-workspace` save/load that serialises the
 * dockview layout and the modules `enabled` map.
 */
export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  name: "default",
  dockviewApi: null,
  setName: (name) => set({ name }),
  setDockviewApi: (dockviewApi) => set({ dockviewApi }),
  openPanel: (panelId) => {
    const api = get().dockviewApi;
    if (!api) {
      return;
    }
    const spec = useModulesStore.getState().findPanel(panelId);
    if (!spec) {
      return;
    }
    // Seed the opened panel's size from the spec's declared defaultSize (a
    // proportional starting ratio; dockview redistributes from there).
    const applySize = (panel: IDockviewPanel) => {
      if (!spec.defaultSize) {
        return;
      }
      panel.api.setSize({
        width: spec.defaultSize.w * GRID_UNIT_PX,
        height: spec.defaultSize.h * GRID_UNIT_PX,
      });
    };
    if (spec.singleton !== false) {
      // Singleton panel: focus the open instance, otherwise add a fresh one.
      const existing = api.getPanel(panelId);
      if (existing) {
        existing.api.setActive();
        return;
      }
      applySize(api.addPanel({ id: spec.id, component: spec.component, title: spec.title }));
      return;
    }
    // Non-singleton (Phase 2 chart): mint a unique panel id so multiple
    // instances can coexist and dockview's id-uniqueness invariant holds.
    const uniqueId = `${spec.id}-${Date.now().toString(36)}-${Math.random()
      .toString(36)
      .slice(2, 6)}`;
    applySize(api.addPanel({ id: uniqueId, component: spec.component, title: spec.title }));
  },
  closePanel: (panelId) => {
    get().dockviewApi?.getPanel(panelId)?.api.close();
  },
  resetToDefaultLayout: () => {
    const api = get().dockviewApi;
    if (!api) {
      return;
    }
    // A true factory reset: re-enable every module (the default state — modules
    // are enabled unless explicitly `false`) so a prior workspace that disabled
    // a module doesn't leave its panel missing from the "default" layout, and
    // drop stale chart drawings (regression-95 BUG-2).
    useModulesStore.getState().setEnabledMap({});
    useChartDrawingsStore.getState().replaceAll({ byPanel: {} });
    api.clear();
    const enabledPanelIds = new Set(
      useModulesStore
        .getState()
        .enabledPanels()
        .map((panel) => panel.id),
    );
    applyDefaultLayout(api, enabledPanelIds);
    set({ name: "default" });
  },
}));
