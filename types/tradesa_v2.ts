/**
 * Vysted Terminal — Tradesa V2 wrapper plugin contracts (v0.6.5).
 *
 * Hand-maintained TypeScript mirror of ``sidecar/models/tradesa_v2.py``.
 * When a Pydantic model changes, update the matching interface here in the
 * same commit (see CLAUDE.md Gotchas).
 *
 * Tradesa V2 is a multi-agent LLM-driven crypto perpetual-futures trading
 * bot (techlogist1/tradesa) running on Oracle VPS, paper-trading on Bybit
 * Demo. The Vysted Terminal plugin in ``plugins/tradesa-v2/`` reads the
 * bot's remote-sync state from its Supabase project. This file mirrors the
 * Supabase row shapes Vysted reads — Vysted never writes to these tables.
 *
 * v0.6.5 is READ-ONLY by operator decision: no commands flow from Vysted
 * Terminal to the bot. Write capability is v0.6.6+ scope. None of the
 * interfaces below carry a "write" companion — the omission is enforced
 * by the wrapper provider's API surface, not by convention alone.
 *
 * Reference for upstream column shapes:
 *  - ``bridge/decision_schema.py`` — DirectorDecision (mirrored as
 *    ``TradesaDecision`` below)
 *  - ``bridge/supabase_sync.py`` — the insert functions whose row shapes
 *    we read back
 *  - ``infra/migrations/v*.sql`` — Supabase DDL
 */

// ---------------------------------------------------------------------------
// Connection state (graceful degradation)
// ---------------------------------------------------------------------------

/**
 * The state the Tradesa V2 wrapper is in. Every panel renders dedicated UX
 * for each value — the plugin never crashes Vysted Terminal on a Tradesa V2
 * outage, never retries-loop, and surfaces a clear reason the user can act
 * on. The string values are stable wire identifiers.
 */
export type TradesaConnectionStatus =
  /** Healthy: Supabase reachable, fresh heartbeat (<5 min old). */
  | "healthy"
  /** Initial connect probe or post-restart catch-up in flight. */
  | "connecting"
  /** No credentials in keychain — show settings dialog. */
  | "unauthenticated"
  /** Supabase reachable but the bot's heartbeat is stale (>5 min). */
  | "bot-offline"
  /** Supabase REST / Realtime calls failing (auth error, network, etc.). */
  | "supabase-error"
  /** Some endpoints reachable, others not — partial-data UX. */
  | "partial";

/** Connection-state snapshot served by ``GET /tradesa-v2/status``. */
export interface TradesaConnectionState {
  status: TradesaConnectionStatus;
  /** Human-readable detail for the plugin-manager / panel banner. */
  message: string;
  /** Epoch milliseconds when this status was produced. */
  checked_at: number;
  /** Epoch milliseconds of the most recent ``bot_health`` row, or null. */
  last_heartbeat_at: number | null;
  /** Seconds since ``last_heartbeat_at``, or null. */
  heartbeat_age_s: number | null;
  /** Tradesa V2 paper/live mode flag if reachable, else null. */
  bot_mode: "paper" | "live" | null;
  /** True if the bot's kill switch is currently engaged. */
  kill_switch_engaged: boolean | null;
}

// ---------------------------------------------------------------------------
// DirectorDecision (mirror of bridge/decision_schema.py:DirectorDecision)
// ---------------------------------------------------------------------------

/** Brain-emitted action types. CLOSE / ADJUST_SL / HOLD never place orders. */
export type DecisionAction =
  | "OPEN_LONG"
  | "OPEN_SHORT"
  | "CLOSE"
  | "ADJUST_SL"
  | "HOLD";

/** Trailing stop mode the brain emits with OPEN actions. */
export type TrailingMode = "step_up" | "atr_based";

/** Stop-loss adjustment direction — ratchet-only, never loosen. */
export type SLAdjustDirection = "tighten";

/**
 * One row from Tradesa V2's ``decisions`` Supabase table — a structured
 * brain output the Director LLM emitted before Sentinel evaluation.
 *
 * Field ranges (validated on the bot side, defended in code):
 *  - ``leverage`` ≤ ``HARD_LEVERAGE_CAP = 4`` (bot enforces; mirror is for display)
 *  - ``size_pct`` ∈ ``[bot_settings.size_pct_min, bot_settings.size_pct_max]`` (typically [0.05, 0.10])
 *  - ``stop_loss_pct`` ∈ ``[bot_settings.stop_pct_min, bot_settings.stop_pct_max]`` (typically [0.02, 0.05])
 *  - ``confidence`` ∈ [0, 1]
 *  - ``rationale`` is truncated to 2000 chars by the bot's validator
 */
