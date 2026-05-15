import { beforeEach, describe, expect, it } from "vitest";

import { type DiscoveredPlugin, PluginRuntime } from "@/lib/plugin-runtime";
import { usePluginsStore } from "@/store/plugins";

import type {
  AgentSpec,
  DataSource,
  NodeSpec,
  PluginCapabilities,
  VystedPlugin,
} from "../../types/plugin";
import type { PluginManifest } from "../../types/plugin-runtime";

const NO_CAPABILITIES: PluginCapabilities = {
  contributesData: false,
  contributesPanels: false,
  contributesCommands: false,
  contributesAgents: false,
  contributesNodes: false,
  supportsControlPlane: false,
};

function fakePlugin(
  id: string,
  capabilities: Partial<PluginCapabilities>,
  contributions: Partial<{
    dataSources: DataSource[];
    agents: AgentSpec[];
    nodes: NodeSpec[];
  }> = {},
): VystedPlugin {
  return {
    pluginId: id,
    pluginName: id,
    pluginType: "data-source",
    version: "1.0.0",
    capabilities: { ...NO_CAPABILITIES, ...capabilities },
    initialize: async () => {},
    shutdown: async () => {},
    healthCheck: async () => ({ status: "healthy", checkedAt: 0 }),
    getDataSources: contributions.dataSources ? () => contributions.dataSources! : undefined,
    getAgents: contributions.agents ? () => contributions.agents! : undefined,
    getNodes: contributions.nodes ? () => contributions.nodes! : undefined,
  };
}

function discovered(plugin: VystedPlugin): DiscoveredPlugin {
  const manifest: PluginManifest = {
    id: plugin.pluginId,
    version: plugin.version,
    name: plugin.pluginName,
    entry: "index.ts",
    requiredHostVersion: "0.0.0",
  };
  return { manifest, instance: plugin };
}

describe("usePluginsStore", () => {
  beforeEach(() => {
    usePluginsStore.setState({
      plugins: [],
      dataSources: [],
      agents: [],
      nodes: [],
      runtime: null,
    });
  });

  it("starts with empty registries and no attached runtime", () => {
    const state = usePluginsStore.getState();
    expect(state.plugins).toEqual([]);
    expect(state.dataSources).toEqual([]);
    expect(state.agents).toEqual([]);
    expect(state.nodes).toEqual([]);
    expect(state.runtime).toBeNull();
  });

  it("attachRuntime pulls the initial state from the runtime", async () => {
    const runtime = new PluginRuntime();
    const ds: DataSource = { id: "ds-1", label: "DS1", kinds: ["equity"], realtime: false };
    await runtime.loadPlugin(
      discovered(fakePlugin("a", { contributesData: true }, { dataSources: [ds] })),
    );
    usePluginsStore.getState().attachRuntime(runtime);
    expect(usePluginsStore.getState().dataSources).toEqual([ds]);
    expect(usePluginsStore.getState().plugins).toHaveLength(1);
  });

  it("attachRuntime re-syncs when the runtime emits events", async () => {
    const runtime = new PluginRuntime();
    usePluginsStore.getState().attachRuntime(runtime);
    expect(usePluginsStore.getState().plugins).toHaveLength(0);

    const ds: DataSource = { id: "ds-2", label: "DS2", kinds: ["equity"], realtime: false };
    await runtime.loadPlugin(
      discovered(fakePlugin("b", { contributesData: true }, { dataSources: [ds] })),
    );
    expect(usePluginsStore.getState().dataSources).toEqual([ds]);
    expect(usePluginsStore.getState().plugins).toHaveLength(1);
  });

  it("aggregates agents and nodes by capability flag", async () => {
    const runtime = new PluginRuntime();
    const agent: AgentSpec = {
      id: "agent-1",
      name: "Agent 1",
      philosophy: "test",
      systemPrompt: "test",
      tools: [],
      defaultProvider: "anthropic",
    };
    const node: NodeSpec = {
      id: "node-1",
      label: "Node 1",
      category: "trigger",
      inputs: [],
      outputs: [],
    };
    await runtime.loadPlugin(
      discovered(
        fakePlugin(
          "c",
          { contributesAgents: true, contributesNodes: true },
          { agents: [agent], nodes: [node] },
        ),
      ),
    );
    usePluginsStore.getState().attachRuntime(runtime);
    expect(usePluginsStore.getState().agents).toEqual([agent]);
    expect(usePluginsStore.getState().nodes).toEqual([node]);
  });

  it("the unsubscribe returned by attachRuntime stops re-syncs", async () => {
    const runtime = new PluginRuntime();
    const unsubscribe = usePluginsStore.getState().attachRuntime(runtime);
    unsubscribe();
    await runtime.loadPlugin(discovered(fakePlugin("d", {})));
    expect(usePluginsStore.getState().plugins).toHaveLength(0);
  });
});
