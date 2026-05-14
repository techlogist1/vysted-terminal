"""News provider — RSS feeds plus an optional NewsAPI key.

Two sources, both mapped to the shared :class:`NewsItem` model:

* **RSS** — Yahoo Finance and MarketWatch market feeds, plus a per-symbol Yahoo
  Finance feed when symbols are requested. Always available, no key needed.
* **NewsAPI** (https://newsapi.org) — used only when a ``NEWSAPI_KEY`` env var
  is set. BYOK, per the project's local-first / bring-your-own-keys positioning;
  absent the key the provider is RSS-only and never errors on that account.

Network I/O uses ``httpx`` (sync client — FastAPI runs the sync router on a
worker thread, matching the yfinance/ccxt providers). Any upstream failure for a
*single* source is swallowed and logged-as-skipped so one dead feed never fails
the whole request; only a total wipeout (every source failed) raises
:class:`ProviderError`.

Tests monkeypatch :func:`fetch_rss` and :func:`fetch_newsapi` directly — see
``sidecar/tests/test_news.py`` — so no test makes a live HTTP call.
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import UTC, datetime
from time import struct_time
from typing import Any

import feedparser
import httpx

from models.news import NewsItem
from services.errors import ProviderError

PROVIDER_RSS = "rss"
PROVIDER_NEWSAPI = "newsapi"

# General market RSS feeds — used when no symbols are requested, and always
# folded in alongside any per-symbol feeds.
_MARKET_RSS_FEEDS: tuple[tuple[str, str], ...] = (
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    (
        "MarketWatch",
        "http://feeds.marketwatch.com/marketwatch/topstories/",
    ),
)

# Per-symbol Yahoo Finance RSS feed template.
_SYMBOL_RSS_TEMPLATE = (
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
)

_NEWSAPI_URL = "https://newsapi.org/v2/everything"
_NEWSAPI_KEY_ENV = "NEWSAPI_KEY"

_HTTP_TIMEOUT = 10.0
# Strip HTML tags out of RSS summaries — feeds vary wildly in how much markup
# they embed and the sentiment scorer wants plain text.
_TAG_RE = re.compile(r"<[^>]+>")


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _stable_id(url: str, title: str) -> str:
    """Derive a stable, deterministic id for a news item from its url+title."""
    digest = hashlib.sha1(f"{url}\n{title}".encode(), usedforsecurity=False)
    return digest.hexdigest()[:16]


def _clean(text: str | None) -> str | None:
    """Strip HTML tags and collapse whitespace; return ``None`` if empty."""
    if not text:
        return None
    stripped = _TAG_RE.sub(" ", text)
    collapsed = " ".join(stripped.split())
    return collapsed or None


def _parse_struct_time(value: struct_time | None) -> datetime:
    """Convert a feedparser ``struct_time`` to a UTC datetime; fall back to now."""
    if value is None:
        return _utcnow()
    try:
        return datetime(*value[:6], tzinfo=UTC)
    except (TypeError, ValueError):
        return _utcnow()


def _parse_iso(value: str | None) -> datetime:
    """Parse an ISO-8601 timestamp (NewsAPI's format); fall back to now."""
    if not value:
        return _utcnow()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return _utcnow()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def fetch_rss(feed_url: str, *, fallback_source: str) -> list[NewsItem]:
    """Fetch and map a single RSS feed to :class:`NewsItem` models.

    ``feedparser`` itself never raises on a bad feed — it sets ``bozo`` — but the
    underlying HTTP fetch can, so the request goes through ``httpx`` first and a
    failure here propagates to the caller, which decides whether to skip it.
    """
    response = httpx.get(
        feed_url,
        timeout=_HTTP_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "VystedTerminal/1.0 (+news)"},
    )
    response.raise_for_status()
    parsed = feedparser.parse(response.content)

    items: list[NewsItem] = []
    for entry in parsed.entries:
        title = _clean(entry.get("title"))
        url = entry.get("link")
        if not title or not url:
            continue
        summary = _clean(entry.get("summary") or entry.get("description"))
        source = (
            (entry.get("source") or {}).get("title") or parsed.feed.get("title") or fallback_source
        )
        published = _parse_struct_time(entry.get("published_parsed") or entry.get("updated_parsed"))
        items.append(
            NewsItem(
                id=_stable_id(url, title),
                title=title,
                summary=summary,
                url=url,
                source=str(source),
                published_at=published,
                symbols=[],
                provider=PROVIDER_RSS,
            )
        )
    return items


def fetch_newsapi(query: str, *, limit: int, api_key: str) -> list[NewsItem]:
    """Fetch and map NewsAPI ``/v2/everything`` results to :class:`NewsItem`."""
    response = httpx.get(
        _NEWSAPI_URL,
        timeout=_HTTP_TIMEOUT,
        params={
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(max(limit, 1), 100),
        },
        headers={"X-Api-Key": api_key},
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()

    items: list[NewsItem] = []
    for article in payload.get("articles", []):
        title = _clean(article.get("title"))
        url = article.get("url")
        if not title or not url:
            continue
        summary = _clean(article.get("description") or article.get("content"))
        source = (article.get("source") or {}).get("name") or "NewsAPI"
        published = _parse_iso(article.get("publishedAt"))
        items.append(
            NewsItem(
                id=_stable_id(url, title),
                title=title,
                summary=summary,
                url=url,
                source=str(source),
                published_at=published,
                symbols=[],
                provider=PROVIDER_NEWSAPI,
            )
        )
    return items


def _newsapi_key() -> str | None:
    """Return the configured NewsAPI key, or ``None`` if BYOK was not provided."""
    key = os.environ.get(_NEWSAPI_KEY_ENV, "").strip()
    return key or None


def _feed_urls_for(symbols: list[str]) -> list[tuple[str, str]]:
    """Build the (source-label, feed-url) list for a request.

    General market feeds are always included; a per-symbol Yahoo Finance feed is
    added for each requested symbol.
    """
    feeds = list(_MARKET_RSS_FEEDS)
    for symbol in symbols:
        feeds.append(
            (
                f"Yahoo Finance · {symbol}",
                _SYMBOL_RSS_TEMPLATE.format(symbol=symbol),
            )
        )
    return feeds


def fetch_news(symbols: list[str], limit: int) -> list[NewsItem]:
    """Fetch news from every configured source, de-duplicated and newest-first.

    ``symbols`` may be empty — in that case only the general market feeds are
    used. Per-source failures are swallowed; if *every* source fails a
    :class:`ProviderError` is raised so the router can surface a clean 502.
    """
    collected: list[NewsItem] = []
    attempted = 0
    failed = 0

    for source_label, feed_url in _feed_urls_for(symbols):
        attempted += 1
        try:
            collected.extend(fetch_rss(feed_url, fallback_source=source_label))
        except Exception:  # noqa: BLE001 - one dead feed must not fail the request
            failed += 1

    api_key = _newsapi_key()
    if api_key is not None:
        attempted += 1
        query = " OR ".join(symbols) if symbols else "stock market OR finance"
        try:
            collected.extend(fetch_newsapi(query, limit=limit, api_key=api_key))
        except Exception:  # noqa: BLE001 - NewsAPI down must not fail the request
            failed += 1

    if attempted > 0 and failed == attempted:
        raise ProviderError("all news sources failed")

    # De-duplicate on the stable id (the same story shows up across feeds).
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in collected:
        if item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)

    unique.sort(key=lambda item: item.published_at, reverse=True)
    return unique
