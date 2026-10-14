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

Batch lookups run on their OWN bounded pool, never the event loop's default
executor: a 100-symbol portfolio batch used to occupy every default worker, so
a single ``/quotes/{symbol}`` (and every other ``to_thread`` route) queued
behind it for minutes (R15-FINAL-006). Batch members also take the NSE
throttle's bulk lane, so an interactive quote is paced ahead of them rather than
behind every slot the batch has reserved.
"""

from __future__ import annotations

import asyncio
import contextvars
import functools
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Query

from models.market import Quote
from services import nse_provider, provider_registry
from services.locale import REGION_FOREIGN, REGION_US, freshness_for, instrument_region

router = APIRouter(prefix="/quotes", tags=["quotes"])

# ponytail: one process-wide pool shared by every batch; per-caller pools if a
# second heavy batch client ever starves the watchlist.
_BATCH_POOL = ThreadPoolExecutor(max_workers=16, thread_name_prefix="quotes-batch")


def _batch_member_quote(symbol: str, asset_class: str) -> Quote:
    nse_provider.bulk_lane.set(True)  # scoped to this member's copied context
    return provider_registry.get_quote(symbol, asset_class)


def _on_batch_pool(symbol: str, asset_class: str) -> asyncio.Future[Quote]:
    """``asyncio.to_thread`` onto the batch pool: the copied context carries the
    request's region ContextVar into the worker, as ``to_thread`` does."""
    call = functools.partial(
        contextvars.copy_context().run, _batch_member_quote, symbol, asset_class
    )
    return asyncio.get_running_loop().run_in_executor(_BATCH_POOL, call)


def _label_freshness(quote: Quote, asset_class: str) -> Quote:
    """Stamp the calendar-aware staleness label on a quote (FR-041 / SC-019).

    A quote already passed the provider correctness gate, so it is never
    fabricated; this adds the live/eod/stale label the UI badges so a legitimate
    weekend/holiday close is not mistaken for a live tick and a genuinely stale
    value is shown as stale, never as live. Crypto trades 24/7, so a fresh fetch
    is always ``live``; equity/ETF freshness is read against the trading calendar
    of the instrument's own exchange, not the session region (R15-UI-090). A
    listing that is not positively US or IN (:data:`REGION_FOREIGN`) has no
    exchange-timezone table here, so it is dated against the US calendar with
    ``intraday=False`` — eod or stale, never live, even mid-session.
    """
    if asset_class == "crypto":
        quote.freshness = "live"
        return quote
    try:
        region = instrument_region(quote.symbol, quote.provider)
        is_foreign = region == REGION_FOREIGN
        calendar_region = REGION_US if is_foreign else region
        freshness = freshness_for(calendar_region, quote.timestamp.date(), intraday=not is_foreign)
        quote.freshness = freshness.state
    except Exception:  # noqa: BLE001 — a label failure must never drop the quote
        quote.freshness = "unknown"  # badged, never an unlabelled (live-looking) quote
    return quote


@router.get("/{symbol:path}")
async def get_quote(symbol: str, asset_class: str = "equity") -> Quote:
    """Return the latest quote for one symbol.

    ``:path`` so a crypto pair (``BTC/USDT``, sent as ``BTC%2FUSDT``) routes —
    Starlette decodes ``%2F`` before matching (R15-DATA-081). The blocking
    provider call runs on a worker thread so a single-symbol request never
    blocks the event loop. A ``ProviderError`` propagates to the app-level
    handler.
    """
    quote = await asyncio.to_thread(provider_registry.get_quote, symbol, asset_class)
    return _label_freshness(quote, asset_class)


@router.get("")
async def get_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    asset_class: str = "equity",
) -> list[Quote]:
    """Return latest quotes for a batch of symbols; failures are skipped.

    Each symbol's blocking provider lookup runs on the bounded batch pool and
    all of them are awaited concurrently. A single symbol's failure (any exception,
    e.g. ``ProviderError``) is skipped, not fatal — matching the prior
    sequential skip-on-failure semantics — so one bad symbol never aborts the
    batch. ``return_exceptions=True`` keeps ``gather`` from short-circuiting on
    the first failure; non-``Quote`` results (exceptions) are filtered out.

    Each quote's ``symbol`` is the REQUESTED spelling (C14): a lane may answer
    ``RELIANCE`` for ``RELIANCE.NS``, and the client joins on what it asked for;
    a requested symbol absent from the list is one that failed.
    """
    parsed = [s.strip() for s in symbols.split(",") if s.strip()]
    tasks = [_on_batch_pool(symbol, asset_class) for symbol in parsed]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    quotes: list[Quote] = []
    for requested, result in zip(parsed, results, strict=True):
        if isinstance(result, Quote):
            result.symbol = requested
            quotes.append(_label_freshness(result, asset_class))
    return quotes
