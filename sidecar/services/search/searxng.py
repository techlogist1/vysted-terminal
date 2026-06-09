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

:func:`detect_searxng` autodetects a running instance with the **capability probe**
``/search?q=…&format=json`` — a 200 with JSON means the instance is up AND the JSON
output the backend needs is enabled (it is OFF by default in SearXNG). A 403 means
"up but JSON disabled" (the operator must add ``json`` to ``search.formats``); both
non-usable cases return ``None`` so the registry only lights up Tier-3 when search
will actually work. When no URL is configured it consults the one-click manager
(:mod:`services.searxng_manager`) first — a READY managed instance routes here with
zero extra config (R7 Component 2) — then probes the two conventional local ports,
``8888`` (pip dev server) and ``8080`` (docker), so a default install on either is
found.
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

#: Conventional local ports probed (in order) when no URL is configured: the pip
#: dev server binds ``8888``, the docker image binds ``8080``.
_DEFAULT_PROBE_URLS: tuple[str, ...] = ("http://localhost:8888", "http://localhost:8080")

#: Identifier this backend reports in :class:`SearchResponse.backend`.
BACKEND_ID = "searxng"

#: Timeout for the autodetect capability probe. A MISSING instance still fails
#: fast (connection-refused returns immediately regardless of this value); the
#: budget exists because a PRESENT instance's ``format=json`` query fans out to
#: many upstream engines and can take a couple of seconds to aggregate.
_DETECT_TIMEOUT_SECS = 6.0

#: Per-request search timeout (a local instance is fast; cap a hung upstream).
_SEARCH_TIMEOUT_SECS = 20.0


def _normalize_base_url(base_url: str | None) -> str:
    """Resolve and tidy the configured base URL (strip a trailing slash)."""
    return (base_url or DEFAULT_BASE_URL).rstrip("/")


def _managed_base_url() -> str | None:
    """The one-click managed instance's URL when its manager reports READY.

    Lazy, guarded import so the backend stays importable in a half-built tree;
    a pure in-memory read otherwise (the capability probe re-verifies the URL,
    so a stale READY can never yield a false positive).
    """
    try:
        from services.searxng_manager import manager
    except ImportError:
        return None
    return manager.ready_base_url()


async def _json_capable(http: httpx.AsyncClient, base: str) -> bool:
    """Capability probe: is a SearXNG at ``base`` up AND serving JSON search?

    SearXNG has no ``/healthz`` (upstream issue #4026) and ``/config`` only proves
    the instance is up, NOT that the JSON output format is enabled (it is OFF by
    default — a search would then 403). So we probe the real thing: a tiny
    ``/search?format=json``. Only a 200 with a parseable JSON body (a ``results``
    list) counts as usable; a 403 (JSON disabled) or any error is "not usable".
    """
    try:
        response = await http.get(f"{base}/search", params={"q": "ping", "format": "json"})
    except httpx.HTTPError:
        return False
    if not response.is_success:
        return False
    try:
        payload = response.json()
    except (ValueError, httpx.HTTPError):
        return False
    return isinstance(payload, dict) and isinstance(payload.get("results"), list)


async def detect_searxng(
    base_url: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Probe for a reachable, JSON-capable local SearXNG; return its base URL else ``None``.

    Uses the capability probe (:func:`_json_capable`) so a "found" instance is one
    that can actually answer ``format=json`` searches — never a false positive
    from an up-but-JSON-disabled instance. With no ``base_url`` it tries the
    one-click managed instance first (when its manager reports READY), then the
    two conventional local ports (``8888`` pip, ``8080`` docker); with one given
    it probes only that. Best-effort: never raises, so the registry silently skips
    Tier-3 when no usable private instance is running.

    Pass ``client`` to reuse a caller-owned :class:`httpx.AsyncClient`
    (the test seam); otherwise a short-timeout client is created per call.
    """
    if base_url:
        candidates = [_normalize_base_url(base_url)]
    else:
        candidates = []
        managed = _managed_base_url()
        if managed:
            candidates.append(_normalize_base_url(managed))
        candidates.extend(url for url in _DEFAULT_PROBE_URLS if url not in candidates)

    async def _probe(http: httpx.AsyncClient) -> str | None:
        for candidate in candidates:
            if await _json_capable(http, candidate):
                return candidate
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
