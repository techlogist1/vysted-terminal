"""Quotes router — latest price quotes, single and batch.

The batch endpoint backs the watchlist panel: a symbol that fails to resolve is
skipped rather than failing the whole request.

The batch endpoint is ``async`` and fans the per-symbol provider calls out
concurrently via ``asyncio.to_thread`` + ``asyncio.gather``. The underlying
``provider_registry.get_quote`` is a blocking call (yfinance ``fast_info`` /
ccxt ``fetch_ticker``), so running them sequentially on the request thread
serialised the whole batch (~26s for 55 symbols) and tied up the uvicorn worker
pool, starving other routes. Fanning out to threads makes the batch latency the
slowest single symbol, not the sum. Mirrors the established pattern in
``services/agent_tools/price_data.py`` + ``services/bar_loader.py``.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query

import config
from models.market import Quote
from services import provider_registry
from services.locale import freshness_for

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _label_freshness(quote: Quote, asset_class: str) -> Quote:
    """Stamp the calendar-aware staleness label on a quote (FR-041 / SC-019).

    A quote already passed the provider correctness gate, so it is never
    fabricated; this adds the live/eod/stale label the UI badges so a legitimate
    weekend/holiday close is not mistaken for a live tick and a genuinely stale
    value is shown as stale, never as live. Crypto trades 24/7, so a fresh fetch
    is always ``live``; equity/ETF freshness is read against the locale's trading
    calendar (region from the per-request ContextVar set by the middleware).
    """
    if asset_class == "crypto":
        quote.freshness = "live"
        return quote
    try:
        quote.freshness = freshness_for(
            config.get_region(), quote.timestamp.date(), intraday=True
        ).state
    except Exception:  # noqa: BLE001 — a label failure must never drop the quote
        quote.freshness = None
    return quote


@router.get("/{symbol}")
async def get_quote(symbol: str, asset_class: str = "equity") -> Quote:
    """Return the latest quote for one symbol.

    The blocking provider call runs on a worker thread so a single-symbol
    request never blocks the event loop. A ``ProviderError`` propagates to the
    app-level handler and surfaces as a clean 502 (unchanged behaviour).
    """
    quote = await asyncio.to_thread(provider_registry.get_quote, symbol, asset_class)
    return _label_freshness(quote, asset_class)


@router.get("")
async def get_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    asset_class: str = "equity",
) -> list[Quote]:
    """Return latest quotes for a batch of symbols; failures are skipped.

    Each symbol's blocking provider lookup runs on its own worker thread and all
    of them are awaited concurrently. A single symbol's failure (any exception,
    e.g. ``ProviderError``) is skipped, not fatal — matching the prior
    sequential skip-on-failure semantics — so one bad symbol never aborts the
    batch. ``return_exceptions=True`` keeps ``gather`` from short-circuiting on
    the first failure; non-``Quote`` results (exceptions) are filtered out.
    """
    parsed = [s.strip() for s in symbols.split(",")]
    tasks = [
        asyncio.to_thread(provider_registry.get_quote, symbol, asset_class)
        for symbol in parsed
        if symbol
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [
        _label_freshness(result, asset_class) for result in results if isinstance(result, Quote)
    ]
