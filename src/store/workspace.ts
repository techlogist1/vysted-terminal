import type { DockviewApi } from "dockview";
import { create } from "zustand";

import { useModulesStore } from "@/store/modules";

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
    if (spec.singleton !== false) {
      // Singleton panel: focus the open instance, otherwise add a fresh one.
      const existing = api.getPanel(panelId);
      if (existing) {
        existing.api.setActive();
        return;
      }
      api.addPanel({ id: spec.id, component: spec.component, title: spec.title });
      return;
    }
    // Non-singleton (Phase 2 chart): mint a unique panel id so multiple
    // instances can coexist and dockview's id-uniqueness invariant holds.
    const uniqueId = `${spec.id}-${Date.now().toString(36)}-${Math.random()
      .toString(36)
      .slice(2, 6)}`;
    api.addPanel({ id: uniqueId, component: spec.component, title: spec.title });
  },
  closePanel: (panelId) => {
    get().dockviewApi?.getPanel(panelId)?.api.close();
  },
}));
