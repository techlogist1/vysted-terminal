"""The SearXNG local/private search backend (Pass B / Pillar C — C.4, FR-084, Tier 3).

SearXNG is a self-hosted metasearch engine. This backend is the **private** tier:
it talks to a SearXNG instance the operator runs on their own machine (or LAN), so
a research query never leaves the box — no vendor REST, no API key, no telemetry
(FR-084). Everything here is scoped to the single configured local ``base_url``.

The instance exposes a JSON search API::

    GET <base_url>/search?q=<query>&format=json[&categories=news]

returning ``{"results": [{"url", "title", "content", "publishedDate", ...}, ...]}``.
We map each result to the normalized :class:`~services.search.base.SearchResult`
(``content`` → ``snippet``, ``publishedDate`` → ``published_at``) and promote the top
results to :class:`~services.search.base.Citation` chips via
:func:`~services.search.base.normalize_results_to_citations`.

:func:`detect_searxng` autodetects a running instance by probing ``/healthz`` then
``/config`` with a short timeout so the registry can light up the Tier-3 option only
when a local SearXNG is actually reachable.
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import (
    SearchBackend,
    SearchError,
    SearchResponse,
    SearchResult,
    normalize_results_to_citations,
)

#: Default SearXNG location — the conventional local docker/host port.
DEFAULT_BASE_URL = "http://localhost:8080"

#: Identifier this backend reports in :class:`SearchResponse.backend`.
BACKEND_ID = "searxng"

#: Short timeout for the autodetect probe — a missing instance must fail fast.
_DETECT_TIMEOUT_SECS = 2.0

#: Per-request search timeout (a local instance is fast; cap a hung upstream).
_SEARCH_TIMEOUT_SECS = 20.0


def _normalize_base_url(base_url: str | None) -> str:
    """Resolve and tidy the configured base URL (strip a trailing slash)."""
    return (base_url or DEFAULT_BASE_URL).rstrip("/")


async def detect_searxng(
    base_url: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Probe for a reachable local SearXNG and return its base URL, else ``None``.

    Tries ``<base_url>/healthz`` first (SearXNG's liveness endpoint) and falls
    back to ``<base_url>/config`` (always present on a running instance). A 2xx
    from either means the instance is up; any connection error, timeout, or
    non-2xx status means "no local SearXNG here" → ``None``. Nothing is raised:
    autodetect is best-effort so the registry can silently skip the Tier-3
    option when no private instance is running.

    Pass ``client`` to reuse a caller-owned :class:`httpx.AsyncClient`
    (the test seam); otherwise a short-timeout client is created per call.
    """
    resolved = _normalize_base_url(base_url)

    async def _probe(http: httpx.AsyncClient) -> str | None:
        for path in ("/healthz", "/config"):
            try:
                response = await http.get(f"{resolved}{path}")
            except httpx.HTTPError:
                continue
            if response.is_success:
                return resolved
        return None

    if client is not None:
        return await _probe(client)

    async with httpx.AsyncClient(timeout=_DETECT_TIMEOUT_SECS) as http:
        return await _probe(http)


class SearxngBackend(SearchBackend):
    """A :class:`SearchBackend` over a local SearXNG JSON API (FR-084, Tier 3).

    No API key — the instance is the operator's own. Every request hits only the
    configured ``base_url``, so a research run on this tier is fully private:
    nothing leaves the machine.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        region: str | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = _normalize_base_url(base_url)
        # ``region`` is accepted for a uniform backend constructor signature (the
        # registry passes it) but local SearXNG does not domain-filter by locale —
        # the user's own instance decides its engines. Kept for parity / future use.
        self.region = region
        self._client = client

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        """Resolve ``query`` against the local SearXNG instance.

        ``options`` is optional: ``categories`` (e.g. ``"news"``) narrows the
        SearXNG category, and ``maxResults`` caps the promoted citations. On any
        connection/transport failure a :class:`SearchError` is raised with a
        human, actionable message (the registry surfaces it so the user can
        start an instance or pick another search tier).
        """
        opts = options or {}
        params: dict[str, str] = {"q": query, "format": "json"}
        categories = opts.get("categories")
        if categories:
            params["categories"] = str(categories)

        url = f"{self.base_url}/search"
        try:
            if self._client is not None:
                response = await self._client.get(url, params=params)
            else:
                async with httpx.AsyncClient(timeout=_SEARCH_TIMEOUT_SECS) as http:
                    response = await http.get(url, params=params)
            response.raise_for_status()
            payload: Any = response.json()
        except httpx.HTTPError as exc:
            raise SearchError(
                f"no local SearXNG at {self.base_url} — start one or pick another search tier"
            ) from exc

        results = _map_results(payload)
        limit = _citation_limit(opts)
        citations = (
            normalize_results_to_citations(results, limit=limit)
            if limit is not None
            else normalize_results_to_citations(results)
        )
        return SearchResponse(
            results=results,
            citations=citations,
            backend=BACKEND_ID,
            query=query,
        )


def _map_results(payload: Any) -> list[SearchResult]:
    """Map a SearXNG JSON payload's ``results[]`` to normalized results.

    SearXNG returns ``content`` for the snippet and ``publishedDate`` for the
    date; both are optional per result. A malformed payload (no ``results``
    list) yields an empty list rather than raising — an empty result set is a
    valid "found nothing" answer, distinct from a transport failure.
    """
    if not isinstance(payload, dict):
        return []
    raw = payload.get("results")
    if not isinstance(raw, list):
        return []

    mapped: list[SearchResult] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue
        mapped.append(
            SearchResult(
                url=url,
                title=str(item.get("title") or ""),
                snippet=str(item.get("content") or ""),
                published_at=_opt_str(item.get("publishedDate")),
                source=BACKEND_ID,
            )
        )
    return mapped


def _opt_str(value: Any) -> str | None:
    """Coerce a present, non-empty value to ``str`` else ``None``."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _citation_limit(opts: dict) -> int | None:
    """Read an optional ``maxResults`` citation cap from ``options``."""
    raw = opts.get("maxResults")
    if raw is None:
        return None
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        return None
    return limit if limit >= 0 else None


#: Canonical name the search registry imports (parity with ExaSearchBackend);
#: ``SearxngBackend`` stays as the short alias the unit tests use.
SearxngSearchBackend = SearxngBackend

__all__ = [
    "BACKEND_ID",
    "DEFAULT_BASE_URL",
    "SearxngBackend",
    "SearxngSearchBackend",
    "detect_searxng",
]
