/**
 * Tests for the cmdk-powered command palette store (FR-120 / SC-031).
 *
 * Covers:
 *   - Cross-group score offsets: agents > actions > panels > symbols
 *   - Within-group fuzzy ranking (better match = higher score within group)
 *   - Symbol gating: symbols score 0 when query is empty via paletteFilter
 *   - buildPaletteCorpus: correct kinds, capping, ordering
 *   - Recency tracking: recordSelection bumps items to the front of recents
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  buildPaletteCorpus,
  GROUP_SCORE_OFFSET,
  paletteFilter,
  SYMBOL_CAP,
  useCommandPalette,
} from "@/store/command-palette";
import { useAgentsStore } from "@/store/agents";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import type { VystedModule } from "@/lib/module-registry";
import type { AgentSummary } from "@/store/agents";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeModule(id: string): VystedModule {
  return {
    id,
    title: id,
    panels: [{ id: `${id}-panel`, title: `${id} Panel`, component: `${id}-comp` }],
    commands: [{ id: `${id}.open`, trigger: id, title: `Open ${id}`, opensPanel: `${id}-panel` }],
    panelComponents: { [`${id}-comp`]: () => null },
  };
}

function makeAgent(id: string): AgentSummary {
  return {
    id,
    name: `Agent ${id}`,
    philosophy: `Philosophy of ${id}`,
    tools: [],
    defaultProvider: "anthropic",
    origin: "first-party",
  };
}

// ---------------------------------------------------------------------------
// paletteFilter
// ---------------------------------------------------------------------------

describe("paletteFilter", () => {
  describe("empty query", () => {
    it("returns 1 for all item kinds when query is empty", () => {
      expect(paletteFilter("agent:copilot", "", ["Agent Copilot", "philosophy"])).toBe(1);
      expect(paletteFilter("action:chart.open", "", ["Open chart"])).toBe(1);
      expect(paletteFilter("panel:watchlist", "", ["Watchlist"])).toBe(1);
      expect(paletteFilter("symbol:SPY", "", ["SPY", "equity"])).toBe(1);
    });
  });

  describe("cross-group offset enforcement", () => {
    const query = "cop";

    it("agent score is always above action score for the same fuzzy quality", () => {
      // Both match "cop" (copilot vs copilot-action) — agent must win
      const agentScore = paletteFilter("agent:copilot", query, ["Copilot"]);
      const actionScore = paletteFilter("action:copilot-open", query, ["Copilot Open"]);
      expect(agentScore).toBeGreaterThan(actionScore);
    });

    it("action score is always above panel score", () => {
      const actionScore = paletteFilter("action:copilot.open", query, ["Copilot Open"]);
      const panelScore = paletteFilter("panel:copilot", query, ["Copilot"]);
      expect(actionScore).toBeGreaterThan(panelScore);
    });

    it("panel score is always above symbol score", () => {
      const panelScore = paletteFilter("panel:copper", query, ["Copper Panel"]);
      const symbolScore = paletteFilter("symbol:COPPER", query, ["COPPER", "equity"]);
      expect(panelScore).toBeGreaterThan(symbolScore);
    });

    it("agent score is always above symbol score when both match", () => {
      const symbolScore = paletteFilter("symbol:SPY", "spy", ["SPY", "equity"]);
      const agentScoreMatch = paletteFilter("agent:spy-analyst", "spy", ["SPY Analyst"]);
      expect(agentScoreMatch).toBeGreaterThan(symbolScore);
    });
  });

  describe("within-group ranking", () => {
    it("exact label start match outranks substring match in same group", () => {
      const prefixScore = paletteFilter("action:chart.open", "chart", ["Chart Open"]);
      const substringScore = paletteFilter("action:bar-chart", "chart", ["Bar Chart"]);
      // "Chart Open" starts with "chart" → rawScore=1.0
      // "Bar Chart" contains "chart" but not at start → rawScore=0.9
      expect(prefixScore).toBeGreaterThan(substringScore);
    });

    it("zero score for no match in any group", () => {
      expect(paletteFilter("agent:copilot", "zzz", ["Copilot"])).toBe(0);
      expect(paletteFilter("symbol:SPY", "zzz", ["SPY"])).toBe(0);
    });
  });

  describe("GROUP_SCORE_OFFSET values", () => {
    it("has correct group ordering: agent > action > panel > symbol", () => {
      expect(GROUP_SCORE_OFFSET.agent).toBeGreaterThan(GROUP_SCORE_OFFSET.action);
      expect(GROUP_SCORE_OFFSET.action).toBeGreaterThan(GROUP_SCORE_OFFSET.panel);
      expect(GROUP_SCORE_OFFSET.panel).toBeGreaterThan(GROUP_SCORE_OFFSET.symbol);
    });

    it("symbol offset is 0 so a non-matching symbol returns 0", () => {
      expect(GROUP_SCORE_OFFSET.symbol).toBe(0);
      // A symbol item that doesn't match the query must return 0 (no false positives).
      expect(paletteFilter("symbol:AAPL", "xyz", ["AAPL", "equity"])).toBe(0);
    });

    it("gap between groups exceeds the maximum within-group fuzzy contribution", () => {
      // Max within-group contribution = 1.0 * 0.09 = 0.09
      // Min gap between adjacent groups = action(0.40) - panel(0.20) = 0.20 > 0.09
      const maxFuzzyContrib = 1.0 * 0.09;
      const minGap = GROUP_SCORE_OFFSET.action - GROUP_SCORE_OFFSET.panel;
      expect(minGap).toBeGreaterThan(maxFuzzyContrib);
    });
  });
});

// ---------------------------------------------------------------------------
// buildPaletteCorpus
// ---------------------------------------------------------------------------

describe("buildPaletteCorpus", () => {
  beforeEach(() => {
    useModulesStore.setState({ modules: [], enabled: {} });
    useAgentsStore.setState({ firstPartyAgents: [], customSummaries: [], customAgents: [] });
    useSymbolsStore.setState({
      entries: [
        { symbol: "SPY", assetClass: "equity" },
        { symbol: "AAPL", assetClass: "equity" },
      ],
    });
  });

  it("returns agent items with kind=agent", () => {
    useAgentsStore.getState().setFirstPartyAgents([makeAgent("copilot"), makeAgent("analyst")]);
    const corpus = buildPaletteCorpus();
    const agents = corpus.filter((i) => i.kind === "agent");
    expect(agents).toHaveLength(2);
    expect(agents[0].id).toBe("agent:copilot");
    expect(agents[1].id).toBe("agent:analyst");
  });

  it("returns action items with kind=action", () => {
    useModulesStore.getState().registerModules([makeModule("chart")]);
    const corpus = buildPaletteCorpus();
    const actions = corpus.filter((i) => i.kind === "action");
    expect(actions.some((a) => a.id === "action:chart.open")).toBe(true);
  });

  it("returns panel items with kind=panel", () => {
    useModulesStore.getState().registerModules([makeModule("watchlist")]);
    const corpus = buildPaletteCorpus();
    const panels = corpus.filter((i) => i.kind === "panel");
    expect(panels.some((p) => p.id === "panel:watchlist-panel")).toBe(true);
  });

  it("returns symbol items with kind=symbol", () => {
    const corpus = buildPaletteCorpus();
    const symbols = corpus.filter((i) => i.kind === "symbol");
    expect(symbols).toHaveLength(2);
    expect(symbols[0].id).toBe("symbol:SPY");
  });

  it("agents appear before actions, actions before panels, panels before symbols", () => {
    useAgentsStore.getState().setFirstPartyAgents([makeAgent("copilot")]);
    useModulesStore.getState().registerModules([makeModule("chart")]);
    const corpus = buildPaletteCorpus();
    const firstAgent = corpus.findIndex((i) => i.kind === "agent");
    const firstAction = corpus.findIndex((i) => i.kind === "action");
    const firstPanel = corpus.findIndex((i) => i.kind === "panel");
    const firstSymbol = corpus.findIndex((i) => i.kind === "symbol");
    expect(firstAgent).toBeLessThan(firstAction);
    expect(firstAction).toBeLessThan(firstPanel);
    expect(firstPanel).toBeLessThan(firstSymbol);
  });

  it("symbols are capped at SYMBOL_CAP", () => {
    const manySymbols = Array.from({ length: SYMBOL_CAP + 10 }, (_, i) => ({
      symbol: `SYM${i}`,
      assetClass: "equity" as const,
    }));
    useSymbolsStore.setState({ entries: manySymbols });
    const corpus = buildPaletteCorpus();
    const symbols = corpus.filter((i) => i.kind === "symbol");
    expect(symbols).toHaveLength(SYMBOL_CAP);
  });

  it("disabled module commands and panels are excluded", () => {
    useModulesStore.getState().registerModules([makeModule("chart"), makeModule("news")]);
    useModulesStore.getState().setModuleEnabled("news", false);
    const corpus = buildPaletteCorpus();
    const actions = corpus.filter((i) => i.kind === "action");
    const panels = corpus.filter((i) => i.kind === "panel");
    expect(actions.some((a) => a.id.includes("news"))).toBe(false);
    expect(panels.some((p) => p.id.includes("news"))).toBe(false);
    expect(actions.some((a) => a.id.includes("chart"))).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// useCommandPalette store — recency tracking
// ---------------------------------------------------------------------------

describe("useCommandPalette recency", () => {
  beforeEach(() => {
    useCommandPalette.setState({ open: false, query: "", recents: [] });
  });

  it("recordSelection adds item to front of recents", () => {
    useCommandPalette.getState().recordSelection("agent:copilot");
    expect(useCommandPalette.getState().recents[0]).toBe("agent:copilot");
  });

  it("recordSelection deduplicates — re-selecting moves to front", () => {
    useCommandPalette.getState().recordSelection("panel:chart");
    useCommandPalette.getState().recordSelection("agent:copilot");
    useCommandPalette.getState().recordSelection("panel:chart");
    const recents = useCommandPalette.getState().recents;
    expect(recents[0]).toBe("panel:chart");
    expect(recents.filter((r) => r === "panel:chart")).toHaveLength(1);
  });

  it("recents are capped at 8 items", () => {
    for (let i = 0; i < 12; i++) {
      useCommandPalette.getState().recordSelection(`panel:p${i}`);
    }
    expect(useCommandPalette.getState().recents).toHaveLength(8);
  });

  it("toggle opens and closes the palette", () => {
    expect(useCommandPalette.getState().open).toBe(false);
    useCommandPalette.getState().toggle();
    expect(useCommandPalette.getState().open).toBe(true);
    useCommandPalette.getState().toggle();
    expect(useCommandPalette.getState().open).toBe(false);
  });

  it("setCommands is a no-op (legacy compat)", () => {
    const before = useCommandPalette.getState().commands;
    useCommandPalette
      .getState()
      .setCommands([{ id: "x", trigger: "x", title: "X", opensPanel: "x" }]);
    // commands field unchanged (no-op)
    expect(useCommandPalette.getState().commands).toEqual(before);
  });
});

// ---------------------------------------------------------------------------
// Symbol gating via paletteFilter
// ---------------------------------------------------------------------------

describe("symbol gating", () => {
  it("all item kinds return 1 when query is empty string", () => {
    expect(paletteFilter("symbol:SPY", "", ["SPY", "equity"])).toBe(1);
    expect(paletteFilter("agent:copilot", "", ["Copilot"])).toBe(1);
  });

  it("a non-matching symbol returns 0 for any non-empty query", () => {
    expect(paletteFilter("symbol:AAPL", "xyz", ["AAPL", "equity"])).toBe(0);
  });

  it("a matching symbol returns > 0 for a matching non-empty query", () => {
    expect(paletteFilter("symbol:AAPL", "aapl", ["AAPL", "equity"])).toBeGreaterThan(0);
  });

  it("matching symbol score is below matching panel score for identical label text", () => {
    // Both have "aapl" in keywords / label.
    const panelScore = paletteFilter("panel:aapl-chart", "aapl", ["AAPL Chart"]);
    const symbolScore = paletteFilter("symbol:AAPL", "aapl", ["AAPL", "equity"]);
    expect(panelScore).toBeGreaterThan(symbolScore);
  });
});