export interface TradesaDecision {
  /** Supabase row id (uuid). */
  id: string;
  action: DecisionAction;
  instrument: string;
  /** Position size as fraction of equity. Null for CLOSE / ADJUST_SL / HOLD. */
  size_pct: number | null;
  leverage: number;
  stop_loss_pct: number | null;
  trailing_mode: TrailingMode;
  confidence: number;
  rationale: string;
  /** ISO-8601 UTC string. */
  timestamp: string;
  /** For CLOSE / ADJUST_SL — the position the decision targets. */
  position_id: string | null;
  /** For CLOSE — free-text reason (separate from rationale). */
  reason: string | null;
  /** For ADJUST_SL — the new stop-loss price. */
  new_sl_price: number | null;
  /** For ADJUST_SL — always 'tighten' (ratchet-only). */
  direction: SLAdjustDirection | null;
  /** Epoch ms when the row landed in Supabase. */
  created_at: number;
}

// ---------------------------------------------------------------------------
// Trades (open + closed)
// ---------------------------------------------------------------------------

/** Whether the position is long or short. */
export type TradeSide = "long" | "short";

/** Whether the trade is currently open, closed cleanly, or in a quirky state. */
export type TradeStatus = "open" | "closed" | "reduce_only" | "orphan_adopted";

/**
 * One row from Tradesa V2's ``trades`` table. Combines OPEN + CLOSE
 * data — closed trades have non-null ``exit_*`` + ``realized_pnl``.
 */
export interface TradesaTrade {
  id: string;
  instrument: string;
  side: TradeSide;
  status: TradeStatus;
  /** Decision id that opened the trade (FK → decisions.id). */
  opened_by_decision_id: string | null;
  /** Decision id that closed the trade, if any (FK → decisions.id). */
  closed_by_decision_id: string | null;
  /** Quantity in instrument units (e.g. BTC contracts). */
  qty: number;
  /** Entry price in quote currency (USDT for Bybit perps). */
  entry_price: number;
  /** Exit price for closed trades; null for open. */
  exit_price: number | null;
  /** Stop-loss price set when the trade was opened (mandatory per bot policy). */
  stop_loss_price: number;
  /** Leverage at entry. */
  leverage: number;
  /** Realized P&L in USDT for closed trades; null for open. */
  realized_pnl: number | null;
  /** Bybit V5 orderLinkId or equivalent broker handle. */
  order_link_id: string | null;
  /** ISO-8601 UTC. */
  opened_at: string;
  /** ISO-8601 UTC for closed trades; null for open. */
  closed_at: string | null;
}

// ---------------------------------------------------------------------------
// Bot health + heartbeat
// ---------------------------------------------------------------------------

/**
 * One row from Tradesa V2's ``bot_health`` table — a heartbeat the bot
 * writes periodically. Staleness >5 minutes is the canonical "bot-offline"
 * signal the wrapper uses.
 */
export interface TradesaBotHealth {
  /** ISO-8601 UTC of the heartbeat write. */
  recorded_at: string;
  /** Bot service identifier (always "tradesa-bot" for V2). */
  service: string;
  /** "starting" | "running" | "degraded" | "stopping". */
  status: string;
  /** Optional human-readable detail. */
  detail: string | null;
  /** Open file-descriptor count at the snapshot time. */
  fd_count: number | null;
  /** Live thread count. */
  thread_count: number | null;
  /** Seconds since the bot process started. */
  uptime_s: number | null;
}

// ---------------------------------------------------------------------------
// Bot settings (config rows the bot hot-reloads every 55s)
// ---------------------------------------------------------------------------

/**
 * One row from Tradesa V2's ``bot_settings`` table. The bot loads these via
 * ``bot.settings_loader.Settings._refresh_loop`` every 55 seconds. Vysted
 * surfaces the live snapshot + drift relative to the previous snapshot the
 * plugin saw, so the operator can see what changed and when.
 *
 * Values are heterogeneous (number / string / bool / json-array depending on
 * key) — surfaced as the wire-side raw string for display, with optional
 * structured parsing on the panel side when the type is known.
 */
