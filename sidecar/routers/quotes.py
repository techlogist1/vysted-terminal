"""Quotes router — latest price quotes, single and batch.

The batch endpoint backs the watchlist panel: a symbol that fails to resolve is
skipped rather than failing the whole request.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from models.market import Quote
from services import provider_registry
from services.errors import ProviderError

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.get("/{symbol}")
def get_quote(symbol: str, asset_class: str = "equity") -> Quote:
    """Return the latest quote for one symbol."""
    return provider_registry.get_quote(symbol, asset_class)


@router.get("")
def get_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    asset_class: str = "equity",
) -> list[Quote]:
    """Return latest quotes for a batch of symbols; failures are skipped."""
    quotes: list[Quote] = []
    for symbol in (s.strip() for s in symbols.split(",")):
        if not symbol:
            continue
        try:
            quotes.append(provider_registry.get_quote(symbol, asset_class))
        except ProviderError:
            continue
    return quotes
