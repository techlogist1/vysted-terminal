/**
 * Tests for the cmdk-powered command palette store (FR-120 / SC-031).
 *
 * Ranking model (R4): MATCH QUALITY DOMINATES; the group offset is only a gentle
 * within-tier tiebreak. Covers:
 *   - Quality tiers: exact > prefix > word-start > substring > (label-only) subsequence
 *   - The "notes" regression: a concrete panel/action match ranks above agents
 *     whose long philosophy prose merely contains the query letters
 *   - Group tiebreak: equal-quality items order agents > actions > panels > symbols
 *   - Symbol gating: symbols score 0 when query is empty via paletteFilter
 *   - buildPaletteCorpus: correct kinds, capping, ordering
 *   - Recency tracking: recordSelection bumps items to the front of recents
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  buildPaletteCorpus,
  GROUP_SCORE_OFFSET,
  GROUP_TIEBREAK_WEIGHT,
  matchQuality,
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
// matchQuality — the quality tiers
// ---------------------------------------------------------------------------

describe("matchQuality tiers", () => {
  it("ranks exact > prefix > word-start > substring", () => {
    const exact = matchQuality("notes", "notes", "notes", "");
    const prefix = matchQuality("not", "notes", "notes", "");
    const wordStart = matchQuality("ed", "notes editor", "notes-editor", "");
    const substr = matchQuality("ote", "notes", "notes", "");
    expect(exact).toBeGreaterThan(prefix);
    expect(prefix).toBeGreaterThan(wordStart);
    expect(wordStart).toBeGreaterThan(substr);
  });

  it("matches subsequence on the label/slug but NOT the description (no prose flood)", () => {
    // 'n','o','t','e','s' appear in order in the label -> weak subsequence hit
    expect(matchQuality("notes", "no tabs evens", "x", "")).toBeGreaterThan(0);
    // The same letters as a subsequence of long prose in the DESCRIPTION must NOT match
    expect(matchQuality("notes", "Quant", "quant", "nuanced options trading expertise spans")).toBe(
      0,
    );
  });

  it("a description substring still scores (an agent literally about notes is allowed)", () => {
    expect(
      matchQuality("notes", "Scribe", "scribe", "takes notes during research"),
    ).toBeGreaterThan(0);
  });
});

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

  describe("the 'notes' regression — quality dominates the group", () => {
    it("the Notes panel (exact label) outranks agents that only weakly match", () => {
      const notesPanel = paletteFilter("panel:notes", "notes", ["Notes", "Markdown notes editor"]);
      // agent whose philosophy prose merely contains the subsequence n-o-t-e-s
      const agentSubseq = paletteFilter("agent:analyst", "notes", [
        "Market Analyst",
        "Nuanced options trading, earnings and footnotes synthesized into theses",
      ]);
      // agent whose description literally substring-contains "notes"
      const agentSubstr = paletteFilter("agent:scribe", "notes", [
        "Scribe",
        "Takes notes during research",
      ]);
      expect(notesPanel).toBeGreaterThan(agentSubseq);
      expect(notesPanel).toBeGreaterThan(agentSubstr);
    });

    it("a Notes action also outranks weakly-matching agents", () => {
      const notesAction = paletteFilter("action:notes.open", "notes", ["Open Notes"]);
      const agentSubstr = paletteFilter("agent:scribe", "notes", [
        "Scribe",
        "Takes notes during research",
      ]);
      expect(notesAction).toBeGreaterThan(agentSubstr);
    });

    it("agent philosophy prose does NOT subsequence-match an arbitrary query (no flood)", () => {
      const agentProse = paletteFilter("agent:quant", "notes", [
        "Quant",
        "Nuanced options trading expertise spans",
      ]);
      expect(agentProse).toBe(0);
    });

    it("a higher quality tier beats a lower tier regardless of group advantage", () => {
      const panelPrefix = paletteFilter("panel:chart", "cha", ["Chart"]); // prefix 0.9
      const agentWordStart = paletteFilter("agent:x", "cha", ["Big Chart Bot"]); // word-start 0.8
      expect(panelPrefix).toBeGreaterThan(agentWordStart);
    });
  });

  describe("group tiebreak — equal quality orders agent > action > panel > symbol", () => {
    const q = "cop";

    it("agent edges out action at equal match quality", () => {
      const agentScore = paletteFilter("agent:copilot", q, ["Copilot"]);
      const actionScore = paletteFilter("action:copilot-open", q, ["Copilot Open"]);
      expect(agentScore).toBeGreaterThan(actionScore);
    });

    it("action edges out panel at equal match quality", () => {
      const actionScore = paletteFilter("action:copilot.open", q, ["Copilot Open"]);
      const panelScore = paletteFilter("panel:copilot", q, ["Copilot Panel"]);
      expect(actionScore).toBeGreaterThan(panelScore);
    });

    it("panel edges out symbol at equal match quality", () => {
      // Both are exact label matches for "copper" → same quality tier; the group
      // tiebreak puts the panel ahead of the symbol.
      const panelScore = paletteFilter("panel:copper", "copper", ["Copper"]);
      const symbolScore = paletteFilter("symbol:COPPER", "copper", ["Copper", "equity"]);
      expect(panelScore).toBeGreaterThan(symbolScore);
    });

    it("an exact symbol match beats a mere agent prefix (quality wins over group)", () => {
      const symbolScore = paletteFilter("symbol:SPY", "spy", ["SPY", "equity"]); // exact 1.0
      const agentScore = paletteFilter("agent:spy-analyst", "spy", ["SPY Analyst"]); // prefix 0.9
      expect(symbolScore).toBeGreaterThan(agentScore);
    });
  });

  describe("no-match", () => {
    it("zero score for no match in any group", () => {
      expect(paletteFilter("agent:copilot", "zzz", ["Copilot"])).toBe(0);
      expect(paletteFilter("symbol:SPY", "zzz", ["SPY"])).toBe(0);
    });
  });

  describe("GROUP_SCORE_OFFSET / tiebreak weight", () => {
    it("has correct group ordering: agent > action > panel > symbol", () => {
      expect(GROUP_SCORE_OFFSET.agent).toBeGreaterThan(GROUP_SCORE_OFFSET.action);
      expect(GROUP_SCORE_OFFSET.action).toBeGreaterThan(GROUP_SCORE_OFFSET.panel);
      expect(GROUP_SCORE_OFFSET.panel).toBeGreaterThan(GROUP_SCORE_OFFSET.symbol);
    });

    it("the max tiebreak contribution is far below the gap between quality tiers", () => {
      // Max group contribution (agent) must not be able to invert a one-tier gap.
      const maxTiebreak = GROUP_SCORE_OFFSET.agent * GROUP_TIEBREAK_WEIGHT; // 0.024
      const minTierGap = 0.8 - 0.7; // word-start vs substring = 0.1
      expect(maxTiebreak).toBeLessThan(minTierGap);
    });

    it("symbol offset is 0 so a non-matching symbol returns 0", () => {
      expect(GROUP_SCORE_OFFSET.symbol).toBe(0);
      expect(paletteFilter("symbol:AAPL", "xyz", ["AAPL", "equity"])).toBe(0);
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

  it("at equal (exact) quality a panel edges out a symbol via the tiebreak", () => {
    const panelScore = paletteFilter("panel:aapl", "aapl", ["AAPL"]);
    const symbolScore = paletteFilter("symbol:AAPL", "aapl", ["AAPL", "equity"]);
    expect(panelScore).toBeGreaterThan(symbolScore);
  });
});
