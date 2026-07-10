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

import { researchSpaceName } from "@/lib/workspace";
import type { Region } from "@/lib/region";
import { useBriefStore } from "@/store/brief";
import { usePanelContextBus } from "@/store/panel-context";
import { usePortfoliosStore } from "@/store/portfolios";
import { useResearchSpacesStore } from "@/store/research-spaces";
import { useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { BriefDepth } from "../../../types/brief";
import type { ResearchSpaceClaim } from "../../../types/research-space";

/** How many prior stated values ride the terminal snapshot (the preamble caps
 *  further) — bounded so the per-turn context stays compact. */
const MAX_CONTEXT_CLAIMS = 20;

export interface TerminalChart {
  panelId: string;
  symbol: string | null;
  timeframe: string | null;
  indicators: string[];
}

/** One holding of the active portfolio, as the panel publishes it. */
export interface TerminalHolding {
  /** The store holding id — the handle a portfolio_update/delete_position
   *  action echoes back as `position_id`. Absent on older bus payloads. */
  id?: string;
  symbol: string;
  quantity: number;
  costBasis: number;
  assetClass: string;
  /** Live market value, or null when no quote resolved (provenance-honest). */
  marketValue?: number | null;
  /** Unrealised P&L, or null when no quote resolved. */
  pnl?: number | null;
}

/** The active portfolio's snapshot the copilot's get_portfolio reads. */
export interface TerminalPortfolio {
  positionCount: number;
  /**
   * Mark-to-market total, or `null` when it could not be computed (the panel
   * was closed so no live quotes were joined, OR the holdings span multiple
   * currencies so no honest cross-currency sum exists — R11/D57, see
   * {@link totalValueNote}). NEVER 0 as a stand-in for unknown — a fabricated
   * `$0` portfolio is the E3/E6 honesty defect; the agent must read `null` as
   * "I don't have a total" and say so.
   */
  totalValue: number | null;
  /** WHY `totalValue` is null when the panel itself published the null (D57:
   *  mixed currencies). Absent when a numeric total was published. */
  totalValueNote?: string;
  activePortfolioId?: string;
  activePortfolioName?: string;
  holdings: TerminalHolding[];
}

/** The active research space the user is working in, with prior-research memory. */
export interface TerminalResearchSpace {
  /** The symbol this research space investigates. */
  symbol: string;
  /** A short prior-research summary (what the agent looked at here before). */
  memory?: string;
  /** Count of prior conversation turns retained for this space. */
  priorTurns: number;
  /**
   * Prior figures the agent STATED in this space (R13 JARVIS 3b) — the sidecar
   * renders them as "PRIOR STATED VALUES" so a materially-contradicting new
   * figure is reconciled openly, never silently switched. Compact + capped.
   */
  claims?: ResearchSpaceClaim[];
}

/**
 * The brief panel's lifecycle identity (R10 D39): `get_terminal_state` answers
 * PANEL TRUTH — which run is in flight, or which artifact is on screen and how
 * fresh it is — so the agent can verify a publish landed instead of assuming.
 */
export interface TerminalBrief {
  phase: "empty" | "in_flight" | "published" | "archived";
  runId?: string;
  symbol?: string;
  createdAt?: number;
  sourceCount?: number;
  depth?: BriefDepth;
}

/** Structured snapshot the copilot reasons over (serialisable). */
export interface TerminalState {
  focusedPanel: string | null;
  /** The ticker the user is "looking at" — focused chart symbol, else watchlist selection. */
  focusedSymbol: string | null;
  charts: TerminalChart[];
  watchlist: { symbols: string[]; selected: string | null };
  portfolio: TerminalPortfolio | null;
  /** The brief panel's lifecycle truth (phase + run/artifact identity). */
  brief: TerminalBrief;
  openPanels: string[];
  /** The active research space + its prior-research memory (S-19). Present iff
   *  the active workspace is a research space. */
  researchSpace?: TerminalResearchSpace;
  /** Cockpit viewport size (px) so the agent arranges a layout that FITS the
   *  screen (Track 4) — never 15 panels on a small display. Omitted before the
   *  dockview layout has measured. */
  viewport?: { width: number; height: number };
  /** The user's active region/locale (drives region-first data) — Pass B B1. */
  region: Region;
  capturedAt: number;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

/** Coerce the bus payload's `holdings` array into `TerminalHolding[]` — older
 *  payloads (pre multi-portfolio truth) carry no `holdings`, yielding `[]`. */
function extractHoldings(value: unknown): TerminalHolding[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const holdings: TerminalHolding[] = [];
  for (const raw of value) {
    const row = asRecord(raw);
    const symbol = asString(row.symbol);
    if (symbol === null) {
      continue;
    }
    const marketValue = typeof row.marketValue === "number" ? row.marketValue : null;
    const pnl = typeof row.pnl === "number" ? row.pnl : null;
    const id = asString(row.id);
    holdings.push({
      ...(id !== null ? { id } : {}),
      symbol,
      quantity: Number(row.quantity ?? 0),
      costBasis: Number(row.costBasis ?? 0),
      assetClass: asString(row.assetClass) ?? "equity",
      marketValue,
      pnl,
    });
  }
  return holdings;
}

/**
 * The ACTIVE portfolio straight from the store — the fallback when the
 * portfolio panel is closed (the bus never published). Carries holding ids so
 * the agent's portfolio writes (E6) can target a position without the panel
 * open; market values stay null (no quotes were joined — provenance-honest).
 */
function portfolioFromStore(): TerminalPortfolio | null {
  const s = usePortfoliosStore.getState();
  const active = s.portfolios.find((p) => p.id === s.activeId) ?? s.portfolios[0];
  if (!active) {
    return null;
  }
  return {
    positionCount: active.holdings.length,
    // No quotes were joined (panel closed) — the total is UNKNOWN, not zero.
    totalValue: null,
    activePortfolioId: active.id,
    activePortfolioName: active.name,
    holdings: active.holdings.map((h) => ({
      id: h.id,
      symbol: h.symbol,
      quantity: h.quantity,
      costBasis: h.costBasis,
      assetClass: h.assetClass,
      marketValue: null,
      pnl: null,
    })),
  };
}

/** The brief panel's lifecycle identity for the snapshot (R10 D39). */
function briefStateForSnapshot(): TerminalBrief {
  const { panel } = useBriefStore.getState();
  if (panel.phase === "in_flight") {
    return {
      phase: "in_flight",
      runId: panel.runId,
      symbol: panel.symbol,
      createdAt: panel.startedAt,
      depth: panel.depth,
    };
  }
  if (panel.phase === "published" || panel.phase === "archived") {
    const brief = panel.brief;
    return {
      phase: panel.phase,
      runId: brief.execution?.runId,
      symbol: brief.symbol,
      createdAt: brief.createdAt,
      sourceCount: brief.sourceCount,
      depth: brief.depth,
    };
  }
  return { phase: "empty" };
}

/** Read the live bus + stores once and assemble a structured snapshot. */
export function captureTerminalState(): TerminalState {
  const bus = usePanelContextBus.getState();
  const bySource = bus.lastEventBySource;

  const charts: TerminalChart[] = [];
  let watchlist: { symbols: string[]; selected: string | null } = { symbols: [], selected: null };
  let portfolio: TerminalPortfolio | null = null;

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
      const activePortfolioId = asString(payload.activePortfolioId);
      const activePortfolioName = asString(payload.activePortfolioName);
      const totalValueNote = asString(payload.totalValueNote);
      portfolio = {
        positionCount: Number(payload.positionCount ?? 0),
        // Honest unknown: the panel publishes a real mark-to-market total when
        // it joined quotes; absent/null → null, never a fabricated 0. The
        // panel publishes null DELIBERATELY for mixed-currency portfolios
        // (D57) and says why via totalValueNote — thread the reason through so
        // the agent can state it instead of guessing.
        totalValue: payload.totalValue != null ? Number(payload.totalValue) : null,
        ...(totalValueNote !== null ? { totalValueNote } : {}),
        ...(activePortfolioId !== null ? { activePortfolioId } : {}),
        ...(activePortfolioName !== null ? { activePortfolioName } : {}),
        holdings: extractHoldings(payload.holdings),
      };
    }
  }

  // The shared symbols store is the canonical watchlist if the panel hasn't
  // published yet (e.g. the watchlist panel is closed).
  if (watchlist.symbols.length === 0) {
    const entries = useSymbolsStore.getState().entries;
    watchlist = { symbols: entries.map((e) => e.symbol), selected: watchlist.selected };
  }

  // Same store-fallback rule for the portfolio (E6): a closed panel must not
  // blind get_portfolio — the portfolios store is the canonical truth.
  if (portfolio === null) {
    portfolio = portfolioFromStore();
  }

  const focusedPanel = bus.focusedSource;
  const focusedChart =
    (focusedPanel && charts.find((c) => c.panelId === focusedPanel)) || charts[0] || null;
  const focusedSymbol = focusedChart?.symbol ?? watchlist.selected ?? watchlist.symbols[0] ?? null;

  // Open panels + viewport size from the dockview layout, if mounted.
  let openPanels: string[] = [];
  let viewport: { width: number; height: number } | undefined;
  try {
    const api = useWorkspaceStore.getState().dockviewApi as {
      panels?: { id: string }[];
      width?: number;
      height?: number;
    } | null;
    const panels = api?.panels;
    if (Array.isArray(panels)) {
      openPanels = panels.map((p) => p.id);
    }
    if (typeof api?.width === "number" && api.width > 0) {
      viewport = { width: Math.round(api.width), height: Math.round(api.height ?? 0) };
    }
  } catch {
    // dockview not mounted — leave empty.
  }

  // Active research space + its durable prior-research memory (S-19) — read off
  // the TYPED workspace field, not the name prefix.
  let researchSpace: TerminalResearchSpace | undefined;
  const researchSymbol = useWorkspaceStore.getState().researchSymbol;
  if (researchSymbol) {
    const memory = useResearchSpacesStore.getState().getMemory(researchSpaceName(researchSymbol));
    researchSpace = {
      symbol: researchSymbol,
      ...(memory?.summary ? { memory: memory.summary } : {}),
      priorTurns: memory?.transcript.length ?? 0,
      ...(memory?.claims && memory.claims.length > 0
        ? { claims: memory.claims.slice(-MAX_CONTEXT_CLAIMS) }
        : {}),
    };
  }

  return {
    focusedPanel,
    focusedSymbol,
    charts,
    watchlist,
    portfolio,
    brief: briefStateForSnapshot(),
    openPanels,
    ...(researchSpace ? { researchSpace } : {}),
    ...(viewport ? { viewport } : {}),
    region: useSettingsStore.getState().region,
    capturedAt: bus.updatedAt || Date.now(),
  };
}
