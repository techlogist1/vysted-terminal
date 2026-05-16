"""In-memory cache for completed backtest results.

A backtest's :class:`BacktestResult` is cached so the Strategy Critic
agent's ``backtest_summary`` tool can retrieve it by run id without
re-running the engine. The cache is bounded (default 32 entries, LRU
eviction) so a long-running session does not leak memory.

v0.5.0 ships in-memory; durable per-result persistence is a v0.5.1
follow-up if user demand emerges. The Phase-3 agent runtime already
keeps its own conversation history; backtest result persistence isn't
load-bearing for the v0.5.0 demo.
"""

from __future__ import annotations

import logging
from collections import OrderedDict

from models.backtest import BacktestResult

logger = logging.getLogger(__name__)

DEFAULT_CAPACITY = 32


class _BacktestCache:
    """Bounded LRU cache. Module-singleton; tests reset it."""

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._capacity = capacity
        self._items: OrderedDict[str, BacktestResult] = OrderedDict()

    def put(self, result: BacktestResult) -> None:
        if result.run_id in self._items:
            self._items.move_to_end(result.run_id)
        self._items[result.run_id] = result
        while len(self._items) > self._capacity:
            evicted, _ = self._items.popitem(last=False)
            logger.debug("backtest_store: evicted run %s", evicted)

    def get(self, run_id: str) -> BacktestResult | None:
        result = self._items.get(run_id)
        if result is not None:
            self._items.move_to_end(run_id)
        return result

    def list(self) -> list[BacktestResult]:
        return list(self._items.values())

    def clear(self) -> None:
        self._items.clear()


_cache = _BacktestCache()


def put(result: BacktestResult) -> None:
    _cache.put(result)


def get(run_id: str) -> BacktestResult | None:
    return _cache.get(run_id)


def list_runs() -> list[BacktestResult]:
    return _cache.list()


def reset_for_tests() -> None:
    _cache.clear()
