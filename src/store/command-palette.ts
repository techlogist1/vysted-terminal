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
 * Ranking model (FR-120): MATCH QUALITY DOMINATES; the group is only a gentle
 * tiebreak. The scorer grades the query against each item's LABEL (and stable id
 * slug) in quality tiers — exact > prefix > word-start > substring > (label-only)
 * subsequence — plus a weaker tier for description substrings. A tiny per-group
 * offset (≤0.024) breaks ties WITHIN a quality tier so, all else equal, agents
 * edge out actions edge out panels edge out symbols. Because quality dominates,
 * typing "notes" ranks the Notes panel/action at the very top — never a wall of
 * agents whose long philosophy prose merely contains the letters n-o-t-e-s.
 * (The prior model inverted this: a 0.60 group offset buried a perfect 0.29
 * panel match under any weak 0.627 agent subsequence hit.)
 *
 * Recents: up to 8 item ids tracked in-memory (no localStorage per CLAUDE.md;
 * in-memory within the session, re-ranks recent picks within their group).
 */

import { create } from "zustand";

import { applyLayoutMode, MENU_PAYLOAD_TO_MODE } from "@/lib/layout-templates";
import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
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
  /**
   * A direct dispatch for an `action` item with no `CommandSpec` (e.g. a
   * layout-menu mode — it isn't a module command, so it has no plugin-contract
   * id to route through `executeCommand`).
   */
  action?: () => void;
}

// ---------------------------------------------------------------------------
// Cross-group score offsets
// ---------------------------------------------------------------------------

/**
 * Per-group tiebreak weight. Effective score = matchQuality + offset * 0.04, so
 * the offset contributes at most 0.024 — far below the ≥0.08 gap between quality
 * tiers. It therefore only re-orders items of EQUAL match quality (all else
 * equal: agents > actions > panels > symbols). It can never override a better
 * match in another group.
 */
export const GROUP_SCORE_OFFSET: Record<PaletteItemKind, number> = {
  agent: 0.6,
  action: 0.4,
  panel: 0.2,
  symbol: 0.0,
};

/** Weight applied to the group offset so it stays a within-tier tiebreak only. */
export const GROUP_TIEBREAK_WEIGHT = 0.04;

/** Max symbols to include in the corpus (cmdk degrades past ~3 k items). */
export const SYMBOL_CAP = 50;

// ---------------------------------------------------------------------------
// Layout-menu modes (R15-CROSS-PLATFORM-004) — cross-platform command route
// ---------------------------------------------------------------------------
//
// The five deterministic layout modes (Fundamental / Technical / Macro /
// Compare / Reset) used to be reachable only from the macOS-only native
// `Window → Layout` menu (`src-tauri/src/lib.rs`, `#[cfg(target_os =
// "macos")]`). `dispatchLayoutMenuCommand` is the ONE place that runs a
// layout-menu payload; the palette command below and the macOS menu bridge
// (`src/lib/menu-bridge.ts`) both call it, so Windows/Linux get the same
// deterministic "clear + tile exactly this mode" behaviour the menu always
// had — never the agent's additive, viewport-downgraded `arrange_layout`.

/** Human label for each menu-bridge payload, matching the native menu's item text. */
const LAYOUT_MENU_LABELS: Readonly<Record<string, string>> = {
  "research-cockpit": "Layout: Fundamental",
  "single-focus": "Layout: Technical",
  "macro-scan": "Layout: Macro",
  compare: "Layout: Compare",
  default: "Layout: Reset to default",
};

/**
 * Run a layout-menu payload (a `MENU_PAYLOAD_TO_MODE` key, or `"default"` for
 * the factory reset). Returns false when the payload is unknown or there's no
 * live dockview api yet (e.g. called before the workspace mounts).
 */
export function dispatchLayoutMenuCommand(payload: string): boolean {
  if (payload === "default") {
    useWorkspaceStore.getState().resetToDefaultLayout();
    return true;
  }
  const mode = MENU_PAYLOAD_TO_MODE[payload];
  const api = useWorkspaceStore.getState().dockviewApi;
  if (!mode || !api) {
    return false;
  }
  applyLayoutMode(api, mode);
  return true;
}

/** Max recents to track per session. */
const MAX_RECENTS = 8;

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

interface CommandPaletteState {
  /** Whether the palette dialog is open. */
  open: boolean;
  /** Recently-used item ids, most-recent first. In-memory only — never localStorage. */
  recents: string[];

  setOpen: (open: boolean) => void;
  toggle: () => void;
  /** Record a selection — bumps the item to the front of recents. */
  recordSelection: (itemId: string) => void;
}

