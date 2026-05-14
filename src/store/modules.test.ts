import { beforeEach, describe, expect, it } from "vitest";

import { vystedModules } from "@/modules";
import { useModulesStore } from "@/store/modules";

describe("modules store", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
  });

  it("registers modules and enables them all", () => {
    useModulesStore.getState().registerModules(vystedModules);
    const state = useModulesStore.getState();
    expect(state.modules).toHaveLength(6);
    expect(state.enabledModules()).toHaveLength(6);
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
});
