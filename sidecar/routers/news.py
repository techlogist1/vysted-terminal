"""News router — RSS + optional NewsAPI fetch with lexicon sentiment scoring.

``GET /news`` fetches news from the provider layer (general market RSS feeds,
per-symbol Yahoo Finance feeds, and NewsAPI when a ``NEWSAPI_KEY`` is set),
scores every item with the VADER lexicon sentiment service, tags each item with
any requested watchlist symbols it mentions, and returns the newest ``limit``
items.

Sentiment is lexicon-based on purpose — a Tier-3 decision recorded in
``services/sentiment.py``: a model-based scorer (FinBERT/torch) cannot be safely
vetted inside the PyInstaller ``--onefile`` bundle, whereas VADER is a pure
-Python wheel. The tradeoff is coarser, social-media-tuned scores.

``app.create_app`` already mounts this router — only this file is edited.
"""

from __future__ import annotations

import re
from typing import Annotated

import httpx
from fastapi import APIRouter, Header, Query, Request

from models.news import NewsItem
from services import news_provider, sentiment, symbol_resolver
from services.locale import strip_exchange_suffix
from services.yfinance_provider import _yahoo_symbol

router = APIRouter(prefix="/news", tags=["news"])

# FR-036: the BYOK NewsAPI key rides the request from the OS keychain as a
# HEADER (never the body/query, mirroring the read-only-plugin credential
# pattern). It is passed straight to the provider and never logged, echoed, or
# persisted. Absent the header, the provider falls back to the NEWSAPI_KEY env
# var (dev only) or RSS-only.
NewsApiKeyHeader = Annotated[
    str | None,
    Header(alias="X-Vysted-Newsapi-Key", description="BYOK NewsAPI key from the OS keychain."),
]

# Default Phase 1 watchlist used when the caller passes no ``symbols``. The real
# watchlist store is owned by another module and is not crossed here.
_DEFAULT_SYMBOLS: tuple[str, ...] = ("SPY", "QQQ", "BTC", "ETH", "NVDA", "AAPL")

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _parse_symbols(symbols: str | None) -> list[str]:
    """Split a comma-separated ``symbols`` query param into clean upper-case codes."""
    if not symbols:
        return []
    seen: set[str] = set()
    parsed: list[str] = []
    for raw in symbols.split(","):
        symbol = raw.strip().upper()
        if symbol and symbol not in seen:
            seen.add(symbol)
            parsed.append(symbol)
    return parsed


def _company_name(symbol: str) -> str | None:
    """The listing's company name without its corporate suffix, lower-case.

    The listing is the region-aware Yahoo form (``_yahoo_symbol``), so bare BDL
    in an IN session is Bharat Dynamics, not Flanigan's.
    """
    listing = _yahoo_symbol(symbol)
    bare = strip_exchange_suffix(listing)
    if listing.endswith(".NS"):
        row = symbol_resolver._nse_master().get(bare)
    elif listing.endswith(".BO"):
        row = symbol_resolver._bse_master().get(bare)
    else:
        row = symbol_resolver._us_master().get(listing)
    name = row[0] if isinstance(row, tuple) else row
    return symbol_resolver._strip_corporate_suffix(name.lower()) if name else None


def _aliases(symbol: str) -> list[str]:
    """Text forms that mean ``symbol``: the ticker as requested and bare (2+
    characters only, so ``A`` never matches the article "a") and the company
    name (the only text alias a one-letter ticker gets)."""
    tickers = dict.fromkeys([symbol, strip_exchange_suffix(symbol)])
    aliases = [t for t in tickers if len(t) >= 2]
    name = _company_name(symbol)
    if name:
        aliases.append(name)
    return aliases


def _tag_symbols(item: NewsItem, aliases: dict[str, list[str]]) -> list[str]:
    """Return the symbols (keys of ``aliases``) the item is about.

    An item from a symbol's own per-symbol feed is tagged by provenance
    (``item.symbols``, set by the provider); otherwise any alias of the symbol
    (:func:`_aliases`) must appear word-boundary-anchored in the title or
    summary, so ``ETH`` does not match ``ethics``.
    """
    haystack = f"{item.title} {item.summary or ''}"
    matched: list[str] = []
    for symbol, forms in aliases.items():
        if symbol in item.symbols or any(
            re.search(rf"\b{re.escape(alias)}\b", haystack, flags=re.IGNORECASE) for alias in forms
        ):
            matched.append(symbol)
    return matched


def _httpx_client(request: Request) -> httpx.AsyncClient:
    """Return the shared pooled ``httpx.AsyncClient`` created in the lifespan."""
    return request.app.state.httpx_client


@router.get("")
async def get_news(
    request: Request,
    symbols: str | None = Query(
        default=None,
        description="Comma-separated watchlist symbols to tag/filter by",
    ),
    limit: int = Query(
        default=_DEFAULT_LIMIT,
        ge=1,
        le=_MAX_LIMIT,
        description="Maximum number of news items to return",
    ),
    newsapi_key: NewsApiKeyHeader = None,
) -> list[NewsItem]:
    """Return scored, symbol-tagged news, newest first.

    With no ``symbols`` the default Phase 1 watchlist is used for tagging and
    general market news is returned. With ``symbols`` given, every item is still
    fetched but the response is filtered to items that mention a requested
    symbol (general market context is dropped in favour of relevance).

    The shared pooled ``httpx.AsyncClient`` (created in the app lifespan) is
    handed to the provider so sources are fetched concurrently over reused
    connections — fixing the cold-first-fetch 502 cascade (#38).
    """
    requested = _parse_symbols(symbols)
    aliases = {symbol: _aliases(symbol) for symbol in requested or _DEFAULT_SYMBOLS}

    raw_items = await news_provider.fetch_news(
        _httpx_client(request), requested, limit, newsapi_key=newsapi_key
    )

    scored: list[NewsItem] = []
    for item in raw_items:
        result = sentiment.score_text(f"{item.title}. {item.summary or ''}")
        tagged = _tag_symbols(item, aliases)
        # Drop general items when the caller explicitly asked for symbols.
        if requested and not tagged:
            continue
        scored.append(
            item.model_copy(
                update={
                    "symbols": tagged,
                    "sentiment": round(result.score, 4),
                    "sentiment_label": result.label,
                }
            )
        )

    return scored[:limit]
