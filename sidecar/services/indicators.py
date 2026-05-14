"""Technical-indicator computation — server-side math for the chart panel.

Each public ``compute_*`` function takes an :class:`~models.market.OHLCVSeries`
and returns an :class:`~models.indicators.IndicatorSeries`. Standard textbook
formulas are used throughout; warm-up windows are emitted as ``None`` points so
the chart panel can leave a gap rather than draw a misleading flat line.

The numbers are computed with pandas/numpy. ``compute`` is the dispatch entry
point the router calls with a list of indicator keys.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from models.indicators import (
    IndicatorLine,
    IndicatorPoint,
    IndicatorResponse,
    IndicatorSeries,
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

    Senkou spans are shifted forward 26 periods and the chikou span back 26, as
    in the classic construction; points pushed beyond the series window are
    dropped (the chart panel does not draw a future projection).
    """
    high, low, close = df["high"], df["low"], df["close"]

    def _mid(window: int) -> pd.Series:
        return (
            high.rolling(window, min_periods=window).max()
            + low.rolling(window, min_periods=window).min()
        ) / 2.0

    tenkan = _mid(9)
    kijun = _mid(26)
    senkou_a = ((tenkan + kijun) / 2.0).shift(26)
    senkou_b = _mid(52).shift(26)
    chikou = close.shift(-26)
    return IndicatorSeries(
        name="ichimoku",
        panel="price",
        lines=[
            _line("Tenkan-sen", times, tenkan),
            _line("Kijun-sen", times, kijun),
            _line("Senkou Span A", times, senkou_a),
            _line("Senkou Span B", times, senkou_b),
            _line("Chikou Span", times, chikou),
        ],
    )


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
    """Volume-weighted average price, cumulative over the supplied window.

    Without intraday session boundaries the sidecar treats the whole series as
    one session — a running VWAP. The chart panel labels it accordingly.
    """
    typical = _typical_price(df)
    cumulative_pv = (typical * df["volume"]).cumsum()
    cumulative_volume = df["volume"].cumsum().replace(0.0, np.nan)
    vwap = cumulative_pv / cumulative_volume
    return IndicatorSeries(
        name="vwap",
        panel="price",
        lines=[_line("VWAP", times, vwap)],
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


def compute_volume_profile(df: pd.DataFrame, times: list[str], bins: int = 24) -> IndicatorSeries:
    """Volume Profile — volume distributed across ``bins`` price buckets.

    Unlike every other indicator this is a *price-axis* histogram, not a
    time-series. To stay inside the ``IndicatorSeries`` contract without a
    contract change, each bucket is emitted as one point whose ``time`` is the
    bucket's price-level label and whose ``value`` is the volume traded there;
    the chart panel renders it as a horizontal histogram rather than a line.
    The non-time ``time`` field is a deliberate, documented overload — see
    ``BLOCKERS-chart.md``.
    """
    closes = df["close"].to_numpy(dtype=float)
    volumes = df["volume"].to_numpy(dtype=float)
    if len(closes) == 0 or not np.isfinite(closes).any():
        return IndicatorSeries(
            name="volume_profile",
            panel="separate",
            lines=[IndicatorLine(label="Volume Profile", points=[])],
        )
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
    points = [
        IndicatorPoint(time=f"{center:.4f}", value=float(total))
        for center, total in zip(centers, totals, strict=True)
    ]
    return IndicatorSeries(
        name="volume_profile",
        panel="separate",
        lines=[IndicatorLine(label="Volume Profile", points=points)],
    )


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

# Each entry maps an indicator key to a builder that takes ``(df, times)``.
_BUILDERS: dict[str, Callable[[pd.DataFrame, list[str]], IndicatorSeries]] = {
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
    "volume_profile": compute_volume_profile,
    "parabolic_sar": compute_parabolic_sar,
    "cci": compute_cci,
    "williams_r": compute_williams_r,
    "roc": compute_roc,
}

# Public, ordered list of every supported indicator key.
SUPPORTED_INDICATORS: tuple[str, ...] = tuple(_BUILDERS)

# Accepted aliases for the keys above — keeps the query string forgiving.
_ALIASES: dict[str, str] = {
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
}


def normalize_key(raw: str) -> str | None:
    """Map a user-supplied indicator token to a canonical key, or ``None``."""
    key = raw.strip().lower().replace(" ", "_")
    if key in _BUILDERS:
        return key
    return _ALIASES.get(key)


def compute(series: OHLCVSeries, keys: list[str]) -> IndicatorResponse:
    """Compute every requested indicator over ``series``.

    Unknown keys are skipped silently — the router validates and surfaces them
    before calling here. Duplicate keys are computed once, in request order.
    """
    df = _frame(series)
    times = list(df.index)
    seen: set[str] = set()
    results: list[IndicatorSeries] = []
    for raw in keys:
        key = normalize_key(raw)
        if key is None or key in seen:
            continue
        seen.add(key)
        results.append(_BUILDERS[key](df, times))
    return IndicatorResponse(
        symbol=series.symbol,
        timeframe=series.timeframe,
        provider=series.provider,
        indicators=results,
    )
