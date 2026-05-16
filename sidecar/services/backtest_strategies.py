"""Concrete backtest strategy archetypes — Teammate K v0.5.0 deliverable.

The Phase-4 foundation ships an event-driven engine + abstract
:class:`BacktestStrategy` + a strategy registry in
``services.backtest_engine``. This module fills the registry with three
production-ready archetypes the AI Strategy Critic interrogates as part
of the BLUEPRINT Use Case 2 demo:

- ``mean_reversion`` — z-score on N-day return; enter when z falls below
  ``entry_z`` (typically a negative number), exit when z rises back above
  ``exit_z``. Position-sizes in fixed share quantity per the brief.
- ``trend_following`` — golden-cross of a short SMA over a long SMA, with
  a 200-day MA price filter. Buys when short MA crosses above long MA AND
  the close trades above the 200-day MA; sells on the opposite cross.
- ``regime_aware`` — realised-volatility-conditioned position sizing on a
  simple momentum signal. Small position in high-vol regimes, large
  position in low-vol regimes. Designed to demonstrate regime adaptation
  for the Critic's regime-robustness critique section.

Each strategy keeps its own per-symbol rolling buffer because the engine
streams bars one at a time (single-asset trading per BLUEPRINT §10 Use
Case 2). Multi-symbol behaviour collapses to per-symbol state — a
strategy that signals on AAPL doesn't read MSFT's history.

Strategies are deliberately permissive about missing optional params —
``params.get(key, default)`` everywhere — so the BacktestRequest's
``params`` dict can be partial when the frontend renders defaults.

The module-level :func:`register_all` is invoked exactly once at sidecar
startup (``main.py``); :func:`reset_for_tests` clears registrations and
the per-strategy state stores between unit tests.
"""

from __future__ import annotations

import logging
import statistics
from collections import deque
from typing import Any

from services.backtest_engine import (
    BacktestOrderIntent,
    BacktestStrategy,
    Bar,
    SimPortfolio,
    register_strategy,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strategy specs — surfaced by GET /backtest/strategies for the frontend picker
# ---------------------------------------------------------------------------


STRATEGY_SPECS: list[dict[str, Any]] = [
    {
        "id": "mean_reversion",
        "name": "Mean Reversion (Z-Score)",
        "description": (
            "Enter long when the N-day return z-score drops below entry_z; "
            "exit when it recovers above exit_z. Fixed share size."
        ),
        "paramsSchema": {
            "type": "object",
            "properties": {
                "window": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 5,
                    "maximum": 200,
                    "description": "Rolling window for the z-score (bars).",
                },
                "entry_z": {
                    "type": "number",
                    "default": -2.0,
                    "description": "Enter long when z drops below this (typically negative).",
                },
                "exit_z": {
                    "type": "number",
                    "default": 0.0,
                    "description": "Exit when z rises above this.",
                },
                "position_size": {
                    "type": "number",
                    "default": 100,
                    "minimum": 1,
                    "description": "Fixed share quantity per trade.",
                },
            },
        },
    },
    {
        "id": "trend_following",
        "name": "Trend Following (Golden Cross)",
        "description": (
            "Buy when short SMA crosses above long SMA and the close is "
            "above the 200-day MA; sell on the opposite cross."
        ),
        "paramsSchema": {
            "type": "object",
            "properties": {
                "short_window": {
                    "type": "integer",
                    "default": 50,
                    "minimum": 2,
                    "maximum": 200,
                    "description": "Short SMA window (bars).",
                },
                "long_window": {
                    "type": "integer",
                    "default": 200,
                    "minimum": 5,
                    "maximum": 500,
                    "description": "Long SMA window (bars).",
                },
                "position_size": {
                    "type": "number",
                    "default": 100,
                    "minimum": 1,
                    "description": "Fixed share quantity per trade.",
                },
            },
        },
    },
    {
        "id": "regime_aware",
        "name": "Regime-Aware Momentum",
        "description": (
            "Buy on a simple positive-momentum signal; size the position "
            "from the 20-day realised volatility (small in high-vol, large "
            "in low-vol). Demonstrates regime adaptation."
        ),
        "paramsSchema": {
            "type": "object",
            "properties": {
                "vol_window": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 5,
                    "maximum": 100,
                    "description": "Rolling window for realised volatility.",
                },
                "low_vol_size": {
                    "type": "number",
                    "default": 100,
                    "minimum": 1,
                    "description": "Position size in low-vol regimes.",
                },
                "high_vol_size": {
                    "type": "number",
                    "default": 25,
                    "minimum": 1,
                    "description": "Position size in high-vol regimes.",
                },
                "vol_threshold": {
                    "type": "number",
                    "default": 0.02,
                    "description": "Daily-return stdev above which the regime is 'high vol'.",
                },
            },
        },
    },
]


