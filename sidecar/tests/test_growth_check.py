"""R12 (D66) — ``services.growth_check``: the quarterly-YoY growth cross-check.

The deterministic MRQ-vs-same-quarter-prior-year computation from the quarterly
income statements — the consistency check for the opaque yfinance
``revenueGrowth``/``earningsGrowth`` scalars (which the R12 battery proved can
be materially wrong on their own claimed ``mrq_yoy`` basis). Never hits the
network (``yf.Ticker`` is patched), never raises into the research path (every
failure is ``None``), reports throttles to the shared Yahoo circuit breaker,
and only DISCLOSES — the snapshot wiring attaches computed figures next to the
provider values, never over them.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pandas as pd
import pytest

from services import growth_check, provider_health
from services.growth_check import QuarterlyYoY, compute_quarterly_yoy, should_cross_check


class YFRateLimitError(Exception):
    """Stand-in matched by TYPE NAME (the module never imports the real one)."""


def _frame(
    columns: list[str],
    rows: dict[str, list[float | None]],
) -> pd.DataFrame:
    """A quarterly income-statement frame shaped like yfinance's (rows = line
    labels, columns = quarter-end Timestamps, most recent first)."""
    return pd.DataFrame(
        {
            pd.Timestamp(col): [rows[label][idx] for label in rows]
            for idx, col in enumerate(columns)
        },
        index=list(rows),
    )


class _FakeTicker:
    def __init__(self, frame: pd.DataFrame | None) -> None:
        self._frame = frame

    @property
    def quarterly_income_stmt(self) -> pd.DataFrame | None:
        return self._frame


def _patch_ticker(monkeypatch: pytest.MonkeyPatch, frame_or_exc: object) -> None:
    def factory(symbol: str) -> _FakeTicker:  # noqa: ARG001
        if isinstance(frame_or_exc, BaseException):
            raise frame_or_exc
        return _FakeTicker(frame_or_exc)  # type: ignore[arg-type]

    monkeypatch.setattr(growth_check.yf, "Ticker", factory)


@pytest.fixture(autouse=True)
def _reset_health() -> None:
    provider_health.reset_for_tests()


# --- compute_quarterly_yoy: the pinned arithmetic -------------------------------


def test_computes_exact_mrq_yoy_from_fixture_quarters() -> None:
    # Five quarters, SBIN-like shape: revenue 103_000 vs 100_000 a year ago
    # (+3.0% exactly) and net profit 21_120 vs 20_000 (+5.6% exactly).
    frame = _frame(
        ["2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31"],
        {
            "Total Revenue": [103_000.0, 99_000.0, 97_000.0, 95_000.0, 100_000.0],
            "Net Income": [21_120.0, 19_000.0, 18_500.0, 18_000.0, 20_000.0],
        },
    )
    yoy = compute_quarterly_yoy(frame)
    assert yoy is not None
    assert yoy.revenue_growth == pytest.approx(0.03)
    assert yoy.earnings_growth == pytest.approx(0.056)
    assert yoy.mrq == "2026-03-31"
    assert yoy.prior == "2025-03-31"


def test_negative_prior_year_base_is_sign_aware() -> None:
    # A loss of 100 turning into a profit of 50 is +150% against |prior| —
    # deterministic sign-aware arithmetic, never a sign-garbled ratio.
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {"Total Revenue": [110.0, 100.0], "Net Income": [50.0, -100.0]},
    )
    yoy = compute_quarterly_yoy(frame)
    assert yoy is not None
    assert yoy.earnings_growth == pytest.approx(1.5)
    assert yoy.revenue_growth == pytest.approx(0.10)


def test_missing_prior_year_quarter_is_a_no_op() -> None:
    # Only four quarters served — no column ~365 days behind the MRQ, so the
    # computation honestly declines (never interpolates a mismatched quarter).
    frame = _frame(
        ["2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30"],
        {
            "Total Revenue": [103.0, 99.0, 97.0, 95.0],
            "Net Income": [21.0, 19.0, 18.5, 18.0],
        },
    )
    assert compute_quarterly_yoy(frame) is None


def test_zero_prior_base_yields_none_for_that_metric() -> None:
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {"Total Revenue": [110.0, 100.0], "Net Income": [50.0, 0.0]},
    )
    yoy = compute_quarterly_yoy(frame)
    assert yoy is not None
    assert yoy.earnings_growth is None
    assert yoy.revenue_growth == pytest.approx(0.10)


def test_nan_mrq_value_yields_none_for_that_metric() -> None:
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {"Total Revenue": [None, 100.0], "Net Income": [50.0, 40.0]},
    )
    yoy = compute_quarterly_yoy(frame)
    assert yoy is not None
    assert yoy.revenue_growth is None
    assert yoy.earnings_growth == pytest.approx(0.25)


def test_row_label_fallbacks_and_case_insensitivity() -> None:
    # "Operating Revenue" backs an absent "Total Revenue"; "Net Income Common
    # Stockholders" backs an absent "Net Income"; label case is tolerated.
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {
            "operating revenue": [120.0, 100.0],
            "net income common stockholders": [60.0, 50.0],
        },
    )
    yoy = compute_quarterly_yoy(frame)
    assert yoy is not None
    assert yoy.revenue_growth == pytest.approx(0.20)
    assert yoy.earnings_growth == pytest.approx(0.20)


def test_no_recognised_rows_or_empty_frame_is_none() -> None:
    assert compute_quarterly_yoy(None) is None
    assert compute_quarterly_yoy(pd.DataFrame()) is None
    frame = _frame(["2026-03-31", "2025-03-31"], {"Gross Profit": [10.0, 8.0]})
    assert compute_quarterly_yoy(frame) is None


# --- should_cross_check: the applicability gate ---------------------------------


def test_gate_requires_a_provider_growth_scalar() -> None:
    assert should_cross_check({"revenue_growth": 0.1}) is True
    assert should_cross_check({"earnings_growth": -0.05}) is True
    assert should_cross_check({"revenue_growth": None, "earnings_growth": None}) is False
    assert should_cross_check({}) is False
    assert should_cross_check({"revenue_growth": True}) is False


def test_gate_requires_the_mrq_yoy_basis() -> None:
    # An explicit non-MRQ basis must never be compared against quarterly YoY —
    # that would manufacture a conflict out of a basis mismatch. An absent
    # basis means the D55 default (mrq_yoy) and passes.
    assert should_cross_check({"revenue_growth": 0.1, "growth_basis": "mrq_yoy"}) is True
    assert should_cross_check({"revenue_growth": 0.1, "growth_basis": "fy_yoy"}) is False
    assert should_cross_check({"revenue_growth": 0.1}) is True


# --- get_quarterly_yoy: the fetching wrapper ------------------------------------


def test_fetch_computes_from_patched_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {"Total Revenue": [102.0, 100.0], "Net Income": [55.0, 50.0]},
    )
    _patch_ticker(monkeypatch, frame)
    yoy = asyncio.run(growth_check.get_quarterly_yoy("SBIN.NS"))
    assert yoy == QuarterlyYoY(
        revenue_growth=pytest.approx(0.02),
        earnings_growth=pytest.approx(0.10),
        mrq="2026-03-31",
        prior="2025-03-31",
    )


def test_unsupportive_statements_return_none_but_record_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"success": 0}
    monkeypatch.setattr(
        provider_health, "record_success", lambda *_a, **_k: calls.__setitem__("success", 1)
    )
    _patch_ticker(monkeypatch, pd.DataFrame())
    assert asyncio.run(growth_check.get_quarterly_yoy("THIN.NS")) is None
    # An empty statement set is a HEALTHY round-trip — the circuit resets.
    assert calls["success"] == 1


def test_rate_limit_records_breaker_and_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ticker(monkeypatch, YFRateLimitError("Too Many Requests"))
    assert asyncio.run(growth_check.get_quarterly_yoy("THROTTLED.NS")) is None
    assert provider_health.status()["throttles_total"] == pytest.approx(1.0)


def test_generic_failure_returns_none_without_recording_a_throttle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_ticker(monkeypatch, RuntimeError("socket reset"))
    assert asyncio.run(growth_check.get_quarterly_yoy("BROKEN.NS")) is None
    assert provider_health.status()["throttles_total"] == pytest.approx(0.0)


def test_empty_symbol_is_rejected_without_touching_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(symbol: str) -> _FakeTicker:  # noqa: ARG001
        raise AssertionError("yfinance must not be touched for an empty symbol")

    monkeypatch.setattr(growth_check.yf, "Ticker", explode)
    assert asyncio.run(growth_check.get_quarterly_yoy("")) is None


# --- snapshot wiring: attach-next-to, never replace ------------------------------


def _fund_tool(fund: dict[str, Any]):
    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        if name == "price_data":
            return {"ok": True, "provider": "yfinance", "quote": {"symbol": "X", "price": 80.0}}
        if name == "fundamentals":
            return {"ok": True, "fundamentals": dict(fund)}
        raise AssertionError(f"unexpected tool {name}")

    return tool


def test_snapshot_attaches_computed_growth_next_to_provider_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.research.fast import snapshot_structured

    async def fake_yoy(symbol: str) -> QuarterlyYoY:
        assert symbol == "ICICIBANK.NS"  # the RESOLVED listing, not the query
        return QuarterlyYoY(
            revenue_growth=0.02, earnings_growth=0.025, mrq="2026-03-31", prior="2025-03-31"
        )

    monkeypatch.setattr(growth_check, "get_quarterly_yoy", fake_yoy)
    snap = asyncio.run(
        snapshot_structured(
            _fund_tool(
                {
                    "symbol": "ICICIBANK.NS",
                    "provider": "yfinance",
                    "revenue_growth": 0.669,
                    "earnings_growth": 0.03,
                }
            ),
            "ICICIBANK",
        )
    )
    fund = snap["fundamentals"]["data"]
    # The provider values are NEVER replaced — the computed figures ride BESIDE them.
    assert fund["revenue_growth"] == 0.669
    assert fund["earnings_growth"] == 0.03
    assert fund["revenue_growth_computed"] == 0.02
    assert fund["earnings_growth_computed"] == 0.025
    assert fund["growth_computed_quarters"] == {"mrq": "2026-03-31", "prior": "2025-03-31"}


def test_snapshot_skips_the_pull_when_provider_carries_no_growth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.research.fast import snapshot_structured

    async def explode(_symbol: str) -> QuarterlyYoY:
        raise AssertionError("no growth scalars to reconcile — must not pull statements")

    monkeypatch.setattr(growth_check, "get_quarterly_yoy", explode)
    snap = asyncio.run(
        snapshot_structured(_fund_tool({"symbol": "X.NS", "provider": "yfinance"}), "X")
    )
    fund = snap["fundamentals"]["data"]
    assert "revenue_growth_computed" not in fund
    assert "growth_computed_quarters" not in fund


def test_snapshot_attaches_nothing_when_statements_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.research.fast import snapshot_structured

    async def none_yoy(_symbol: str) -> None:
        return None

    monkeypatch.setattr(growth_check, "get_quarterly_yoy", none_yoy)
    snap = asyncio.run(
        snapshot_structured(
            _fund_tool({"symbol": "X.NS", "provider": "yfinance", "revenue_growth": 0.1}), "X"
        )
    )
    fund = snap["fundamentals"]["data"]
    assert fund["revenue_growth"] == 0.1  # untouched
    assert "revenue_growth_computed" not in fund
    assert "earnings_growth_computed" not in fund
    assert "growth_computed_quarters" not in fund
