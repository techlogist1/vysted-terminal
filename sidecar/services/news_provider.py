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
from services import sentiment, symbol_resolver
from services.errors import ProviderError
from services.locale import strip_exchange_suffix
from services.yfinance_provider import _yahoo_symbol

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
# to the locale. The symbol is resolved with ``_yahoo_symbol`` first, so a bare
# NSE ticker in an IN session hits its ``.NS`` feed, not a US namesake.
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


def _parse_struct_time(value: struct_time | None) -> datetime | None:
    """Convert a feedparser ``struct_time`` to a UTC datetime.

    ``None`` when the entry carried no date or a malformed one: an undated item
    is never stamped now() (which would sort it above genuinely recent stories).
    """
    if value is None:
        return None
    try:
        return datetime(*value[:6], tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp (NewsAPI's format); ``None`` when absent or
    malformed, never now()."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
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


def _feed_urls_for(symbols: list[str], region: str) -> list[tuple[str, str, str | None]]:
    """Build the (source-label, feed-url, feed-symbol) list for a request in ``region``.

    The region-appropriate general market feeds are always included (feed-symbol
    ``None``); a per-symbol Yahoo Finance feed (with locale-shaped
    ``region``/``lang`` params) is added for each requested symbol, carrying
    that symbol so its items are tagged to it by provenance.
    """
    feeds: list[tuple[str, str, str | None]] = [
        (label, url, None) for label, url in _market_rss_feeds(region)
    ]
    feed_region, feed_lang = _symbol_feed_locale(region)
    for symbol in symbols:
        feeds.append(
            (
                f"Yahoo Finance · {symbol}",
                _SYMBOL_RSS_TEMPLATE.format(
                    symbol=_yahoo_symbol(symbol), region=feed_region, lang=feed_lang
                ),
                symbol,
            )
        )
    return feeds


async def _fetch_feed(
    client: httpx.AsyncClient, feed_url: str, *, fallback_source: str, symbol: str | None
) -> list[NewsItem]:
    """Fetch one RSS feed; a symbol's own feed tags its items to that symbol."""
    items = await _fetch_rss_resilient(client, feed_url, fallback_source=fallback_source)
    if symbol is None:
        return items
    return [item.model_copy(update={"symbols": [symbol]}) for item in items]


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


async def _fetch_newsapi_status(
    client: httpx.AsyncClient, query: str, *, limit: int, api_key: str
) -> tuple[list[NewsItem], str]:
    """Fetch NewsAPI with bounded retry/backoff; return ``(items, status)``.

    ``status`` is one of ``"ok"``, ``"unauthorized"`` (a 401 — the key itself is
    bad, so retrying is pointless and the loop stops at once) or ``"error"``
    (anything else, still retried). R15-DATA-094: a bad key used to be silently
    swallowed into an empty list indistinguishable from "no news right now" —
    the caller needs to know *why* NewsAPI produced nothing.
    """
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return await fetch_newsapi(client, query, limit=limit, api_key=api_key), "ok"
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                logger.warning("news: NewsAPI key rejected (401)")
                return [], "unauthorized"
            last_exc = exc
        except Exception as exc:  # noqa: BLE001 - NewsAPI down must not fail the request
            last_exc = exc
        if attempt < _MAX_RETRIES:
            await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
    logger.warning("news: NewsAPI source failed after retries: %s", last_exc)
    return [], "error"


async def probe_newsapi_key(client: httpx.AsyncClient, api_key: str) -> str:
    """Single, no-retry probe of whether ``api_key`` is a valid NewsAPI key.

    Used by ``GET /news/sources/status`` (R15-DATA-094) — a bad key should fail
    fast, not pay the ``_fetch_newsapi_status`` retry backoff. Returns ``"ok"``,
    ``"unauthorized"`` (401) or ``"error"`` for any other failure.
    """
    try:
        await fetch_newsapi(client, "stock market", limit=1, api_key=api_key)
        return "ok"
    except httpx.HTTPStatusError as exc:
        return "unauthorized" if exc.response.status_code == 401 else "error"
    except Exception:  # noqa: BLE001 - a probe failure is reported, never raised
        return "error"


async def fetch_news(
    client: httpx.AsyncClient,
    symbols: list[str],
    limit: int,
    *,
    newsapi_key: str | None = None,
    source_status: dict[str, str] | None = None,
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

    ``source_status``, when given, is filled in-place with
    ``{"newsapi": "ok"|"unauthorized"|"error"|"absent"}`` (R15-DATA-094) so a
    caller (the ``/news`` route's ``X-News-Sources`` header) can report *why*
    NewsAPI contributed nothing instead of that being indistinguishable from
    "no fresh articles right now".

    The active region is read here (not passed by the router) via
    :func:`config.get_region` so the market feeds + per-symbol locale are
    region-appropriate (Pass B / Pillar A — FR-060) without changing the router
    contract. The default ``"US"`` keeps every existing caller unchanged.
    """
    region = get_region()
    tasks: list[asyncio.Future[list[NewsItem]]] = [
        asyncio.ensure_future(
            _fetch_feed(client, feed_url, fallback_source=source_label, symbol=feed_symbol)
        )
        for source_label, feed_url, feed_symbol in _feed_urls_for(symbols, region)
    ]

    api_key = _newsapi_key(newsapi_key)
    newsapi_task_index: int | None = None
    if api_key is not None:
        query = " OR ".join(symbols) if symbols else "stock market OR finance"
        newsapi_task_index = len(tasks)
        tasks.append(
            asyncio.ensure_future(
                _fetch_newsapi_status(client, query, limit=limit, api_key=api_key)
            )
        )
    elif source_status is not None:
        source_status["newsapi"] = "absent"

    results = await asyncio.gather(*tasks, return_exceptions=True)

    collected: list[NewsItem] = []
    for index, result in enumerate(results):
        # The resilient helpers swallow their own errors, but guard against any
        # unexpected exception escaping so one source still cannot fail the batch.
        if isinstance(result, BaseException):
            logger.warning("news: source raised unexpectedly: %s", result)
            if index == newsapi_task_index and source_status is not None:
                source_status["newsapi"] = "error"
            continue
        if index == newsapi_task_index:
            items, status = result
            if source_status is not None:
                source_status["newsapi"] = status
            collected.extend(items)
            continue
        collected.extend(result)

    if not collected:
        raise ProviderError("all news sources failed")

    # De-duplicate on the stable id (the same story shows up across feeds),
    # keeping every feed's provenance symbol on the surviving copy.
    by_id: dict[str, NewsItem] = {}
    for item in collected:
        kept = by_id.get(item.id)
        if kept is None:
            by_id[item.id] = item
        elif item.symbols:
            merged = kept.symbols + [s for s in item.symbols if s not in kept.symbols]
            by_id[item.id] = kept.model_copy(update={"symbols": merged})
    unique = list(by_id.values())

    # Newest first; an undated item sorts last (its recency is unknown).
    dated = [item for item in unique if item.published_at is not None]
    dated.sort(key=lambda item: item.published_at, reverse=True)
    return dated + [item for item in unique if item.published_at is None]


# ---------------------------------------------------------------------------
# Enrichment — sentiment scoring + symbol tagging (R15-AGENT-063)
#
# Moved here from ``routers/news.py`` so the agent-tool path (``news_tool``)
# gets the SAME scoring/tagging/filtering the HTTP route does, instead of
# returning raw unscored items. A symbol like ``BTC/USDT`` is normalised to
# its base (``BTC``) before alias matching — a headline says "BTC", never the
# literal pair — while the tag on the returned item still carries the symbol
# exactly as requested.
# ---------------------------------------------------------------------------


def _normalize_symbol_for_aliases(symbol: str) -> str:
    """Strip a crypto pair's quote leg or an NSE/BSE exchange suffix down to
    the bare base a headline would actually mention (``BTC/USDT`` → ``BTC``,
    ``RELIANCE.NS`` → ``RELIANCE``)."""
    upper = symbol.strip().upper()
    if "/" in upper:
        upper = upper.split("/", 1)[0]
    return strip_exchange_suffix(upper)


#: Base -> display name for the ``crypto_top50.json`` universe (R15-AGENT-063):
#: the symbol master carries no names, and a headline says "Bitcoin", never
#: the raw pair "BTC/USDT". Lower-case to match `_company_name`'s convention.
_CRYPTO_NAMES: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "bnb",
    "SOL": "solana",
    "XRP": "xrp",
    "USDC": "usd coin",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche",
    "TRX": "tron",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "polygon",
    "TON": "toncoin",
    "SHIB": "shiba inu",
    "LTC": "litecoin",
    "BCH": "bitcoin cash",
    "ATOM": "cosmos",
    "ICP": "internet computer",
    "UNI": "uniswap",
    "ETC": "ethereum classic",
    "XLM": "stellar",
    "FIL": "filecoin",
    "APT": "aptos",
    "ARB": "arbitrum",
    "NEAR": "near protocol",
    "OP": "optimism",
    "HBAR": "hedera",
    "VET": "vechain",
    "AAVE": "aave",
    "ALGO": "algorand",
    "EOS": "eos",
    "GRT": "the graph",
    "INJ": "injective",
    "RUNE": "thorchain",
    "SUI": "sui",
    "FTM": "fantom",
    "STX": "stacks",
    "IMX": "immutable",
    "RNDR": "render",
    "SAND": "the sandbox",
    "MANA": "decentraland",
    "AXS": "axie infinity",
    "FLOW": "flow",
    "EGLD": "multiversx",
    "THETA": "theta network",
    "XTZ": "tezos",
    "CHZ": "chiliz",
    "KAVA": "kava",
    "CAKE": "pancakeswap",
}


def _company_name(symbol: str) -> str | None:
    """The listing's company name without its corporate suffix, lower-case.

    The listing is the region-aware Yahoo form (``_yahoo_symbol``), so bare BDL
    in an IN session is Bharat Dynamics, not Flanigan's. A crypto pair
    (``BTC/USDT``) resolves against `_CRYPTO_NAMES` instead — it has no
    equity listing to look up.
    """
    if "/" in symbol:
        return _CRYPTO_NAMES.get(symbol.strip().upper().split("/", 1)[0])
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
    """Text forms that mean ``symbol``: the ticker as requested, its bare
    exchange/pair-stripped base (2+ characters only, so ``A`` never matches
    the article "a"), and the company name (the only text alias a one-letter
    ticker gets)."""
    tickers = dict.fromkeys(
        [symbol, strip_exchange_suffix(symbol), _normalize_symbol_for_aliases(symbol)]
    )
    aliases = [t for t in tickers if len(t) >= 2]
    name = _company_name(symbol)
    if name:
        aliases.append(name)
    return aliases


def build_aliases(symbols: list[str]) -> dict[str, list[str]]:
    """Build the ``{symbol: [alias, ...]}`` map :func:`enrich` tags against."""
    return {symbol: _aliases(symbol) for symbol in symbols}


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


def enrich(
    items: list[NewsItem], symbols: list[str], aliases: dict[str, list[str]]
) -> list[NewsItem]:
    """Score every item's sentiment and tag it against ``aliases``.

    ``aliases`` is typically :func:`build_aliases` output. When ``symbols`` is
    non-empty (an explicit request), untagged items are dropped — the
    requested-symbol relevance filter both the ``/news`` route and the
    ``news`` agent tool need identically.
    """
    enriched: list[NewsItem] = []
    for item in items:
        result = sentiment.score_text(f"{item.title}. {item.summary or ''}")
        tagged = _tag_symbols(item, aliases)
        if symbols and not tagged:
            continue
        enriched.append(
            item.model_copy(
                update={
                    "symbols": tagged,
                    "sentiment": round(result.score, 4),
                    "sentiment_label": result.label,
                }
            )
        )
    return enriched