export const useCommandPalette = create<CommandPaletteState>((set) => ({
  open: false,
  recents: [],

  setOpen: (open) => set({ open }),
  toggle: () => set((state) => ({ open: !state.open })),
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
 * Build the live multi-source corpus from the current store state. The palette
 * re-runs it whenever a source store changes (so agents and plugins that load
 * while it is open appear).
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
  const commands = modulesState.enabledCommands();
  for (const cmd of commands) {
    items.push({
      id: `action:${cmd.id}`,
      kind: "action",
      label: cmd.title,
      description: cmd.description,
      commandSpec: cmd,
    });
  }

  // 2b. Layout-menu modes — cross-platform route for the deterministic
  // layouts the native macOS menu exposes (R15-CROSS-PLATFORM-004).
  for (const payload of [...Object.keys(MENU_PAYLOAD_TO_MODE), "default"]) {
    items.push({
      id: `action:layout:${payload}`,
      kind: "action",
      label: LAYOUT_MENU_LABELS[payload] ?? `Layout: ${payload}`,
      description:
        payload === "default"
          ? "Clear the cockpit back to its default panels"
          : "Clear the cockpit and tile this mode's panels",
      action: () => dispatchLayoutMenuCommand(payload),
    });
  }

  // 3. Panels — a panel an enabled command already opens is left to that
  // command's row (which carries its chord), so no two rows open one panel.
  const commandedPanels = new Set(commands.map((cmd) => cmd.opensPanel));
  for (const panel of modulesState.enabledPanels()) {
    if (commandedPanels.has(panel.id)) continue;
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

/** Does any whitespace/sep-delimited word in `haystack` start with `needle`? */
function wordStartsWith(haystack: string, needle: string): boolean {
  if (!haystack) return false;
  for (const word of haystack.split(/[\s\-_/:.,]+/)) {
    if (word.startsWith(needle)) return true;
  }
  return false;
}

/** Are all chars of `needle` present in `haystack` in order (fuzzy/acronym)? */
function isSubsequence(needle: string, haystack: string): boolean {
  if (!haystack) return false;
  let pos = 0;
  for (const ch of needle) {
    const idx = haystack.indexOf(ch, pos);
    if (idx === -1) return false;
    pos = idx + 1;
  }
  return true;
}

/**
 * Grade `needle` against an item's label, id-slug, and description, returning a
 * match-quality score in (0, 1] (0 = no match). Tiers are spaced ≥0.08 apart so
 * the tiny group tiebreak can never invert them. Subsequence (the weakest, most
 * permissive tier) matches the LABEL/SLUG ONLY — never the long description —
 * so an agent's philosophy prose can't subsequence-match arbitrary queries and
 * flood the results.
 */
export function matchQuality(
  needle: string,
  label: string,
  slug: string,
  description: string,
): number {
  if (label === needle || slug === needle) return 1.0; // exact
  if (label.startsWith(needle) || slug.startsWith(needle)) return 0.9; // prefix
  if (wordStartsWith(label, needle) || wordStartsWith(slug, needle)) return 0.8; // word-start
  if (label.includes(needle) || slug.includes(needle)) return 0.7; // label substring
  if (description) {
    if (description.startsWith(needle)) return 0.55;
    if (wordStartsWith(description, needle)) return 0.48;
    if (description.includes(needle)) return 0.4; // description substring
  }
  if (isSubsequence(needle, label) || isSubsequence(needle, slug)) return 0.25; // label-only fuzzy
  return 0;
}

/**
 * Custom cmdk `filter`: returns `matchQuality + group_offset * GROUP_TIEBREAK_WEIGHT`.
 * Match quality dominates; the group offset only re-orders equal-quality items.
 *
 * cmdk calls this as `filter(itemValue, searchQuery, keywords?): number`, where
 * `itemValue` is the `value` prop (e.g. "panel:notes") and `keywords` is
 * `[label, description]` from the row.
 */
export function paletteFilter(value: string, search: string, keywords?: string[]): number {
  const needle = search.trim().toLowerCase();
  if (!needle) return 1; // no query — everything visible; render-order governs

  // Group from the id prefix (default to action for unprefixed values).
  let kind: PaletteItemKind = "action";
  if (value.startsWith("agent:")) kind = "agent";
  else if (value.startsWith("panel:")) kind = "panel";
  else if (value.startsWith("symbol:")) kind = "symbol";
  else if (value.startsWith("action:")) kind = "action";

  const label = (keywords?.[0] ?? "").toLowerCase();
  const description = (keywords?.[1] ?? "").toLowerCase();
  const slug = (value.includes(":") ? value.slice(value.indexOf(":") + 1) : value).toLowerCase();

  const quality = matchQuality(needle, label, slug, description);
  if (quality <= 0) return 0;

  return quality + GROUP_SCORE_OFFSET[kind] * GROUP_TIEBREAK_WEIGHT;
}
