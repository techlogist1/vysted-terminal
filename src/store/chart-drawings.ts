/**
 * Chart drawings store — per-panel drawing state, Zustand-backed.
 *
 * The chart panel is non-singleton (Phase 2 multi-chart sync), so each chart
 * instance has a distinct `panelId` and its own drawings collection. The store
 * keeps a `byPanel` map mirroring `WorkspaceDrawings.byPanel` exactly, which
 * lets workspace serialization round-trip without re-shaping the data.
 *
 * Drawings are pure serializable data. The renderer (`drawings/factory.ts`)
 * builds an `ISeriesPrimitive` from a `DrawingSpec`; ChartPanel subscribes to
 * the slice for its `panelId` and reconciles primitives by stable `id`.
 */

import { create } from "zustand";

import { DEFAULT_REGION, type Region } from "@/lib/region";

import type { ChartView, DrawingSpec, WorkspaceDrawings } from "../../types/drawings";

interface ChartDrawingsState {
  /** Drawings per chart-panel id (every symbol/timeframe the panel has shown). */
  byPanel: Record<string, DrawingSpec[]>;
  /** What each chart panel shows — persisted so a relaunch reopens it (R15-UI-020). */
  views: Record<string, ChartView>;
  /** Record a panel's view; a no-op when nothing changed (no autosave churn). */
  setView: (panelId: string, view: ChartView) => void;
  /** Replace every panel's view — used by workspace load and reset. */
  replaceViews: (views: Record<string, ChartView>) => void;
  /** Replace every panel's drawings — used by workspace load. */
  replaceAll: (drawings: WorkspaceDrawings) => void;
  /** Snapshot the current state in `WorkspaceDrawings` shape — used by workspace save. */
  snapshot: () => WorkspaceDrawings;
  /** Append a drawing to a panel's collection. */
  addDrawing: (panelId: string, drawing: DrawingSpec) => void;
  /** Replace one drawing by id — no-op if the id is not present. */
  updateDrawing: (
    panelId: string,
    id: string,
    update: (drawing: DrawingSpec) => DrawingSpec,
  ) => void;
  /** Remove one drawing by id. */
  removeDrawing: (panelId: string, id: string) => void;
  /** Clear every drawing on a panel — used when the panel closes. */
  clearPanel: (panelId: string) => void;
  /** All drawings on a panel; stable empty array if the panel has none. */
  getDrawings: (panelId: string) => readonly DrawingSpec[];
}

const EMPTY: readonly DrawingSpec[] = Object.freeze([]);

/** What a chart panel opens on for a region (R15-UI-076): `IN` (the app
 *  default) opens on the NIFTY 50 index, not a US ticker. */
export function defaultChartSymbolForRegion(region: Region): string {
  return region === "IN" ? "^NSEI" : "SPY";
}

/** What a chart panel opens on when it has no persisted view. */
export const DEFAULT_CHART_SYMBOL = defaultChartSymbolForRegion(DEFAULT_REGION);
export const DEFAULT_CHART_TIMEFRAME = "1d";

export const useChartDrawingsStore = create<ChartDrawingsState>((set, get) => ({
  byPanel: {},
  views: {},
  setView: (panelId, view) =>
    set((state) => {
      const prev = state.views[panelId];
      if (
        prev &&
        prev.symbol === view.symbol &&
        prev.timeframe === view.timeframe &&
        prev.compare === view.compare &&
        prev.indicators.join() === view.indicators.join()
      ) {
        return state;
      }
      return { views: { ...state.views, [panelId]: view } };
    }),
  replaceViews: (views) => set({ views: { ...views } }),
  replaceAll: (drawings) => {
    // Defensive copy — Zustand does shallow equality, so cloning the inner
    // arrays ensures subscribers notice changes even if a caller hands in the
    // same object reference twice.
    const next: Record<string, DrawingSpec[]> = {};
    for (const [panelId, list] of Object.entries(drawings.byPanel)) {
      next[panelId] = [...list];
    }
    set({ byPanel: next });
  },
  snapshot: () => {
    const out: Record<string, DrawingSpec[]> = {};
    for (const [panelId, list] of Object.entries(get().byPanel)) {
      out[panelId] = [...list];
    }
    return { byPanel: out };
  },
  addDrawing: (panelId, drawing) =>
    set((state) => {
      const existing = state.byPanel[panelId] ?? [];
      return { byPanel: { ...state.byPanel, [panelId]: [...existing, drawing] } };
    }),
  updateDrawing: (panelId, id, update) =>
    set((state) => {
      const existing = state.byPanel[panelId];
      if (!existing) {
        return state;
      }
      let changed = false;
      const next = existing.map((drawing) => {
        if (drawing.id !== id) {
          return drawing;
        }
        changed = true;
        return update(drawing);
      });
      if (!changed) {
        return state;
      }
      return { byPanel: { ...state.byPanel, [panelId]: next } };
    }),
  removeDrawing: (panelId, id) =>
    set((state) => {
      const existing = state.byPanel[panelId];
      if (!existing) {
        return state;
      }
      const next = existing.filter((drawing) => drawing.id !== id);
      if (next.length === existing.length) {
        return state;
      }
      return { byPanel: { ...state.byPanel, [panelId]: next } };
    }),
  clearPanel: (panelId) =>
    set((state) => {
      if (!(panelId in state.byPanel)) {
        return state;
      }
      const next = { ...state.byPanel };
      delete next[panelId];
      return { byPanel: next };
    }),
  getDrawings: (panelId) => get().byPanel[panelId] ?? EMPTY,
}));

/** The drawings a panel shows for one symbol/timeframe. */
export function drawingsFor(
  list: readonly DrawingSpec[],
  symbol: string,
  timeframe: string,
): DrawingSpec[] {
  return list.filter((d) => d.symbol === symbol && d.timeframe === timeframe);
}

/**
 * Stable per-drawing id generator — uses `crypto.randomUUID` when available
 * (browsers + recent Node), falls back to a timestamp+random combo for the
 * jsdom test runner that does not expose `crypto.randomUUID` by default.
 */
export function newDrawingId(): string {
  if (typeof globalThis.crypto !== "undefined" && "randomUUID" in globalThis.crypto) {
    return globalThis.crypto.randomUUID();
  }
  return `dr_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}
