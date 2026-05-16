"""Pydantic models for the Vysted Terminal sidecar.

Every model here mirrors a TypeScript interface by hand:

  - Phase 1 data layer  ↔ ``types/data.ts``
  - Phase 3 agent layer ↔ ``types/ai.ts`` (via ``models/agent.py``)
  - Phase 4 workflow    ↔ ``types/workflow.ts``
  - Phase 4 backtest    ↔ ``types/backtest.ts``
  - Phase 5 broker      ↔ ``types/broker.ts``
  - Phase 5 safety      ↔ ``types/safety.ts``

When a model changes, update its TypeScript mirror in the same commit
(see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from models.audit_log import AUDIT_LOG_DB_FILENAME, AUDIT_LOG_DDL, AUDIT_LOG_NAMESPACE
from models.backtest import (
    BacktestFeeModel,
    BacktestMetrics,
    BacktestRequest,
    BacktestResult,
    BacktestRunEvent,
    BacktestStrategySpec,
    BacktestSummary,
    BacktestTrade,
    EquityCurvePoint,
    WalkForwardSlice,
)
from models.broker import (
    AccountSummary,
    BrokerCapabilities,
    BrokerConfirmRequest,
    BrokerConnectRequest,
    BrokerOrderProposal,
    BrokerOrderResult,
    BrokerPosition,
    BrokerState,
)
from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    FinancialStatement,
    Fundamentals,
    IncomeStatement,
    StatementLine,
)
from models.indicators import (
    IndicatorLine,
    IndicatorPoint,
    IndicatorResponse,
    IndicatorSeries,
    VolumeProfile,
    VolumeProfileBucket,
)
from models.market import (
    MacroObservation,
    MacroSeries,
    OHLCVBar,
    OHLCVSeries,
    Quote,
)
from models.news import NewsItem
from models.portfolio import Position, PositionInput
from models.safety import (
    AiOrderGateProposal,
    AuditLogAppendRequest,
    AuditLogEntry,
    DisclaimerAcknowledgment,
    KillSwitchEvent,
    KillSwitchFireResult,
    PositionLimits,
    StaticIpStatus,
)
from models.workflow import (
    NodeRunResult,
    WorkflowEdge,
    WorkflowNode,
    WorkflowRunEvent,
    WorkflowRunRequest,
    WorkflowRunResult,
    WorkflowSpec,
)

__all__ = [
    "AUDIT_LOG_DB_FILENAME",
    "AUDIT_LOG_DDL",
    "AUDIT_LOG_NAMESPACE",
    "AccountSummary",
    "AiOrderGateProposal",
    "AnalystRating",
    "AuditLogAppendRequest",
    "AuditLogEntry",
    "BacktestFeeModel",
    "BacktestMetrics",
    "BacktestRequest",
    "BacktestResult",
    "BacktestRunEvent",
    "BacktestStrategySpec",
    "BacktestSummary",
    "BacktestTrade",
    "BalanceSheet",
    "BrokerCapabilities",
    "BrokerConfirmRequest",
    "BrokerConnectRequest",
    "BrokerOrderProposal",
    "BrokerOrderResult",
    "BrokerPosition",
    "BrokerState",
    "CashFlowStatement",
    "DisclaimerAcknowledgment",
    "EquityCurvePoint",
    "FinancialStatement",
    "Fundamentals",
    "IncomeStatement",
    "IndicatorLine",
    "IndicatorPoint",
    "IndicatorResponse",
    "IndicatorSeries",
    "KillSwitchEvent",
    "KillSwitchFireResult",
    "MacroObservation",
    "MacroSeries",
    "NewsItem",
    "NodeRunResult",
    "OHLCVBar",
    "OHLCVSeries",
    "Position",
    "PositionInput",
    "PositionLimits",
    "Quote",
    "StatementLine",
    "StaticIpStatus",
    "VolumeProfile",
    "VolumeProfileBucket",
    "WalkForwardSlice",
    "WorkflowEdge",
    "WorkflowNode",
    "WorkflowRunEvent",
    "WorkflowRunRequest",
    "WorkflowRunResult",
    "WorkflowSpec",
]
