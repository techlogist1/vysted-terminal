"""Pydantic models for the Vysted Terminal sidecar.

Every model here mirrors a TypeScript interface by hand:

  - Phase 1 data layer  ↔ ``types/data.ts``
  - Phase 3 agent layer ↔ ``types/ai.ts`` (via ``models/agent.py``)
  - Phase 4 workflow    ↔ ``types/workflow.ts``
  - Phase 4 backtest    ↔ ``types/backtest.ts``

When a model changes, update its TypeScript mirror in the same commit
(see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from models.announcements import (
    Announcement,
    AnnouncementsResponse,
    ResultsCalendarResponse,
    ResultsEvent,
    ShareholdingPattern,
    ShareholdingResponse,
)
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
    "AnalystRating",
    "Announcement",
    "AnnouncementsResponse",
    "BacktestFeeModel",
    "BacktestMetrics",
    "BacktestRequest",
    "BacktestResult",
    "BacktestRunEvent",
    "BacktestStrategySpec",
    "BacktestSummary",
    "BacktestTrade",
    "BalanceSheet",
    "CashFlowStatement",
    "EquityCurvePoint",
    "FinancialStatement",
    "Fundamentals",
    "IncomeStatement",
    "IndicatorLine",
    "IndicatorPoint",
    "IndicatorResponse",
    "IndicatorSeries",
    "MacroObservation",
    "MacroSeries",
    "NewsItem",
    "NodeRunResult",
    "OHLCVBar",
    "OHLCVSeries",
    "Position",
    "PositionInput",
    "Quote",
    "ResultsCalendarResponse",
    "ResultsEvent",
    "ShareholdingPattern",
    "ShareholdingResponse",
    "StatementLine",
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
