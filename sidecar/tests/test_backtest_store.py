"""R15-LIFECYCLE-015: backtest results outlive the memory cache and a restart."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from models.backtest import BacktestMetrics, BacktestRequest, BacktestResult
from services import backtest_store


@pytest.fixture(autouse=True)
def _data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VYSTED_DATA_DIR", str(tmp_path))
    backtest_store.reset_for_tests()
    yield
    backtest_store.reset_for_tests()


def _result(started_at: int) -> BacktestResult:
    zero = dict.fromkeys(
        (
            "total_return",
            "annualized_return",
            "sharpe",
            "sortino",
            "calmar",
            "max_drawdown_pct",
            "win_rate",
            "best_trade_pnl",
            "worst_trade_pnl",
        ),
        0.0,
    )
    return BacktestResult(
        run_id=str(uuid.uuid4()),
        strategy_id="sma_crossover",
        request=BacktestRequest(
            strategy_id="sma_crossover",
            symbols=["AAPL"],
            start_date="2024-01-01",
            end_date="2024-12-31",
        ),
        metrics=BacktestMetrics(trade_count=0, **zero),
        trades=[],
        equity_curve=[],
        started_at=started_at,
        duration_ms=1.0,
    )


def test_a_result_survives_a_restart() -> None:
    result = _result(1)
    backtest_store.put(result)
    backtest_store.reset_for_tests()  # the process restarts: memory is gone
    assert backtest_store.get(result.run_id) == result


def test_the_33rd_run_leaves_the_first_readable() -> None:
    runs = [_result(i) for i in range(backtest_store.DEFAULT_CAPACITY + 1)]
    for run in runs:
        backtest_store.put(run)
    assert backtest_store.get(runs[0].run_id) == runs[0]
    assert len(backtest_store.list_runs()) == len(runs)


def test_list_is_newest_first_even_after_an_old_run_is_read() -> None:
    old, mid, new = _result(100), _result(200), _result(300)
    for run in (mid, new, old):
        backtest_store.put(run)
    backtest_store.reset_for_tests()
    backtest_store.get(old.run_id)  # touching it must not reorder the list
    assert [r.run_id for r in backtest_store.list_runs()] == [new.run_id, mid.run_id, old.run_id]


def test_a_non_uuid_run_id_never_names_a_file(tmp_path: Path) -> None:
    (tmp_path / "secret.json").write_text("{}", encoding="utf-8")
    assert backtest_store.get("../secret") is None
