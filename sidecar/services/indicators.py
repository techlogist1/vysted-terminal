"""Technical-indicator computation — server-side math for the chart panel.

Each public ``compute_*`` function takes an :class:`~models.market.OHLCVSeries`
and returns an :class:`~models.indicators.IndicatorSeries`. Standard textbook
formulas are used throughout; warm-up windows are emitted as ``None`` points so
the chart panel can leave a gap rather than draw a misleading flat line.

The numbers are computed with pandas/numpy. ``compute`` is the dispatch entry
point the router calls with a list of indicator keys.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pandas as pd

from models.indicators import (
    IndicatorLine,
    IndicatorPoint,
    IndicatorResponse,
    IndicatorSeries,
    VolumeProfile,
    VolumeProfileBucket,
)
from models.market import OHLCVSeries

# --------------------------------------------------------------------------
# Frame helpers
# --------------------------------------------------------------------------


def _frame(series: OHLCVSeries) -> pd.DataFrame:
    """Build a float DataFrame indexed by ISO timestamp string from a series."""
    times = [bar.timestamp.isoformat() for bar in series.bars]
    return pd.DataFrame(
        {
            "open": [float(bar.open) for bar in series.bars],
            "high": [float(bar.high) for bar in series.bars],
            "low": [float(bar.low) for bar in series.bars],
            "close": [float(bar.close) for bar in series.bars],
            "volume": [float(bar.volume) for bar in series.bars],
        },
        index=times,
    )


def _points(times: list[str], values: pd.Series) -> list[IndicatorPoint]:
    """Zip an aligned time list and value series into indicator points.

    ``NaN`` / ``inf`` become ``None`` so the JSON payload stays finite and the
    chart panel renders a gap.
    """
    out: list[IndicatorPoint] = []
    for time, raw in zip(times, values.tolist(), strict=True):
        if raw is None or not np.isfinite(raw):
            out.append(IndicatorPoint(time=time, value=None))
        else:
            out.append(IndicatorPoint(time=time, value=float(raw)))
    return out


def _line(label: str, times: list[str], values: pd.Series) -> IndicatorLine:
    return IndicatorLine(label=label, points=_points(times, values))


# --------------------------------------------------------------------------
# Shared building blocks
# --------------------------------------------------------------------------


def _rma(values: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (the running moving average used by RSI/ADX/ATR)."""
    return values.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _true_range(df: pd.DataFrame) -> pd.Series:
    """Wilder's true range."""
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _typical_price(df: pd.DataFrame) -> pd.Series:
    return (df["high"] + df["low"] + df["close"]) / 3.0


# --------------------------------------------------------------------------
# Overlay indicators (price pane)
# --------------------------------------------------------------------------


