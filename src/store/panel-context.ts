/**
 * Panel context bus — per-panel state announcements.
 *
 * Phase 3 wires the AI chat sidebar to the rest of the terminal: when the
 * user invokes an agent, the agent reads which panel is focused, what
 * symbol is loaded, what indicators are active. The bus is how each panel
 * publishes that state and how the chat sidebar reads it.
 *
 * Mirrors the `useChartSyncBus` pattern (`src/store/chart-sync.ts`) — pure
 * Zustand, no Tauri IPC, no debouncing, no replay buffer. Subscribers
 * identify by `source` so a panel can skip its own re-broadcasts; module-
 * level frozen empty references defeat the `useSyncExternalStore`
 * infinite-loop precedent from Phase 2.
 *
 * Publishers (Phase 3 Teammate C): chart / watchlist / news / equity /
 * portfolio. Subscriber (Phase 3 Teammate A): the chat sidebar.
 */

import { create } from "zustand";

import type { PanelContextEvent, PanelContextSnapshot } from "../../types/panel-context";

interface PanelContextBusState {
  /** Most-recent event per `source` — overwritten on each publish from that source. */
  lastEventBySource: Record<string, PanelContextEvent>;
  /** Source id of the currently focused panel; `null` when no panel is focused. */
  focusedSource: string | null;
  /** Epoch milliseconds of the last state change. Bumped on every publish/focus. */
  updatedAt: number;
  /** Publish an event. Overwrites the prior event from the same source. */
  publish: (event: PanelContextEvent) => void;
  /** Set / clear the focused-panel source id. Idempotent. */
  setFocusedSource: (source: string | null) => void;
  /** Drop a panel's most-recent event — used by panels on unmount. */
  unregisterSource: (source: string) => void;
}

export const usePanelContextBus = create<PanelContextBusState>((set) => ({
  lastEventBySource: {},
  focusedSource: null,
  updatedAt: 0,
  publish: (event) =>
    set((state) => ({
      lastEventBySource: { ...state.lastEventBySource, [event.source]: event },
      updatedAt: Date.now(),
    })),
  setFocusedSource: (source) =>
    set((state) => {
      if (state.focusedSource === source) {
        return state;
      }
      return { focusedSource: source, updatedAt: Date.now() };
    }),
  unregisterSource: (source) =>
    set((state) => {
      if (!(source in state.lastEventBySource) && state.focusedSource !== source) {
        return state;
      }
      const next = { ...state.lastEventBySource };
      delete next[source];
      return {
        lastEventBySource: next,
        focusedSource: state.focusedSource === source ? null : state.focusedSource,
        updatedAt: Date.now(),
      };
    }),
}));

/**
 * Stable empty event map — re-used so a selector that returns it does not
 * mint a fresh object on every render. `useSyncExternalStore` callers infinite
 * loop on fresh empty references (CLAUDE.md Phase-2 gotcha from chart-sync).
 */
const EMPTY_EVENT_MAP: Readonly<Record<string, PanelContextEvent>> = Object.freeze({});

/** A frozen "no context" snapshot returned when the bus is empty. */
const EMPTY_SNAPSHOT: Readonly<PanelContextSnapshot> = Object.freeze({
  lastEventBySource: EMPTY_EVENT_MAP,
  focusedSource: null,
  updatedAt: 0,
});

/**
 * Read the aggregated snapshot the chat sidebar attaches to agent
 * invocations. Returns a stable empty snapshot when no panels have
 * published yet — so an idle chat sidebar does not re-render forever.
 */
export function selectSnapshot(state: PanelContextBusState): PanelContextSnapshot {
  if (state.updatedAt === 0) {
    return EMPTY_SNAPSHOT;
  }
  return {
    lastEventBySource: state.lastEventBySource,
    focusedSource: state.focusedSource,
    updatedAt: state.updatedAt,
  };
}

/**
 * Read the most-recent event from one specific source. Returns `null` if
 * that source has never published. Useful for panel-pair coupling (e.g. a
 * future watchlist-driven chart panel).
 */
export function selectEventBySource(
  state: PanelContextBusState,
  source: string,
): PanelContextEvent | null {
  return state.lastEventBySource[source] ?? null;
}
