import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { SettingsPanel } from "@/components/SettingsPanel";
import { vystedModules } from "@/modules";
import { PLATFORM_MODULE_ID } from "@/modules/platform";
import { useModulesStore } from "@/store/modules";

describe("SettingsPanel", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useModulesStore.getState().registerModules(vystedModules);
  });

  afterEach(() => {
    cleanup();
  });

  it("lists every registered module", () => {
    render(<SettingsPanel />);
    for (const mod of vystedModules) {
      expect(screen.getByText(mod.title)).toBeInTheDocument();
    }
  });

  it("toggling a module updates the modules store", () => {
    render(<SettingsPanel />);

    const chartToggle = screen.getByRole("switch", { name: "Chart enabled" });
    expect(chartToggle).toBeChecked();

    fireEvent.click(chartToggle);
    expect(useModulesStore.getState().enabled.chart).toBe(false);
    expect(chartToggle).not.toBeChecked();

    fireEvent.click(chartToggle);
    expect(useModulesStore.getState().enabled.chart).toBe(true);
    expect(chartToggle).toBeChecked();
  });

  it("the platform module toggle is not user-disableable", () => {
    render(<SettingsPanel />);

    const platformToggle = screen.getByRole("switch", { name: "Platform enabled" });
    expect(platformToggle).toBeChecked();
    expect(platformToggle).toBeDisabled();

    // Clicking the disabled toggle must not flip the platform module off.
    fireEvent.click(platformToggle);
    expect(useModulesStore.getState().enabled[PLATFORM_MODULE_ID]).not.toBe(false);
  });
});
