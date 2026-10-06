"""Tests for the shared ``routers._cached.cached()`` helper.

fundamentals.py's three/earnings.py's four near-identical cache-read/
validate/fetch/store blocks (each with its own dead ``except ProviderError``
half the app's one global handler already covers) collapsed into this ONE
helper (R15-CODE-DATA-011, R15-CODE-DATA-012) — every route below rides the
SAME ``data_cache.get_with_meta`` call site.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _no_network_filed_basis(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import exchange_financials

    async def _stub(_listing: str) -> None:
        return None

    monkeypatch.setattr(exchange_financials, "filed_basis", _stub)


@pytest.fixture(autouse=True)
def _isolated_data_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> None:
    from config import DATA_DIR_ENV
    from services import data_cache

    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield
    data_cache.reset_for_tests()


def test_corrupt_cache_entry_refetches_for_all_rating_routes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cache row that fails ``model_validate`` (an empty dict, missing every
    required field) must be treated as a miss and refetched — for every
    fundamentals ratings route, not just the aggregate ``/ratings`` one, and
    for the earnings router too. All ride the same helper."""
    from models.analyst_extended import (
        IndividualAnalystForecast,
        IndividualAnalystResponse,
        PriceTargetEntry,
        PriceTargetHistoryResponse,
        RatingsHistoryEntry,
        RatingsHistoryResponse,
    )
    from models.earnings import EarningsHistoryEntry, EarningsHistoryResponse
    from models.fundamentals import AnalystRating
    from services import analyst_ratings_extended, earnings_provider, provider_registry
    from services.yfinance_provider import _yahoo_symbol

    symbol = "MSFT"
    listing = _yahoo_symbol(symbol)

    async def _rating(sym: str) -> AnalystRating:
        return AnalystRating(symbol=sym, provider="yfinance", consensus="buy")

    async def _history(sym: str) -> RatingsHistoryResponse:
        return RatingsHistoryResponse(
            symbol=sym,
            history=[
                RatingsHistoryEntry(
                    symbol=sym,
                    date="2026-01-01",
                    firm="Example Capital",
                    rating_to="buy",
                    raw_rating="Buy",
                    provider="yfinance",
                )
            ],
        )

    async def _price_targets(sym: str) -> PriceTargetHistoryResponse:
        return PriceTargetHistoryResponse(
            symbol=sym,
            history=[
                PriceTargetEntry(
                    symbol=sym,
                    date="2026-01-01",
                    firm="Example Capital",
                    target_to=500.0,
                    provider="yfinance",
                )
            ],
        )

    async def _individual(sym: str) -> IndividualAnalystResponse:
        return IndividualAnalystResponse(
            symbol=sym,
            analysts=[
                IndividualAnalystForecast(
                    symbol=sym,
                    firm="Example Capital",
                    analyst_name="Jane Analyst",
                    current_rating="buy",
                    rating_issued_date="2026-01-01",
                    provider="yfinance",
                )
            ],
        )

    async def _earnings_history(sym: str) -> EarningsHistoryResponse:
        return EarningsHistoryResponse(
            symbol=sym,
            history=[EarningsHistoryEntry(period_end="2026-01-31", eps_actual=1.0)],
        )

    monkeypatch.setattr(provider_registry, "get_analyst_rating", _rating)
    monkeypatch.setattr(analyst_ratings_extended, "get_ratings_history", _history)
    monkeypatch.setattr(analyst_ratings_extended, "get_price_target_history", _price_targets)
    monkeypatch.setattr(analyst_ratings_extended, "get_individual_analysts", _individual)
    monkeypatch.setattr(earnings_provider, "get_history", _earnings_history)

    routes_and_keys = [
        ("/fundamentals/MSFT/ratings", f"fundamentals:{listing}:ratings"),
        ("/fundamentals/MSFT/ratings/history", f"ratings:{listing}:history"),
        (
            "/fundamentals/MSFT/ratings/price-target-history",
            f"ratings:{listing}:price-targets",
        ),
        ("/fundamentals/MSFT/ratings/individual", f"ratings:{listing}:individual"),
        ("/earnings/MSFT/history", f"earnings:{listing}:history"),
    ]
    for path, cache_key in routes_and_keys:
        asyncio.run(_seed_corrupt_entry(cache_key))
        resp = client.get(path)
        assert resp.status_code == 200, (path, resp.text)
        assert resp.json()["symbol"] == "MSFT", (path, resp.json())


async def _seed_corrupt_entry(cache_key: str) -> None:
    from services import data_cache

    # An empty dict is missing every model's required fields, so
    # ``model_validate`` raises regardless of which response shape reads it —
    # the ONE deserialise-or-refetch branch in ``routers._cached.cached``.
    await data_cache.set(cache_key, {})
