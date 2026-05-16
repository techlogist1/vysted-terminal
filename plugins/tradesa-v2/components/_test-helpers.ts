/**
 * Tradesa V2 wrapper — test helpers for the panel Vitest suites.
 *
 * Centralises the boilerplate the per-panel tests share: stubbing the
 * connection adapter, resetting the Zustand store, building realistic
 * sample rows for each Supabase table mirror.
 *
 * Each panel test file imports these helpers and only mints the rows
 * its panel renders — no panel-specific data lives here.
 */

import { vi } from "vitest";

import { _setAdapterForTests, type TradingBotReadAdapter } from "../connection";
import { useTradesaStore } from "../store";

import type {
  TradesaBotSetting,
  TradesaConnectionState,
  TradesaConnectionStatus,
  TradesaCostRollup,
  TradesaDecision,
  TradesaDiscoveryHypothesis,
  TradesaKillSwitchEvent,
  TradesaReflectionNote,
  TradesaSentinelBlock,
  TradesaSettingsDrift,
  TradesaTrade,
  TradesaTuningProposal,
} from "../../../types/tradesa_v2";
import type { TradesaBotHealthLike } from "../connection";

// ---------------------------------------------------------------------------
// Connection state builders
// ---------------------------------------------------------------------------

const baseTimestamp = Date.parse("2026-05-17T12:00:00Z");

