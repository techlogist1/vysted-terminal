"""Mojeek HTML search engine adapter — keyless T1 rotation member (R7 Component 1).

Scrapes the Mojeek SERP at ``https://www.mojeek.com/search?q=`` into the
uniform ``{title, url, snippet}`` result shape. Mojeek runs its OWN index (not
a Google/Bing meta-layer), which makes it the most independent member of the
keyless rotation — when DDG and Brave are both throttling, Mojeek usually is
not. It is friendly to plain httpx with browser headers, so it rides the
httpx lane (no impersonation needed).

Parsing is bs4 with layered selectors (``ul.results-standard li`` first, then
looser fallbacks) so markup drift degrades to fewer fields, never a crash.
Zero parsed rows → empty successful response; transport failure / block →
typed :class:`~services.search.base.SearchError` for the rotation layer.
"""

from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import (
    SEARCH_REASON_RATE_LIMITED,
    SearchBackend,
    SearchError,
    SearchResponse,
    SearchResult,
    normalize_results_to_citations,
)
from .transport import TransportError, httpx_fetch

#: Identifier this engine reports in :class:`SearchResponse.backend`.
BACKEND_ID = "mojeek"

_ENDPOINT = "https://www.mojeek.com/search"

#: Mojeek throttle/block statuses — transient bench signals for the breaker.
_RATE_LIMIT_STATUSES = frozenset({403, 429})

#: Mojeek region bias (``arc`` param) by Vysted region.
_REGION_ARC = {"US": "us", "IN": "in"}

_DEFAULT_MAX = 8

_SKIP_HOSTS = ("mojeek.com",)


def _clean(text: str) -> str:
    return " ".join(text.split())


def _is_organic_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and not any(host == h or host.endswith("." + h) for h in _SKIP_HOSTS)


def _node_to_result(node) -> SearchResult | None:  # noqa: ANN001 — bs4 Tag
    anchor = node.select_one("a.title") or (node.h2.find("a", href=True) if node.h2 else None)
    if anchor is None:
        anchor = node.find("a", href=True)
    if anchor is None or not anchor.get("href"):
        return None
    url = anchor["href"].strip()
    if not _is_organic_url(url):
        return None
    snippet_node = node.select_one("p.s") or node.select_one(".s")
    title = _clean(anchor.get_text(" ", strip=True)) or url
    snippet = _clean(snippet_node.get_text(" ", strip=True)) if snippet_node else ""
    return SearchResult(url=url, title=title, snippet=snippet, source="mojeek")


def _parse(html_text: str, *, limit: int) -> list[SearchResult]:
    """Parse the Mojeek SERP into normalized results (layered selectors)."""
    soup = BeautifulSoup(html_text, "html.parser")
    containers = soup.select("ul.results-standard li")
    if not containers:
        containers = soup.select("ul.results li") or soup.select("li.result")
    out: list[SearchResult] = []
    seen: set[str] = set()
    for node in containers:
        result = _node_to_result(node)
        if result is None or result.url in seen:
            continue
        seen.add(result.url)
        out.append(result)
        if len(out) >= limit:
            break
    return out


class MojeekSearchBackend(SearchBackend):
    """Keyless Mojeek HTML scrape over the friendly httpx lane."""

    def __init__(self, *, region: str | None = None, fetch=None) -> None:  # noqa: ANN001
        self.region = region
        # Injectable fetch (same signature as httpx_fetch) for tests.
        self._fetch = fetch or httpx_fetch

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        opts = options or {}
        limit = _coerce_limit(opts) or _DEFAULT_MAX
        params: dict[str, str] = {"q": query}
        arc = _REGION_ARC.get((self.region or "").strip().upper())
        if arc:
            params["arc"] = arc

        try:
            fetched = await self._fetch(_ENDPOINT, params=params)
        except TransportError as exc:
            raise SearchError(f"Mojeek search is unreachable: {exc}") from exc

        if fetched.status_code in _RATE_LIMIT_STATUSES:
            raise SearchError(
                "Mojeek is blocking/rate-limiting right now "
                f"(HTTP {fetched.status_code}) — rotating to the next keyless engine",
                reason=SEARCH_REASON_RATE_LIMITED,
            )
        if fetched.status_code >= 400:
            raise SearchError(f"Mojeek search failed (HTTP {fetched.status_code})")

        results = _parse(fetched.text, limit=limit)
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


__all__ = ["BACKEND_ID", "MojeekSearchBackend"]
