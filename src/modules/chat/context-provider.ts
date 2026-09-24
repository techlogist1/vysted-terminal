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
import { useNotesStore } from "@/store/notes";
import { usePanelContextBus } from "@/store/panel-context";
import { usePortfoliosStore } from "@/store/portfolios";
import { useResearchSpacesStore } from "@/store/research-spaces";
import { useSettingsStore } from "@/store/settings";
import { useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";
import type { AgentContextSnapshot } from "../../../types/ai";
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

/**
 * A generic per-panel summary for every bus source that isn't one of the
 * hand-modelled fields (chart/watchlist/portfolio) — news, backtest,
 * earnings, analyst ratings, SEC filings, screener, macro, quant, etc.
 * (R15-AGENT-053). `summary` is a compact `key=value` projection of the
 * published payload, capped to `MAX_OTHER_PANEL_SUMMARY_CHARS`, so a new
 * panel is visible to the copilot the moment it publishes — with zero
 * per-panel wiring here.
 */
export interface TerminalPanelSummary {
  source: string;
  symbol?: string;
  summary: string;
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
  /** Every other published source's generic summary (R15-AGENT-053) — news,
   *  backtest, earnings, analyst ratings, SEC filings, screener, macro,
   *  quant, and any future panel that publishes to the bus. */
  otherPanels: TerminalPanelSummary[];
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

/**
 * The symbol the focused panel publishes, whatever its kind (`symbol` on a
 * chart, `ticker` on Equity Overview), or null when the focused panel carries
 * none. The one derivation behind the context badge, the suggestion chips and
 * the snapshot's `focusedSymbol` (R15-CODE-FRONTEND-015).
 */
export function focusedSymbolFromBus(
  bus: Record<string, { payload: unknown } | undefined>,
  focusedSource: string | null,
): string | null {
  if (!focusedSource) {
    return null;
  }
  const payload = asRecord(bus[focusedSource]?.payload);
  return asString(payload.symbol) ?? asString(payload.ticker);
}

/** A generic per-source summary's cap (R15-AGENT-053) — compact enough that
 *  N un-modelled panels never bloat the snapshot. */
export const MAX_OTHER_PANEL_SUMMARY_CHARS = 200;

/**
 * Compactly project an arbitrary published payload into one `key=value, …`
 * line, capped to {@link MAX_OTHER_PANEL_SUMMARY_CHARS}. Works for ANY panel's
 * payload shape with zero per-panel code (R15-AGENT-053) — a new publisher is
 * visible to the copilot the moment it starts publishing. Arrays collapse to
 * a count, nested objects to `…`, so the line stays terse.
 */
export function genericPanelSummary(payload: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(payload)) {
    if (value === null || value === undefined) {
      continue;
    }
    let rendered: string;
    if (Array.isArray(value)) {
      rendered = `${value.length} item${value.length === 1 ? "" : "s"}`;
    } else if (typeof value === "object") {
      rendered = "…";
    } else {
      rendered = String(value);
    }
    parts.push(`${key}=${rendered}`);
  }
  const joined = parts.join(", ");
  return joined.length > MAX_OTHER_PANEL_SUMMARY_CHARS
    ? joined.slice(0, MAX_OTHER_PANEL_SUMMARY_CHARS) + "…"
    : joined;
}

/** Each note rides the request capped at this many characters (C2). */
export const NOTE_CHAR_CAP = 4_000;
export const NOTE_TRUNCATION_MARKER =
  "\n[note truncated here; the full text is in the Notes panel]";

/** The user's notes as the `__notes__` snapshot entry (C2): the general note
 *  and every non-empty per-symbol note, each capped. They ride beside
 *  `__terminal__`, not inside it, so `get_terminal_state` stays compact. */
export interface TerminalNotes {
  general: string;
  bySymbol: Record<string, string>;
}

function capNote(text: string): string {
  if (!text.trim()) {
    return "";
  }
  return text.length > NOTE_CHAR_CAP ? text.slice(0, NOTE_CHAR_CAP) + NOTE_TRUNCATION_MARKER : text;
}

export function captureNotes(): TerminalNotes {
  const { general, bySymbol } = useNotesStore.getState();
  const notes: Record<string, string> = {};
  for (const [symbol, text] of Object.entries(bySymbol)) {
    if (text.trim()) {
      notes[symbol] = capNote(text);
    }
  }
  return { general: capNote(general), bySymbol: notes };
}

/** The context an agent invocation carries: the terminal state plus the
 *  user's notes, which the agent reads with `read_notes` (R15-AGENT-020). */
export function captureAgentContext(): AgentContextSnapshot {
  const terminalState = captureTerminalState();
  return {
    focusedSource: terminalState.focusedPanel,
    bySource: { __terminal__: terminalState, __notes__: captureNotes() },
    capturedAt: terminalState.capturedAt,
  };
}

/** Read the live bus + stores once and assemble a structured snapshot. */
export function captureTerminalState(): TerminalState {
  const bus = usePanelContextBus.getState();
  const bySource = bus.lastEventBySource;

  const charts: TerminalChart[] = [];
  let watchlist: { symbols: string[]; selected: string | null } = { symbols: [], selected: null };
  let portfolio: TerminalPortfolio | null = null;
  const otherPanels: TerminalPanelSummary[] = [];

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
    } else {
      // R15-AGENT-053: every other publisher (news, backtest, earnings,
      // analyst ratings, SEC filings, screener, macro, quant, …) gets a
      // generic summary instead of silently vanishing from the snapshot.
      const symbol = asString(payload.symbol) ?? asString(payload.ticker);
      otherPanels.push({
        source,
        ...(symbol !== null ? { symbol } : {}),
        summary: genericPanelSummary(payload),
      });
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

  // The focused panel's own symbol wins (a focused Equity Overview on INFY is
  // "this", not the chart behind it); a panel with none falls back to a chart,
  // then the watchlist, so "this" still resolves.
  const focusedPanel = bus.focusedSource;
  const focusedChart =
    (focusedPanel && charts.find((c) => c.panelId === focusedPanel)) || charts[0] || null;
  const focusedSymbol =
    focusedSymbolFromBus(bySource, focusedPanel) ??
    focusedChart?.symbol ??
    watchlist.selected ??
    watchlist.symbols[0] ??
    null;

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
    otherPanels,
    openPanels,
    ...(researchSpace ? { researchSpace } : {}),
    ...(viewport ? { viewport } : {}),
    region: useSettingsStore.getState().region,
    capturedAt: bus.updatedAt || Date.now(),
  };
}
