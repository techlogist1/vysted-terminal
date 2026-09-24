"""Tests for the extended analyst-ratings provider.

The provider's only external dependency is ``yfinance.Ticker``; tests
swap that out with a deterministic fake. The rating normaliser is also
exercised directly.
"""

from __future__ import annotations

import pandas as pd
import pytest

from services import analyst_ratings_extended

# ---------------------------------------------------------------------------
# Normaliser unit tests — exercises the five-bucket mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Strong Buy", "strong-buy"),
        ("strong buy", "strong-buy"),
        ("Buy", "buy"),
        ("Outperform", "buy"),
        ("Overweight", "buy"),
        ("Accumulate", "buy"),
        ("Hold", "hold"),
        ("Neutral", "hold"),
        ("Market Perform", "hold"),
        ("Equal-Weight", "hold"),
        ("In-Line", "hold"),
        ("Sell", "sell"),
        ("Underperform", "sell"),
        ("Underweight", "sell"),
        ("Reduce", "sell"),
        ("Strong Sell", "strong-sell"),
        ("Conviction Sell", "strong-sell"),
    ],
)
def test_normalise_action_maps_to_buckets(raw: str, expected: str) -> None:
    assert analyst_ratings_extended._normalise_action(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "  ", "Coverage Initiated", "Some Other Phrase"])
def test_normalise_action_unknown_returns_none(raw: str | None) -> None:
    assert analyst_ratings_extended._normalise_action(raw) is None


# ---------------------------------------------------------------------------
# Provider integration — patched yfinance
# ---------------------------------------------------------------------------


class _FakeRatingsTicker:
    """Stand-in for yfinance.Ticker covering upgrades_downgrades + targets."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    def upgrades_downgrades(self) -> pd.DataFrame:
        # R15-DATA-069: yfinance's LIVE column names are ``currentPriceTarget``
        # / ``priorPriceTarget`` — the old ``PriceTarget``/``Target``/
        # ``Price Target`` names this fixture used to carry were dead (no
        # shipped yfinance version has ever used them), so every row silently
        # fell through to the single-snapshot fallback.
        return pd.DataFrame(
            [
                {
                    "Firm": "Morgan Stanley",
                    "ToGrade": "Overweight",
                    "FromGrade": "Equal-Weight",
                    "Action": "up",
                    "currentPriceTarget": 230.0,
                    "priorPriceTarget": 200.0,
                },
                {
                    "Firm": "Goldman Sachs",
                    "ToGrade": "Buy",
                    "FromGrade": "Neutral",
                    "Action": "up",
                    "currentPriceTarget": 225.0,
                    "priorPriceTarget": 210.0,
                },
                {
                    "Firm": "JP Morgan",
                    "ToGrade": "Underweight",
                    "FromGrade": "Neutral",
                    "Action": "down",
                    "currentPriceTarget": 180.0,
                    "priorPriceTarget": 210.0,
                },
                {
                    "Firm": "Morgan Stanley",
                    "ToGrade": "Equal-Weight",
                    "FromGrade": "Underperform",
                    "Action": "up",
                    "currentPriceTarget": 200.0,
                    "priorPriceTarget": float("nan"),
                },
            ],
            index=pd.to_datetime(["2026-05-01", "2026-04-15", "2026-04-01", "2026-03-01"]),
        )

    @property
    def recommendations(self) -> pd.DataFrame:
        return pd.DataFrame()

    @property
    def analyst_price_targets(self) -> dict:
        return {"current": 220.0, "low": 180.0, "high": 260.0, "mean": 225.0}

    @property
    def info(self) -> dict:
        return {"currency": "USD"}


@pytest.fixture
def mock_yf_ratings(monkeypatch: pytest.MonkeyPatch) -> type[_FakeRatingsTicker]:
    monkeypatch.setattr(analyst_ratings_extended, "_yf_ticker", _FakeRatingsTicker)
    return _FakeRatingsTicker


@pytest.mark.asyncio
async def test_get_ratings_history(mock_yf_ratings: type[_FakeRatingsTicker]) -> None:
    response = await analyst_ratings_extended.get_ratings_history("AAPL")
    assert response.symbol == "AAPL"
    assert len(response.history) == 4
    first = response.history[0]
    # Sorted newest-first.
    assert first.firm == "Morgan Stanley"
    assert first.rating_from == "hold"
    assert first.rating_to == "buy"


@pytest.mark.asyncio
async def test_get_price_target_history(mock_yf_ratings: type[_FakeRatingsTicker]) -> None:
    response = await analyst_ratings_extended.get_price_target_history("AAPL")
    assert response.symbol == "AAPL"
    assert len(response.history) == 4
    # The MS entry from 2026-05-01 should reference its previous target (200.0)
    # because the provider pairs adjacent rows from the same firm.
    ms_latest = next(
        e for e in response.history if e.firm == "Morgan Stanley" and e.target_to == 230.0
    )
    assert ms_latest.target_from == 200.0


@pytest.mark.asyncio
async def test_get_individual_analysts(mock_yf_ratings: type[_FakeRatingsTicker]) -> None:
    response = await analyst_ratings_extended.get_individual_analysts("AAPL")
    assert response.symbol == "AAPL"
    firms = {entry.firm for entry in response.analysts}
    assert {"Morgan Stanley", "Goldman Sachs", "JP Morgan"} <= firms
    # R15-DATA-069: the Individual table's Target reads currentPriceTarget —
    # each firm's kept row is its newest, so Morgan Stanley's is 230.0.
    ms = next(e for e in response.analysts if e.firm == "Morgan Stanley")
    assert ms.current_price_target == 230.0
    # Star rating + accuracy are placeholders pending richer providers.
    for entry in response.analysts:
        assert entry.one_year_accuracy is None
        assert entry.star_rating is None


@pytest.mark.asyncio
async def test_price_target_history_fallback_to_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When upgrades_downgrades has no currentPriceTarget column, the snapshot
    fills in."""

    class _NoTargetTicker(_FakeRatingsTicker):
        @property
        def upgrades_downgrades(self) -> pd.DataFrame:  # type: ignore[override]
            return pd.DataFrame()

    monkeypatch.setattr(analyst_ratings_extended, "_yf_ticker", _NoTargetTicker)
    response = await analyst_ratings_extended.get_price_target_history("AAPL")
    # Single consensus anchor row.
    assert len(response.history) == 1
    assert response.history[0].firm == "Consensus"
    assert response.history[0].target_to == 225.0