export interface TradesaBotSetting {
  key: string;
  /** Raw value as stored in Supabase (TEXT column on the bot side). */
  value: string;
  /** Free-text description from the bot's settings catalog. */
  description: string | null;
  /** ISO-8601 UTC of the last write to this row. */
  updated_at: string;
  /** Source of last change: "operator" | "self_tuning" | "bootstrap" | etc. */
  changed_by: string | null;
}

/** One detected drift between two snapshots of ``bot_settings``. */
export interface TradesaSettingsDrift {
  key: string;
  /** The value the plugin's last snapshot saw. */
  previous_value: string | null;
  /** The value now in Supabase. */
  current_value: string;
  /** ISO-8601 UTC of the upstream change. */
  changed_at: string;
  changed_by: string | null;
}

// ---------------------------------------------------------------------------
// Meta-agent runs (LLM call ledger + cost tracking)
// ---------------------------------------------------------------------------

/** Meta-agent kinds the bot runs. */
export type MetaAgentKind =
  | "director"
  | "market_analyst"
  | "pattern_analyst"
  | "social_analyst"
  | "news_analyst"
  | "router"
  | "reflection"
  | "self_tuning"
  | "discovery"
  | "compaction";

/** Run status the bot emits in `meta_agent_runs.status`. */
export type MetaAgentRunStatus = "running" | "success" | "error" | "timeout";

/**
 * One row from ``meta_agent_runs`` — the per-LLM-call audit row the bot
 * writes for every agent invocation. Cost rollups in the Brain panel are
 * derived from this table; the dedicated ``meta_agent_tokens_cost`` table
 * is a precomputed daily rollup for fast dashboard display.
 */
export interface TradesaMetaAgentRun {
  id: string;
  kind: MetaAgentKind;
  model: string;
  status: MetaAgentRunStatus;
  tokens_in: number;
  tokens_out: number;
  /** Cost in USD computed by the bot's pricing table. */
  cost_usd: number;
  duration_s: number;
  /** FK → decisions.id when this run produced a DirectorDecision. */
  brain_decision_id: string | null;
  /** ISO-8601 UTC. */
  started_at: string;
  /** ISO-8601 UTC; null while status === "running". */
  finished_at: string | null;
  /** Error class when status === "error" (e.g. "api_timeout", "rate_limit"). */
  error_class: string | null;
}

/** Daily cost rollup from ``meta_agent_tokens_cost``. */
export interface TradesaCostRollup {
  /** ISO date (YYYY-MM-DD). */
  date: string;
  /** Per-model breakdown — keys are model identifiers. */
  by_model: Record<string, number>;
  /** Total USD across all models for the day. */
  total_usd: number;
}

// ---------------------------------------------------------------------------
// Kill-switch events (display-only — Vysted never fires the bot's kill switch)
// ---------------------------------------------------------------------------

/** Who fired the bot's kill switch in this event. */
export type KillSwitchSource = "operator_telegram" | "self_tuning" | "sentinel" | "daily_loss" | "manual_cli";

/**
 * One row from Tradesa V2's ``kill_switch_events`` table. Vysted reads this
 * for display ONLY — the bot's kill switch lives on the bot side and is
 * triggered via Telegram or VPS-local control. v0.6.5 never fires it.
 */
export interface TradesaKillSwitchEvent {
  id: string;
  /** ISO-8601 UTC of the kill-switch fire. */
  fired_at: string;
  source: KillSwitchSource;
  /** Telegram chat id / CLI user / null. */
  actor: string | null;
  /** Free-text reason given by the actor. */
  reason: string | null;
  /** Whether the bot subsequently disengaged (manual operator re-enable). */
  cleared_at: string | null;
}

// ---------------------------------------------------------------------------
// Sentinel block counts (gate-decline stats)
// ---------------------------------------------------------------------------

/**
 * One row from Tradesa V2's ``sentinel_block_counts`` table — the
 * per-gate decline tally. Used by the Sentinel panel to show which of
 * the 12-18 sentinel gates is rejecting the most decisions today.
 */
export interface TradesaSentinelBlock {
  /** Gate identifier (e.g. "gate_06_news_blackout", "gate_09_correlation_cap"). */
  gate_id: string;
  /** Human-readable label. */
  gate_label: string;
  /** Count of declines today (UTC-day). */
  today_count: number;
  /** Total count since bot inception. */
  total_count: number;
  /** ISO-8601 UTC of the most recent decline on this gate. */
  last_blocked_at: string | null;
  /** Whether this gate is "fail_closed" — soft fail vs hard refuse. */
  fail_closed: boolean;
}

