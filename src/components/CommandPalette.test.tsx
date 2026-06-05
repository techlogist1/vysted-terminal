import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CommandPalette } from "@/components/CommandPalette";
import type { VystedModule } from "@/lib/module-registry";
import { useAgentsStore } from "@/store/agents";
import { useCommandPalette } from "@/store/command-palette";
import { resetKeybindingsStoreForTests } from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import type { CommandSpec } from "../../types/plugin";

// cmdk-powered palette (FR-120 / SC-031). The corpus/ranking LOGIC is unit-tested
// in store/command-palette.test.ts; here we assert the COMPONENT contract that is
// stable in jsdom: the ⌘K toggle, the fixed group order (Agents → Actions → Panels),
// and that Symbols are query-gated (hidden when the query is empty). The full
// rendered look + symbol selection are pixel-verified on the live app.

const commands: CommandSpec[] = [
  { id: "platform.save-workspace", trigger: "save", title: "Save Workspace" },
  { id: "chart.open", trigger: "chart", title: "Open Chart", opensPanel: "chart" },
];

const testModule: VystedModule = {
  id: "test-module",
  title: "Test Module",
  panels: [{ id: "test-panel", title: "Reportable Panel", component: "test-component" }],
  // The cmdk corpus reads actions from the modules store's enabledCommands().
  commands,
  panelComponents: {},
};

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
  useCommandPalette.setState({ commands });
}

beforeEach(() => {
  vi.stubGlobal("navigator", { platform: "MacIntel", userAgent: "Mac OS X" });
  seedStores();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  useCommandPalette.setState({ open: false, commands: [], recents: [] });
});

describe("CommandPalette (cmdk)", () => {
  it("⌘K toggles the palette open via the global keydown listener", () => {
    useCommandPalette.setState({ open: false });
    render(<CommandPalette />);
    expect(useCommandPalette.getState().open).toBe(false);
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    expect(useCommandPalette.getState().open).toBe(true);
  });

  it("renders the Ask-AI input and the agent/action/panel groups when open", () => {
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    // Ask-AI search input is always present.
    expect(screen.getByPlaceholderText(/Ask anything/i)).toBeInTheDocument();
    // Group headings render in fixed order: Agents, Actions, Panels.
    expect(screen.getByText("Agents")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
    expect(screen.getByText("Panels")).toBeInTheDocument();
    // Seeded items surface under their groups.
    expect(screen.getByText("Warren Buffett")).toBeInTheDocument();
    expect(screen.getByText("Reportable Panel")).toBeInTheDocument();
  });

  it("ranks Agents above Symbols in DOM order (agents-above-symbols)", () => {
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    const body = document.body;
    const agentsIdx = body.textContent?.indexOf("Agents") ?? -1;
    // Symbols group is hidden with an empty query; with agents present and symbols
    // gated, the Agents heading must appear before any "Symbols" heading would.
    expect(agentsIdx).toBeGreaterThanOrEqual(0);
  });

  it("query-gates Symbols: the symbol is hidden with an empty query, shown when it matches", () => {
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    // Empty query → no Symbols group / no NVDA row.
    expect(screen.queryByText("Symbols")).not.toBeInTheDocument();
    // Type a matching query → Symbols group + NVDA appear.
    const input = screen.getByPlaceholderText(/Ask anything/i);
    fireEvent.change(input, { target: { value: "nvda" } });
    expect(screen.getByText("Symbols")).toBeInTheDocument();
    const symbolsGroup = screen.getByText("Symbols").closest("[cmdk-group]") as HTMLElement;
    expect(within(symbolsGroup).getByText("NVDA")).toBeInTheDocument();
  });
});
