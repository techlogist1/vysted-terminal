"""The common search-backend contract (Pass B / Pillar C — C.4, FR-080).

Every web-search backend — Exa REST, Tavily REST, Linkup MCP, SearXNG JSON —
conforms to ONE interface so the agent calls :meth:`SearchBackend.search`
through this seam, never a vendor SDK directly (model Cursor/OpenCode). The
concrete backends live in sibling modules (``services.search.exa`` /
``services.search.searxng``) and are selected at call time by the registry
(:mod:`services.search.registry`).

The shapes here are the normalized wire contract:

  * :class:`SearchResult` — one retrieved document
    (``url``/``title``/``snippet`` + optional ``published_at``/``source``).
  * :class:`Citation` — the normalized citation chip ``{url, title, excerpt}``
    that the written brief renders as an inline ``[n]`` reference; every
    vendor's citation shape is collapsed to this by
    :func:`normalize_results_to_citations`.
  * :class:`SearchResponse` — what a backend returns: the results, the
    derived citations, the backend id that served them, and the query.

Locale-native search (C.2): Exa/Tavily-style domain allow-lists are sourced
from :func:`locale_domains`, which returns the US/IN preferred-domain profile
so a region-scoped research run stays on region-native sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# --- Wire shapes ------------------------------------------------------------


@dataclass
class SearchResult:
    """One retrieved document from a search backend."""

    url: str
    title: str
    snippet: str
    published_at: str | None = None
    source: str | None = None


@dataclass
class Citation:
    """A normalized citation chip — ``{url, title, excerpt}`` (C.4 / FR-080).

    Every vendor citation shape (Exa ``text``, Anthropic ``cited_text``,
    OpenAI ``url_citation``, Gemini ``groundingChunks``) collapses to this so
    the written brief renders uniform inline ``[n]`` references.
    """

    url: str
    title: str
    excerpt: str


@dataclass
class SearchResponse:
    """A backend's reply: results, derived citations, the backend id + query."""

    results: list[SearchResult]
    citations: list[Citation]
    backend: str
    query: str


class SearchError(Exception):
    """Raised when a search backend cannot satisfy a request."""


@runtime_checkable
class SearchBackend(Protocol):
    """The interface every search backend implements.

    A backend resolves a free-text ``query`` (optionally constrained by
    ``options`` — e.g. ``preferredDomains``/``maxResults``/``region``) into a
    :class:`SearchResponse`. Implementations raise :class:`SearchError` on an
    upstream failure rather than returning a partial/empty success.
    """

    async def search(self, query: str, *, options: dict | None = None) -> SearchResponse:
        """Resolve ``query`` into a normalized :class:`SearchResponse`."""
        ...


# --- Citation normalization -------------------------------------------------

#: Default number of top results promoted to citations for the written brief.
DEFAULT_CITATION_LIMIT = 8


def normalize_results_to_citations(
    results: list[SearchResult], *, limit: int = DEFAULT_CITATION_LIMIT
) -> list[Citation]:
    """Promote the top-N ``results`` to ``{url, title, excerpt}`` citations.

    The excerpt is the result's snippet (the inline-quotable span); a
    backend that supplies no snippet still yields a citation with an empty
    excerpt so the source is never silently dropped.
    """
    citations: list[Citation] = []
    for result in results[: max(limit, 0)]:
        citations.append(Citation(url=result.url, title=result.title, excerpt=result.snippet or ""))
    return citations


# --- Locale-native domain profiles (C.2) ------------------------------------

REGION_US = "US"
REGION_IN = "IN"

#: US research-native preferred domains (allow-list seed for Exa/Tavily etc.).
US_DOMAINS: tuple[str, ...] = (
    "finance.yahoo.com",
    "sec.gov",
    "bloomberg.com",
    "reuters.com",
    "wsj.com",
)

#: IN research-native preferred domains.
IN_DOMAINS: tuple[str, ...] = (
    "nseindia.com",
    "bseindia.com",
    "moneycontrol.com",
    "economictimes.indiatimes.com",
    "sebi.gov.in",
)

_DOMAINS_BY_REGION: dict[str, tuple[str, ...]] = {
    REGION_US: US_DOMAINS,
    REGION_IN: IN_DOMAINS,
}


def locale_domains(region: str) -> list[str]:
    """Return the preferred-domain allow-list for ``region`` (C.2).

    ``"IN"`` → NSE/BSE/Moneycontrol/ET/SEBI; ``"US"`` → Yahoo Finance/SEC/
    Bloomberg/Reuters/WSJ; an unknown region → the US profile (the global
    default sources). Case-insensitive on the region code.
    """
    return list(_DOMAINS_BY_REGION.get((region or "").strip().upper(), US_DOMAINS))


__all__ = [
    "Citation",
    "DEFAULT_CITATION_LIMIT",
    "IN_DOMAINS",
    "REGION_IN",
    "REGION_US",
    "SearchBackend",
    "SearchError",
    "SearchResponse",
    "SearchResult",
    "US_DOMAINS",
    "locale_domains",
    "normalize_results_to_citations",
]
