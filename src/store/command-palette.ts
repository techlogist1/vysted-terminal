import { create } from "zustand";

import { executeCommand } from "@/lib/commands";
import { selectCustomAgents, selectFirstPartyAgents, useAgentsStore } from "@/store/agents";
import { useChartCommandStore } from "@/store/chart-command";
import { formatBinding, useKeybindingsStore } from "@/store/keybindings";
import { useModulesStore } from "@/store/modules";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { CommandSpec } from "../../types/plugin";

/**
 * The kind of corpus item — drives the category badge in the palette and the
 * action that runs on select. Widened past `CommandSpec` so the palette can
 * fuzzy-rank panels, symbols, and agents alongside commands (FR-031).
 */
export type PaletteItemKind = "command" | "panel" | "symbol" | "agent";

/** A single searchable, runnable palette entry. */
export interface PaletteItem {
  /** Stable id, unique within the corpus (kind-prefixed to avoid collisions). */
  id: string;
  kind: PaletteItemKind;
  /** Primary label shown in the row (the fuzzy-ranked text). */
  title: string;
  /** Optional secondary line shown beneath the title. */
  subtitle?: string;
  /** Run the item's action (open a panel, run a command, load a symbol, …). */
  run: () => void;
  /**
   * Display combo (already formatted, e.g. `"⌘K"`) for the item's mnemonic, if
   * one exists in the keybindings store. The palette renders it as a `<kbd>`.
   */
  keybinding?: string;
}

interface CommandPaletteState {
  /** Whether the cmd+K command palette modal is open. */
  open: boolean;
  /** Commands shown in the palette — aggregated from enabled modules. */
  commands: CommandSpec[];
  setOpen: (open: boolean) => void;
  toggle: () => void;
  setCommands: (commands: CommandSpec[]) => void;
}

/**
 * Global UI state for the command palette. The command list is populated from
 * the enabled modules at startup (`page.tsx`); the corpus the palette actually
 * fuzzy-ranks is assembled live in `buildPaletteCorpus()` (it pulls the wider
 * panel/symbol/agent universe straight from their stores at open time, so it
 * always reflects the latest watchlist/agent roster without an extra sync).
 */
export const useCommandPalette = create<CommandPaletteState>((set) => ({
  open: false,
  commands: [],
  setOpen: (open) => set({ open }),
  toggle: () => set((state) => ({ open: !state.open })),
  setCommands: (commands) => set({ commands }),
}));

/**
 * Assemble the unified, ordered corpus the palette fuzzy-ranks. Order is the
 * stable "empty query" order: commands first (the verbs a user reaches for),
 * then panels, then symbols, then agents.
 *
 * Pure of React — reads each store via `getState()` so it can run inside the
 * palette body's `useMemo` and in tests without a render. The keybinding label
 * is resolved from `useKeybindingsStore` (the host-side companion keymap, since
 * `CommandSpec` is Tier-1 LOCKED and carries no binding field).
 */
export function buildPaletteCorpus(commands: CommandSpec[]): PaletteItem[] {
  const items: PaletteItem[] = [];

  const keybindings = useKeybindingsStore.getState();
  const bindingLabel = (actionId: string): string | undefined => {
    const def = keybindings.defFor(actionId);
    return def && def.keys ? formatBinding(def.keys) : undefined;
  };

  // 1) Commands (CommandSpec from enabled modules).
  for (const command of commands) {
    items.push({
      id: `command:${command.id}`,
      kind: "command",
      title: command.title,
      subtitle: command.description,
      run: () => executeCommand(command),
      keybinding: bindingLabel(command.id),
    });
  }

  // 2) Panels (open or focus via the workspace store).
  const seenPanels = new Set<string>();
  for (const panel of useModulesStore.getState().enabledPanels()) {
    if (seenPanels.has(panel.id)) {
      continue;
    }
    seenPanels.add(panel.id);
    items.push({
      id: `panel:${panel.id}`,
      kind: "panel",
      title: panel.title,
      subtitle: "Open panel",
      run: () => useWorkspaceStore.getState().openPanel(panel.id),
    });
  }

  // 3) Symbols — selecting one commands the open chart to load it (the same
  //    always-consumed channel the copilot uses, so it actually lands).
  for (const entry of useSymbolsStore.getState().entries) {
    items.push({
      id: `symbol:${entry.symbol}`,
      kind: "symbol",
      title: entry.symbol,
      subtitle: entry.assetClass === "crypto" ? "Crypto" : "Equity",
      run: () => useChartCommandStore.getState().loadSymbol(entry.symbol),
    });
  }

  // 4) Agents — first-party + custom. Selecting one is a safe focus action:
  //    it just opens/focuses the chat surface (no agent run is triggered from
  //    the palette — that would be a mutation the user didn't confirm).
  const agentsState = useAgentsStore.getState();
  const agents = [...selectFirstPartyAgents(agentsState), ...selectCustomAgents(agentsState)];
  const seenAgents = new Set<string>();
  for (const agent of agents) {
    if (seenAgents.has(agent.id)) {
      continue;
    }
    seenAgents.add(agent.id);
    items.push({
      id: `agent:${agent.id}`,
      kind: "agent",
      title: agent.name,
      subtitle: agent.philosophy,
      run: () => useWorkspaceStore.getState().openPanel("chat"),
    });
  }

  return items;
}
