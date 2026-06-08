"""DuckDuckGo keyless web search — the always-available search FLOOR (Track 1).

The BYOK (Exa) and local (SearXNG) tiers both need setup: an API key or a running
instance. On a FRESH install with neither, web search was dark — the research
engine's web round returned "no backend configured" and a keyless user got only
structured data. This backend closes that gap: a zero-key, zero-config metasearch
over DuckDuckGo's HTML endpoint, wired as the LAST fallback in
:mod:`services.agent_tools.web_search` so web search is never dark out of the box.

It is the FLOOR, not a tier: it only runs when no native / BYOK / SearXNG backend
is configured, so a user who set up a better route always gets that route. The
HTML is parsed with the standard library (``re`` + ``html`` + ``urllib.parse``) —
no new dependency, no PyInstaller bundle surprise. A transport failure raises
:class:`~services.search.base.SearchError` (the research loop then degrades to
structured-only — exactly today's behaviour, never worse); a markup change that
yields no parsed rows returns an empty (but successful) response.
"""

from __future__ import annotations

import asyncio
import html
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from .base import (
    SEARCH_REASON_RATE_LIMITED,
    SearchBackend,
    SearchError,
    SearchResponse,
    SearchResult,
    normalize_results_to_citations,
)

#: Identifier this backend reports in :class:`SearchResponse.backend`.
BACKEND_ID = "ddg"

#: The HTML results endpoint. POST is more reliable than GET (avoids some
#: rate-limit redirects) and the ``html.`` host returns server-rendered rows.
_ENDPOINT = "https://html.duckduckgo.com/html/"

#: The DDG Lite endpoint — a simpler, more stable results table. Used as a
#: fallback when the HTML endpoint parses ZERO rows (markup drift or a soft block)
#: so a transient HTML-side hiccup doesn't leave a keyless user with no web data.
_LITE_ENDPOINT = "https://lite.duckduckgo.com/lite/"

#: DDG soft-rate-limit statuses. ``html.duckduckgo.com`` answers an over-eager
#: client with 202 (an "anomaly" challenge page) rather than a 4xx; treat it (and
#: 429) as a RETRIABLE rate-limit so the loop surfaces an honest "try again"
#: instead of silently parsing a block page as "no results".
_RATE_LIMIT_STATUSES = frozenset({202, 429})

#: Bounded retry: a single re-attempt with a short backoff absorbs a transient
#: network blip / momentary rate-limit without turning a keyless search into a
#: long stall.
_MAX_ATTEMPTS = 2
_BACKOFF_SECS = 0.3

#: A desktop User-Agent — the bare httpx UA gets a thinner/blocked response.
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

#: DuckDuckGo region/locale codes (``kl`` param) by Vysted region.
_REGION_KL = {"US": "us-en", "IN": "in-en"}

_SEARCH_TIMEOUT_SECS = 12.0
_DEFAULT_MAX = 8

# One organic result block opens with this class; split on it then parse each.
_BLOCK_SPLIT = re.compile(r'<div class="result results_links')
_ANCHOR = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_SNIPPET = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>', re.S)
_URLLABEL = re.compile(r'class="result__url"[^>]*>(.*?)</a>', re.S)
_TAG = re.compile(r"<[^>]+>")

# DDG Lite markup: result links carry class="result-link" (attribute order
# varies, so match the whole anchor tag then pull href out); snippets are a
# following td.result-snippet, paired positionally (a missing snippet → "").
_LITE_ANCHOR = re.compile(r'<a\b([^>]*\bclass="[^"]*result-link[^"]*"[^>]*)>(.*?)</a>', re.S)
_LITE_HREF = re.compile(r'href="([^"]+)"')
_LITE_SNIPPET = re.compile(r'class="result-snippet"[^>]*>(.*?)</td>', re.S)


def _strip(fragment: str) -> str:
    """HTML fragment → plain text (drop tags, unescape entities, collapse space)."""
    return " ".join(html.unescape(_TAG.sub("", fragment)).split())


def _decode_href(href: str) -> str:
    """Resolve a DuckDuckGo result href to its real target.

    DDG sometimes wraps the link in a redirect (``//duckduckgo.com/l/?uddg=…``);
    unwrap it to the underlying URL so citations point at the real source.
    """
    href = html.unescape(href.strip())
    if href.startswith("//"):
        href = "https:" + href
    if "uddg=" in href:
        target = parse_qs(urlparse(href).query).get("uddg")
        if target:
            return unquote(target[0])
    return href


def _parse(text: str, *, limit: int) -> list[SearchResult]:
    """Map the DuckDuckGo HTML results page to normalized :class:`SearchResult`s.

    Returns an empty list (not an error) when nothing parses — an empty result
    set is a valid "found nothing", distinct from a transport failure.
    """
    out: list[SearchResult] = []
    for block in _BLOCK_SPLIT.split(text)[1:]:
        anchor = _ANCHOR.search(block)
        if not anchor:
            continue
        url = _decode_href(anchor.group(1))
        if not url.startswith("http"):
            continue
        snippet = _SNIPPET.search(block)
        label = _URLLABEL.search(block)
        out.append(
            SearchResult(
                url=url,
                title=_strip(anchor.group(2)) or url,
                snippet=_strip(snippet.group(1)) if snippet else "",
                source=_strip(label.group(1)) if label else "duckduckgo",
            )
        )
        if len(out) >= limit:
            break
    return out


