"""News provider — RSS feeds plus an optional NewsAPI key.

Two sources, both mapped to the shared :class:`NewsItem` model:

* **RSS** — region-keyed market feeds (the active region is read per-request via
  :func:`config.get_region`), plus a per-symbol Yahoo Finance feed when symbols
  are requested. Always available, no key needed. The market-feed set is keyed by
  region (Pass B / Pillar A — FR-060): US/GLOBAL use Yahoo Finance + MarketWatch;
  IN uses the verified-working India feeds per ``docs/redesign/PASS_B_RESEARCH.md``
  §A.2 — Economic Times Markets + ET Stocks
  (``economictimes.indiatimes.com/markets/rssfeeds/…``), LiveMint
  (``livemint.com/rss/news``), and the Zerodha Pulse aggregator
  (``pulse.zerodha.com``). (Moneycontrol dropped first-party RSS and Business
  Standard 403s on direct fetch, so neither is used.)
* **NewsAPI** (https://newsapi.org) — used only when a BYOK key is supplied.
  FR-036: the key rides the request from the OS keychain (the ``/news`` router
  reads it from a header and passes it as ``newsapi_key``); the ``NEWSAPI_KEY``
  env var is a last-resort dev fallback only. Absent both, the provider is
  RSS-only and never errors on that account. The key is never logged, echoed, or
  persisted beyond process memory.

Network I/O uses a *shared* ``httpx.AsyncClient`` (owned by ``app.state`` and
created/closed in the FastAPI lifespan). Connection pooling matters: on a cold
first fetch each source previously opened a brand-new sync connection, and a
cascade of slow TLS handshakes/timeouts could make *every* source fail before
the first response landed — yielding a 502 that a warm retry (reusing pooled
connections) then recovered from (#38). Sharing one pooled client + fetching all
sources concurrently fixes the cold-start cascade.

Failure handling is partial-success: every source is fetched concurrently and a
*single* source's failure is swallowed (with a bounded retry/backoff first) so
one dead feed never fails the whole request. A :class:`ProviderError` is raised
*only* when nothing at all was collected (every source returned empty/failed) —
not merely when "all attempted == all failed". Any collected item → HTTP 200.

Tests monkeypatch :func:`fetch_rss` and :func:`fetch_newsapi` directly — see
``sidecar/tests/test_news.py`` — so no test makes a live HTTP call.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
from datetime import UTC, datetime
from time import struct_time
from typing import Any

import feedparser
import httpx

from config import get_region
from models.news import NewsItem
from services.errors import ProviderError

logger = logging.getLogger(__name__)

PROVIDER_RSS = "rss"
PROVIDER_NEWSAPI = "newsapi"

# General market RSS feeds, keyed by region — used when no symbols are requested,
# and always folded in alongside any per-symbol feeds. The active region is read
# per-request via ``config.get_region`` (Pass B / Pillar A — FR-060). The IN feeds
# are the verified-working set from ``docs/redesign/PASS_B_RESEARCH.md`` §A.2;
# Moneycontrol (dropped first-party RSS) and Business Standard (403s) are
# deliberately excluded. GLOBAL reuses the US set.
_US_MARKET_RSS_FEEDS: tuple[tuple[str, str], ...] = (
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    (
        "MarketWatch",
        "http://feeds.marketwatch.com/marketwatch/topstories/",
    ),
)
_IN_MARKET_RSS_FEEDS: tuple[tuple[str, str], ...] = (
    (
        "Economic Times Markets",
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    ),
    (
        "ET Stocks",
        "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    ),
    ("LiveMint", "https://www.livemint.com/rss/news"),
    ("Zerodha Pulse", "https://pulse.zerodha.com/feed.php"),
)
_MARKET_RSS_FEEDS_BY_REGION: dict[str, tuple[tuple[str, str], ...]] = {
    "US": _US_MARKET_RSS_FEEDS,
    "IN": _IN_MARKET_RSS_FEEDS,
    "GLOBAL": _US_MARKET_RSS_FEEDS,
}

# Per-symbol Yahoo Finance RSS feed template. Yahoo serves ``.NS`` (NSE) per-symbol
# feeds, so it is kept for every region; only the ``region``/``lang`` params shift
# to the locale. For un-suffixed Indian symbols this is best-effort.
_SYMBOL_RSS_TEMPLATE = (
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region={region}&lang={lang}"
)
# Yahoo per-symbol feed region/lang params, keyed by Vysted region. GLOBAL reuses US.
_SYMBOL_FEED_LOCALE_BY_REGION: dict[str, tuple[str, str]] = {
    "US": ("US", "en-US"),
    "IN": ("IN", "en-IN"),
    "GLOBAL": ("US", "en-US"),
}


def _market_rss_feeds(region: str) -> tuple[tuple[str, str], ...]:
    """Return the market RSS feed set for ``region`` (US set as the fallback)."""
    return _MARKET_RSS_FEEDS_BY_REGION.get(region, _US_MARKET_RSS_FEEDS)


def _symbol_feed_locale(region: str) -> tuple[str, str]:
    """Return the Yahoo per-symbol ``(region, lang)`` params for ``region``."""
    return _SYMBOL_FEED_LOCALE_BY_REGION.get(region, ("US", "en-US"))


_NEWSAPI_URL = "https://newsapi.org/v2/everything"
_NEWSAPI_KEY_ENV = "NEWSAPI_KEY"

_HTTP_TIMEOUT = 10.0
# Per-source bounded retry: total attempts = 1 + _MAX_RETRIES. A short backoff
# rides out a transient first-fetch failure (DNS/TLS warm-up, flaky feed) without
# letting one dead source delay the concurrent batch for long.
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = 0.25
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


async def fetch_rss(
    client: httpx.AsyncClient, feed_url: str, *, fallback_source: str
) -> list[NewsItem]:
    """Fetch and map a single RSS feed to :class:`NewsItem` models.

    Uses the shared, pooled ``client`` so connections are reused across sources
    and requests. ``feedparser`` itself never raises on a bad feed — it sets
    ``bozo`` — but the underlying HTTP fetch can, so the request goes through
    ``httpx`` first and a failure here propagates to the caller, which decides
    whether to skip it.
    """
    response = await client.get(
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


async def fetch_newsapi(
    client: httpx.AsyncClient, query: str, *, limit: int, api_key: str
) -> list[NewsItem]:
    """Fetch and map NewsAPI ``/v2/everything`` results to :class:`NewsItem`."""
    response = await client.get(
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


def _newsapi_key(request_key: str | None = None) -> str | None:
    """Resolve the NewsAPI key, preferring the request-supplied BYOK key.

    FR-036: the key rides the request from the OS keychain (a header read by the
    ``/news`` router), never env/disk. ``request_key`` (from the keychain) takes
    precedence; the ``NEWSAPI_KEY`` env var is a last-resort dev fallback only.
    """
    if request_key and request_key.strip():
        return request_key.strip()
    key = os.environ.get(_NEWSAPI_KEY_ENV, "").strip()
    return key or None


def _feed_urls_for(symbols: list[str], region: str) -> list[tuple[str, str]]:
    """Build the (source-label, feed-url) list for a request in ``region``.

    The region-appropriate general market feeds are always included; a per-symbol
    Yahoo Finance feed (with locale-shaped ``region``/``lang`` params) is added for
    each requested symbol.
    """
    feeds = list(_market_rss_feeds(region))
    feed_region, feed_lang = _symbol_feed_locale(region)
    for symbol in symbols:
        feeds.append(
            (
                f"Yahoo Finance · {symbol}",
                _SYMBOL_RSS_TEMPLATE.format(symbol=symbol, region=feed_region, lang=feed_lang),
            )
        )
    return feeds


async def _fetch_rss_resilient(
    client: httpx.AsyncClient, feed_url: str, *, fallback_source: str
) -> list[NewsItem]:
    """Fetch one RSS feed with bounded retry/backoff; return ``[]`` on final failure.

    A transient cold-start failure (slow first TLS handshake, a momentarily
    unreachable feed) is retried a couple of times with a short backoff so it
    does not count against the request. A persistently-dead feed degrades to an
    empty list — never an exception — so one bad source never fails the batch.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return await fetch_rss(client, feed_url, fallback_source=fallback_source)
        except Exception as exc:  # noqa: BLE001 - one dead feed must not fail the request
            last_exc = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
    logger.warning("news: RSS source %s failed after retries: %s", fallback_source, last_exc)
    return []


