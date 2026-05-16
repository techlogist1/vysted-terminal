"""Tradesa V2 wrapper plugin Pydantic models — v0.6.5.

Hand-maintained Python mirror of ``types/tradesa_v2.ts``. When a TypeScript
interface changes, update the matching model here in the same commit (see
CLAUDE.md Gotchas — ``types/data.ts`` precedent).

Every model carries ``ConfigDict(extra="forbid")`` so schema drift surfaces
as ``ValidationError`` instead of silent acceptance — important here because
Tradesa V2 is an evolving project (Stage F+/G+ as of v0.6.5; new migration
files land monthly) and Vysted's wrapper must fail loudly rather than ship
silently-stale data.

The wrapper is READ-ONLY by API surface. None of these models have a
companion writer in ``bridge/supabase_sync.py`` shape — Tradesa V2 owns
all writes to its own Supabase project; Vysted only reads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Connection state (graceful degradation)
# ---------------------------------------------------------------------------

TradesaConnectionStatus = Literal[
    "healthy",
    "connecting",
    "unauthenticated",
    "bot-offline",
    "supabase-error",
    "partial",
]


class TradesaConnectionState(BaseModel):
    """Connection-state snapshot served by ``GET /tradesa-v2/status``."""

    model_config = ConfigDict(extra="forbid")

    status: TradesaConnectionStatus
    message: str
    checked_at: int
    last_heartbeat_at: int | None = None
    heartbeat_age_s: float | None = None
    bot_mode: Literal["paper", "live"] | None = None
    kill_switch_engaged: bool | None = None


# ---------------------------------------------------------------------------
# DirectorDecision (mirror of Tradesa V2 bridge/decision_schema.py)
# ---------------------------------------------------------------------------

DecisionAction = Literal["OPEN_LONG", "OPEN_SHORT", "CLOSE", "ADJUST_SL", "HOLD"]
TrailingMode = Literal["step_up", "atr_based"]
SLAdjustDirection = Literal["tighten"]


class TradesaDecision(BaseModel):
    """One row from Tradesa V2's ``decisions`` Supabase table."""

    model_config = ConfigDict(extra="forbid")

    id: str
    action: DecisionAction
    instrument: str
    size_pct: float | None = None
    leverage: int
    stop_loss_pct: float | None = None
    trailing_mode: TrailingMode = "step_up"
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    timestamp: datetime
    position_id: str | None = None
    reason: str | None = None
    new_sl_price: float | None = None
    direction: SLAdjustDirection | None = None
    created_at: int


# ---------------------------------------------------------------------------
# Trades (open + closed)
# ---------------------------------------------------------------------------

TradeSide = Literal["long", "short"]
TradeStatus = Literal["open", "closed", "reduce_only", "orphan_adopted"]


class TradesaTrade(BaseModel):
    """One row from Tradesa V2's ``trades`` table."""

    model_config = ConfigDict(extra="forbid")

    id: str
    instrument: str
    side: TradeSide
    status: TradeStatus
    opened_by_decision_id: str | None = None
    closed_by_decision_id: str | None = None
    qty: float
    entry_price: float
    exit_price: float | None = None
    stop_loss_price: float
    leverage: int
    realized_pnl: float | None = None
    order_link_id: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Bot health + heartbeat
# ---------------------------------------------------------------------------


class TradesaBotHealth(BaseModel):
    """One row from Tradesa V2's ``bot_health`` table."""

    model_config = ConfigDict(extra="forbid")

    recorded_at: datetime
    service: str
    status: str
    detail: str | None = None
    fd_count: int | None = None
    thread_count: int | None = None
    uptime_s: float | None = None


# ---------------------------------------------------------------------------
# Bot settings + drift detection
# ---------------------------------------------------------------------------


class TradesaBotSetting(BaseModel):
    """One row from Tradesa V2's ``bot_settings`` table."""

    model_config = ConfigDict(extra="forbid")

    key: str
    value: str
    description: str | None = None
    updated_at: datetime
    changed_by: str | None = None


class TradesaSettingsDrift(BaseModel):
    """One detected drift between two snapshots of ``bot_settings``."""

    model_config = ConfigDict(extra="forbid")

    key: str
    previous_value: str | None = None
    current_value: str
    changed_at: datetime
    changed_by: str | None = None