@pytest.mark.asyncio
async def test_price_target_history_ignores_the_dead_legacy_column_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class pin (R15-DATA-069, a case not written against): a frame carrying
    ONLY the old dead names (``PriceTarget``/``Target``/``Price Target`` — no
    shipped yfinance version has ever used them) yields no per-row entries and
    falls back to the single consensus anchor row, exactly as an empty frame
    would — proving the reader no longer reads them."""

    class _DeadColumnTicker(_FakeRatingsTicker):
        @property
        def upgrades_downgrades(self) -> pd.DataFrame:  # type: ignore[override]
            return pd.DataFrame(
                [
                    {
                        "Firm": "Morgan Stanley",
                        "ToGrade": "Buy",
                        "FromGrade": "Hold",
                        "Action": "up",
                        "PriceTarget": 230.0,
                        "Target": 230.0,
                        "Price Target": 230.0,
                    }
                ],
                index=pd.to_datetime(["2026-05-01"]),
            )

    monkeypatch.setattr(analyst_ratings_extended, "_yf_ticker", _DeadColumnTicker)
    response = await analyst_ratings_extended.get_price_target_history("AAPL")
    assert len(response.history) == 1
    assert response.history[0].firm == "Consensus"


@pytest.mark.asyncio
@pytest.mark.parametrize("symbol", ["RELIANCE.NS", "532540.BO"])
async def test_ratings_lane_keeps_india_suffixes(
    monkeypatch: pytest.MonkeyPatch, symbol: str
) -> None:
    """R15-DATA-029: the old dot-to-dash normaliser sent RELIANCE-NS / 532540-BO."""
    asked: list[str] = []

    def _recording(sym: str) -> _FakeRatingsTicker:
        asked.append(sym)
        return _FakeRatingsTicker(sym)

    monkeypatch.setattr(analyst_ratings_extended, "_yf_ticker", _recording)
    result = await analyst_ratings_extended.get_ratings_history(symbol)
    assert asked == [symbol]
    assert result.symbol == symbol
