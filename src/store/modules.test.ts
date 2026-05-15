import { beforeEach, describe, expect, it } from "vitest";

import type { VystedModule } from "@/lib/module-registry";
import { vystedModules } from "@/modules";
import { useModulesStore } from "@/store/modules";

function fakeModule(id: string, panelId = `${id}-panel`): VystedModule {
  return {
    id,
    title: id,
    panels: [{ id: panelId, title: `${id} Panel`, component: `${id}-component` }],
    commands: [{ id: `${id}.open`, trigger: id, title: `Open ${id}`, opensPanel: panelId }],
    panelComponents: { [`${id}-component`]: () => null },
  };
}

describe("modules store", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
  });

  it("registers modules and enables them all", () => {
    useModulesStore.getState().registerModules(vystedModules);
    const state = useModulesStore.getState();
    expect(state.modules.length).toBeGreaterThanOrEqual(7);
    expect(state.enabledModules().length).toBe(state.modules.length);
  });

  it("disabling a module drops its panels and commands", () => {
    useModulesStore.getState().registerModules(vystedModules);
    useModulesStore.getState().setModuleEnabled("chart", false);
    const state = useModulesStore.getState();
    expect(state.enabledModules().map((module) => module.id)).not.toContain("chart");
    expect(state.enabledPanels().some((panel) => panel.id === "chart")).toBe(false);
    expect(state.enabledCommands().some((command) => command.id === "chart.open")).toBe(false);
  });

  it("findPanel locates a panel spec by id", () => {
    useModulesStore.getState().registerModules(vystedModules);
    expect(useModulesStore.getState().findPanel("watchlist")?.title).toBe("Watchlist");
    expect(useModulesStore.getState().findPanel("does-not-exist")).toBeUndefined();
  });

  it("findPanel still resolves panels of disabled modules", () => {
    useModulesStore.getState().registerModules(vystedModules);
    useModulesStore.getState().setModuleEnabled("chart", false);
    expect(useModulesStore.getState().findPanel("chart")).toBeDefined();
  });

  it("setEnabledMap replaces the whole enabled map", () => {
    useModulesStore.getState().registerModules(vystedModules);
    useModulesStore.getState().setEnabledMap({ chart: true, watchlist: false });
    const state = useModulesStore.getState();
    expect(state.enabled).toEqual({ chart: true, watchlist: false });
    expect(state.enabledModules().map((module) => module.id)).not.toContain("watchlist");
  });

  it("appendModules adds new modules and preserves the existing enabled map", () => {
    useModulesStore.getState().registerModules(vystedModules);
    useModulesStore.getState().setModuleEnabled("chart", false);
    useModulesStore.getState().appendModules([fakeModule("plugin-a")]);
    const state = useModulesStore.getState();
    expect(state.modules).toHaveLength(vystedModules.length + 1);
    expect(state.modules.at(-1)?.id).toBe("plugin-a");
    // Pre-existing disabled flag preserved.
    expect(state.enabled.chart).toBe(false);
    // New module starts enabled.
    expect(state.enabled["plugin-a"]).toBe(true);
  });

  it("appendModules deduplicates against the existing registry", () => {
    useModulesStore.getState().registerModules(vystedModules);
    const lengthBefore = useModulesStore.getState().modules.length;
    useModulesStore.getState().appendModules([fakeModule("chart")]);
    expect(useModulesStore.getState().modules).toHaveLength(lengthBefore);
  });

  it("appendModules into an empty registry adds modules and enables them", () => {
    useModulesStore.getState().appendModules([fakeModule("plugin-a"), fakeModule("plugin-b")]);
    const state = useModulesStore.getState();
    expect(state.modules.map((module) => module.id)).toEqual(["plugin-a", "plugin-b"]);
    expect(state.enabled).toEqual({ "plugin-a": true, "plugin-b": true });
  });
});
