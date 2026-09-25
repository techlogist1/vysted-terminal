"""Shared HTML-SERP scrape contract for keyless rotation engines (R15-CODE-RESEARCH-010).

``brave.py`` and ``mojeek.py`` were near-identical copies of the same shape —
fetch → typed rate-limit/unreachable → parse (dedup by URL, capped at a
limit) — differing only in endpoint, region param/map, markup selectors and
self-link hosts. This module carries the shared parts: the fetch/error
handling (:class:`_HtmlSerpBackend`, configured per engine by
:class:`HtmlSerpConfig`) and the small parse helpers
(:func:`clean_text`, :func:`is_organic_url`, :func:`parse_containers`) every
layered-selector SERP parser needs. ``brave.py``/``mojeek.py`` supply only
their endpoint, selectors and node-to-result mapping as configuration.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from .base import (
    SEARCH_REASON_RATE_LIMITED,
    SearchBackend,
    SearchError,
    SearchResponse,
    SearchResult,
    normalize_results_to_citations,
    result_limit,
)
from .transport import TransportError

if TYPE_CHECKING:
    from .transport import FetchResult

Fetch = Callable[..., Awaitable["FetchResult"]]
NodeToResult = Callable[[Any], SearchResult | None]


def clean_text(text: str) -> str:
    """Collapse whitespace in an extracted text fragment (shared by every HTML-SERP parser)."""
    return " ".join(text.split())


def is_organic_url(url: str, *, skip_hosts: tuple[str, ...]) -> bool:
    """True when ``url`` is a real result link, not engine chrome/self/ad on ``skip_hosts``."""
    if not url.startswith(("http://", "https://")):
        return False
    host = (urlparse(url).hostname or "").lower()
    return bool(host) and not any(host == h or host.endswith("." + h) for h in skip_hosts)


def parse_containers(
    containers: Iterable[Any], *, limit: int, node_to_result: NodeToResult
) -> list[SearchResult]:
    """Map result containers to deduped :class:`SearchResult`s, capped at ``limit``.

    The dedup-by-url scan loop every layered-selector SERP parser repeated.
    """
    out: list[SearchResult] = []
    seen: set[str] = set()
    for node in containers:
        result = node_to_result(node)
        if result is None or result.url in seen:
            continue
        seen.add(result.url)
        out.append(result)
        if len(out) >= limit:
            break
    return out


@dataclass(frozen=True)
class HtmlSerpConfig:
    """One engine's configuration onto the shared HTML-SERP contract."""

    backend_id: str
    #: Human name used in error messages ("Brave HTML search", "Mojeek").
    engine_label: str
    endpoint: str
    #: The engine's default transport (``impersonated_fetch`` or ``httpx_fetch``).
    default_fetch: Fetch
    #: ``(page_text, limit) -> results`` — the engine's own selector chain.
    parse: Callable[[str, int], list[SearchResult]]
    rate_limit_statuses: frozenset[int] = frozenset({403, 429})
    #: The query-param name a region bias rides (``"country"``/``"arc"``), or
    #: ``None`` when the engine takes no region param.
    region_param: str | None = None
    region_map: dict[str, str] = field(default_factory=dict)
    #: Extra static query params every request carries (Brave's ``source=web``).
    extra_params: dict[str, str] = field(default_factory=dict)


class _HtmlSerpBackend(SearchBackend):
    """fetch → typed rate-limit/unreachable → parse, configured per engine."""

    def __init__(
        self, config: HtmlSerpConfig, *, region: str | None = None, fetch: Fetch | None = None
    ) -> None:
        self._config = config
        self.region = region
        # Injectable fetch (same signature as the engine's default transport) for tests.
        self._fetch = fetch or config.default_fetch

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        cfg = self._config
        limit = result_limit(options or {})
        params: dict[str, str] = {"q": query, **cfg.extra_params}
        if cfg.region_param:
            biased = cfg.region_map.get((self.region or "").strip().upper())
            if biased:
                params[cfg.region_param] = biased

        try:
            fetched = await self._fetch(cfg.endpoint, params=params)
        except TransportError as exc:
            raise SearchError(f"{cfg.engine_label} is unreachable: {exc}") from exc

        if fetched.status_code in cfg.rate_limit_statuses:
            raise SearchError(
                f"{cfg.engine_label} is blocking/rate-limiting right now "
                f"(HTTP {fetched.status_code}) — rotating to the next keyless engine",
                reason=SEARCH_REASON_RATE_LIMITED,
            )
        if fetched.status_code >= 400:
            raise SearchError(f"{cfg.engine_label} failed (HTTP {fetched.status_code})")

        results = cfg.parse(fetched.text, limit)
        return SearchResponse(
            results=results,
            citations=normalize_results_to_citations(results, limit=limit),
            backend=cfg.backend_id,
            query=query,
        )


__all__ = ["HtmlSerpConfig", "clean_text", "is_organic_url", "parse_containers"]
