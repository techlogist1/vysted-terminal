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

from fastapi import APIRouter, Query

from models.news import NewsItem
from services import news_provider, sentiment

router = APIRouter(prefix="/news", tags=["news"])

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


def _tag_symbols(item: NewsItem, symbols: list[str]) -> list[str]:
    """Return the subset of ``symbols`` whose ticker appears in the item's text.

    Matching is word-boundary-anchored against the title and summary so ``A``
    does not match every word starting with ``a`` and ``ETH`` does not match
    ``ethics``.
    """
    haystack = f"{item.title} {item.summary or ''}"
    matched: list[str] = []
    for symbol in symbols:
        if re.search(rf"\b{re.escape(symbol)}\b", haystack, flags=re.IGNORECASE):
            matched.append(symbol)
    return matched


@router.get("")
def get_news(
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
) -> list[NewsItem]:
    """Return scored, symbol-tagged news, newest first.

    With no ``symbols`` the default Phase 1 watchlist is used for tagging and
    general market news is returned. With ``symbols`` given, every item is still
    fetched but the response is filtered to items that mention a requested
    symbol (general market context is dropped in favour of relevance).
    """
    requested = _parse_symbols(symbols)
    tag_symbols = requested or list(_DEFAULT_SYMBOLS)

    raw_items = news_provider.fetch_news(requested, limit)

    scored: list[NewsItem] = []
    for item in raw_items:
        result = sentiment.score_text(f"{item.title}. {item.summary or ''}")
        tagged = _tag_symbols(item, tag_symbols)
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
