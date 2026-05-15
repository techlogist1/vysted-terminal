/**
 * Chart sync bus — opt-in cross-chart broadcasting.
 *
 * Phase 2 makes the chart panel non-singleton, so multiple chart instances can
 * be open at once. The sync bus lets each instance opt into one or more of
 * three independent flavors:
 *
 *  - **crosshair** — broadcast hover-time across panels for visual alignment
 *  - **visibleRange** — broadcast pan/zoom so panels share an x-axis window
 *  - **symbol** — broadcast symbol changes so panels track the same instrument
 *
 * Each flavor is its own Zustand slice so a panel can subscribe to one without
 * receiving the others. Subscribers self-identify by `subscriberId` so a panel
 * does not echo its own broadcast back to itself.
 *
 * The bus is intentionally minimal — no debouncing, no replay buffer, no
 * Tauri IPC. State changes flow through Zustand's existing subscribe path.
 */

import { create } from "zustand";

/** Crosshair payload — chart time (UTC seconds) plus the originating panel id. */
export interface CrosshairBroadcast {
  /** UTCTimestamp seconds; `null` when the crosshair leaves the chart. */
  time: number | null;
  /** Source panel — broadcasters skip self-echoes. */
  source: string;
  /** Bumped on each set so equal payloads still trigger subscribers. */
  seq: number;
}

/** Visible-range payload — left/right edges of the time scale. */
export interface VisibleRangeBroadcast {
  /** Left edge time (UTCTimestamp seconds). */
  from: number;
  /** Right edge time (UTCTimestamp seconds). */
  to: number;
  source: string;
  seq: number;
}

/** Symbol payload — broadcasts the active symbol on the source panel. */
export interface SymbolBroadcast {
  symbol: string;
  source: string;
  seq: number;
}

interface ChartSyncBusState {
  crosshair: CrosshairBroadcast | null;
  visibleRange: VisibleRangeBroadcast | null;
  symbol: SymbolBroadcast | null;
  /** Per-panel toggles — which flavors a panel listens to. */
  subscriptions: Record<string, { crosshair: boolean; visibleRange: boolean; symbol: boolean }>;
  setCrosshair: (source: string, time: number | null) => void;
  setVisibleRange: (source: string, from: number, to: number) => void;
  setSymbol: (source: string, symbol: string) => void;
  setSubscription: (
    panelId: string,
    flavor: "crosshair" | "visibleRange" | "symbol",
    on: boolean,
  ) => void;
  unregisterPanel: (panelId: string) => void;
}

const DEFAULT_SUBS = { crosshair: false, visibleRange: false, symbol: false } as const;

export const useChartSyncBus = create<ChartSyncBusState>((set, get) => ({
  crosshair: null,
  visibleRange: null,
  symbol: null,
  subscriptions: {},
  setCrosshair: (source, time) =>
    set((state) => ({
      crosshair: { time, source, seq: (state.crosshair?.seq ?? 0) + 1 },
    })),
  setVisibleRange: (source, from, to) =>
    set((state) => ({
      visibleRange: { from, to, source, seq: (state.visibleRange?.seq ?? 0) + 1 },
    })),
  setSymbol: (source, symbol) =>
    set((state) => ({
      symbol: { symbol, source, seq: (state.symbol?.seq ?? 0) + 1 },
    })),
  setSubscription: (panelId, flavor, on) => {
    const existing = get().subscriptions[panelId] ?? { ...DEFAULT_SUBS };
    set((state) => ({
      subscriptions: {
        ...state.subscriptions,
        [panelId]: { ...existing, [flavor]: on },
      },
    }));
  },
  unregisterPanel: (panelId) =>
    set((state) => {
      if (!(panelId in state.subscriptions)) {
        return state;
      }
      const next = { ...state.subscriptions };
      delete next[panelId];
      return { subscriptions: next };
    }),
}));

/** Stable empty subscriptions reference — re-used so selectors stay referentially equal. */
const EMPTY_SUBS = Object.freeze({ ...DEFAULT_SUBS });

/**
 * Convenience selector: subscriptions for a specific panel, with defaults.
 * Returns a stable, frozen empty object when the panel is unknown so callers
 * subscribed via `useChartSyncBus(state => selectSubscriptions(...))` do not
 * see a fresh object on every render and trigger an infinite loop.
 */
export function selectSubscriptions(
  state: ChartSyncBusState,
  panelId: string,
): { crosshair: boolean; visibleRange: boolean; symbol: boolean } {
  return state.subscriptions[panelId] ?? EMPTY_SUBS;
}
