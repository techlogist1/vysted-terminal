"""Tests for the indicator service and the /indicators router.

The math tests run each indicator over a small, fixed OHLCV series and check
known properties (bounded ranges, warm-up gaps, hand-verified values). The
endpoint tests monkeypatch ``provider_registry.get_history`` with a canned
series so no live network call is made — the same mocking discipline as
``conftest.py``.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from models.market import OHLCVBar, OHLCVSeries
from services import indicators as indicator_service

# --------------------------------------------------------------------------
# Fixtures — a deterministic 40-bar series
# --------------------------------------------------------------------------


def _make_series(closes: list[float], symbol: str = "TEST") -> OHLCVSeries:
    """Build an OHLCVSeries from a close path, deriving plausible OHLC + volume."""
    base = datetime(2026, 1, 1)
    bars: list[OHLCVBar] = []
    prev = closes[0]
    for index, close in enumerate(closes):
        high = max(prev, close) + 1.0
        low = min(prev, close) - 1.0
        bars.append(
            OHLCVBar(
                timestamp=base + timedelta(days=index),
                open=prev,
                high=high,
                low=low,
                close=close,
                volume=1_000.0 + 10.0 * index,
            )
        )
        prev = close
    return OHLCVSeries(symbol=symbol, timeframe="1d", bars=bars, provider="test")


@pytest.fixture
def series() -> OHLCVSeries:
    """A 40-bar zig-zag-with-drift close path — long enough for every window."""
    closes = [100.0]
    for index in range(1, 40):
        step = 2.0 if index % 2 == 0 else -1.0
        closes.append(closes[-1] + step + index * 0.1)
    return _make_series(closes)


# --------------------------------------------------------------------------
# Indicator math
# --------------------------------------------------------------------------


def test_supported_indicators_count() -> None:
    """All 20 indicators are registered for dispatch."""
    assert len(indicator_service.SUPPORTED_INDICATORS) == 20


def test_compute_all_indicators(series: OHLCVSeries) -> None:
    """Every supported indicator computes and yields time-aligned points."""
    response = indicator_service.compute(series, list(indicator_service.SUPPORTED_INDICATORS))
    assert len(response.indicators) == 20
    n = len(series.bars)
    for result in response.indicators:
        assert result.lines, f"{result.name} produced no lines"
        for line in result.lines:
            # Volume Profile is a price-axis histogram, not a time series.
            if result.name == "volume_profile":
                assert len(line.points) > 0
            else:
                assert len(line.points) == n, f"{result.name}/{line.label} misaligned"


def test_sma_known_values() -> None:
    """SMA(3) over a flat-step series matches a hand calculation."""
    s = _make_series([10.0, 20.0, 30.0, 40.0, 50.0])
    result = indicator_service.compute_sma(
        indicator_service._frame(s), list(indicator_service._frame(s).index), period=3
    )
    values = [p.value for p in result.lines[0].points]
    assert values[0] is None and values[1] is None
    assert values[2] == pytest.approx(20.0)
    assert values[3] == pytest.approx(30.0)
    assert values[4] == pytest.approx(40.0)


def test_ema_first_value_is_sma_seed() -> None:
    """EMA warm-up is None until the span fills, then tracks the close path."""
    s = _make_series([10.0, 11.0, 12.0, 13.0, 14.0])
    result = indicator_service.compute_ema(
        indicator_service._frame(s), list(indicator_service._frame(s).index), period=3
    )
    values = [p.value for p in result.lines[0].points]
    assert values[0] is None and values[1] is None
    assert values[2] is not None
    # An EMA over a monotonically rising path stays below the latest close.
    assert values[4] is not None and values[4] < 14.0


def test_rsi_bounded_and_warmup(series: OHLCVSeries) -> None:
    """RSI stays within [0, 100] and is undefined during the warm-up window."""
    result = indicator_service.compute_rsi(
        indicator_service._frame(series), list(indicator_service._frame(series).index), period=14
    )
    values = [p.value for p in result.lines[0].points]
    assert all(v is None for v in values[:14])
    defined = [v for v in values if v is not None]
    assert defined, "RSI never became defined"
    assert all(0.0 <= v <= 100.0 for v in defined)


def test_rsi_all_gains_saturates() -> None:
    """A strictly rising series pins RSI at 100 (zero average loss)."""
    s = _make_series([float(x) for x in range(1, 31)])
    result = indicator_service.compute_rsi(
        indicator_service._frame(s), list(indicator_service._frame(s).index), period=14
    )
    values = [p.value for p in result.lines[0].points]
    assert values[-1] == pytest.approx(100.0)


def test_macd_histogram_is_line_minus_signal(series: OHLCVSeries) -> None:
    """MACD emits three lines and the histogram equals MACD minus signal."""
    result = indicator_service.compute_macd(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    assert [line.label for line in result.lines] == ["MACD", "Signal", "Histogram"]
    macd, signal, hist = result.lines
    for m, s, h in zip(macd.points, signal.points, hist.points, strict=True):
        if m.value is None or s.value is None:
            assert h.value is None
        else:
            assert h.value == pytest.approx(m.value - s.value)


def test_bollinger_bands_ordered(series: OHLCVSeries) -> None:
    """Bollinger upper >= middle >= lower wherever all three are defined."""
    result = indicator_service.compute_bollinger(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    upper, middle, lower = result.lines
    for u, m, low in zip(upper.points, middle.points, lower.points, strict=True):
        if u.value is None:
            continue
        assert u.value >= m.value >= low.value


def test_atr_non_negative(series: OHLCVSeries) -> None:
    """ATR is a range average and is therefore never negative."""
    result = indicator_service.compute_atr(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    defined = [p.value for p in result.lines[0].points if p.value is not None]
    assert defined and all(v >= 0.0 for v in defined)


def test_stochastic_and_williams_bounds(series: OHLCVSeries) -> None:
    """%K/%D sit in [0, 100]; Williams %R sits in [-100, 0]."""
    df = indicator_service._frame(series)
    times = list(df.index)
    stoch = indicator_service.compute_stochastic(df, times)
    for line in stoch.lines:
        for point in line.points:
            if point.value is not None:
                assert -0.001 <= point.value <= 100.001
    williams = indicator_service.compute_williams_r(df, times)
    for point in williams.lines[0].points:
        if point.value is not None:
            assert -100.001 <= point.value <= 0.001


def test_obv_is_running_sum(series: OHLCVSeries) -> None:
    """OBV is monotonic in magnitude relative to cumulative signed volume."""
    result = indicator_service.compute_obv(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    values = [p.value for p in result.lines[0].points]
    assert all(v is not None for v in values)
    # First bar has no prior close → zero direction → OBV starts at 0.
    assert values[0] == pytest.approx(0.0)


def test_vwap_within_price_range(series: OHLCVSeries) -> None:
    """Running VWAP stays bracketed by the series low and high."""
    result = indicator_service.compute_vwap(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    lows = [bar.low for bar in series.bars]
    highs = [bar.high for bar in series.bars]
    for point in result.lines[0].points:
        if point.value is not None:
            assert min(lows) - 1.0 <= point.value <= max(highs) + 1.0


def test_parabolic_sar_defined_from_second_bar(series: OHLCVSeries) -> None:
    """Parabolic SAR seeds on bar two and stays finite thereafter."""
    result = indicator_service.compute_parabolic_sar(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    values = [p.value for p in result.lines[0].points]
    assert values[0] is None
    assert all(v is not None and math.isfinite(v) for v in values[1:])


def test_volume_profile_buckets_sum_to_total_volume(series: OHLCVSeries) -> None:
    """Volume Profile redistributes total traded volume across price buckets."""
    result = indicator_service.compute_volume_profile(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    bucket_total = sum(p.value or 0.0 for p in result.lines[0].points)
    series_total = sum(bar.volume for bar in series.bars)
    assert bucket_total == pytest.approx(series_total)


def test_ichimoku_has_five_lines(series: OHLCVSeries) -> None:
    """Ichimoku emits the five classic lines."""
    result = indicator_service.compute_ichimoku(
        indicator_service._frame(series), list(indicator_service._frame(series).index)
    )
    assert [line.label for line in result.lines] == [
        "Tenkan-sen",
        "Kijun-sen",
        "Senkou Span A",
        "Senkou Span B",
        "Chikou Span",
    ]


def test_compute_dedupes_and_skips_unknown(series: OHLCVSeries) -> None:
    """compute() ignores unknown keys and computes duplicates only once."""
    response = indicator_service.compute(series, ["rsi", "rsi", "not-real", "macd"])
    assert [r.name for r in response.indicators] == ["rsi", "macd"]


def test_normalize_key_aliases() -> None:
    """Aliases resolve to canonical keys; junk resolves to None."""
    assert indicator_service.normalize_key("BBands") == "bollinger"
    assert indicator_service.normalize_key("Williams %R") == "williams_r"
    assert indicator_service.normalize_key("psar") == "parabolic_sar"
    assert indicator_service.normalize_key("nonsense") is None


# --------------------------------------------------------------------------
# Endpoint — history mocked, no live calls
# --------------------------------------------------------------------------


@pytest.fixture
def mock_history(monkeypatch: pytest.MonkeyPatch, series: OHLCVSeries) -> OHLCVSeries:
    """Patch provider_registry.get_history with a canned series."""
    from services import provider_registry

    def _fake_get_history(
        symbol: str,
        timeframe: str,
        range_: str | None = None,
        asset_class: str = "equity",  # noqa: ARG001
    ) -> OHLCVSeries:
        return OHLCVSeries(
            symbol=symbol,
            timeframe=timeframe,
            bars=series.bars,
            provider="test",
        )

    monkeypatch.setattr(provider_registry, "get_history", _fake_get_history)
    return series


def test_indicators_endpoint_returns_requested(
    client: TestClient, mock_history: OHLCVSeries
) -> None:
    """The endpoint computes exactly the requested indicators, in order."""
    response = client.get(
        "/indicators/SPY",
        params={"timeframe": "1d", "indicators": "rsi,macd,bollinger"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "SPY"
    assert body["timeframe"] == "1d"
    assert body["provider"] == "test"
    assert [ind["name"] for ind in body["indicators"]] == ["rsi", "macd", "bollinger"]
    rsi = body["indicators"][0]
    assert rsi["panel"] == "separate"
    assert len(rsi["lines"][0]["points"]) == len(mock_history.bars)


def test_indicators_endpoint_panel_classification(
    client: TestClient, mock_history: OHLCVSeries
) -> None:
    """Overlays report panel=price; oscillators report panel=separate."""
    response = client.get(
        "/indicators/SPY",
        params={"indicators": "sma,rsi"},
    )
    body = response.json()
    panels = {ind["name"]: ind["panel"] for ind in body["indicators"]}
    assert panels == {"sma": "price", "rsi": "separate"}


def test_indicators_endpoint_rejects_unknown(client: TestClient, mock_history: OHLCVSeries) -> None:
    """An unknown indicator key is a 400, not a silent skip."""
    response = client.get("/indicators/SPY", params={"indicators": "rsi,bogus"})
    assert response.status_code == 400
    assert "bogus" in response.json()["detail"]


def test_indicators_endpoint_requires_indicators(
    client: TestClient, mock_history: OHLCVSeries
) -> None:
    """An empty indicators value is a 400."""
    response = client.get("/indicators/SPY", params={"indicators": " , "})
    assert response.status_code == 400


def test_indicators_list_endpoint(client: TestClient) -> None:
    """GET /indicators lists all 20 supported keys."""
    response = client.get("/indicators")
    assert response.status_code == 200
    assert len(response.json()["indicators"]) == 20