async def _fetch_newsapi_resilient(
    client: httpx.AsyncClient, query: str, *, limit: int, api_key: str
) -> list[NewsItem]:
    """Fetch NewsAPI with bounded retry/backoff; return ``[]`` on final failure."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return await fetch_newsapi(client, query, limit=limit, api_key=api_key)
        except Exception as exc:  # noqa: BLE001 - NewsAPI down must not fail the request
            last_exc = exc
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
    logger.warning("news: NewsAPI source failed after retries: %s", last_exc)
    return []


async def fetch_news(
    client: httpx.AsyncClient,
    symbols: list[str],
    limit: int,
    *,
    newsapi_key: str | None = None,
) -> list[NewsItem]:
    """Fetch news from every configured source, de-duplicated and newest-first.

    ``symbols`` may be empty — in that case only the general market feeds are
    used. All sources are fetched **concurrently** over the shared pooled
    ``client``. Per-source failures are swallowed (partial success). A
    :class:`ProviderError` is raised *only* when nothing at all was collected
    (every source returned empty or failed) so the router can surface a clean
    502; any collected item yields a normal 200.

    ``newsapi_key`` is the BYOK NewsAPI key the ``/news`` router reads from a
    request header (sourced from the OS keychain — FR-036). It takes precedence
    over the ``NEWSAPI_KEY`` env var; absent both, the fetch is RSS-only.

    The active region is read here (not passed by the router) via
    :func:`config.get_region` so the market feeds + per-symbol locale are
    region-appropriate (Pass B / Pillar A — FR-060) without changing the router
    contract. The default ``"US"`` keeps every existing caller unchanged.
    """
    region = get_region()
    tasks: list[asyncio.Future[list[NewsItem]]] = [
        asyncio.ensure_future(_fetch_rss_resilient(client, feed_url, fallback_source=source_label))
        for source_label, feed_url in _feed_urls_for(symbols, region)
    ]

    api_key = _newsapi_key(newsapi_key)
    if api_key is not None:
        query = " OR ".join(symbols) if symbols else "stock market OR finance"
        tasks.append(
            asyncio.ensure_future(
                _fetch_newsapi_resilient(client, query, limit=limit, api_key=api_key)
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    collected: list[NewsItem] = []
    for result in results:
        # The resilient helpers swallow their own errors, but guard against any
        # unexpected exception escaping so one source still cannot fail the batch.
        if isinstance(result, BaseException):
            logger.warning("news: source raised unexpectedly: %s", result)
            continue
        collected.extend(result)

    if not collected:
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
