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

Production routing never probes the network to find an instance: a configured
``searxng_url`` (custom or the one-click manager's) is resolved in-process via
:func:`services.searxng_manager.manager.ready_base_url` /
``ready_base_url_detected`` (:mod:`services.search.registry`), and this backend
is only constructed once that URL is known.
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
    result_limit,
)

#: Default SearXNG location — the conventional local docker/host port.
DEFAULT_BASE_URL = "http://localhost:8080"

#: Identifier this backend reports in :class:`SearchResponse.backend`.
BACKEND_ID = "searxng"

#: Per-request search timeout (a local instance is fast; cap a hung upstream).
_SEARCH_TIMEOUT_SECS = 20.0


def _normalize_base_url(base_url: str | None) -> str:
    """Resolve and tidy the configured base URL (strip a trailing slash)."""
    return (base_url or DEFAULT_BASE_URL).rstrip("/")


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
        SearXNG category, and ``maxResults``/``numResults`` caps the results and
        citations (:func:`~services.search.base.result_limit`). On any
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
        except httpx.HTTPStatusError as exc:
            if exc.response is not None and exc.response.status_code == 403:
                raise SearchError(
                    f"SearXNG at {self.base_url} has JSON output disabled — add 'json' to "
                    "search.formats in settings.yml (and restart), then retry"
                ) from exc
            raise SearchError(
                f"no local SearXNG at {self.base_url} — start one or pick another search tier"
            ) from exc
        except httpx.HTTPError as exc:
            raise SearchError(
                f"no local SearXNG at {self.base_url} — start one or pick another search tier"
            ) from exc

        limit = result_limit(opts)
        results = _map_results(payload)[:limit]
        return SearchResponse(
            results=results,
            citations=normalize_results_to_citations(results, limit=limit),
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


#: Canonical name the search registry imports (parity with ExaSearchBackend);
#: ``SearxngBackend`` stays as the short alias the unit tests use.
SearxngSearchBackend = SearxngBackend

__all__ = [
    "BACKEND_ID",
    "DEFAULT_BASE_URL",
    "SearxngBackend",
    "SearxngSearchBackend",
]
