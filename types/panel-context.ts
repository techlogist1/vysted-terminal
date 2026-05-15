/**
 * Vysted Terminal — per-panel context bus types.
 *
 * Phase 3 wires every panel to a Zustand bus (`src/store/panel-context.ts`)
 * that the AI chat sidebar subscribes to. When the user invokes an agent,
 * the bus's aggregated snapshot is attached to the request so the agent
 * reasons over the actual terminal state — what symbol the chart is on,
 * which indicators are active, which article the user has focused, which
 * positions are in the portfolio.
 *
 * The bus mirrors the `useChartSyncBus` pattern (`src/store/chart-sync.ts`)
 * — subscribers identify by `source` to skip self-echoes, and module-level
 * frozen empty references defeat infinite re-render loops on
 * `useSyncExternalStore` fallbacks (CLAUDE.md gotcha from Phase 2).
 *
 * Publishers (Teammate C wires each Phase-1 panel): chart, watchlist, news,
 * equity, portfolio. Subscriber (Teammate A): the chat sidebar.
 */

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

/** What kind of context change a publisher is announcing. */
export type PanelContextEventKind =
  /** Symbol changed (e.g. user picked a new ticker in watchlist). */
  | "symbol"
  /** Timeframe changed (chart panel only — daily → hourly, etc.). */
  | "timeframe"
  /** Active selection inside the panel changed (focused article, picked row). */
  | "selection"
  /** Broader snapshot — used for panels whose state is multi-field. */
  | "snapshot";

/**
 * One event published by a panel. `source` identifies the publisher; the
 * chat sidebar subscriber MUST skip events whose `source` matches its own
 * read identity to avoid self-echo loops (the Phase-2 chart-sync gotcha).
 *
 * `payload` shape is per-panel and intentionally `unknown` — agents read
 * the snapshot blob via `JSON.stringify` for the system-prompt preamble;
 * type narrowing per panel happens at the publisher and (optionally) at
 * the agent runtime when crafting tool-specific summaries.
 */
export interface PanelContextEvent {
  /**
   * Source identifier. Single-instance panels use a flat id (e.g.
   * `"watchlist"`); multi-instance panels (chart) prefix with the panel
   * id (e.g. `"chart-abc123"`).
   */
  source: string;
  kind: PanelContextEventKind;
  payload: unknown;
  /** Epoch milliseconds when the event was emitted. */
  emittedAt: number;
}

// ---------------------------------------------------------------------------
// Aggregated snapshot
// ---------------------------------------------------------------------------

/**
 * The chat sidebar's view of the bus. The store maintains the most-recent
 * event per `source` and tracks which `source` is currently focused (the
 * panel the user last interacted with), so the agent's system prompt
 * naturally prioritises the focused panel's state.
 */
export interface PanelContextSnapshot {
  /** Most-recent event per publisher. */
  lastEventBySource: Record<string, PanelContextEvent>;
  /** Source id of the focused panel, or `null` if no panel is focused. */
  focusedSource: string | null;
  /** Epoch milliseconds when this snapshot was last updated. */
  updatedAt: number;
}