def list_strategy_specs() -> list[dict[str, Any]]:
    """Return the JSON-shaped metadata for the registered strategies.

    The frontend's strategy picker renders the params form from
    ``paramsSchema``. Kept as a plain ``dict`` rather than a Pydantic
    model so the schema sub-object stays free-form.
    """
    return [dict(spec) for spec in STRATEGY_SPECS]


# ---------------------------------------------------------------------------
# 1. Mean reversion — z-score on N-day return
# ---------------------------------------------------------------------------


class MeanReversionStrategy(BacktestStrategy):
    """Z-score mean-reversion entry; threshold-based exit.

    Maintains a per-symbol ring buffer of the last ``window`` *bar
    returns* (not raw closes — z-scoring returns is the standard
    formulation; z-scoring prices is misleading when the underlying has
    a deterministic drift). When the rolling z falls below ``entry_z``
    and the strategy is flat in that symbol, emit a long entry of
    ``position_size`` shares. When z rises above ``exit_z`` and the
    strategy is long, emit a flatten.
    """

    NAME = "mean_reversion"

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self.window = int(params.get("window", 20))
        self.entry_z = float(params.get("entry_z", -2.0))
        self.exit_z = float(params.get("exit_z", 0.0))
        self.position_size = float(params.get("position_size", 100))
        # Per-symbol rolling-return buffers + last-close for return calc.
        self._returns: dict[str, deque[float]] = {}
        self._last_close: dict[str, float] = {}

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        intents: list[BacktestOrderIntent] = []
        prev_close = self._last_close.get(bar.symbol)
        self._last_close[bar.symbol] = bar.close
        if prev_close is None or prev_close == 0:
            return intents
        bar_return = (bar.close - prev_close) / prev_close

        buffer = self._returns.setdefault(bar.symbol, deque(maxlen=self.window))
        buffer.append(bar_return)
        if len(buffer) < self.window:
            return intents

        mean = statistics.fmean(buffer)
        stdev = statistics.pstdev(buffer)
        if stdev <= 0:
            return intents
        z = (bar_return - mean) / stdev

        already_long = portfolio.has_position(bar.symbol)
        if z < self.entry_z and not already_long:
            intents.append(
                BacktestOrderIntent(
                    symbol=bar.symbol,
                    quantity=self.position_size,
                    reason=f"mean-reversion entry (z={z:.2f})",
                )
            )
        elif z > self.exit_z and already_long:
            held = portfolio.positions[bar.symbol].quantity
            intents.append(
                BacktestOrderIntent(
                    symbol=bar.symbol,
                    quantity=-held,
                    reason=f"mean-reversion exit (z={z:.2f})",
                )
            )
        return intents


# ---------------------------------------------------------------------------
# 2. Trend following — golden cross with 200-day filter
# ---------------------------------------------------------------------------


class TrendFollowingStrategy(BacktestStrategy):
    """Golden-cross trend follower with a 200-day MA price filter.

    Maintains a per-symbol ring buffer of the last ``max(long, 200)``
    closes. Emits a buy intent on the bar that completes the golden
    cross (short MA crosses above long MA) AND when the bar's close is
    above the 200-day MA — the secular-trend filter avoids whipsaw
    crosses inside a bear market.

    A second per-symbol slot remembers the previous (short, long) MA
    pair so the strategy can detect the cross *transition*, not just
    the steady-state condition.
    """

    NAME = "trend_following"

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self.short_window = int(params.get("short_window", 50))
        self.long_window = int(params.get("long_window", 200))
        self.position_size = float(params.get("position_size", 100))
        # Buffer length must be at least max(long, 200) so we can compute
        # both the long SMA and the 200-day filter simultaneously.
        self._buffer_len = max(self.long_window, 200)
        self._closes: dict[str, deque[float]] = {}
        self._prev_signal: dict[str, str | None] = {}

    def _signal(self, closes: deque[float]) -> str | None:
        """Compute the current cross state.

        Returns ``"above"`` if short MA > long MA, ``"below"`` if short
        MA <= long MA, or ``None`` if we don't yet have enough bars.
        """
        if len(closes) < self.long_window:
            return None
        as_list = list(closes)
        short_window = as_list[-self.short_window :]
        long_window = as_list[-self.long_window :]
        short_ma = statistics.fmean(short_window)
        long_ma = statistics.fmean(long_window)
        return "above" if short_ma > long_ma else "below"

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        intents: list[BacktestOrderIntent] = []
        buffer = self._closes.setdefault(bar.symbol, deque(maxlen=self._buffer_len))
        buffer.append(bar.close)
        signal = self._signal(buffer)
        prev = self._prev_signal.get(bar.symbol)
        self._prev_signal[bar.symbol] = signal

        if signal is None or prev is None:
            return intents

        already_long = portfolio.has_position(bar.symbol)
        if prev == "below" and signal == "above" and not already_long:
            # Golden cross transition — apply the 200-day price filter.
            if len(buffer) >= 200:
                ma_200 = statistics.fmean(list(buffer)[-200:])
                if bar.close <= ma_200:
                    return intents
            intents.append(
                BacktestOrderIntent(
                    symbol=bar.symbol,
                    quantity=self.position_size,
                    reason="golden cross",
                )
            )
        elif prev == "above" and signal == "below" and already_long:
            held = portfolio.positions[bar.symbol].quantity
            intents.append(
                BacktestOrderIntent(
                    symbol=bar.symbol,
                    quantity=-held,
                    reason="death cross",
                )
            )
        return intents


