/**
 * Command palette store — global open/close state, multi-source corpus builder,
 * and recency tracker for the cmdk-powered palette (FR-120 / SC-031).
 *
 * Corpus sources, in group-priority order:
 *   1. Ask AI     — always-present free-text row (synthesised at render time, not here)
 *   2. Agents     — first-party + custom agents from `useAgentsStore`
 *   3. Actions    — CommandSpec[] from `useModulesStore.enabledCommands()`
 *   4. Panels     — PanelSpec[] from `useModulesStore.enabledPanels()`
 *   5. Symbols    — SymbolEntry[] from `useSymbolsStore.entries` (query-gated, ≤50)
 *
 * Cross-group score offsets ensure the group ordering holds while cmdk's built-in
 * fuzzy filter still ranks within each group.  The filter returns a score in [0, 1]
 * where higher = better match.  We add a per-group offset so:
 *   agents  (offset 0.60) always outrank actions (0.40) outrank panels (0.20) outrank
 *   symbols (0.00) — and within a group the fuzzy delta (max 1.0) is preserved.
 *
 * Recents: up to 8 item ids persisted in the store (no localStorage per CLAUDE.md;
 * in-memory within the session, re-ranks recent picks within their group).
 */

import { create } from "zustand";

import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import type { AgentSummary } from "@/store/agents";
import type { CommandSpec, PanelSpec } from "../../types/plugin";

// ---------------------------------------------------------------------------
// Item kinds
// ---------------------------------------------------------------------------

export type PaletteItemKind = "agent" | "action" | "panel" | "symbol";

export interface PaletteItem {
  /** Unique stable id used as cmdk item value. */
  id: string;
  kind: PaletteItemKind;
  /** Primary label. */
  label: string;
  /** Secondary description / meta text. */
  description?: string;
  /** Underlying spec — typed per kind below. */
  agentSummary?: AgentSummary;
  commandSpec?: CommandSpec;
  panelSpec?: PanelSpec;
  symbolEntry?: { symbol: string; assetClass: "equity" | "crypto" };
}

// ---------------------------------------------------------------------------
// Cross-group score offsets
// ---------------------------------------------------------------------------

/**
 * Group offset added to the raw cmdk fuzzy score (0..1) to enforce the
 * group priority while preserving within-group ranking.
 *
 * Effective score = offset + rawScore * 0.1 (rawScore contributes only the
 * tiebreak within the group; the offset dominates).
 *
 * Order: agents > actions > panels > symbols
 */
export const GROUP_SCORE_OFFSET: Record<PaletteItemKind, number> = {
  agent: 0.6,
  action: 0.4,
  panel: 0.2,
  symbol: 0.0,
};

/** Max symbols to include in the corpus (cmdk degrades past ~3 k items). */
export const SYMBOL_CAP = 50;

/** Max recents to track per session. */
const MAX_RECENTS = 8;

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

interface CommandPaletteState {
  /** Whether the palette dialog is open. */
  open: boolean;
  /** The current search query (mirror of cmdk input value — stored so corpus can gate symbols). */
  query: string;
  /** Recently-used item ids, most-recent first. */
  recents: string[];

  setOpen: (open: boolean) => void;
  toggle: () => void;
  setQuery: (query: string) => void;
  /** Record a selection — bumps the item to the front of recents. */
  recordSelection: (itemId: string) => void;

  // --- legacy compat (page.tsx calls setCommands; we keep the signature but
  //     the corpus is now built dynamically from live stores) ---
  /** @deprecated Kept for backward compat with page.tsx bootstrap; no-op in the new model. */
  commands: CommandSpec[];
  /** @deprecated */
  setCommands: (_commands: CommandSpec[]) => void;
}

export const useCommandPalette = create<CommandPaletteState>((set) => ({
  open: false,
  query: "",
  recents: [],
  // legacy compat
  commands: [],
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  setCommands: (_c) => {
    // no-op — corpus is now built on-demand from live stores
  },

  setOpen: (open) => set({ open }),
  toggle: () => set((state) => ({ open: !state.open })),
  setQuery: (query) => set({ query }),
  recordSelection: (itemId) =>
    set((state) => {
      const filtered = state.recents.filter((id) => id !== itemId);
      return { recents: [itemId, ...filtered].slice(0, MAX_RECENTS) };
    }),
}));

// ---------------------------------------------------------------------------
// Corpus builder
// ---------------------------------------------------------------------------

