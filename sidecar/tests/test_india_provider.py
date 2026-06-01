"""Pass B (B1) — the keyless India NSE provider (jugaad-data adapter).

jugaad is mocked at ``jugaad_data.nse.stock_df`` so no test hits the live NSE;
these assert the date-correction (IST trading day from jugaad's UTC-encoded
``DATE``), newest-first sorting, quote derivation, EOD-only timeframes, the
non-NSE fast-fail, and the cache-dir-race retry.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from services import india_provider
from services.errors import ProviderError


def _fake_jugaad_frame() -> pd.DataFrame:
    """Mimic jugaad's output: newest-first, DATE at 18:30 UTC (IST-midnight)."""
    # Raw DATE + 1 day = the IST trading date → trading days 05-27, 05-28, 05-29.
    return pd.DataFrame(
        [
            {
                "DATE": pd.Timestamp("2026-05-28 18:30:00"),
                "SERIES": "EQ",
                "OPEN": 130.0,
                "HIGH": 131.0,
                "LOW": 129.0,
                "CLOSE": 130.5,
                "PREV. CLOSE": 129.8,
                "VOLUME": 5000,
            },
            {
                "DATE": pd.Timestamp("2026-05-27 18:30:00"),
                "SERIES": "EQ",
                "OPEN": 128.0,
                "HIGH": 130.0,
                "LOW": 127.5,
                "CLOSE": 129.8,
                "PREV. CLOSE": 127.9,
                "VOLUME": 4200,
            },
            {
                "DATE": pd.Timestamp("2026-05-26 18:30:00"),
                "SERIES": "EQ",
                "OPEN": 127.0,
                "HIGH": 128.5,
                "LOW": 126.0,
                "CLOSE": 127.9,
                "PREV. CLOSE": 126.5,
                "VOLUME": 3900,
            },
        ]
    )


@pytest.fixture
def mock_jugaad(monkeypatch: pytest.MonkeyPatch) -> None:
    import jugaad_data.nse as jnse

    monkeypatch.setattr(jnse, "stock_df", lambda **kwargs: _fake_jugaad_frame())


def test_get_history_corrects_date_and_sorts_ascending(mock_jugaad: None) -> None:
    series = india_provider.get_history("GOLDBEES", "1d", "1mo")
    assert series.provider == "nse"
    assert series.symbol == "GOLDBEES"
    assert len(series.bars) == 3
    # Sorted ascending; last bar is the newest IST trading day (raw 05-28 + 1d).
    dates = [b.timestamp.date() for b in series.bars]
    assert dates == [date(2026, 5, 27), date(2026, 5, 28), date(2026, 5, 29)]
    assert series.bars[-1].close == 130.5


def test_get_quote_derives_from_latest_eod(mock_jugaad: None) -> None:
    q = india_provider.get_quote("GOLDBEES")
    assert q.provider == "nse"
    assert q.symbol == "GOLDBEES"
    assert q.currency == "INR"
    assert q.price == 130.5  # newest CLOSE
    # change vs the official PREV. CLOSE on the newest row (129.8).
    assert round(q.change, 2) == round(130.5 - 129.8, 2)
    assert q.timestamp.date() == date(2026, 5, 29)


def test_non_nse_symbol_fails_fast_without_network() -> None:
    # Not in the bundled NSE master → ProviderError (registry falls through), no fetch.
    with pytest.raises(ProviderError):
        india_provider.get_quote("AAPL")
    with pytest.raises(ProviderError):
        india_provider.get_history("ZZZZNOTREAL", "1d")


def test_intraday_timeframe_rejected(mock_jugaad: None) -> None:
    with pytest.raises(ProviderError, match="intraday"):
        india_provider.get_history("GOLDBEES", "1h")


def test_resample_to_weekly(mock_jugaad: None) -> None:
    series = india_provider.get_history("GOLDBEES", "1wk", "1mo")
    assert series.timeframe == "1wk"
    assert series.bars  # resampled, non-empty
    assert all(b.close > 0 for b in series.bars)


def test_stock_df_retries_on_cache_dir_race(monkeypatch: pytest.MonkeyPatch) -> None:
    import jugaad_data.nse as jnse

    calls = {"n": 0}

    def flaky(**kwargs: object) -> pd.DataFrame:
        calls["n"] += 1
        if calls["n"] == 1:
            raise FileExistsError("nsehistory-stock")
        return _fake_jugaad_frame()

    monkeypatch.setattr(jnse, "stock_df", flaky)
    series = india_provider.get_history("GOLDBEES", "1d")
    assert len(series.bars) == 3
    assert calls["n"] == 2  # retried past the cache-dir race


def test_empty_frame_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import jugaad_data.nse as jnse

    monkeypatch.setattr(jnse, "stock_df", lambda **kwargs: pd.DataFrame())
    with pytest.raises(ProviderError):
        india_provider.get_quote("GOLDBEES")
