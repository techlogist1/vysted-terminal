"""Brave HTML search engine adapter — keyless T1 rotation member (R7 Component 1).

Scrapes the server-rendered Brave SERP at ``https://search.brave.com/search?q=``
into the uniform ``{title, url, snippet}`` result shape. No key, no setup —
but Brave fingerprint-blocks plain httpx TLS, so EVERY request rides the
curl_cffi Chrome-impersonation lane (:func:`services.search.transport
.impersonated_fetch`).

Parsing is bs4 with layered selectors: the precise current markup first
(``div.snippet[data-type="web"]``), then progressively looser heuristics so a
class-name drift degrades to "fewer fields" rather than zero rows. Zero parsed
rows is returned as an empty (successful) response — a valid "found nothing",
distinct from a transport failure or a block (which raise the typed
:class:`~services.search.base.SearchError` the rotation layer keys on).
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
from .transport import TransportError, impersonated_fetch

#: Identifier this engine reports in :class:`SearchResponse.backend`.
BACKEND_ID = "brave"

_ENDPOINT = "https://search.brave.com/search"

#: Statuses Brave answers a throttled/blocked scraper with. 429 is the honest
#: throttle; 403 is the fingerprint/CAPTCHA wall — both are TRANSIENT bench
#: signals for the breaker, not a missing backend.
_RATE_LIMIT_STATUSES = frozenset({403, 429})

#: Brave SERP country codes by Vysted region (best-effort locale bias).
_REGION_COUNTRY = {"US": "us", "IN": "in"}

_DEFAULT_MAX = 8

#: Hosts that are Brave chrome, not organic results (ad/redirect/self links).
_SKIP_HOSTS = ("search.brave.com", "brave.com")


def _clean(text: str) -> str:
    """Collapse whitespace in an extracted text fragment."""
    return " ".join(text.split())


def _is_organic_url(url: str) -> bool:
    if not url.startswith(("http://", "https://")):
        return False
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and not any(host == h or host.endswith("." + h) for h in _SKIP_HOSTS)


def _node_to_result(node) -> SearchResult | None:  # noqa: ANN001 — bs4 Tag
    """Map one result container to a :class:`SearchResult` (or None)."""
    anchor = node.find("a", href=True)
    if anchor is None:
        return None
    url = anchor["href"].strip()
    if not _is_organic_url(url):
        return None
    title_node = node.select_one(".title") or anchor
    desc_node = node.select_one(".snippet-description") or node.select_one(".snippet-content")
    title = _clean(title_node.get_text(" ", strip=True)) or url
    snippet = _clean(desc_node.get_text(" ", strip=True)) if desc_node else ""
    return SearchResult(url=url, title=title, snippet=snippet, source="brave")


def _parse(html_text: str, *, limit: int) -> list[SearchResult]:
    """Parse the Brave SERP HTML into normalized results (layered selectors).

    Empty list when nothing parses — a valid "found nothing", never an error.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    containers = soup.select('div.snippet[data-type="web"]')
    if not containers:
        containers = soup.select("#results .snippet") or soup.select("div.snippet")
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


class BraveSearchBackend(SearchBackend):
    """Keyless Brave HTML scrape over the Chrome-impersonation transport."""

    def __init__(self, *, region: str | None = None, fetch=None) -> None:  # noqa: ANN001
        self.region = region
        # Injectable fetch (same signature as impersonated_fetch) for tests.
        self._fetch = fetch or impersonated_fetch

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        opts = options or {}
        limit = _coerce_limit(opts) or _DEFAULT_MAX
        params: dict[str, str] = {"q": query, "source": "web"}
        country = _REGION_COUNTRY.get((self.region or "").strip().upper())
        if country:
            params["country"] = country

        try:
            fetched = await self._fetch(_ENDPOINT, params=params)
        except TransportError as exc:
            raise SearchError(f"Brave HTML search is unreachable: {exc}") from exc

        if fetched.status_code in _RATE_LIMIT_STATUSES:
            raise SearchError(
                "Brave HTML search is blocking/rate-limiting right now "
                f"(HTTP {fetched.status_code}) — rotating to the next keyless engine",
                reason=SEARCH_REASON_RATE_LIMITED,
            )
        if fetched.status_code >= 400:
            raise SearchError(f"Brave HTML search failed (HTTP {fetched.status_code})")

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


__all__ = ["BACKEND_ID", "BraveSearchBackend"]
