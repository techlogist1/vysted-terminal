import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CommandPalette } from "@/components/CommandPalette";
import type { VystedModule } from "@/lib/module-registry";
import { useAgentsStore } from "@/store/agents";
import { useChartSyncBus } from "@/store/chart-sync";
import { useCommandPalette } from "@/store/command-palette";
import { resetKeybindingsStoreForTests } from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { CommandSpec } from "../../types/plugin";

const testModule: VystedModule = {
  id: "test-module",
  title: "Test Module",
  panels: [{ id: "test-panel", title: "Reportable Panel", component: "test-component" }],
  commands: [],
  panelComponents: {},
};

const commands: CommandSpec[] = [
  { id: "platform.save-workspace", trigger: "save", title: "Save Workspace" },
  { id: "chart.open", trigger: "chart", title: "Open Chart", opensPanel: "chart" },
];

function seedStores() {
  useModulesStore.setState({ modules: [], enabled: {} });
  useModulesStore.getState().registerModules([testModule]);
  useSymbolsStore.setState({ entries: [{ symbol: "NVDA", assetClass: "equity" }] });
  useAgentsStore.setState({
    firstPartyAgents: [
      {
        id: "buffett",
        name: "Warren Buffett",
        philosophy: "Value investing.",
        tools: [],
        defaultProvider: "openai",
        defaultModel: null,
        icon: null,
        origin: "first-party",
      },
    ],
    customAgents: [],
    customSummaries: [],
  });
  resetKeybindingsStoreForTests();
  useCommandPalette.setState({ open: true, commands });
}

beforeEach(() => {
  // macOS so the ⌘K mnemonic renders deterministically.
  vi.stubGlobal("navigator", { platform: "MacIntel", userAgent: "Mac OS X" });
  seedStores();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  useCommandPalette.setState({ open: false, commands: [] });
});

describe("CommandPalette", () => {
  it("renders a unified corpus: command, panel, symbol, and agent", () => {
    render(<CommandPalette />);
    expect(screen.getByText("Save Workspace")).toBeInTheDocument();
    expect(screen.getByText("Reportable Panel")).toBeInTheDocument();
    expect(screen.getByText("NVDA")).toBeInTheDocument();
    expect(screen.getByText("Warren Buffett")).toBeInTheDocument();
  });

  it("fuzzy-ranks results by query", () => {
    render(<CommandPalette />);
    const input = screen.getByLabelText("Search the command palette");
    fireEvent.change(input, { target: { value: "nvda" } });

    const options = screen.getAllByRole("option");
    // Only the symbol matches "nvda".
    expect(options).toHaveLength(1);
    expect(within(options[0]).getByText("NVDA")).toBeInTheDocument();
  });

  it("renders a mnemonic <kbd> for a bound command", () => {
    render(<CommandPalette />);
    // platform.save-workspace seeds mod+s → ⌘S on macOS.
    expect(screen.getByText("⌘S")).toBeInTheDocument();
  });

  it("selecting a symbol runs its action (broadcasts on the chart sync bus)", () => {
    render(<CommandPalette />);
    fireEvent.click(screen.getByText("NVDA"));
    expect(useChartSyncBus.getState().symbol).toMatchObject({
      symbol: "NVDA",
      source: "palette",
    });
    // Selecting closes the palette.
    expect(useCommandPalette.getState().open).toBe(false);
  });

  it("selecting a panel opens it via the workspace store", () => {
    const open = vi.spyOn(useWorkspaceStore.getState(), "openPanel");
    render(<CommandPalette />);
    fireEvent.click(screen.getByText("Reportable Panel"));
    expect(open).toHaveBeenCalledWith("test-panel");
  });

  it("⌘K toggles the palette via the keybindings store (data-driven open)", () => {
    useCommandPalette.setState({ open: false, commands });
    render(<CommandPalette />);
    expect(useCommandPalette.getState().open).toBe(false);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(useCommandPalette.getState().open).toBe(true);
  });

  it("category badges label each kind", () => {
    render(<CommandPalette />);
    expect(screen.getAllByText("Command").length).toBeGreaterThan(0);
    expect(screen.getByText("Panel")).toBeInTheDocument();
    expect(screen.getByText("Symbol")).toBeInTheDocument();
    expect(screen.getByText("Agent")).toBeInTheDocument();
  });
});
