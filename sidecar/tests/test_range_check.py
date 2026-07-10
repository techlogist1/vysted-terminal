"""R13 (D71) — ``services.research.range_check``: the 52-week range cross-check.

Recomputes the 52-week high/low from the app's own exchange-direct daily history
(the same lane the chart uses) to catch a wrong provider pair (the BI 75-vs-116 /
PML 645-vs-823 misses). Never hits the network (``provider_registry.get_history``
is patched), never raises into the research path (every failure is ``None``),
and is APPLICABILITY-GATED twice — Indian names only, and only when the series
actually spans ~52 weeks.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from models.market import OHLCVBar, OHLCVSeries
from services import provider_health, symbol_resolver
from services.research import range_check
from services.research.range_check import Range52w, compute_range, should_cross_check


@pytest.fixture(autouse=True)
def _reset() -> None:
    provider_health.reset_for_tests()
    symbol_resolver.reset_caches_for_tests()


_LATEST = datetime(2026, 7, 10, tzinfo=UTC)


def _bars(
    *, days: int, high: float, low: float, high_at: int = 5, low_at: int = 6
) -> list[OHLCVBar]:
    """One daily bar per calendar day back from ``_LATEST`` for ``days`` days.

    A flat ~100 series, with ``high`` planted on bar ``high_at`` and ``low`` on
    bar ``low_at`` so the reduction has a known max/min.
    """
    out: list[OHLCVBar] = []
    for i in range(days):
        ts = _LATEST - timedelta(days=i)
        h = high if i == high_at else 100.0
        low_v = low if i == low_at else 95.0
        out.append(OHLCVBar(timestamp=ts, open=98.0, high=h, low=low_v, close=99.0, volume=1000.0))
    return out


# --- compute_range: the pinned reduction ----------------------------------------


def test_computes_high_low_over_the_window() -> None:
    rng = compute_range(_bars(days=360, high=116.0, low=50.0), "nse_direct")
    assert rng is not None
    assert rng.high == 116.0
    assert rng.low == 50.0
    assert rng.bars == 360
    assert rng.coverage_days == 359
    assert rng.source == "nse_direct"


def test_bars_outside_the_52_week_window_are_excluded() -> None:
    # A 116 high planted 400 days back is outside the 365-day window and must
    # NOT set the 52-week high.
    bars = _bars(days=360, high=100.0, low=50.0)
    bars.append(
        OHLCVBar(
            timestamp=_LATEST - timedelta(days=400),
            open=98.0,
            high=116.0,
            low=95.0,
            close=99.0,
            volume=1000.0,
        )
    )
    rng = compute_range(bars, "bse")
    assert rng is not None
    assert rng.high == 100.0  # the out-of-window 116 is excluded


def test_thin_series_below_coverage_floor_is_none() -> None:
    # Only 40 days / 40 bars — cannot honestly witness a 52-week range.
    assert compute_range(_bars(days=40, high=116.0, low=50.0), "bse") is None


def test_too_few_bars_over_a_long_span_is_none() -> None:
    # 200 calendar days of span but only ~30 bars (a sparse cold cache).
    sparse = [
        OHLCVBar(
            timestamp=_LATEST - timedelta(days=i * 7),
            open=98.0,
            high=100.0,
            low=95.0,
            close=99.0,
            volume=1000.0,
        )
        for i in range(30)
    ]
    assert compute_range(sparse, "bse") is None


def test_empty_or_none_bars_is_none() -> None:
    assert compute_range(None, "nse_direct") is None
    assert compute_range([], "nse_direct") is None


def test_naive_timestamps_are_tolerated() -> None:
    bars = [
        OHLCVBar(
            timestamp=datetime(2026, 7, 10) - timedelta(days=i),
            open=98.0,
            high=116.0 if i == 5 else 100.0,
            low=50.0 if i == 6 else 95.0,
            close=99.0,
            volume=1000.0,
        )
        for i in range(360)
    ]
    rng = compute_range(bars, "nse_direct")
    assert rng is not None and rng.high == 116.0


# --- should_cross_check / is_applicable -----------------------------------------


def test_gate_requires_a_provider_52w_bound() -> None:
    assert should_cross_check({"fifty_two_week_high": 75.0}) is True
    assert should_cross_check({"fifty_two_week_low": 50.0}) is True
    assert should_cross_check({}) is False
    assert should_cross_check({"fifty_two_week_high": None}) is False
    assert should_cross_check({"fifty_two_week_high": True}) is False


def test_is_applicable_only_india() -> None:
    assert range_check.is_applicable("BI")  # NSE+BSE micro-cap
    assert not range_check.is_applicable("AAPL")
    assert not range_check.is_applicable("")


# --- get_52w_range: the fetching wrapper ----------------------------------------


def _patch_history(monkeypatch: pytest.MonkeyPatch, result: object) -> None:
    from services import provider_registry

    def factory(symbol: str, timeframe: str, range_: str, asset_class: str) -> object:  # noqa: ARG001
        if isinstance(result, BaseException):
            raise result
        return result

    monkeypatch.setattr(provider_registry, "get_history", factory)


def test_fetch_recomputes_from_the_exchange_series(monkeypatch: pytest.MonkeyPatch) -> None:
    series = OHLCVSeries(
        symbol="BI",
        timeframe="1d",
        bars=_bars(days=360, high=116.0, low=50.0),
        provider="nse_direct",
    )
    _patch_history(monkeypatch, series)
    rng = asyncio.run(range_check.get_52w_range("BI"))
    assert rng == Range52w(high=116.0, low=50.0, coverage_days=359, bars=360, source="nse_direct")


def test_non_india_never_fetches(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import provider_registry

    def must_not_run(*_a: object, **_k: object) -> object:
        raise AssertionError("non-India symbol must not reach the history lane")

    monkeypatch.setattr(provider_registry, "get_history", must_not_run)
    assert asyncio.run(range_check.get_52w_range("AAPL")) is None


def test_provider_error_is_none_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.errors import ProviderError

    _patch_history(monkeypatch, ProviderError("bse: empty series"))
    assert asyncio.run(range_check.get_52w_range("BI")) is None
    assert not provider_health.is_open(range_check.EXCHANGE_HISTORY)


def test_block_opens_the_exchange_history_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.errors import ProviderError

    _patch_history(monkeypatch, ProviderError("nse_direct: blocked (HTTP 401)"))
    for _ in range(3):
        assert asyncio.run(range_check.get_52w_range("BI")) is None
    assert provider_health.is_open(range_check.EXCHANGE_HISTORY)


def test_open_circuit_skips_the_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    provider_health.record_rate_limited(range_check.EXCHANGE_HISTORY, weight=3)
    assert provider_health.is_open(range_check.EXCHANGE_HISTORY)
    from services import provider_registry

    def explode(*_a: object, **_k: object) -> object:
        raise AssertionError("open circuit must skip the history fetch")

    monkeypatch.setattr(provider_registry, "get_history", explode)
    assert asyncio.run(range_check.get_52w_range("BI")) is None


def test_thin_returned_series_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    series = OHLCVSeries(
        symbol="BI",
        timeframe="1d",
        bars=_bars(days=30, high=116.0, low=50.0),
        provider="bse",
    )
    _patch_history(monkeypatch, series)
    assert asyncio.run(range_check.get_52w_range("BI")) is None


# --- get_52w_range: the circularity guard (R13 D-1) ------------------------------


def test_yfinance_served_series_declines_to_witness(monkeypatch: pytest.MonkeyPatch) -> None:
    # A yfinance-served fallback series must NOT be used to recompute the 52w
    # range — witnessing yfinance against itself is a false negative by
    # construction, and its auto-adjusted OHLC would manufacture false
    # positives against the unadjusted 52w scalar it also serves.
    series = OHLCVSeries(
        symbol="BI",
        timeframe="1d",
        bars=_bars(days=360, high=116.0, low=50.0),
        provider="yfinance",
    )
    _patch_history(monkeypatch, series)
    assert asyncio.run(range_check.get_52w_range("BI")) is None


def test_bse_served_series_with_coverage_computes(monkeypatch: pytest.MonkeyPatch) -> None:
    # bse is exchange-direct — with adequate coverage it must compute, not decline.
    series = OHLCVSeries(
        symbol="BI",
        timeframe="1d",
        bars=_bars(days=360, high=116.0, low=50.0),
        provider="bse",
    )
    _patch_history(monkeypatch, series)
    rng = asyncio.run(range_check.get_52w_range("BI"))
    assert rng == Range52w(high=116.0, low=50.0, coverage_days=359, bars=360, source="bse")
