"""Completed backtest results, persisted as JSON under the data dir (D-B10-9).

A backtest's :class:`BacktestResult` is kept so the Strategy Critic agent's
``backtest_summary`` tool and ``GET /backtest/runs/{id}`` can retrieve it by
run id without re-running the engine. Each result is written once to
``<data-dir>/backtests/<run_id>.json`` (the directory resolves per call, so a
test pointing ``VYSTED_DATA_DIR`` at ``tmp_path`` gets its own store); a
bounded in-memory LRU (default 32) caches the recent ones. A restart or the
33rd run no longer forgets a run the user is still looking at
(R15-LIFECYCLE-015), and :func:`list_runs` is newest first.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from pathlib import Path

from pydantic import ValidationError

from config import get_data_dir
from models.backtest import BacktestResult

logger = logging.getLogger(__name__)

DEFAULT_CAPACITY = 32
DIRNAME = "backtests"


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
            logger.debug("backtest_store: evicted run %s from memory", evicted)

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


def _dir() -> Path:
    path = get_data_dir() / DIRNAME
    path.mkdir(exist_ok=True)
    return path


def _load(path: Path) -> BacktestResult | None:
    try:
        return BacktestResult.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        logger.warning("backtest_store: unreadable result file %s", path.name)
        return None


def put(result: BacktestResult) -> None:
    _cache.put(result)
    try:
        (_dir() / f"{result.run_id}.json").write_text(
            result.model_dump_json(by_alias=True), encoding="utf-8"
        )
    except OSError:
        # The run still completes and stays readable from memory.
        logger.warning("backtest_store: could not persist run %s", result.run_id, exc_info=True)


def get(run_id: str) -> BacktestResult | None:
    result = _cache.get(run_id)
    # A run id is a uuid; anything else (the agent tool passes model text)
    # never names a file.
    if result is not None or not run_id.replace("-", "").isalnum():
        return result
    path = _dir() / f"{run_id}.json"
    result = _load(path) if path.is_file() else None
    if result is not None:
        _cache.put(result)
    return result


def list_runs() -> list[BacktestResult]:
    """Every stored run, newest first."""
    # ponytail: parses every result file per call; index started_at if the list gets long.
    runs = {r.run_id: r for r in _cache.list()}
    for path in _dir().glob("*.json"):
        if path.stem not in runs and (loaded := _load(path)) is not None:
            runs[loaded.run_id] = loaded
    return sorted(runs.values(), key=lambda r: r.started_at, reverse=True)


def reset_for_tests() -> None:
    _cache.clear()
