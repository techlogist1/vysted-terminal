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

from typing import Annotated

import httpx
from fastapi import APIRouter, Header, Query, Request, Response

from models.news import NewsItem
from services import news_provider

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


def _httpx_client(request: Request) -> httpx.AsyncClient:
    """Return the shared pooled ``httpx.AsyncClient`` created in the lifespan."""
    return request.app.state.httpx_client


@router.get("")
async def get_news(
    request: Request,
    response: Response,
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

    R15-DATA-094: the response carries ``X-News-Sources: rss=ok;newsapi=<state>``
    (``ok``/``unauthorized``/``error``/``absent``) — RSS is keyless and always
    attempted, so it is reported ``ok`` whenever this handler returns at all;
    NewsAPI's state is whatever :func:`news_provider.fetch_news` observed on
    this request, so a rejected BYOK key is visible without a separate probe.
    """
    requested = _parse_symbols(symbols)
    aliases = news_provider.build_aliases(requested or list(_DEFAULT_SYMBOLS))

    source_status: dict[str, str] = {}
    raw_items = await news_provider.fetch_news(
        _httpx_client(request),
        requested,
        limit,
        newsapi_key=newsapi_key,
        source_status=source_status,
    )

    scored = news_provider.enrich(raw_items, requested, aliases)
    response.headers["X-News-Sources"] = f"rss=ok;newsapi={source_status.get('newsapi', 'absent')}"
    return scored[:limit]


@router.get("/sources/status")
async def get_news_sources_status(
    request: Request,
    newsapi_key: NewsApiKeyHeader = None,
) -> dict[str, str]:
    """Probe a BYOK NewsAPI key's validity without fetching a full feed.

    R15-DATA-094: used by the marketplace ``configure()`` flow to reject a bad
    NewsAPI key at save time ("NewsAPI rejected this key") instead of only
    discovering the 401 on the next ``/news`` fetch, and by NewsFeedPanel to
    badge an already-saved key that has gone bad. RSS needs no key and is not
    probed here. The key is read from the same header as ``/news`` and is never
    echoed in the response.
    """
    key = (newsapi_key or "").strip()
    if not key:
        return {"newsapi": "absent"}
    status = await news_provider.probe_newsapi_key(_httpx_client(request), key)
    return {"newsapi": status}
