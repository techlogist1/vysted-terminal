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

import html
import re
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from .base import (
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
        headers = {"User-Agent": _USER_AGENT}
        try:
            if self._client is not None:
                response = await self._client.post(_ENDPOINT, data=data, headers=headers)
            else:
                async with httpx.AsyncClient(
                    timeout=_SEARCH_TIMEOUT_SECS, follow_redirects=True
                ) as http:
                    response = await http.post(_ENDPOINT, data=data, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SearchError(
                "keyless web search (DuckDuckGo) is unreachable — check your network, "
                "or add an Exa key / local SearXNG for a dedicated search route"
            ) from exc

        results = _parse(response.text, limit=limit)
        return SearchResponse(
            results=results,
            citations=normalize_results_to_citations(results, limit=limit),
            backend=BACKEND_ID,
            query=query,
        )


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