def _parse_lite(text: str, *, limit: int) -> list[SearchResult]:
    """Map the DDG Lite results table to normalized :class:`SearchResult`s.

    Anchors (``result-link``) and snippets (``result-snippet``) are paired
    positionally; a missing snippet degrades to "". Returns an empty list (not an
    error) when nothing parses — same contract as :func:`_parse`.
    """
    snippets = _LITE_SNIPPET.findall(text)
    out: list[SearchResult] = []
    for index, match in enumerate(_LITE_ANCHOR.finditer(text)):
        attrs, title = match.group(1), match.group(2)
        href_match = _LITE_HREF.search(attrs)
        if not href_match:
            continue
        url = _decode_href(href_match.group(1))
        if not url.startswith("http"):
            continue
        out.append(
            SearchResult(
                url=url,
                title=_strip(title) or url,
                snippet=_strip(snippets[index]) if index < len(snippets) else "",
                source="duckduckgo",
            )
        )
        if len(out) >= limit:
            break
    return out


async def _fetch(http: httpx.AsyncClient, endpoint: str, data: dict[str, str]) -> str:
    """POST to a DDG endpoint with a bounded retry + honest rate-limit handling.

    Returns the response text. Raises :class:`SearchError` (unreachable OR
    rate-limited) only after the retry budget is spent — so a transient blip
    self-heals, while a persistent block surfaces a clear, human message instead
    of being silently parsed as "no results".
    """
    headers = {"User-Agent": _USER_AGENT}
    unreachable = (
        "keyless web search (DuckDuckGo) is unreachable — check your network, "
        "or add an Exa key / local SearXNG for a dedicated search route"
    )
    for attempt in range(_MAX_ATTEMPTS):
        last = attempt + 1 >= _MAX_ATTEMPTS
        try:
            resp = await http.post(endpoint, data=data, headers=headers)
        except httpx.HTTPError as exc:
            if last:
                raise SearchError(unreachable) from exc
            await asyncio.sleep(_BACKOFF_SECS)
            continue
        if resp.status_code in _RATE_LIMIT_STATUSES:
            if last:
                # TRANSIENT throttle (202 anomaly / 429), NOT a missing backend:
                # tag it so the brief surfaces "rate-limited, retrying" instead of
                # the false global "no web-search backend configured".
                raise SearchError(
                    "keyless web search (DuckDuckGo) is rate-limiting right now — wait a "
                    "moment and retry, or add an Exa key / local SearXNG for a dedicated route",
                    reason=SEARCH_REASON_RATE_LIMITED,
                )
            await asyncio.sleep(_BACKOFF_SECS)
            continue
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            if last:
                raise SearchError(unreachable) from exc
            await asyncio.sleep(_BACKOFF_SECS)
            continue
        return resp.text
    raise SearchError(unreachable)  # pragma: no cover — loop always returns/raises


class DdgSearchBackend(SearchBackend):
    """Keyless DuckDuckGo metasearch — the always-available search floor."""

    def __init__(
        self, *, region: str | None = None, client: httpx.AsyncClient | None = None
    ) -> None:
        self.region = region
        self._client = client

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        opts = options or {}
        limit = _coerce_limit(opts) or _DEFAULT_MAX
        data: dict[str, str] = {"q": query}
        kl = _REGION_KL.get((self.region or "").strip().upper())
        if kl:
            data["kl"] = kl

        if self._client is not None:
            results = await self._search_with(self._client, data, limit)
        else:
            async with httpx.AsyncClient(
                timeout=_SEARCH_TIMEOUT_SECS, follow_redirects=True
            ) as http:
                results = await self._search_with(http, data, limit)

        return SearchResponse(
            results=results,
            citations=normalize_results_to_citations(results, limit=limit),
            backend=BACKEND_ID,
            query=query,
        )

    async def _search_with(
        self, http: httpx.AsyncClient, data: dict[str, str], limit: int
    ) -> list[SearchResult]:
        """Query the HTML endpoint; on zero rows, fall back to DDG Lite."""
        results = _parse(await _fetch(http, _ENDPOINT, data), limit=limit)
        if results:
            return results
        # Zero rows from HTML (markup drift or a soft block) → try the simpler,
        # more stable Lite page. A Lite failure leaves the empty HTML result —
        # never worse than before this fallback existed.
        try:
            lite_text = await _fetch(http, _LITE_ENDPOINT, data)
        except SearchError:
            return results
        return _parse_lite(lite_text, limit=limit)


def _coerce_limit(opts: dict) -> int | None:
    """Read an optional ``maxResults``/``numResults`` cap from ``options``."""
    raw = opts.get("maxResults", opts.get("numResults"))
    if raw is None:
        return None
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        return None
    return limit if limit > 0 else None


__all__ = ["BACKEND_ID", "DdgSearchBackend"]