# ---------------------------------------------------------------------------
# Meta-agent runs (LLM call ledger + cost tracking)
# ---------------------------------------------------------------------------

MetaAgentKind = Literal[
    "director",
    "market_analyst",
    "pattern_analyst",
    "social_analyst",
    "news_analyst",
    "router",
    "reflection",
    "self_tuning",
    "discovery",
    "compaction",
]

MetaAgentRunStatus = Literal["running", "success", "error", "timeout"]


class TradesaMetaAgentRun(BaseModel):
    """One row from ``meta_agent_runs`` — per-LLM-call audit row."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: MetaAgentKind
    model: str
    status: MetaAgentRunStatus
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    duration_s: float = Field(ge=0.0)
    brain_decision_id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    error_class: str | None = None


class TradesaCostRollup(BaseModel):
    """Daily cost rollup from ``meta_agent_tokens_cost``."""

    model_config = ConfigDict(extra="forbid")

    date: str
    by_model: dict[str, float]
    total_usd: float = Field(ge=0.0)


# ---------------------------------------------------------------------------
# Kill-switch events (display-only)
# ---------------------------------------------------------------------------

KillSwitchSource = Literal[
    "operator_telegram",
    "self_tuning",
    "sentinel",
    "daily_loss",
    "manual_cli",
]


class TradesaKillSwitchEvent(BaseModel):
    """One row from Tradesa V2's ``kill_switch_events`` table."""

    model_config = ConfigDict(extra="forbid")

    id: str
    fired_at: datetime
    source: KillSwitchSource
    actor: str | None = None
    reason: str | None = None
    cleared_at: datetime | None = None


# ---------------------------------------------------------------------------
# Sentinel block counts
# ---------------------------------------------------------------------------


class TradesaSentinelBlock(BaseModel):
    """One row from Tradesa V2's ``sentinel_block_counts`` table."""

    model_config = ConfigDict(extra="forbid")

    gate_id: str
    gate_label: str
    today_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    last_blocked_at: datetime | None = None
    fail_closed: bool


# ---------------------------------------------------------------------------
# Meta-agent outputs (tuning / discovery / reflection)
# ---------------------------------------------------------------------------

TuningProposalStatus = Literal["pending", "approved", "rejected", "applied", "expired"]


class TradesaTuningProposal(BaseModel):
    """One row from ``tuning_proposals``."""

    model_config = ConfigDict(extra="forbid")

    id: str
    status: TuningProposalStatus
    target_key: str
    proposed_value: str
    current_value: str
    rationale: str
    queue_reason: str
    proposed_at: datetime
    resolved_at: datetime | None = None
    telegram_message_id: str | None = None


class TradesaDiscoveryHypothesis(BaseModel):
    """One row from ``discovery_hypotheses``."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    body: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["open", "approved", "rejected", "tested"]
    proposed_at: datetime
    resolved_at: datetime | None = None


class TradesaReflectionNote(BaseModel):
    """One row from ``reflection_notes``."""

    model_config = ConfigDict(extra="forbid")

    id: str
    trade_id: str
    summary: str
    tags: list[str]
    body: str
    created_at: datetime
    error_class: str | None = None


# ---------------------------------------------------------------------------
# Watcher events (Phase 1: included for future panels; v0.6.5 unused)
# ---------------------------------------------------------------------------

WatcherKind = Literal[
    "price",
    "liquidation",
    "funding",
    "oi",
    "news",
    "calendar",
    "staleness",
]


class TradesaWatcherEvent(BaseModel):
    """One row from ``watcher_events`` — normalized event from the seven watchers."""

    model_config = ConfigDict(extra="forbid")

    id: str
    kind: WatcherKind
    severity: float = Field(ge=0.0, le=1.0)
    triggered_brain: bool
    payload: str
    emitted_at: datetime


# ---------------------------------------------------------------------------
# Realtime stream events
# ---------------------------------------------------------------------------

TradesaRealtimeEventKind = Literal[
    "decision-inserted",
    "trade-opened",
    "trade-closed",
    "health-updated",
    "kill-switch-fired",
    "settings-changed",
]


class TradesaRealtimeEvent(BaseModel):
    """One realtime event landing on the SSE stream from the wrapper proxy."""

    model_config = ConfigDict(extra="forbid")

    kind: TradesaRealtimeEventKind
    emitted_at: datetime
    payload: dict[str, object]
