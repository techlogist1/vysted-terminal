/**
 * Terminal context provider for the copilot.
 *
 * Reads the live panel-context bus + the canonical stores and assembles a
 * compact, serialisable `TerminalState`. The copilot sends this under the
 * reserved `__terminal__` key of the agent context snapshot; the sidecar
 * renders a terse "what the user is looking at" preamble from it (and the
 * `get_terminal_state` tool returns it verbatim on demand). No React types —
 * this must JSON-serialise onto the wire.
 */

import { usePanelContextBus } from "@/store/panel-context";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

export interface TerminalChart {
  panelId: string;
  symbol: string | null;
  timeframe: string | null;
  indicators: string[];
}

/** Structured snapshot the copilot reasons over (serialisable). */
export interface TerminalState {
  focusedPanel: string | null;
  /** The ticker the user is "looking at" — focused chart symbol, else watchlist selection. */
  focusedSymbol: string | null;
  charts: TerminalChart[];
  watchlist: { symbols: string[]; selected: string | null };
  portfolio: { positionCount: number; totalValue: number } | null;
  openPanels: string[];
  capturedAt: number;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

/** Read the live bus + stores once and assemble a structured snapshot. */
export function captureTerminalState(): TerminalState {
  const bus = usePanelContextBus.getState();
  const bySource = bus.lastEventBySource;

  const charts: TerminalChart[] = [];
  let watchlist: { symbols: string[]; selected: string | null } = { symbols: [], selected: null };
  let portfolio: { positionCount: number; totalValue: number } | null = null;

  for (const [source, event] of Object.entries(bySource)) {
    const payload = asRecord(event?.payload);
    if (source.startsWith("chart")) {
      const indicators = Array.isArray(payload.activeIndicators)
        ? (payload.activeIndicators as unknown[]).map(String)
        : [];
      charts.push({
        panelId: source,
        symbol: asString(payload.symbol),
        timeframe: asString(payload.timeframe),
        indicators,
      });
    } else if (source === "watchlist") {
      watchlist = {
        symbols: Array.isArray(payload.symbols) ? (payload.symbols as unknown[]).map(String) : [],
        selected: asString(payload.selectedSymbol),
      };
    } else if (source === "portfolio") {
      portfolio = {
        positionCount: Number(payload.positionCount ?? 0),
        totalValue: Number(payload.totalValue ?? 0),
      };
    }
  }

  // The shared symbols store is the canonical watchlist if the panel hasn't
  // published yet (e.g. the watchlist panel is closed).
  if (watchlist.symbols.length === 0) {
    const entries = useSymbolsStore.getState().entries;
    watchlist = { symbols: entries.map((e) => e.symbol), selected: watchlist.selected };
  }

  const focusedPanel = bus.focusedSource;
  const focusedChart =
    (focusedPanel && charts.find((c) => c.panelId === focusedPanel)) || charts[0] || null;
  const focusedSymbol = focusedChart?.symbol ?? watchlist.selected ?? watchlist.symbols[0] ?? null;

  // Open panels from the dockview layout, if mounted.
  let openPanels: string[] = [];
  try {
    const api = useWorkspaceStore.getState().dockviewApi;
    const panels = (api as { panels?: { id: string }[] } | null)?.panels;
    if (Array.isArray(panels)) {
      openPanels = panels.map((p) => p.id);
    }
  } catch {
    // dockview not mounted — leave empty.
  }

  return {
    focusedPanel,
    focusedSymbol,
    charts,
    watchlist,
    portfolio,
    openPanels,
    capturedAt: bus.updatedAt || Date.now(),
  };
}