def compute_sma(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Simple moving average of close."""
    sma = df["close"].rolling(window=period, min_periods=period).mean()
    return IndicatorSeries(
        name="sma",
        panel="price",
        lines=[_line(f"SMA({period})", times, sma)],
    )


def compute_ema(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Exponential moving average of close."""
    ema = df["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    return IndicatorSeries(
        name="ema",
        panel="price",
        lines=[_line(f"EMA({period})", times, ema)],
    )


def compute_ma(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """A trio of simple moving averages — the conventional 20/50/200 ribbon."""
    lines = [
        _line(f"MA({period})", times, df["close"].rolling(period, min_periods=period).mean())
        for period in (20, 50, 200)
    ]
    return IndicatorSeries(name="ma", panel="price", lines=lines)


def compute_bollinger(
    df: pd.DataFrame, times: list[str], period: int = 20, std: float = 2.0
) -> IndicatorSeries:
    """Bollinger Bands — SMA mid band with ``std``-deviation envelopes."""
    mid = df["close"].rolling(period, min_periods=period).mean()
    deviation = df["close"].rolling(period, min_periods=period).std(ddof=0)
    upper = mid + std * deviation
    lower = mid - std * deviation
    return IndicatorSeries(
        name="bollinger",
        panel="price",
        lines=[
            _line(f"Upper ({period}, {std})", times, upper),
            _line(f"Middle ({period})", times, mid),
            _line(f"Lower ({period}, {std})", times, lower),
        ],
    )


def compute_ichimoku(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Ichimoku Cloud — the five standard 9/26/52 lines.

    Tenkan, Kijun, and Chikou stay on the bar timeline (``times``); the two
    Senkou spans are shifted forward 26 periods and emitted on the extended
    timeline ``times + 26 future bars`` so the forward-projected cloud is
    delivered to the chart rather than dropped at the series edge.
    """
    high, low, close = df["high"], df["low"], df["close"]

    def _mid(window: int) -> pd.Series:
        return (
            high.rolling(window, min_periods=window).max()
            + low.rolling(window, min_periods=window).min()
        ) / 2.0

    tenkan = _mid(9)
    kijun = _mid(26)
    # The forward-shifted spans are computed on the historical span first; the
    # extension to ``times + future`` happens below.
    senkou_a_now = (tenkan + kijun) / 2.0
    senkou_b_now = _mid(52)
    chikou = close.shift(-26)

    future_times = _project_future_times(df.index, count=26)
    extended_times = list(times) + future_times
    # Place the spans on the extended timeline by aligning each historical
    # value 26 bars to its right; the trailing 26 cells are the forward cloud.
    senkou_a_values = pd.Series([None] * len(extended_times), index=extended_times, dtype="object")
    senkou_b_values = pd.Series([None] * len(extended_times), index=extended_times, dtype="object")
    for offset, value in enumerate(senkou_a_now):
        target_index = offset + 26
        if target_index < len(extended_times):
            senkou_a_values.iloc[target_index] = value
    for offset, value in enumerate(senkou_b_now):
        target_index = offset + 26
        if target_index < len(extended_times):
            senkou_b_values.iloc[target_index] = value
    senkou_a = pd.to_numeric(senkou_a_values, errors="coerce")
    senkou_b = pd.to_numeric(senkou_b_values, errors="coerce")

    return IndicatorSeries(
        name="ichimoku",
        panel="price",
        lines=[
            _line("Tenkan-sen", times, tenkan),
            _line("Kijun-sen", times, kijun),
            _line("Senkou Span A", extended_times, senkou_a),
            _line("Senkou Span B", extended_times, senkou_b),
            _line("Chikou Span", times, chikou),
        ],
    )


def _project_future_times(index: pd.Index, count: int) -> list[str]:
    """Generate ``count`` future ISO timestamps continuing the bar cadence.

    The bar interval is inferred from the median of the parsed-index deltas;
    the projected timestamps are emitted in the same ISO format the frame's
    index already uses so the response stays internally consistent.
    """
    if count <= 0 or len(index) == 0:
        return []
    parsed = pd.to_datetime(index, errors="coerce", utc=True)
    valid = parsed.dropna()
    if len(valid) < 2:
        return []
    deltas = valid[1:] - valid[:-1]
    interval = pd.Series(deltas).median()
    if pd.isna(interval) or interval <= pd.Timedelta(0):
        return []
    last_time = valid[-1]
    return [(last_time + interval * (step + 1)).isoformat() for step in range(count)]


def compute_keltner(
    df: pd.DataFrame, times: list[str], period: int = 20, mult: float = 2.0
) -> IndicatorSeries:
    """Keltner Channels — EMA mid line with ATR-scaled envelopes."""
    mid = df["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    atr = _rma(_true_range(df), period)
    return IndicatorSeries(
        name="keltner",
        panel="price",
        lines=[
            _line(f"Upper ({period})", times, mid + mult * atr),
            _line(f"Middle ({period})", times, mid),
            _line(f"Lower ({period})", times, mid - mult * atr),
        ],
    )


def compute_vwap(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Volume-weighted average price.

    Intraday timeframes (median bar-to-bar gap below ~20 hours) reset the
    cumulative numerator and denominator at each calendar-date boundary so the
    line traces the canonical *session* VWAP. Daily-or-coarser series keep the
    whole-series running cumulative — the correct behaviour at those scales,
    where each bar already represents a full session.
    """
    typical = _typical_price(df)
    volume = df["volume"]
    # ``df.index`` carries the ISO-8601 timestamp strings the frame was built
    # from; reparse to datetimes to measure cadence and group by date.
    parsed_times = pd.to_datetime(df.index, errors="coerce", utc=True)
    is_intraday = False
    if len(parsed_times) >= 2:
        gaps = parsed_times[1:] - parsed_times[:-1]
        median_gap = pd.Series(gaps).median()
        if pd.notna(median_gap) and median_gap < pd.Timedelta(hours=20):
            is_intraday = True

    pv = typical * volume
    if is_intraday:
        # Group by calendar date — each group restarts the running sums, which
        # is the standard session-VWAP construction. ``transform('cumsum')``
        # preserves the original index order across groups.
        session = parsed_times.normalize()
        session_series = pd.Series(session, index=df.index)
        cumulative_pv = pv.groupby(session_series, sort=False).cumsum()
        cumulative_volume = volume.groupby(session_series, sort=False).cumsum()
        label = "VWAP (session)"
    else:
        cumulative_pv = pv.cumsum()
        cumulative_volume = volume.cumsum()
        label = "VWAP"
    safe_volume = cumulative_volume.replace(0.0, np.nan)
    vwap = cumulative_pv / safe_volume
    return IndicatorSeries(
        name="vwap",
        panel="price",
        lines=[_line(label, times, vwap)],
    )


def compute_parabolic_sar(
    df: pd.DataFrame,
    times: list[str],
    step: float = 0.02,
    max_step: float = 0.2,
) -> IndicatorSeries:
    """Wilder's Parabolic SAR — iterative, with acceleration-factor ramp."""
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    length = len(df)
    sar = np.full(length, np.nan)
    if length < 2:
        return IndicatorSeries(
            name="parabolic_sar",
            panel="price",
            lines=[_line("Parabolic SAR", times, pd.Series(sar, index=df.index))],
        )

    rising = high[1] >= high[0]
    accel = step
    extreme = high[1] if rising else low[1]
    sar[1] = low[0] if rising else high[0]

    for i in range(2, length):
        prior = sar[i - 1]
        current = prior + accel * (extreme - prior)
        if rising:
            current = min(current, low[i - 1], low[i - 2])
            if low[i] < current:
                rising = False
                current = extreme
                extreme = low[i]
                accel = step
            elif high[i] > extreme:
                extreme = high[i]
                accel = min(accel + step, max_step)
        else:
            current = max(current, high[i - 1], high[i - 2])
            if high[i] > current:
                rising = True
                current = extreme
                extreme = high[i]
                accel = step
            elif low[i] < extreme:
                extreme = low[i]
                accel = min(accel + step, max_step)
        sar[i] = current

    return IndicatorSeries(
        name="parabolic_sar",
        panel="price",
        lines=[_line("Parabolic SAR", times, pd.Series(sar, index=df.index))],
    )


# --------------------------------------------------------------------------
# Oscillators / volume indicators (separate pane)
# --------------------------------------------------------------------------


def compute_rsi(df: pd.DataFrame, times: list[str], period: int = 14) -> IndicatorSeries:
    """Wilder's Relative Strength Index."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = _rma(gain, period)
    avg_loss = _rma(loss, period)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # When average loss is zero the market only rose — RSI saturates at 100.
    rsi = rsi.where(avg_loss != 0.0, 100.0).where(avg_gain.notna())
    return IndicatorSeries(
        name="rsi",
        panel="separate",
        lines=[_line(f"RSI({period})", times, rsi)],
    )


def compute_macd(
    df: pd.DataFrame,
    times: list[str],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> IndicatorSeries:
    """Moving Average Convergence Divergence — line, signal, and histogram."""
    fast_ema = df["close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = df["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line
    return IndicatorSeries(
        name="macd",
        panel="separate",
        lines=[
            _line("MACD", times, macd_line),
            _line("Signal", times, signal_line),
            _line("Histogram", times, histogram),
        ],
    )


def compute_adx(df: pd.DataFrame, times: list[str], period: int = 14) -> IndicatorSeries:
    """Average Directional Index with the +DI / -DI directional lines."""
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0.0), up_move, 0.0), index=df.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0.0), down_move, 0.0), index=df.index
    )
    atr = _rma(_true_range(df), period)
    plus_di = 100.0 * _rma(plus_dm, period) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * _rma(minus_dm, period) / atr.replace(0.0, np.nan)
    di_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum
    adx = _rma(dx, period)
    return IndicatorSeries(
        name="adx",
        panel="separate",
        lines=[
            _line(f"ADX({period})", times, adx),
            _line("+DI", times, plus_di),
            _line("-DI", times, minus_di),
        ],
    )


def compute_stochastic(
    df: pd.DataFrame,
    times: list[str],
    k_period: int = 14,
    d_period: int = 3,
) -> IndicatorSeries:
    """Stochastic Oscillator — %K (fast) and %D (its SMA)."""
    lowest = df["low"].rolling(k_period, min_periods=k_period).min()
    highest = df["high"].rolling(k_period, min_periods=k_period).max()
    span = (highest - lowest).replace(0.0, np.nan)
    percent_k = 100.0 * (df["close"] - lowest) / span
    percent_d = percent_k.rolling(d_period, min_periods=d_period).mean()
    return IndicatorSeries(
        name="stochastic",
        panel="separate",
        lines=[
            _line(f"%K({k_period})", times, percent_k),
            _line(f"%D({d_period})", times, percent_d),
        ],
    )


def compute_atr(df: pd.DataFrame, times: list[str], period: int = 14) -> IndicatorSeries:
    """Average True Range (Wilder)."""
    atr = _rma(_true_range(df), period)
    return IndicatorSeries(
        name="atr",
        panel="separate",
        lines=[_line(f"ATR({period})", times, atr)],
    )


def compute_obv(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """On-Balance Volume — running volume signed by close-to-close direction."""
    direction = np.sign(df["close"].diff().fillna(0.0))
    obv = (direction * df["volume"]).cumsum()
    return IndicatorSeries(
        name="obv",
        panel="separate",
        lines=[_line("OBV", times, obv)],
    )


def compute_mfi(df: pd.DataFrame, times: list[str], period: int = 14) -> IndicatorSeries:
    """Money Flow Index — a volume-weighted RSI on typical price."""
    typical = _typical_price(df)
    raw_money_flow = typical * df["volume"]
    direction = typical.diff()
    positive_flow = raw_money_flow.where(direction > 0.0, 0.0)
    negative_flow = raw_money_flow.where(direction < 0.0, 0.0)
    positive_sum = positive_flow.rolling(period, min_periods=period).sum()
    negative_sum = negative_flow.rolling(period, min_periods=period).sum()
    money_ratio = positive_sum / negative_sum.replace(0.0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + money_ratio))
    mfi = mfi.where(negative_sum != 0.0, 100.0).where(positive_sum.notna())
    return IndicatorSeries(
        name="mfi",
        panel="separate",
        lines=[_line(f"MFI({period})", times, mfi)],
    )


def compute_cci(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Commodity Channel Index."""
    typical = _typical_price(df)
    sma = typical.rolling(period, min_periods=period).mean()
    mean_deviation = typical.rolling(period, min_periods=period).apply(
        lambda window: np.abs(window - window.mean()).mean(), raw=True
    )
    cci = (typical - sma) / (0.015 * mean_deviation.replace(0.0, np.nan))
    return IndicatorSeries(
        name="cci",
        panel="separate",
        lines=[_line(f"CCI({period})", times, cci)],
    )


def compute_williams_r(df: pd.DataFrame, times: list[str], period: int = 14) -> IndicatorSeries:
    """Williams %R — a 0..-100 inverted stochastic."""
    highest = df["high"].rolling(period, min_periods=period).max()
    lowest = df["low"].rolling(period, min_periods=period).min()
    span = (highest - lowest).replace(0.0, np.nan)
    williams = -100.0 * (highest - df["close"]) / span
    return IndicatorSeries(
        name="williams_r",
        panel="separate",
        lines=[_line(f"%R({period})", times, williams)],
    )


def compute_roc(df: pd.DataFrame, times: list[str], period: int = 12) -> IndicatorSeries:
    """Rate of Change — percentage change over ``period`` bars."""
    roc = 100.0 * (df["close"] - df["close"].shift(period)) / df["close"].shift(period)
    return IndicatorSeries(
        name="roc",
        panel="separate",
        lines=[_line(f"ROC({period})", times, roc)],
    )


def compute_volume(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Raw traded volume — plotted as a line in its own pane."""
    return IndicatorSeries(
        name="volume",
        panel="separate",
        lines=[_line("Volume", times, df["volume"])],
    )


def compute_volume_profile(df: pd.DataFrame, bins: int = 24) -> VolumeProfile:
    """Volume Profile — volume distributed across ``bins`` price buckets.

    Unlike every other indicator this is a *price-axis* histogram, not a
    time-series. The chart panel renders it as a horizontal histogram on the
    price pane via a custom series primitive, so the result is delivered on its
    own contract — :class:`VolumeProfile` — rather than on the time-keyed
    ``IndicatorSeries``.
    """
    closes = df["close"].to_numpy(dtype=float)
    volumes = df["volume"].to_numpy(dtype=float)
    if len(closes) == 0 or not np.isfinite(closes).any():
        return VolumeProfile(buckets=[])
    low, high = float(np.min(closes)), float(np.max(closes))
    if high <= low:
        high = low + 1.0
    edges = np.linspace(low, high, bins + 1)
    bucket = np.clip(np.digitize(closes, edges) - 1, 0, bins - 1)
    totals = np.zeros(bins)
    for index, volume in zip(bucket, volumes, strict=True):
        if np.isfinite(volume):
            totals[index] += volume
    centers = (edges[:-1] + edges[1:]) / 2.0
    buckets = [
        VolumeProfileBucket(price=float(center), volume=float(total))
        for center, total in zip(centers, totals, strict=True)
    ]
    return VolumeProfile(buckets=buckets)


# --------------------------------------------------------------------------
# Phase 2 — additional moving averages
# --------------------------------------------------------------------------


def compute_wma(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Linearly-weighted moving average — weights ``1, 2, ..., period``."""
    weights = np.arange(1, period + 1, dtype=float)
    weight_sum = weights.sum()

    def _weighted(window: np.ndarray) -> float:
        return float(np.dot(window, weights) / weight_sum)

    wma = df["close"].rolling(period, min_periods=period).apply(_weighted, raw=True)
    return IndicatorSeries(
        name="wma",
        panel="price",
        lines=[_line(f"WMA({period})", times, wma)],
    )


def compute_hma(df: pd.DataFrame, times: list[str], period: int = 16) -> IndicatorSeries:
    """Hull MA — ``WMA(2 * WMA(close, n/2) − WMA(close, n), sqrt(n))``.

    Default period is 16 because ``floor(sqrt(16)) = 4`` keeps a clean integer
    final smoothing window; the conventional default is anywhere from 9–21.
    """
    half = max(2, period // 2)
    sqrt_period = max(2, int(round(math.sqrt(period))))

    def _wma_series(values: pd.Series, win: int) -> pd.Series:
        weights = np.arange(1, win + 1, dtype=float)
        weight_sum = weights.sum()
        return values.rolling(win, min_periods=win).apply(
            lambda window: float(np.dot(window, weights) / weight_sum), raw=True
        )

    raw = 2.0 * _wma_series(df["close"], half) - _wma_series(df["close"], period)
    hma = _wma_series(raw, sqrt_period)
    return IndicatorSeries(
        name="hma",
        panel="price",
        lines=[_line(f"HMA({period})", times, hma)],
    )


def compute_dema(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Double Exponential MA — ``2 * EMA − EMA(EMA)``, reduces lag vs EMA."""
    ema = df["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    ema_of_ema = ema.ewm(span=period, adjust=False, min_periods=period).mean()
    dema = 2.0 * ema - ema_of_ema
    return IndicatorSeries(
        name="dema",
        panel="price",
        lines=[_line(f"DEMA({period})", times, dema)],
    )


def compute_tema(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Triple Exponential MA — ``3 * EMA − 3 * EMA(EMA) + EMA(EMA(EMA))``."""
    ema1 = df["close"].ewm(span=period, adjust=False, min_periods=period).mean()
    ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()
    ema3 = ema2.ewm(span=period, adjust=False, min_periods=period).mean()
    tema = 3.0 * ema1 - 3.0 * ema2 + ema3
    return IndicatorSeries(
        name="tema",
        panel="price",
        lines=[_line(f"TEMA({period})", times, tema)],
    )


def compute_kama(
    df: pd.DataFrame,
    times: list[str],
    period: int = 10,
    fast: int = 2,
    slow: int = 30,
) -> IndicatorSeries:
    """Kaufman Adaptive Moving Average — efficiency-ratio-driven smoothing."""
    close = df["close"]
    direction = (close - close.shift(period)).abs()
    volatility = close.diff().abs().rolling(period, min_periods=period).sum()
    er = direction / volatility.replace(0.0, np.nan)
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    closes = close.to_numpy(dtype=float)
    sc_values = sc.to_numpy(dtype=float)
    kama = np.full(len(close), np.nan)
    seed_index = period
    if seed_index < len(close):
        kama[seed_index] = closes[seed_index]
        for i in range(seed_index + 1, len(close)):
            sc_i = sc_values[i]
            if np.isnan(sc_i):
                kama[i] = kama[i - 1]
                continue
            kama[i] = kama[i - 1] + sc_i * (closes[i] - kama[i - 1])
    return IndicatorSeries(
        name="kama",
        panel="price",
        lines=[_line(f"KAMA({period})", times, pd.Series(kama, index=df.index))],
    )


# --------------------------------------------------------------------------
# Phase 2 — momentum
# --------------------------------------------------------------------------


def compute_tsi(
    df: pd.DataFrame,
    times: list[str],
    long: int = 25,
    short: int = 13,
) -> IndicatorSeries:
    """True Strength Index — double-smoothed momentum, bounded ±100."""
    momentum = df["close"].diff()
    abs_momentum = momentum.abs()

    def _double_ema(values: pd.Series) -> pd.Series:
        first = values.ewm(span=long, adjust=False, min_periods=long).mean()
        return first.ewm(span=short, adjust=False, min_periods=short).mean()

    smoothed = _double_ema(momentum)
    smoothed_abs = _double_ema(abs_momentum)
    tsi = 100.0 * smoothed / smoothed_abs.replace(0.0, np.nan)
    return IndicatorSeries(
        name="tsi",
        panel="separate",
        lines=[_line(f"TSI({long},{short})", times, tsi)],
    )


def compute_kst(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Know Sure Thing — sum of four smoothed rates of change, plus signal."""
    close = df["close"]

    def _smoothed_roc(roc_period: int, sma_period: int) -> pd.Series:
        roc = close.pct_change(roc_period) * 100.0
        return roc.rolling(sma_period, min_periods=sma_period).mean()

    rcma1 = _smoothed_roc(10, 10)
    rcma2 = _smoothed_roc(15, 10)
    rcma3 = _smoothed_roc(20, 10)
    rcma4 = _smoothed_roc(30, 15)
    kst = rcma1 + 2.0 * rcma2 + 3.0 * rcma3 + 4.0 * rcma4
    signal = kst.rolling(9, min_periods=9).mean()
    return IndicatorSeries(
        name="kst",
        panel="separate",
        lines=[_line("KST", times, kst), _line("Signal", times, signal)],
    )


def compute_awesome_oscillator(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Awesome Oscillator — SMA(median, 5) − SMA(median, 34)."""
    median = (df["high"] + df["low"]) / 2.0
    fast = median.rolling(5, min_periods=5).mean()
    slow = median.rolling(34, min_periods=34).mean()
    ao = fast - slow
    return IndicatorSeries(
        name="awesome_oscillator",
        panel="separate",
        lines=[_line("AO", times, ao)],
    )


def compute_ppo(
    df: pd.DataFrame,
    times: list[str],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> IndicatorSeries:
    """Percentage Price Oscillator — MACD as a percentage of the slow EMA."""
    fast_ema = df["close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = df["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()
    ppo_line = 100.0 * (fast_ema - slow_ema) / slow_ema.replace(0.0, np.nan)
    signal_line = ppo_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = ppo_line - signal_line
    return IndicatorSeries(
        name="ppo",
        panel="separate",
        lines=[
            _line("PPO", times, ppo_line),
            _line("Signal", times, signal_line),
            _line("Histogram", times, histogram),
        ],
    )


def compute_ultimate_oscillator(
    df: pd.DataFrame,
    times: list[str],
    short: int = 7,
    medium: int = 14,
    long: int = 28,
) -> IndicatorSeries:
    """Ultimate Oscillator — multi-timeframe momentum, bounded [0, 100]."""
    close = df["close"]
    prev_close = close.shift(1)
    true_low = pd.concat([df["low"], prev_close], axis=1).min(axis=1)
    bp = close - true_low
    tr = _true_range(df)

    def _avg(period: int) -> pd.Series:
        bp_sum = bp.rolling(period, min_periods=period).sum()
        tr_sum = tr.rolling(period, min_periods=period).sum()
        return bp_sum / tr_sum.replace(0.0, np.nan)

    avg_short = _avg(short)
    avg_medium = _avg(medium)
    avg_long = _avg(long)
    uo = 100.0 * (4.0 * avg_short + 2.0 * avg_medium + avg_long) / 7.0
    return IndicatorSeries(
        name="ultimate_oscillator",
        panel="separate",
        lines=[_line("UO", times, uo)],
    )


# --------------------------------------------------------------------------
# Phase 2 — volatility
# --------------------------------------------------------------------------


def compute_std_dev(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Rolling standard deviation of close — population statistic."""
    sd = df["close"].rolling(period, min_periods=period).std(ddof=0)
    return IndicatorSeries(
        name="std_dev",
        panel="separate",
        lines=[_line(f"StdDev({period})", times, sd)],
    )


def compute_bollinger_bandwidth(
    df: pd.DataFrame, times: list[str], period: int = 20, std: float = 2.0
) -> IndicatorSeries:
    """Bollinger Bandwidth — ``(upper − lower) / middle``, % of mid band."""
    mid = df["close"].rolling(period, min_periods=period).mean()
    sd = df["close"].rolling(period, min_periods=period).std(ddof=0)
    upper = mid + std * sd
    lower = mid - std * sd
    bandwidth = (upper - lower) / mid.replace(0.0, np.nan)
    return IndicatorSeries(
        name="bollinger_bandwidth",
        panel="separate",
        lines=[_line(f"BBW({period})", times, bandwidth)],
    )


def compute_donchian(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Donchian Channels — rolling-max high, rolling-min low, midline avg."""
    upper = df["high"].rolling(period, min_periods=period).max()
    lower = df["low"].rolling(period, min_periods=period).min()
    middle = (upper + lower) / 2.0
    return IndicatorSeries(
        name="donchian",
        panel="price",
        lines=[
            _line(f"Upper ({period})", times, upper),
            _line(f"Middle ({period})", times, middle),
            _line(f"Lower ({period})", times, lower),
        ],
    )


def compute_chaikin_volatility(
    df: pd.DataFrame, times: list[str], period: int = 10
) -> IndicatorSeries:
    """Chaikin Volatility — rate-of-change (in %) of EMA of high-low range."""
    hl = df["high"] - df["low"]
    ema_hl = hl.ewm(span=period, adjust=False, min_periods=period).mean()
    cv = 100.0 * (ema_hl - ema_hl.shift(period)) / ema_hl.shift(period).replace(0.0, np.nan)
    return IndicatorSeries(
        name="chaikin_volatility",
        panel="separate",
        lines=[_line(f"CV({period})", times, cv)],
    )


# --------------------------------------------------------------------------
# Phase 2 — volume
# --------------------------------------------------------------------------


def _money_flow_multiplier(df: pd.DataFrame) -> pd.Series:
    """Chaikin's money-flow multiplier ``((C-L) − (H-C)) / (H-L)``."""
    span = (df["high"] - df["low"]).replace(0.0, np.nan)
    return ((df["close"] - df["low"]) - (df["high"] - df["close"])) / span


def compute_ad_line(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Accumulation/Distribution Line — running sum of money-flow * volume."""
    mf_volume = _money_flow_multiplier(df).fillna(0.0) * df["volume"]
    ad = mf_volume.cumsum()
    return IndicatorSeries(
        name="ad_line",
        panel="separate",
        lines=[_line("A/D", times, ad)],
    )


def compute_chaikin_money_flow(
    df: pd.DataFrame, times: list[str], period: int = 20
) -> IndicatorSeries:
    """Chaikin Money Flow — money-flow-volume / volume over a rolling window."""
    mf_volume = _money_flow_multiplier(df).fillna(0.0) * df["volume"]
    numer = mf_volume.rolling(period, min_periods=period).sum()
    denom = df["volume"].rolling(period, min_periods=period).sum()
    cmf = numer / denom.replace(0.0, np.nan)
    return IndicatorSeries(
        name="chaikin_money_flow",
        panel="separate",
        lines=[_line(f"CMF({period})", times, cmf)],
    )


def compute_force_index(df: pd.DataFrame, times: list[str], period: int = 13) -> IndicatorSeries:
    """Force Index — ``(close − close[1]) * volume`` smoothed by EMA(13)."""
    raw = df["close"].diff() * df["volume"]
    ema = raw.ewm(span=period, adjust=False, min_periods=1).mean()
    return IndicatorSeries(
        name="force_index",
        panel="separate",
        lines=[
            _line("Force", times, raw),
            _line(f"FI({period})", times, ema),
        ],
    )


def compute_ease_of_movement(
    df: pd.DataFrame, times: list[str], period: int = 14
) -> IndicatorSeries:
    """Ease of Movement — midpoint move relative to volume/range box."""
    midpoint = (df["high"] + df["low"]) / 2.0
    midpoint_move = midpoint.diff()
    box_ratio = (df["volume"] / 100_000_000.0) / (df["high"] - df["low"]).replace(0.0, np.nan)
    raw = midpoint_move / box_ratio
    smoothed = raw.rolling(period, min_periods=period).mean()
    return IndicatorSeries(
        name="ease_of_movement",
        panel="separate",
        lines=[_line(f"EOM({period})", times, smoothed)],
    )


def compute_vpt(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Volume Price Trend — cumulative ``volume * close-pct-change``."""
    increment = df["volume"] * df["close"].pct_change().fillna(0.0)
    vpt = increment.cumsum()
    return IndicatorSeries(
        name="vpt",
        panel="separate",
        lines=[_line("VPT", times, vpt)],
    )


# --------------------------------------------------------------------------
# Phase 2 — trend
# --------------------------------------------------------------------------


def compute_aroon(df: pd.DataFrame, times: list[str], period: int = 25) -> IndicatorSeries:
    """Aroon — bars-since-extreme over a lookback window, scaled to 0–100."""

    def _aroon(window: np.ndarray, kind: str) -> float:
        idx = int(np.argmax(window) if kind == "high" else np.argmin(window))
        return 100.0 * idx / period

    high_aroon = (
        df["high"]
        .rolling(period + 1, min_periods=period + 1)
        .apply(lambda w: _aroon(w, "high"), raw=True)
    )
    low_aroon = (
        df["low"]
        .rolling(period + 1, min_periods=period + 1)
        .apply(lambda w: _aroon(w, "low"), raw=True)
    )
    return IndicatorSeries(
        name="aroon",
        panel="separate",
        lines=[
            _line(f"Aroon Up ({period})", times, high_aroon),
            _line(f"Aroon Down ({period})", times, low_aroon),
        ],
    )


def compute_aroon_oscillator(
    df: pd.DataFrame, times: list[str], period: int = 25
) -> IndicatorSeries:
    """Aroon Oscillator — ``Aroon Up − Aroon Down``."""

    def _aroon(window: np.ndarray, kind: str) -> float:
        idx = int(np.argmax(window) if kind == "high" else np.argmin(window))
        return 100.0 * idx / period

    high_aroon = (
        df["high"]
        .rolling(period + 1, min_periods=period + 1)
        .apply(lambda w: _aroon(w, "high"), raw=True)
    )
    low_aroon = (
        df["low"]
        .rolling(period + 1, min_periods=period + 1)
        .apply(lambda w: _aroon(w, "low"), raw=True)
    )
    return IndicatorSeries(
        name="aroon_oscillator",
        panel="separate",
        lines=[_line(f"Aroon Osc ({period})", times, high_aroon - low_aroon)],
    )


def compute_vortex(df: pd.DataFrame, times: list[str], period: int = 14) -> IndicatorSeries:
    """Vortex Indicator — VI+ and VI− directional persistence."""
    high, low, close = df["high"], df["low"], df["close"]
    vm_plus = (high - low.shift(1)).abs()
    vm_minus = (low - high.shift(1)).abs()
    tr = _true_range(df)
    vi_plus = vm_plus.rolling(period, min_periods=period).sum() / tr.rolling(
        period, min_periods=period
    ).sum().replace(0.0, np.nan)
    vi_minus = vm_minus.rolling(period, min_periods=period).sum() / tr.rolling(
        period, min_periods=period
    ).sum().replace(0.0, np.nan)
    _ = close  # silence "unused" — kept for clarity that the indicator is OHLC-derived
    return IndicatorSeries(
        name="vortex",
        panel="separate",
        lines=[
            _line(f"VI+ ({period})", times, vi_plus),
            _line(f"VI- ({period})", times, vi_minus),
        ],
    )


def compute_mass_index(
    df: pd.DataFrame, times: list[str], period: int = 9, sum_period: int = 25
) -> IndicatorSeries:
    """Mass Index — sum of EMA9(H-L)/EMA9(EMA9(H-L)) over 25 bars (reversal)."""
    range_hl = df["high"] - df["low"]
    ema = range_hl.ewm(span=period, adjust=False, min_periods=period).mean()
    ema_of_ema = ema.ewm(span=period, adjust=False, min_periods=period).mean()
    ratio = ema / ema_of_ema.replace(0.0, np.nan)
    mass = ratio.rolling(sum_period, min_periods=sum_period).sum()
    return IndicatorSeries(
        name="mass_index",
        panel="separate",
        lines=[_line(f"MI({sum_period})", times, mass)],
    )


def compute_pivot_points(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Classic floor-trader Pivot Points — pivot, R1/R2, S1/S2 from prior bar."""
    prev_high = df["high"].shift(1)
    prev_low = df["low"].shift(1)
    prev_close = df["close"].shift(1)
    pivot = (prev_high + prev_low + prev_close) / 3.0
    r1 = 2.0 * pivot - prev_low
    s1 = 2.0 * pivot - prev_high
    r2 = pivot + (prev_high - prev_low)
    s2 = pivot - (prev_high - prev_low)
    return IndicatorSeries(
        name="pivot_points",
        panel="price",
        lines=[
            _line("R2", times, r2),
            _line("R1", times, r1),
            _line("Pivot", times, pivot),
            _line("S1", times, s1),
            _line("S2", times, s2),
        ],
    )


def compute_supertrend(
    df: pd.DataFrame, times: list[str], period: int = 10, multiplier: float = 3.0
) -> IndicatorSeries:
    """SuperTrend — ATR-based trailing-stop trend follower.

    Returns one line: the active trend line (upper band when in downtrend, lower
    band when in uptrend), suitable for rendering as a price-pane overlay.
    """
    atr = _rma(_true_range(df), period)
    hl2 = (df["high"] + df["low"]) / 2.0
    upper_basic = hl2 + multiplier * atr
    lower_basic = hl2 - multiplier * atr
    upper = upper_basic.copy()
    lower = lower_basic.copy()
    closes = df["close"].to_numpy(dtype=float)
    # Copy so we can mutate in place — pandas may hand back a non-writable view.
    upper_arr = upper.to_numpy(dtype=float).copy()
    lower_arr = lower.to_numpy(dtype=float).copy()
    trend = np.full(len(df), np.nan)
    direction = 1  # 1 = uptrend, -1 = downtrend
    for i in range(1, len(df)):
        if not (np.isfinite(upper_arr[i]) and np.isfinite(lower_arr[i])):
            continue
        if i > 1 and np.isfinite(upper_arr[i - 1]):
            if upper_arr[i] > upper_arr[i - 1] and closes[i - 1] <= upper_arr[i - 1]:
                upper_arr[i] = upper_arr[i - 1]
            if lower_arr[i] < lower_arr[i - 1] and closes[i - 1] >= lower_arr[i - 1]:
                lower_arr[i] = lower_arr[i - 1]
        if direction == 1 and closes[i] < lower_arr[i]:
            direction = -1
        elif direction == -1 and closes[i] > upper_arr[i]:
            direction = 1
        trend[i] = lower_arr[i] if direction == 1 else upper_arr[i]
    return IndicatorSeries(
        name="supertrend",
        panel="price",
        lines=[
            _line(f"SuperTrend({period}, {multiplier})", times, pd.Series(trend, index=df.index))
        ],
    )


# --------------------------------------------------------------------------
# Phase 2 — statistical
# --------------------------------------------------------------------------


def _rolling_linreg(values: pd.Series, period: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Rolling linear-regression of ``values`` on bar index.

    Returns ``(fitted_endpoint, slope, residual_std)`` per bar — each column
    aligned on the same index as ``values``. The fitted endpoint is the
    regression line evaluated at the latest x in the window (the conventional
    "Linear Regression" indicator value).
    """
    n = period
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    x_diff = x - x_mean
    sum_xx = float(np.dot(x_diff, x_diff))

    fitted = np.full(len(values), np.nan)
    slopes = np.full(len(values), np.nan)
    residual_std = np.full(len(values), np.nan)
    arr = values.to_numpy(dtype=float)
    for i in range(n - 1, len(values)):
        window = arr[i - n + 1 : i + 1]
        if not np.all(np.isfinite(window)):
            continue
        y_mean = window.mean()
        y_diff = window - y_mean
        slope = float(np.dot(x_diff, y_diff)) / sum_xx
        intercept = y_mean - slope * x_mean
        # Endpoint: fitted value at the most recent x (= n - 1).
        fitted[i] = intercept + slope * (n - 1)
        slopes[i] = slope
        residuals = window - (intercept + slope * x)
        residual_std[i] = float(np.sqrt(np.mean(residuals * residuals)))
    return (
        pd.Series(fitted, index=values.index),
        pd.Series(slopes, index=values.index),
        pd.Series(residual_std, index=values.index),
    )


def compute_linreg(df: pd.DataFrame, times: list[str], period: int = 20) -> IndicatorSeries:
    """Linear-Regression line — least-squares fit of close over a window."""
    fitted, _, _ = _rolling_linreg(df["close"], period)
    return IndicatorSeries(
        name="linreg",
        panel="price",
        lines=[_line(f"LinReg({period})", times, fitted)],
    )


def compute_std_error_bands(
    df: pd.DataFrame, times: list[str], period: int = 20, multiplier: float = 2.0
) -> IndicatorSeries:
    """Standard-Error Bands — linreg endpoint ± k * residual standard error."""
    fitted, _, residual_std = _rolling_linreg(df["close"], period)
    upper = fitted + multiplier * residual_std
    lower = fitted - multiplier * residual_std
    return IndicatorSeries(
        name="std_error_bands",
        panel="price",
        lines=[
            _line(f"Upper ({period})", times, upper),
            _line(f"Middle ({period})", times, fitted),
            _line(f"Lower ({period})", times, lower),
        ],
    )


def compute_hlc3(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Typical Price — ``(high + low + close) / 3`` per bar."""
    return IndicatorSeries(
        name="hlc3",
        panel="price",
        lines=[_line("HLC/3", times, (df["high"] + df["low"] + df["close"]) / 3.0)],
    )


def compute_ohlc4(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Average Price — ``(open + high + low + close) / 4`` per bar."""
    return IndicatorSeries(
        name="ohlc4",
        panel="price",
        lines=[
            _line(
                "OHLC/4",
                times,
                (df["open"] + df["high"] + df["low"] + df["close"]) / 4.0,
            )
        ],
    )


def compute_median_price(df: pd.DataFrame, times: list[str]) -> IndicatorSeries:
    """Median Price — ``(high + low) / 2`` per bar."""
    return IndicatorSeries(
        name="median_price",
        panel="price",
        lines=[_line("Median", times, (df["high"] + df["low"]) / 2.0)],
    )


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

# Each entry maps an indicator key to a builder that takes ``(df, times)``.
# ``volume_profile`` is special-cased in :func:`compute` — its result is a
# price-axis histogram on a different contract (:class:`VolumeProfile`) and
# does not fit the time-keyed ``IndicatorSeries`` builder signature.
_BUILDERS: dict[str, Callable[[pd.DataFrame, list[str]], IndicatorSeries]] = {
    # --- Phase 1 (20) ---
    "rsi": compute_rsi,
    "macd": compute_macd,
    "ma": compute_ma,
    "ema": compute_ema,
    "sma": compute_sma,
    "bollinger": compute_bollinger,
    "volume": compute_volume,
    "adx": compute_adx,
    "stochastic": compute_stochastic,
    "atr": compute_atr,
    "obv": compute_obv,
    "mfi": compute_mfi,
    "ichimoku": compute_ichimoku,
    "keltner": compute_keltner,
    "vwap": compute_vwap,
    "parabolic_sar": compute_parabolic_sar,
    "cci": compute_cci,
    "williams_r": compute_williams_r,
    "roc": compute_roc,
    # --- Phase 2 — moving averages ---
    "wma": compute_wma,
    "hma": compute_hma,
    "dema": compute_dema,
    "tema": compute_tema,
    "kama": compute_kama,
    # --- Phase 2 — momentum ---
    "tsi": compute_tsi,
    "kst": compute_kst,
    "awesome_oscillator": compute_awesome_oscillator,
    "ppo": compute_ppo,
    "ultimate_oscillator": compute_ultimate_oscillator,
    # --- Phase 2 — volatility ---
    "std_dev": compute_std_dev,
    "bollinger_bandwidth": compute_bollinger_bandwidth,
    "donchian": compute_donchian,
    "chaikin_volatility": compute_chaikin_volatility,
    # --- Phase 2 — volume ---
    "ad_line": compute_ad_line,
    "chaikin_money_flow": compute_chaikin_money_flow,
    "force_index": compute_force_index,
    "ease_of_movement": compute_ease_of_movement,
    "vpt": compute_vpt,
    # --- Phase 2 — trend ---
    "aroon": compute_aroon,
    "aroon_oscillator": compute_aroon_oscillator,
    "vortex": compute_vortex,
    "mass_index": compute_mass_index,
    "pivot_points": compute_pivot_points,
    "supertrend": compute_supertrend,
    # --- Phase 2 — statistical ---
    "linreg": compute_linreg,
    "std_error_bands": compute_std_error_bands,
    "hlc3": compute_hlc3,
    "ohlc4": compute_ohlc4,
    "median_price": compute_median_price,
}

# The volume_profile key is supported and resolvable through ``normalize_key``,
# but it returns a separate :class:`VolumeProfile` payload (see ``compute``).
_VOLUME_PROFILE_KEY = "volume_profile"

# Public, ordered list of every supported indicator key — keeps volume_profile
# visible to the catalog and the ``GET /indicators`` discovery endpoint.
SUPPORTED_INDICATORS: tuple[str, ...] = (*tuple(_BUILDERS), _VOLUME_PROFILE_KEY)

# Accepted aliases for the keys above — keeps the query string forgiving.
_ALIASES: dict[str, str] = {
    # --- Phase 1 ---
    "bollinger_bands": "bollinger",
    "bbands": "bollinger",
    "bb": "bollinger",
    "stoch": "stochastic",
    "williams": "williams_r",
    "williams%r": "williams_r",
    "williams_%r": "williams_r",
    "%r": "williams_r",
    "willr": "williams_r",
    "wpr": "williams_r",
    "psar": "parabolic_sar",
    "sar": "parabolic_sar",
    "volume-profile": "volume_profile",
    "volprofile": "volume_profile",
    "vp": "volume_profile",
    "moneyflow": "mfi",
    # --- Phase 2 ---
    "hull_ma": "hma",
    "hullma": "hma",
    "double_ema": "dema",
    "triple_ema": "tema",
    "true_strength_index": "tsi",
    "know_sure_thing": "kst",
    "ao": "awesome_oscillator",
    "awesome": "awesome_oscillator",
    "uo": "ultimate_oscillator",
    "ultosc": "ultimate_oscillator",
    "stdev": "std_dev",
    "stddev": "std_dev",
    "bbw": "bollinger_bandwidth",
    "bollinger_width": "bollinger_bandwidth",
    "donchian_channels": "donchian",
    "dc": "donchian",
    "cv": "chaikin_volatility",
    "ad": "ad_line",
    "accumulation_distribution": "ad_line",
    "cmf": "chaikin_money_flow",
    "fi": "force_index",
    "eom": "ease_of_movement",
    "emv": "ease_of_movement",
    "volume_price_trend": "vpt",
    "aroon_osc": "aroon_oscillator",
    "vi": "vortex",
    "mass": "mass_index",
    "pivots": "pivot_points",
    "pp": "pivot_points",
    "st": "supertrend",
    "linear_regression": "linreg",
    "lreg": "linreg",
    "std_err_bands": "std_error_bands",
    "seb": "std_error_bands",
    "typical_price": "hlc3",
    "average_price": "ohlc4",
}


def normalize_key(raw: str) -> str | None:
    """Map a user-supplied indicator token to a canonical key, or ``None``."""
    key = raw.strip().lower().replace(" ", "_")
    if key in _BUILDERS or key == _VOLUME_PROFILE_KEY:
        return key
    return _ALIASES.get(key)


def compute(series: OHLCVSeries, keys: list[str]) -> IndicatorResponse:
    """Compute every requested indicator over ``series``.

    Unknown keys are skipped silently — the router validates and surfaces them
    before calling here. Duplicate keys are computed once, in request order.
    ``volume_profile`` is routed into the response's dedicated
    ``volume_profile`` field rather than the ``indicators`` list.
    """
    df = _frame(series)
    times = list(df.index)
    seen: set[str] = set()
    results: list[IndicatorSeries] = []
    volume_profile: VolumeProfile | None = None
    for raw in keys:
        key = normalize_key(raw)
        if key is None or key in seen:
            continue
        seen.add(key)
        if key == _VOLUME_PROFILE_KEY:
            volume_profile = compute_volume_profile(df)
            continue
        results.append(_BUILDERS[key](df, times))
    return IndicatorResponse(
        symbol=series.symbol,
        timeframe=series.timeframe,
        provider=series.provider,
        indicators=results,
        volume_profile=volume_profile,
    )
