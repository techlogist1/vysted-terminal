import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { PluginManagerPanel } from "@/components/PluginManagerPanel";
import { type DiscoveredPlugin, PluginRuntime } from "@/lib/plugin-runtime";
import { usePluginsStore } from "@/store/plugins";

import type { DataSource, PluginCapabilities, VystedPlugin } from "../../types/plugin";
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
  capabilities: Partial<PluginCapabilities> = {},
  options: { initializeError?: Error; dataSources?: DataSource[]; description?: string } = {},
): VystedPlugin {
  return {
    pluginId: id,
    pluginName: id,
    pluginType: "data-source",
    version: "1.0.0",
    capabilities: { ...NO_CAPABILITIES, ...capabilities },
    initialize: async () => {
      if (options.initializeError) {
        throw options.initializeError;
      }
    },
    shutdown: async () => {},
    healthCheck: async () => ({ status: "healthy", checkedAt: 0 }),
    getDataSources: options.dataSources ? () => options.dataSources! : undefined,
  };
}

function discovered(
  plugin: VystedPlugin,
  manifestExtras: Partial<PluginManifest> = {},
): DiscoveredPlugin {
  return {
    manifest: {
      id: plugin.pluginId,
      version: plugin.version,
      name: plugin.pluginName,
      entry: "index.ts",
      requiredHostVersion: "0.0.0",
      ...manifestExtras,
    },
    instance: plugin,
  };
}

describe("PluginManagerPanel", () => {
  beforeEach(() => {
    usePluginsStore.setState({
      plugins: [],
      dataSources: [],
      agents: [],
      nodes: [],
      runtime: null,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the empty-state copy when no plugins are loaded", () => {
    render(<PluginManagerPanel />);
    expect(screen.getByText(/no plugins loaded yet/i)).toBeInTheDocument();
  });

  it("renders each loaded plugin with its name, version, and active state", async () => {
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(
        fakePlugin(
          "example",
          { contributesData: true },
          {
            dataSources: [{ id: "ds-1", label: "DS", kinds: ["equity"], realtime: false }],
          },
        ),
        { name: "Example Plugin", description: "A minimal example" },
      ),
    );
    usePluginsStore.getState().attachRuntime(runtime);

    render(<PluginManagerPanel />);
    expect(screen.getByText("Example Plugin")).toBeInTheDocument();
    expect(screen.getByText(/v1\.0\.0/)).toBeInTheDocument();
    expect(screen.getByTestId("plugin-state-example").textContent?.toLowerCase()).toContain(
      "active",
    );
  });

  it("renders the error message when a plugin is in the error state", async () => {
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(
      discovered(fakePlugin("broken", {}, { initializeError: new Error("init crashed") })),
    );
    usePluginsStore.getState().attachRuntime(runtime);

    render(<PluginManagerPanel />);
    expect(screen.getByTestId("plugin-state-broken").textContent?.toLowerCase()).toContain("error");
    expect(screen.getByTestId("plugin-error-broken").textContent).toContain("init crashed");
  });

  it("the toggle calls runtime.unloadPlugin when an active plugin is disabled", async () => {
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(discovered(fakePlugin("toggleable")));
    usePluginsStore.getState().attachRuntime(runtime);

    render(<PluginManagerPanel />);
    const toggle = screen.getByRole("switch", { name: "toggleable enabled" });
    expect(toggle).toBeChecked();

    fireEvent.click(toggle);
    await waitFor(() => {
      expect(runtime.getPlugin("toggleable")?.state).toBe("stopped");
    });
  });

  it("renders the health-history strip after a healthCheck has run", async () => {
    const runtime = new PluginRuntime();
    await runtime.loadPlugin(discovered(fakePlugin("ticker")));
    await runtime.healthCheckAll();
    usePluginsStore.getState().attachRuntime(runtime);

    render(<PluginManagerPanel />);
    expect(screen.getByTestId("plugin-health-history")).toBeInTheDocument();
  });
});
