/**
 * Tradesa V2 wrapper — plugin-scoped Zustand store.
 *
 * Holds the connection-state snapshot the panel layer renders against +
 * the most-recent fetched data per panel. Polling refresh is wired here
 * (no Realtime in v0.6.5 — deferred to v0.6.6+ per Tier-3 scope decision).
 *
 * No localStorage / sessionStorage — Tauri WebView doesn't reliably
 * surface them and the CLAUDE.md constraint forbids browser storage
 * across the whole app. The bot's authoritative state lives in its
 * Supabase project; this store is in-memory cache only.
 *
 * Frozen-empty references for "no data yet" selectors follow the
 * `useSyncExternalStore` pattern documented in `src/store/macro.ts` —
 * unknown keys don't mint a fresh empty array each render.
 */

import { create } from "zustand";

import { getTradesaAdapter } from "./connection";

import type {
  TradesaBotSetting,
  TradesaConnectionState,
  TradesaConnectionStatus,
  TradesaCostRollup,
  TradesaDecision,
  TradesaDiscoveryHypothesis,
  TradesaKillSwitchEvent,
  TradesaMetaAgentRun,
  TradesaReflectionNote,
  TradesaSentinelBlock,
  TradesaSettingsDrift,
  TradesaTrade,
  TradesaTuningProposal,
} from "../../types/tradesa_v2";

import type { TradesaBotHealthLike } from "./connection";

const EMPTY_ARRAY: readonly never[] = Object.freeze([] as never[]);

/** Polling cadences per panel — picked from Tradesa V2's write cadence. */
export const POLL_CADENCE_MS = {
  /** Connection probe — fires on every panel mount + every 30s afterwards. */
  status: 30_000,
  /** Heartbeat panel — bot writes a fresh row every ≤30s. */
  health: 15_000,
  /** Open positions — close-out is the most time-sensitive read. */
  positions: 10_000,
  /** Brain decisions — Router LLM fires only on watcher events; 30s plenty. */
  decisions: 30_000,
  /** Sentinel block counts — change rarely; 60s is fine. */
  sentinel: 60_000,
  /** Settings — bot reloads every 55s on its side; 60s. */
  settings: 60_000,
  /** Cost rollup — updated per LLM call; 60s. */
  cost: 60_000,
  /** Meta-agent output streams — slow cadence; 120s. */
  metaAgents: 120_000,
  /** Closed-trade history — append-only; 5 min. */
  tradeHistory: 300_000,
} as const;

interface FetchState<T> {
  data: T | undefined;
  /** Epoch ms of the last successful fetch. */
  fetchedAt: number | null;
  /** Whether a fetch is in flight right now. */
  inflight: boolean;
  /** Last error message, if the most recent fetch failed. */
  error: string | null;
}

function freshFetchState<T>(): FetchState<T> {
  return { data: undefined, fetchedAt: null, inflight: false, error: null };
}

interface TradesaState {
  /** Connection probe result — drives the graceful-degradation UX. */
  connection: TradesaConnectionState | null;

  // Per-panel fetch states (typed shells; populated by refresh actions).
  positions: FetchState<TradesaTrade[]>;
  tradeHistory: FetchState<TradesaTrade[]>;
  decisions: FetchState<TradesaDecision[]>;
  metaAgentRuns: FetchState<TradesaMetaAgentRun[]>;
  health: FetchState<{
    latest: TradesaBotHealthLike | null;
    recent_kill_switch_events: TradesaKillSwitchEvent[];
  }>;
  killSwitchEvents: FetchState<TradesaKillSwitchEvent[]>;
  sentinelBlocks: FetchState<TradesaSentinelBlock[]>;
  settings: FetchState<TradesaBotSetting[]>;
  settingsDrift: FetchState<TradesaSettingsDrift[]>;
  tuningProposals: FetchState<TradesaTuningProposal[]>;
  discoveryHypotheses: FetchState<TradesaDiscoveryHypothesis[]>;
  reflectionNotes: FetchState<TradesaReflectionNote[]>;
  costToday: FetchState<TradesaCostRollup>;

  // Actions
  setConnection: (state: TradesaConnectionState | null) => void;
  refreshConnection: () => Promise<void>;
  refreshPositions: () => Promise<void>;
  refreshTradeHistory: () => Promise<void>;
  refreshDecisions: () => Promise<void>;
  refreshMetaAgentRuns: (opts?: { kind?: string }) => Promise<void>;
  refreshHealth: () => Promise<void>;
  refreshKillSwitchEvents: () => Promise<void>;
  refreshSentinel: () => Promise<void>;
  refreshSettings: () => Promise<void>;
  refreshSettingsDrift: () => Promise<void>;
  refreshMetaAgentSurface: (kind: "tuning" | "discovery" | "reflection") => Promise<void>;
  refreshCostToday: () => Promise<void>;
  reset: () => void;
}

/**
 * Wrap an adapter call into the standard FetchState lifecycle: set inflight,
 * try, set data + fetchedAt, catch error, clear inflight.
 */
