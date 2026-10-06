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
    def __init__(self, series: pd.Series, listed_days: int | None) -> None:
        self._series = series
        self._listed_days = listed_days

    @property
    def dividends(self) -> pd.Series:
        return self._series

    def history(self, period: str, interval: str) -> pd.DataFrame:  # noqa: ARG002
        """Monthly closes from the listing (``listed_days`` ago) to today."""
        if self._listed_days is None:
            return pd.DataFrame({"Close": []}, index=pd.DatetimeIndex([]))
        start = pd.Timestamp.now() - pd.Timedelta(days=min(self._listed_days, 730))
        index = pd.date_range(start, pd.Timestamp.now(), freq="30D")
        return pd.DataFrame({"Close": [1.0] * len(index)}, index=index)


def _patch_ticker(
    monkeypatch: pytest.MonkeyPatch, series_or_exc: object, listed_days: int | None = None
) -> None:
    def factory(symbol: str) -> _FakeTicker:  # noqa: ARG001
        if isinstance(series_or_exc, BaseException):
            raise series_or_exc
        return _FakeTicker(series_or_exc, listed_days)  # type: ignore[arg-type]

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


def test_never_paid_with_a_year_of_price_history_affirms_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # DAL / ICON shape (R15-DATA-049): no dividend ever recorded, but the listing
    # has traded for years — a stateable 0.00%, not "provider did not publish".
    _patch_ticker(monkeypatch, _series([]), listed_days=1500)
    result = asyncio.run(dividend_history.get_dividend_ttm("DAL.BO"))
    assert result.status == "affirmed_zero"
    assert result.value == 0.0

    # A listing younger than the window cannot affirm anything yet.
    _patch_ticker(monkeypatch, _series([]), listed_days=150)
    result = asyncio.run(dividend_history.get_dividend_ttm("NEWIPO.NS"))
    assert result.status == "unavailable"
    assert result.reason == dividend_history.INSUFFICIENT_DEPTH_REASON


def _fund(**fields: object) -> dict:
    meta = {k: {"status": "ok", "provider": "yfinance"} for k, v in fields.items() if v is not None}
    return {"symbol": "X.NS", "provider": "yfinance", "field_meta": meta, **fields}


def test_apply_flags_a_rate_that_omits_a_special_dividend() -> None:
    # ABBOTINDIA: dividendRate 525 against 656 actually paid (525 + 131 special).
    fund = _fund(dividend_per_share=525.0, dividend_yield=0.0193, ratio_price=26935.0)
    dividend_history.apply_dividend_ttm(fund, dividend_history.DividendTTM(656.0, "paid"))
    assert fund["dividend_per_share"] == 525.0  # kept, never replaced
    assert fund["dividend_per_share_ttm"] == 656.0
    meta = fund["field_meta"]
    assert meta["dividend_per_share"]["status"] == "flagged"
    assert "656" in meta["dividend_per_share"]["reason"]
    assert meta["dividend_per_share_ttm"]["status"] == "ok"
    assert fund["dividend_yield"] == 0.0193  # a published yield is left alone


def test_apply_affirmed_zero_serves_a_labelled_zero_yield() -> None:
    fund = _fund(dividend_per_share=None, dividend_yield=None, ratio_price=49.88)
    affirmed = dividend_history.DividendTTM(
        0.0, "affirmed_zero", dividend_history.AFFIRMED_ZERO_LABEL
    )
    dividend_history.apply_dividend_ttm(fund, affirmed)
    assert fund["dividend_per_share_ttm"] == 0.0
    assert fund["dividend_yield"] == 0.0
    for field in ("dividend_per_share_ttm", "dividend_yield"):
        assert fund["field_meta"][field]["status"] == "ok"
        assert fund["field_meta"][field]["label"] == dividend_history.AFFIRMED_ZERO_LABEL


def test_apply_serves_an_unpublished_yield_from_the_paid_ttm() -> None:
    # ELCIDIN.NS: Yahoo publishes neither dividendRate nor dividendYield; Rs 25
    # was paid in July at a price of Rs 1,05,800.
    fund = _fund(dividend_per_share=None, dividend_yield=None, ratio_price=105800.0)
    dividend_history.apply_dividend_ttm(fund, dividend_history.DividendTTM(25.0, "paid"))
    assert fund["dividend_yield"] == pytest.approx(25.0 / 105800.0)
    assert "paid" in fund["field_meta"]["dividend_yield"]["reason"]
    assert "dividend_per_share" not in fund["field_meta"]  # nothing to flag


def test_apply_unavailable_leaves_the_field_null_with_its_reason() -> None:
    fund = _fund(dividend_per_share=10.0, dividend_yield=None, ratio_price=100.0)
    dividend_history.apply_dividend_ttm(fund, None)
    assert fund.get("dividend_per_share_ttm") is None
    assert fund["dividend_yield"] is None
    assert fund["field_meta"]["dividend_per_share_ttm"]["status"] == "unavailable"
    assert fund["field_meta"]["dividend_per_share"]["status"] == "ok"