/**
 * Build the live multi-source corpus.  Called inside the palette component on
 * each render (stores are cheap Zustand reads — no async, no caching needed).
 *
 * Symbols are always included in the corpus (gating is done in the rendering
 * layer via `query`-check and `forceMount={false}` on the group), capped at
 * `SYMBOL_CAP` to keep cmdk snappy.
 */
export function buildPaletteCorpus(): PaletteItem[] {
  const modulesState = useModulesStore.getState();
  const agentsState = useAgentsStore.getState();
  const symbolsState = useSymbolsStore.getState();

  const items: PaletteItem[] = [];

  // 1. Agents
  const firstParty = selectFirstPartyAgents(agentsState);
  const custom = selectCustomAgents(agentsState);
  for (const agent of [...firstParty, ...custom]) {
    items.push({
      id: `agent:${agent.id}`,
      kind: "agent",
      label: agent.name,
      description: agent.philosophy,
      agentSummary: agent,
    });
  }

  // 2. Actions (commands)
  for (const cmd of modulesState.enabledCommands()) {
    items.push({
      id: `action:${cmd.id}`,
      kind: "action",
      label: cmd.title,
      description: cmd.description,
      commandSpec: cmd,
    });
  }

  // 3. Panels
  for (const panel of modulesState.enabledPanels()) {
    items.push({
      id: `panel:${panel.id}`,
      kind: "panel",
      label: panel.title,
      panelSpec: panel,
    });
  }

  // 4. Symbols (capped)
  const entries = symbolsState.entries.slice(0, SYMBOL_CAP);
  for (const entry of entries) {
    items.push({
      id: `symbol:${entry.symbol}`,
      kind: "symbol",
      label: entry.symbol,
      description: entry.assetClass,
      symbolEntry: entry,
    });
  }

  return items;
}

/**
 * Custom cmdk `filter` function that applies cross-group score offsets so the
 * group order (agents > actions > panels > symbols) always holds while still
 * preserving within-group fuzzy ranking.
 *
 * cmdk calls this as: `filter(itemValue, searchQuery, keywords?): number`
 *
 * `itemValue` is the `value` prop on `Command.Item` — we set it to the item's
 * `id` (e.g. "agent:copilot", "action:chart.open", "panel:watchlist",
 * "symbol:SPY").
 *
 * The raw cmdk default filter (command-score) returns 0..1.  We can't call
 * it from user-land directly, so we implement a simple substring / initials
 * match that returns a 0..1 raw score, then add the group offset.
 */
export function paletteFilter(value: string, search: string, keywords?: string[]): number {
  if (!search) {
    // No query — show everything.  Return 1.0 (all items visible).
    return 1;
  }

  const needle = search.toLowerCase();

  // Determine group from the id prefix.
  let kind: PaletteItemKind = "action";
  if (value.startsWith("agent:")) kind = "agent";
  else if (value.startsWith("action:")) kind = "action";
  else if (value.startsWith("panel:")) kind = "panel";
  else if (value.startsWith("symbol:")) kind = "symbol";

  const offset = GROUP_SCORE_OFFSET[kind];

  // Build the haystack from value + keywords (label, description).
  const haystackParts = [value, ...(keywords ?? [])].map((s) => s.toLowerCase());
  const haystack = haystackParts.join(" ");

  let rawScore = 0;

  if (haystack.includes(needle)) {
    // Direct substring match — high raw score.
    rawScore = 0.9;
    // Bonus if the needle appears at the start of the label segment.
    const labelPart = (keywords?.[0] ?? "").toLowerCase();
    if (labelPart.startsWith(needle)) {
      rawScore = 1.0;
    }
  } else {
    // Initials / acronym match: check if all needle chars appear in order.
    let pos = 0;
    for (const ch of needle) {
      const idx = haystack.indexOf(ch, pos);
      if (idx === -1) {
        rawScore = 0;
        break;
      }
      rawScore = 0.3;
      pos = idx + 1;
    }
  }

  if (rawScore === 0) {
    return 0;
  }

  // Effective score = group_offset + raw_score * 0.09
  // The 0.09 multiplier keeps the raw delta well below the 0.20 group gap,
  // so a perfect symbol match (0.00 + 0.09 = 0.09) never outranks even a
  // weak agent match (0.60 + 0.009 = 0.609).
  return offset + rawScore * 0.09;
}