// ---------------------------------------------------------------------------
// Meta-agent outputs (tuning / discovery / reflection)
// ---------------------------------------------------------------------------

/** Status of a self-tuning proposal in the queue. */
export type TuningProposalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "applied"
  | "expired";

/**
 * One row from ``tuning_proposals``. The bot's self-tuning agent proposes
 * config changes; operator approves via Telegram inline keyboard. v0.6.5
 * surfaces these for read-only display — Vysted never approves or rejects.
 */
export interface TradesaTuningProposal {
  id: string;
  status: TuningProposalStatus;
  /** The ``bot_settings.key`` the proposal targets. */
  target_key: string;
  /** Value the proposal wants to change to. */
  proposed_value: string;
  /** Value at the time the proposal was raised. */
  current_value: string;
  /** Free-text rationale from the tuning agent. */
  rationale: string;
  /** Queue-reason category (e.g. "loss_streak", "drawdown_breach"). */
  queue_reason: string;
  /** ISO-8601 UTC. */
  proposed_at: string;
  /** ISO-8601 UTC; null until terminal. */
  resolved_at: string | null;
  /** Telegram message id when raised, for cross-reference. */
  telegram_message_id: string | null;
}

/**
 * One row from ``discovery_hypotheses``. Re-enabled at closed_trades ≥ 100.
 */
export interface TradesaDiscoveryHypothesis {
  id: string;
  /** Short title the discovery agent emitted. */
  title: string;
  /** Long-form hypothesis body. */
  body: string;
  /** Confidence the agent assigned, [0, 1]. */
  confidence: number;
  /** Whether the operator approved this hypothesis for further testing. */
  status: "open" | "approved" | "rejected" | "tested";
  proposed_at: string;
  resolved_at: string | null;
}

/**
 * One row from ``reflection_notes``. The reflection agent writes one note
 * per closed trade, summarizing what worked / didn't.
 */
export interface TradesaReflectionNote {
  id: string;
  /** FK → trades.id of the closed trade this reflects on. */
  trade_id: string;
  /** Short summary the reflection agent emitted. */
  summary: string;
  /** Lesson-tag taxonomy (e.g. "entry_timing", "stop_placement"). */
  tags: string[];
  /** Long-form analysis body. */
  body: string;
  /** ISO-8601 UTC. */
  created_at: string;
  /** Error class when the reflection agent failed (then summary is fallback). */
  error_class: string | null;
}

// ---------------------------------------------------------------------------
// Watcher events (Phase 1: included for future panels; v0.6.5 unused)
// ---------------------------------------------------------------------------

/** Watcher kind the bot's event router consumes. */
export type WatcherKind =
  | "price"
  | "liquidation"
  | "funding"
  | "oi"
  | "news"
  | "calendar"
  | "staleness";

/**
 * One row from ``watcher_events`` — a normalized event the bot's seven
 * watchers emit into the Router LLM. Not surfaced as a v0.6.5 panel but
 * the type lives here so future panels (v0.6.6+ event-stream panel) can
 * consume it without a migration.
 */
export interface TradesaWatcherEvent {
  id: string;
  kind: WatcherKind;
  /** Severity 0–1 the watcher assigned. */
  severity: number;
  /** Whether the Router LLM woke the brain on this event. */
  triggered_brain: boolean;
  /** Free-text payload from the watcher. */
  payload: string;
  /** ISO-8601 UTC. */
  emitted_at: string;
}

// ---------------------------------------------------------------------------
// Realtime stream events (SSE fan-out from the sidecar proxy)
// ---------------------------------------------------------------------------

/**
 * Kinds of Supabase ``postgres_changes`` events the wrapper subscribes to
 * and fans out via SSE. The frontend store applies these to its in-memory
 * snapshot incrementally to keep panels live without re-fetching the full
 * page.
 */
export type TradesaRealtimeEventKind =
  | "decision-inserted"
  | "trade-opened"
  | "trade-closed"
  | "health-updated"
  | "kill-switch-fired"
  | "settings-changed";

/** One realtime event landing on the SSE stream. */
export interface TradesaRealtimeEvent {
  kind: TradesaRealtimeEventKind;
  /** ISO-8601 UTC the event landed at the wrapper. */
  emitted_at: string;
  /** The new row (typed by the panel that consumes it; opaque on the wire). */
  payload: unknown;
}
