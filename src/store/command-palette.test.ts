import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { buildPaletteCorpus, useCommandPalette } from "./command-palette";
import { useAgentsStore } from "./agents";
import { useChartSyncBus } from "./chart-sync";
import { resetKeybindingsStoreForTests } from "./keybindings";
import { useModulesStore } from "./modules";
import { useSymbolsStore } from "./symbols";
import { useWorkspaceStore } from "./workspace";
import type { VystedModule } from "@/lib/module-registry";
import type { CommandSpec } from "../../types/plugin";

const fakeModule: VystedModule = {
  id: "test-module",
  title: "Test Module",
  panels: [{ id: "test-panel", title: "Test Panel", component: "test-component" }],
  commands: [],
  panelComponents: {},
};

beforeEach(() => {
  useCommandPalette.setState({ open: false, commands: [] });
  useModulesStore.setState({ modules: [], enabled: {} });
  useModulesStore.getState().registerModules([fakeModule]);
  useSymbolsStore.setState({ entries: [{ symbol: "AAPL", assetClass: "equity" }] });
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
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useCommandPalette", () => {
  it("toggles and sets open", () => {
    useCommandPalette.getState().toggle();
    expect(useCommandPalette.getState().open).toBe(true);
    useCommandPalette.getState().setOpen(false);
    expect(useCommandPalette.getState().open).toBe(false);
  });

  it("stores the command list", () => {
    const commands: CommandSpec[] = [
      { id: "x.open", trigger: "x", title: "Open X", opensPanel: "x" },
    ];
    useCommandPalette.getState().setCommands(commands);
    expect(useCommandPalette.getState().commands).toEqual(commands);
  });
});

describe("buildPaletteCorpus", () => {
  const commands: CommandSpec[] = [
    { id: "platform.save-workspace", trigger: "save", title: "Save Workspace" },
    { id: "test.open", trigger: "test", title: "Open Test", opensPanel: "test-panel" },
  ];

  it("includes commands, panels, symbols, and agents", () => {
    const corpus = buildPaletteCorpus(commands);
    const kinds = new Set(corpus.map((i) => i.kind));
    expect(kinds.has("command")).toBe(true);
    expect(kinds.has("panel")).toBe(true);
    expect(kinds.has("symbol")).toBe(true);
    expect(kinds.has("agent")).toBe(true);

    expect(corpus.find((i) => i.id === "panel:test-panel")?.title).toBe("Test Panel");
    expect(corpus.find((i) => i.id === "symbol:AAPL")?.title).toBe("AAPL");
    expect(corpus.find((i) => i.id === "agent:buffett")?.title).toBe("Warren Buffett");
  });

  it("orders commands first, then panels, symbols, agents (stable empty-query order)", () => {
    const kinds = buildPaletteCorpus(commands).map((i) => i.kind);
    const firstCommand = kinds.indexOf("command");
    const firstPanel = kinds.indexOf("panel");
    const firstSymbol = kinds.indexOf("symbol");
    const firstAgent = kinds.indexOf("agent");
    expect(firstCommand).toBeLessThan(firstPanel);
    expect(firstPanel).toBeLessThan(firstSymbol);
    expect(firstSymbol).toBeLessThan(firstAgent);
  });

  it("attaches a formatted mnemonic to a bound command", () => {
    const corpus = buildPaletteCorpus(commands);
    const save = corpus.find((i) => i.id === "command:platform.save-workspace");
    // platform.save-workspace is seeded (mod+s) in the keybindings store.
    expect(save?.keybinding).toBeTruthy();
  });

  it("symbol select broadcasts on the chart sync bus", () => {
    const corpus = buildPaletteCorpus(commands);
    const symbol = corpus.find((i) => i.id === "symbol:AAPL");
    symbol?.run();
    expect(useChartSyncBus.getState().symbol).toMatchObject({ symbol: "AAPL", source: "palette" });
  });

  it("panel select opens the panel via the workspace store", () => {
    const open = vi.spyOn(useWorkspaceStore.getState(), "openPanel");
    const corpus = buildPaletteCorpus(commands);
    corpus.find((i) => i.id === "panel:test-panel")?.run();
    expect(open).toHaveBeenCalledWith("test-panel");
  });
});