# ---------------------------------------------------------------------------
# 3. Regime-aware — vol-conditioned sizing on a momentum entry
# ---------------------------------------------------------------------------


class RegimeAwareStrategy(BacktestStrategy):
    """Realised-volatility-conditioned position sizing on a momentum signal.

    Computes 20-day realised return-stdev as the regime proxy. When the
    rolling stdev is below ``vol_threshold`` the regime is "low vol" and
    the strategy buys ``low_vol_size`` shares; when it exceeds the
    threshold the regime is "high vol" and the strategy buys
    ``high_vol_size`` shares (typically smaller). Entries are gated on a
    one-bar positive-momentum signal — the rolling-window mean return is
    positive — so the strategy buys cheap volatility, not falling
    knives.

    Exits are symmetric: when the rolling mean return turns negative and
    the strategy is long, flatten.
    """

    NAME = "regime_aware"

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        self.vol_window = int(params.get("vol_window", 20))
        self.low_vol_size = float(params.get("low_vol_size", 100))
        self.high_vol_size = float(params.get("high_vol_size", 25))
        self.vol_threshold = float(params.get("vol_threshold", 0.02))
        self._returns: dict[str, deque[float]] = {}
        self._last_close: dict[str, float] = {}

    async def on_bar(self, bar: Bar, portfolio: SimPortfolio) -> list[BacktestOrderIntent]:
        intents: list[BacktestOrderIntent] = []
        prev_close = self._last_close.get(bar.symbol)
        self._last_close[bar.symbol] = bar.close
        if prev_close is None or prev_close == 0:
            return intents
        bar_return = (bar.close - prev_close) / prev_close

        buffer = self._returns.setdefault(bar.symbol, deque(maxlen=self.vol_window))
        buffer.append(bar_return)
        if len(buffer) < self.vol_window:
            return intents

        realised_vol = statistics.pstdev(buffer)
        mean_return = statistics.fmean(buffer)
        already_long = portfolio.has_position(bar.symbol)

        if mean_return > 0 and not already_long:
            size = self.high_vol_size if realised_vol > self.vol_threshold else self.low_vol_size
            regime = "high-vol" if realised_vol > self.vol_threshold else "low-vol"
            intents.append(
                BacktestOrderIntent(
                    symbol=bar.symbol,
                    quantity=size,
                    reason=f"momentum entry ({regime}, vol={realised_vol:.3f})",
                )
            )
        elif mean_return <= 0 and already_long:
            held = portfolio.positions[bar.symbol].quantity
            intents.append(
                BacktestOrderIntent(
                    symbol=bar.symbol,
                    quantity=-held,
                    reason="momentum exit",
                )
            )
        return intents


# ---------------------------------------------------------------------------
# Bulk registration — main.py calls this once at startup.
# ---------------------------------------------------------------------------


def register_all() -> None:
    """Register every concrete strategy with the engine's registry.

    Idempotent — calling twice replaces the registered class with the
    same class. Safe to call from tests after a registry reset.
    """
    register_strategy("mean_reversion", MeanReversionStrategy)
    register_strategy("trend_following", TrendFollowingStrategy)
    register_strategy("regime_aware", RegimeAwareStrategy)
    logger.info(
        "backtest_strategies: registered %s",
        ", ".join(spec["id"] for spec in STRATEGY_SPECS),
    )