function makeRefresher<T>(
  set: (fn: (s: TradesaState) => Partial<TradesaState>) => void,
  fieldName: keyof TradesaState,
  loader: () => Promise<T>,
): () => Promise<void> {
  return async () => {
    set((s) => ({
      [fieldName]: { ...(s[fieldName] as FetchState<T>), inflight: true, error: null },
    }));
    try {
      const data = await loader();
      set(() => ({
        [fieldName]: { data, fetchedAt: Date.now(), inflight: false, error: null },
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      set((s) => ({
        [fieldName]: {
          ...(s[fieldName] as FetchState<T>),
          inflight: false,
          error: message,
        },
      }));
    }
  };
}

export const useTradesaStore = create<TradesaState>((set) => {
  // Build refreshers lazily so they pick up the adapter at call time
  // (the test hook may swap it between renders).
  const refresh = {
    positions: () => getTradesaAdapter().listOpenPositions(),
    tradeHistory: () => getTradesaAdapter().listClosedTrades(),
    decisions: () => getTradesaAdapter().listDecisions(),
    metaAgentRuns: (opts?: { kind?: string }) => getTradesaAdapter().listMetaAgentRuns(opts),
    health: () => getTradesaAdapter().getHealth(),
    killSwitchEvents: () => getTradesaAdapter().listKillSwitchEvents(),
    sentinel: () => getTradesaAdapter().listSentinelBlocks(),
    settings: () => getTradesaAdapter().listSettings(),
    settingsDrift: () => getTradesaAdapter().getSettingsDrift(),
    tuning: () => getTradesaAdapter().listTuningProposals(),
    discovery: () => getTradesaAdapter().listDiscoveryHypotheses(),
    reflection: () => getTradesaAdapter().listReflectionNotes(),
    cost: () => getTradesaAdapter().getCostToday(),
  };

  return {
    connection: null,
    positions: freshFetchState(),
    tradeHistory: freshFetchState(),
    decisions: freshFetchState(),
    metaAgentRuns: freshFetchState(),
    health: freshFetchState(),
    killSwitchEvents: freshFetchState(),
    sentinelBlocks: freshFetchState(),
    settings: freshFetchState(),
    settingsDrift: freshFetchState(),
    tuningProposals: freshFetchState(),
    discoveryHypotheses: freshFetchState(),
    reflectionNotes: freshFetchState(),
    costToday: freshFetchState(),

    setConnection: (state) => set(() => ({ connection: state })),

    refreshConnection: async () => {
      try {
        const state = await getTradesaAdapter().probeStatus();
        set(() => ({ connection: state }));
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        set(() => ({
          connection: {
            status: "supabase-error",
            message,
            checked_at: Date.now(),
            last_heartbeat_at: null,
            heartbeat_age_s: null,
            bot_mode: null,
            kill_switch_engaged: null,
          },
        }));
      }
    },

    refreshPositions: makeRefresher(set, "positions", refresh.positions),
    refreshTradeHistory: makeRefresher(set, "tradeHistory", refresh.tradeHistory),
    refreshDecisions: makeRefresher(set, "decisions", refresh.decisions),
    refreshMetaAgentRuns: async (opts) => {
      const refresher = makeRefresher(set, "metaAgentRuns", () => refresh.metaAgentRuns(opts));
      await refresher();
    },
    refreshHealth: makeRefresher(set, "health", refresh.health),
    refreshKillSwitchEvents: makeRefresher(set, "killSwitchEvents", refresh.killSwitchEvents),
    refreshSentinel: makeRefresher(set, "sentinelBlocks", refresh.sentinel),
    refreshSettings: makeRefresher(set, "settings", refresh.settings),
    refreshSettingsDrift: makeRefresher(set, "settingsDrift", refresh.settingsDrift),
    refreshMetaAgentSurface: async (kind) => {
      // Specialize the makeRefresher generic per branch — using a
      // single dispatch table forces TypeScript to widen the loader
      // function to a union, which then doesn't match the field type.
      if (kind === "tuning") {
        const refresher = makeRefresher<TradesaTuningProposal[]>(
          set,
          "tuningProposals",
          refresh.tuning,
        );
        await refresher();
      } else if (kind === "discovery") {
        const refresher = makeRefresher<TradesaDiscoveryHypothesis[]>(
          set,
          "discoveryHypotheses",
          refresh.discovery,
        );
        await refresher();
      } else {
        const refresher = makeRefresher<TradesaReflectionNote[]>(
          set,
          "reflectionNotes",
          refresh.reflection,
        );
        await refresher();
      }
    },
    refreshCostToday: makeRefresher(set, "costToday", refresh.cost),

    reset: () =>
      set(() => ({
        connection: null,
        positions: freshFetchState(),
        tradeHistory: freshFetchState(),
        decisions: freshFetchState(),
        metaAgentRuns: freshFetchState(),
        health: freshFetchState(),
        killSwitchEvents: freshFetchState(),
        sentinelBlocks: freshFetchState(),
        settings: freshFetchState(),
        settingsDrift: freshFetchState(),
        tuningProposals: freshFetchState(),
        discoveryHypotheses: freshFetchState(),
        reflectionNotes: freshFetchState(),
        costToday: freshFetchState(),
      })),
  };
});

// ---------------------------------------------------------------------------
// Selector helpers
// ---------------------------------------------------------------------------

/** Map a connection status to a human-readable label. */
export const STATUS_LABEL: Record<TradesaConnectionStatus, string> = {
  healthy: "Bot online",
  connecting: "Connecting…",
  unauthenticated: "Not configured",
  "bot-offline": "Bot offline",
  "supabase-error": "Supabase error",
  partial: "Partial data",
};

/** Map a connection status to a banner color hint. */
export const STATUS_TONE: Record<TradesaConnectionStatus, "ok" | "warn" | "error" | "muted"> = {
  healthy: "ok",
  connecting: "muted",
  unauthenticated: "muted",
  "bot-offline": "error",
  "supabase-error": "error",
  partial: "warn",
};

/** Convenience: returns a frozen empty array when the data is undefined. */
export function arrayOrEmpty<T>(value: T[] | undefined): readonly T[] {
  return value ?? EMPTY_ARRAY;
}
