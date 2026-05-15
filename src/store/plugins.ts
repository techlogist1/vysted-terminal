import { create } from "zustand";

import type { PluginRuntime } from "@/lib/plugin-runtime";
import type { AgentSpec, DataSource, NodeSpec } from "../../types/plugin";
import type { LoadedPlugin } from "../../types/plugin-runtime";

/**
 * Plugin runtime store — surfaces the loaded plugins, their lifecycle state,
 * and the data-source / agent / node capabilities the runtime has aggregated.
 *
 * Bridge points (one per capability the host doesn't yet have a Phase-1 home
 * for):
 *
 * - `dataSources` — discovered `DataSource`s. Phase 3 surfaces these in the
 *   data-source picker; Phase 2 wires the registry so the contract is proven
 *   end-to-end.
 * - `agents` — discovered `AgentSpec`s. Phase 3 surfaces these in the AI
 *   chat sidebar.
 * - `nodes` — discovered `NodeSpec`s. Phase 4 surfaces these in the node
 *   editor palette.
 *
 * Plugin-contributed panels and commands flow through `useModulesStore` via
 * `appendModules()` (one source of truth for the dockview host and the cmd+K
 * palette) — not through this store.
 *
 * `attachRuntime()` subscribes the store to runtime events so any lifecycle
 * change re-syncs the snapshot. The runtime itself owns no state — this
 * store is the React-facing projection.
 */
interface PluginsState {
  plugins: LoadedPlugin[];
  dataSources: DataSource[];
  agents: AgentSpec[];
  nodes: NodeSpec[];
  /** The currently-attached runtime, or null before `attachRuntime` runs. */
  runtime: PluginRuntime | null;
  /** Subscribe the store to a runtime so its state mirrors runtime events. */
  attachRuntime: (runtime: PluginRuntime) => () => void;
  /** Force a re-pull from the runtime (used internally by event subscribers). */
  refreshFromRuntime: () => void;
}

export const usePluginsStore = create<PluginsState>((set, get) => ({
  plugins: [],
  dataSources: [],
  agents: [],
  nodes: [],
  runtime: null,
  attachRuntime: (runtime) => {
    set({ runtime });
    // Pull the initial state synchronously so any plugins discovered before
    // attachment are visible immediately.
    const refresh = () => {
      set({
        plugins: runtime.getPlugins() as LoadedPlugin[],
        dataSources: runtime.collectDataSources(),
        agents: runtime.collectAgents(),
        nodes: runtime.collectNodes(),
      });
    };
    refresh();
    // Re-pull on every runtime event — the surface area is small enough that
    // a full re-pull is simpler than computing diffs.
    return runtime.subscribe(() => refresh());
  },
  refreshFromRuntime: () => {
    const runtime = get().runtime;
    if (!runtime) {
      return;
    }
    set({
      plugins: runtime.getPlugins() as LoadedPlugin[],
      dataSources: runtime.collectDataSources(),
      agents: runtime.collectAgents(),
      nodes: runtime.collectNodes(),
    });
  },
}));
