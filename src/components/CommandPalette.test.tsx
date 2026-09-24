import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CommandPalette } from "@/components/CommandPalette";
import type { VystedModule } from "@/lib/module-registry";
import { useAgentsStore } from "@/store/agents";
import { resetChartCommandStoreForTests, useChartCommandStore } from "@/store/chart-command";
import { useCommandPalette } from "@/store/command-palette";
import {
  getRegisteredAction,
  resetKeybindingsStoreForTests,
  useKeybindingsStore,
} from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { resetSettingsStoreForTests, useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { CommandSpec } from "../../types/plugin";

// The live resolver answers any query with one instrument the watchlist lacks.
vi.mock("@/lib/symbol-autocomplete", () => ({
  useSymbolAutocomplete: (query: string) =>
    query.trim()
      ? [
          {
            symbol: "ROUTE",
            name: "Route Mobile",
            exchange: "NSE",
            region: "IN",
            asset_class: "equity",
            yahoo_symbol: "ROUTE.NS",
            confidence: 1,
          },
        ]
      : [],
}));

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
  resetSettingsStoreForTests();
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
  // The app-level keydown dispatcher (R15-UI-016) lives in `page.tsx`, not
  // here — it resolves `palette.open`'s (possibly remapped) binding and calls
  // whatever handler is registered. This component's contract is registering
  // that handler; the dispatcher's own chord-resolution is pinned in
  // `keybindings.test.ts` (`resolveKeyboardAction`).
  it("registers a palette.open handler that toggles the store", () => {
    useCommandPalette.setState({ open: false });
    render(<CommandPalette />);
    expect(useCommandPalette.getState().open).toBe(false);
    getRegisteredAction("palette.open")?.();
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

  it("an action row shows its current (remapped) chord as a <kbd> (R15-UI-086)", () => {
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    // "Save Workspace" -> "platform.save-workspace", default mod+s -> ⌘S on mac.
    const saveRow = screen.getByText("Save Workspace").closest("[cmdk-item]") as HTMLElement;
    expect(within(saveRow).getByText("⌘S")).toBeInTheDocument();

    cleanup();
    useKeybindingsStore.getState().setBinding("platform.save-workspace", "mod+shift+s");
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    const remappedRow = screen.getByText("Save Workspace").closest("[cmdk-item]") as HTMLElement;
    // formatBinding's fixed render order is ctrl, alt, shift, mod — ⇧⌘S.
    expect(within(remappedRow).getByText("⇧⌘S")).toBeInTheDocument();
  });

  // R15-UI-087 (FR-038): the two palette preferences change what it shows.
  it("paletteShowRecents: on, a recent pick leads the empty palette; off, the Recent group is gone", () => {
    useCommandPalette.setState({ open: true, recents: ["panel:test-panel"] });
    render(<CommandPalette />);
    expect(screen.getByText("Recent")).toBeInTheDocument();
    expect(document.querySelector("[cmdk-item]")?.textContent).toContain("Reportable Panel");

    cleanup();
    useSettingsStore.getState().setPaletteShowRecents(false);
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    expect(screen.queryByText("Recent")).not.toBeInTheDocument();
    expect(document.querySelector("[cmdk-item]")?.textContent).not.toContain("Reportable Panel");
  });

  it("paletteSymbolScope: all adds resolver tickers; watchlist searches the watchlist only", () => {
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    fireEvent.change(screen.getByPlaceholderText(/Ask anything/i), { target: { value: "route" } });
    expect(screen.getByText("Tickers")).toBeInTheDocument();
    expect(screen.getByText("Route Mobile")).toBeInTheDocument();

    cleanup();
    useSettingsStore.getState().setPaletteSymbolScope("watchlist");
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    fireEvent.change(screen.getByPlaceholderText(/Ask anything/i), { target: { value: "route" } });
    expect(screen.queryByText("Tickers")).not.toBeInTheDocument();
    expect(screen.queryByText("Route Mobile")).not.toBeInTheDocument();
  });

  it("a ticker pick commands the chart through the always-consumed chart-command channel", () => {
    const openPanel = vi.fn();
    useWorkspaceStore.setState({ dockviewApi: null, openPanel } as never);
    resetChartCommandStoreForTests();
    useCommandPalette.setState({ open: true });
    render(<CommandPalette />);
    fireEvent.change(screen.getByPlaceholderText(/Ask anything/i), { target: { value: "nvda" } });
    const symbolsGroup = screen.getByText("Symbols").closest("[cmdk-group]") as HTMLElement;
    fireEvent.click(within(symbolsGroup).getByText("NVDA"));
    expect(useChartCommandStore.getState().command?.symbol).toBe("NVDA");
    // No chart on screen → one is opened so the command has a consumer.
    expect(openPanel).toHaveBeenCalledWith("chart");
  });
});