export function makeConnectionState(
  status: TradesaConnectionStatus,
  overrides: Partial<TradesaConnectionState> = {},
): TradesaConnectionState {
  return {
    status,
    message:
      status === "healthy"
        ? "Bot online; last heartbeat 12s ago."
        : status === "unauthenticated"
          ? "No credentials configured."
          : status === "bot-offline"
            ? "Bot heartbeat stale (>5 min)."
            : status === "supabase-error"
              ? "Supabase REST returned 401."
              : status === "partial"
                ? "Some endpoints unreachable."
                : "Probing…",
    checked_at: baseTimestamp,
    last_heartbeat_at: status === "healthy" ? baseTimestamp - 12_000 : null,
    heartbeat_age_s: status === "healthy" ? 12 : status === "bot-offline" ? 600 : null,
    bot_mode:
      status === "healthy" || status === "partial" || status === "bot-offline" ? "paper" : null,
    kill_switch_engaged: status === "healthy" ? false : null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Sample data builders
// ---------------------------------------------------------------------------

export function makeTrade(overrides: Partial<TradesaTrade> = {}): TradesaTrade {
  return {
    id: "trade-1",
    instrument: "BTCUSDT",
    side: "long",
    status: "open",
    opened_by_decision_id: "dec-1",
    closed_by_decision_id: null,
    qty: 0.5,
    entry_price: 65000,
    exit_price: null,
    stop_loss_price: 63000,
    leverage: 3,
    realized_pnl: null,
    order_link_id: "lnk-1",
    opened_at: "2026-05-17T11:55:00Z",
    closed_at: null,
    ...overrides,
  };
}

export function makeDecision(overrides: Partial<TradesaDecision> = {}): TradesaDecision {
  return {
    id: "dec-1",
    action: "OPEN_LONG",
    instrument: "BTCUSDT",
    size_pct: 0.05,
    leverage: 3,
    stop_loss_pct: 0.03,
    trailing_mode: "step_up",
    confidence: 0.72,
    rationale: "Pattern + market alignment with bullish news flow.",
    timestamp: "2026-05-17T11:55:00Z",
    position_id: null,
    reason: null,
    new_sl_price: null,
    direction: null,
    created_at: baseTimestamp - 60_000,
    ...overrides,
  };
}

export function makeCostRollup(overrides: Partial<TradesaCostRollup> = {}): TradesaCostRollup {
  return {
    date: "2026-05-17",
    by_model: { "gpt-4o": 1.23, "claude-3-haiku": 0.45 },
    total_usd: 1.68,
    ...overrides,
  };
}

export function makeSentinelBlock(
  overrides: Partial<TradesaSentinelBlock> = {},
): TradesaSentinelBlock {
  return {
    gate_id: "gate_06_news_blackout",
    gate_label: "News-blackout window",
    today_count: 4,
    total_count: 137,
    last_blocked_at: "2026-05-17T11:50:00Z",
    fail_closed: true,
    ...overrides,
  };
}

export function makeKillSwitchEvent(
  overrides: Partial<TradesaKillSwitchEvent> = {},
): TradesaKillSwitchEvent {
  return {
    id: "ks-1",
    fired_at: "2026-05-17T10:00:00Z",
    source: "operator_telegram",
    actor: "lokavya",
    reason: "Pre-market volatility spike — pausing for review.",
    cleared_at: "2026-05-17T10:45:00Z",
    ...overrides,
  };
}

export function makeBotHealth(overrides: Partial<TradesaBotHealthLike> = {}): TradesaBotHealthLike {
  return {
    recorded_at: "2026-05-17T11:59:48Z",
    service: "tradesa-bot",
    status: "running",
    detail: null,
    fd_count: 142,
    thread_count: 23,
    uptime_s: 86400 + 7200, // 1d 2h
    ...overrides,
  };
}

export function makeBotSetting(overrides: Partial<TradesaBotSetting> = {}): TradesaBotSetting {
  return {
    key: "size_pct_max",
    value: "0.10",
    description: "Maximum position size as fraction of equity.",
    updated_at: "2026-05-17T08:00:00Z",
    changed_by: "operator",
    ...overrides,
  };
}

export function makeSettingsDrift(
  overrides: Partial<TradesaSettingsDrift> = {},
): TradesaSettingsDrift {
  return {
    key: "stop_pct_max",
    previous_value: "0.04",
    current_value: "0.05",
    changed_at: "2026-05-17T11:30:00Z",
    changed_by: "self_tuning",
    ...overrides,
  };
}

export function makeTuningProposal(
  overrides: Partial<TradesaTuningProposal> = {},
): TradesaTuningProposal {
  return {
    id: "tp-1",
    status: "pending",
    target_key: "size_pct_max",
    proposed_value: "0.08",
    current_value: "0.10",
    rationale: "5-day loss streak; reduce exposure until pattern recovers.",
    queue_reason: "loss_streak",
    proposed_at: "2026-05-17T09:00:00Z",
    resolved_at: null,
    telegram_message_id: "tg-1",
    ...overrides,
  };
}

export function makeDiscoveryHypothesis(
  overrides: Partial<TradesaDiscoveryHypothesis> = {},
): TradesaDiscoveryHypothesis {
  return {
    id: "dh-1",
    title: "Asian session breakout shows higher win-rate",
    body: "Trades opened during 00:00-04:00 UTC show 12% higher win-rate than overall.",
    confidence: 0.68,
    status: "open",
    proposed_at: "2026-05-17T07:00:00Z",
    resolved_at: null,
    ...overrides,
  };
}

export function makeReflectionNote(
  overrides: Partial<TradesaReflectionNote> = {},
): TradesaReflectionNote {
  return {
    id: "rn-1",
    trade_id: "trade-abc12345",
    summary: "Stop hit just before reversal — entry timing too early.",
    tags: ["entry_timing", "stop_placement"],
    body: "Position opened during low-conviction signal; reversal happened 5min after stop.",
    created_at: "2026-05-17T11:00:00Z",
    error_class: null,
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Adapter stub
// ---------------------------------------------------------------------------

export interface StubAdapterOverrides {
  probeState?: TradesaConnectionState;
  positions?: TradesaTrade[];
  tradeHistory?: TradesaTrade[];
  decisions?: TradesaDecision[];
  cost?: TradesaCostRollup;
  health?: {
    latest: TradesaBotHealthLike | null;
    recent_kill_switch_events: TradesaKillSwitchEvent[];
  };
  killSwitch?: TradesaKillSwitchEvent[];
  sentinel?: TradesaSentinelBlock[];
  settings?: TradesaBotSetting[];
  drift?: TradesaSettingsDrift[];
  tuning?: TradesaTuningProposal[];
  discovery?: TradesaDiscoveryHypothesis[];
  reflection?: TradesaReflectionNote[];
}

/**
 * Install a stub adapter that returns the supplied collections for each
 * read method. Missing collections default to empty arrays / null —
 * mirrors a fresh / empty bot state.
 */
export function installStubAdapter(overrides: StubAdapterOverrides = {}): TradingBotReadAdapter {
  const adapter: TradingBotReadAdapter = {
    probeStatus: vi.fn(async () => overrides.probeState ?? makeConnectionState("healthy")),
    listOpenPositions: vi.fn(async () => overrides.positions ?? []),
    listClosedTrades: vi.fn(async () => overrides.tradeHistory ?? []),
    listDecisions: vi.fn(async () => overrides.decisions ?? []),
    listMetaAgentRuns: vi.fn(async () => []),
    getCostToday: vi.fn(
      async () => overrides.cost ?? makeCostRollup({ by_model: {}, total_usd: 0 }),
    ),
    getHealth: vi.fn(
      async () => overrides.health ?? { latest: null, recent_kill_switch_events: [] },
    ),
    listKillSwitchEvents: vi.fn(async () => overrides.killSwitch ?? []),
    listSentinelBlocks: vi.fn(async () => overrides.sentinel ?? []),
    listSettings: vi.fn(async () => overrides.settings ?? []),
    getSettingsDrift: vi.fn(async () => overrides.drift ?? []),
    listTuningProposals: vi.fn(async () => overrides.tuning ?? []),
    listDiscoveryHypotheses: vi.fn(async () => overrides.discovery ?? []),
    listReflectionNotes: vi.fn(async () => overrides.reflection ?? []),
  };
  _setAdapterForTests(adapter);
  return adapter;
}

/**
 * Force the store's connection slice to a known state without going
 * through the probeStatus adapter call. Useful for tests that want to
 * render a panel in a specific state synchronously.
 */
export function setConnectionState(state: TradesaConnectionState | null): void {
  useTradesaStore.setState({ connection: state });
}

export function resetStore(): void {
  useTradesaStore.getState().reset();
  _setAdapterForTests(null);
}
