"""R11 (D56) — ``services.dividend_history.get_dividend_ttm``.

The deterministic trailing-12m-paid cross-check for the opaque yfinance
``dividendRate`` scalar. Never hits the network (``yf.Ticker`` is patched) and
never raises into the research path: every failure is ``None``, a detected
throttle records against the shared Yahoo circuit breaker, a healthy round-trip
resets it.
"""

from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from services import dividend_history, provider_health


class YFRateLimitError(Exception):
    """Stand-in matched by TYPE NAME (the module never imports the real one)."""


def _series(pairs: list[tuple[pd.Timestamp, float]]) -> pd.Series:
    index = pd.DatetimeIndex([ts for ts, _ in pairs])
    return pd.Series([amt for _, amt in pairs], index=index)


class _FakeTicker:
    def __init__(self, series: pd.Series) -> None:
        self._series = series

    @property
    def dividends(self) -> pd.Series:
        return self._series


def _patch_ticker(monkeypatch: pytest.MonkeyPatch, series_or_exc: object) -> None:
    def factory(symbol: str) -> _FakeTicker:  # noqa: ARG001
        if isinstance(series_or_exc, BaseException):
            raise series_or_exc
        return _FakeTicker(series_or_exc)  # type: ignore[arg-type]

    monkeypatch.setattr(dividend_history.yf, "Ticker", factory)


@pytest.fixture(autouse=True)
def _reset_health() -> None:
    provider_health.reset_for_tests()


def test_sums_trailing_twelve_months_including_special(monkeypatch: pytest.MonkeyPatch) -> None:
    # ABBOTINDIA shape: a final (525) plus a special (131) inside the window sum
    # to 656 — the true figure Yahoo's dividendRate (525) omits. A dividend from
    # two years ago is excluded.
    now = pd.Timestamp.now()
    series = _series(
        [
            (now - pd.Timedelta(days=800), 500.0),  # outside the window
            (now - pd.Timedelta(days=200), 525.0),  # final
            (now - pd.Timedelta(days=40), 131.0),  # special
        ]
    )
    _patch_ticker(monkeypatch, series)
    result = asyncio.run(dividend_history.get_dividend_ttm("ABBOTINDIA.NS"))
    assert result.status == "paid"
    assert result.value == pytest.approx(656.0)


def test_tz_aware_index_is_handled(monkeypatch: pytest.MonkeyPatch) -> None:
    now = pd.Timestamp.now(tz="Asia/Kolkata")
    series = _series([(now - pd.Timedelta(days=10), 12.5), (now - pd.Timedelta(days=100), 7.5)])
    _patch_ticker(monkeypatch, series)
    result = asyncio.run(dividend_history.get_dividend_ttm("INFY.NS"))
    assert result.status == "paid"
    assert result.value == pytest.approx(20.0)


def test_empty_history_is_unavailable_but_records_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"success": 0}
    monkeypatch.setattr(
        provider_health, "record_success", lambda *_a, **_k: calls.__setitem__("success", 1)
    )
    _patch_ticker(monkeypatch, _series([]))
    result = asyncio.run(dividend_history.get_dividend_ttm("NODIV.NS"))
    # An EMPTY series has no depth to affirm a zero — null with a stated reason,
    # never a fabricated affirmed zero.
    assert result.value is None
    assert result.status == "unavailable"
    assert result.reason == dividend_history.INSUFFICIENT_DEPTH_REASON
    # An empty history is still a HEALTHY round-trip — the circuit resets.
    assert calls["success"] == 1


def test_all_dividends_outside_window_affirms_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    # UFO shape: real dividend history (last paid > 12 months ago), nothing in the
    # trailing window → an AFFIRMED 0.0, not an unknown null. The depth (a dividend
    # older than the window) is what makes the zero stateable.
    now = pd.Timestamp.now()
    series = _series([(now - pd.Timedelta(days=400), 10.0), (now - pd.Timedelta(days=900), 8.0)])
    _patch_ticker(monkeypatch, series)
    result = asyncio.run(dividend_history.get_dividend_ttm("OLD.NS"))
    assert result.status == "affirmed_zero"
    assert result.value == 0.0
    assert result.reason == dividend_history.AFFIRMED_ZERO_LABEL
    assert result.is_affirmed_zero


def test_rate_limit_records_breaker_and_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ticker(monkeypatch, YFRateLimitError("Too Many Requests"))
    result = asyncio.run(dividend_history.get_dividend_ttm("THROTTLED.NS"))
    assert result.value is None and result.status == "unavailable"
    # The throttle was reported to the shared Yahoo family breaker.
    assert provider_health.status()["throttles_total"] == pytest.approx(1.0)


def test_generic_failure_is_unavailable_without_recording_a_throttle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_ticker(monkeypatch, RuntimeError("socket reset"))
    result = asyncio.run(dividend_history.get_dividend_ttm("BROKEN.NS"))
    assert result.value is None and result.status == "unavailable"
    assert provider_health.status()["throttles_total"] == pytest.approx(0.0)


def test_empty_symbol_is_rejected_without_touching_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(symbol: str) -> _FakeTicker:  # noqa: ARG001
        raise AssertionError("yfinance must not be touched for an empty symbol")

    monkeypatch.setattr(dividend_history.yf, "Ticker", explode)
    result = asyncio.run(dividend_history.get_dividend_ttm(""))
    assert result.value is None and result.status == "unavailable"
