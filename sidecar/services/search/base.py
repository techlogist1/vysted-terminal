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
    (+ the bare-host ``domain`` and ``published_at`` the brief's sources rail
    shows) that the written brief renders as an inline ``[n]`` reference; every
    vendor's citation shape is collapsed to this by
    :func:`normalize_results_to_citations`.
  * :class:`SearchResponse` — what a backend returns: the results, the
    derived citations, the backend id that served them, and the query.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from urllib.parse import urlparse

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
    #: The URL's bare host (``sec.gov``) — never a provenance label or "web".
    domain: str | None = None
    #: The result's publication date as the backend reported it, or ``None``.
    published_at: str | None = None


def bare_host(url: str) -> str | None:
    """The URL's host without ``www.`` (``https://www.sec.gov/x`` → ``sec.gov``)."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return None
    return host.removeprefix("www.") or None


@dataclass
class SearchResponse:
    """A backend's reply: results, derived citations, the backend id + query."""

    results: list[SearchResult]
    citations: list[Citation]
    backend: str
    query: str


#: Typed reasons a :class:`SearchError` can carry, so a caller can distinguish a
#: TRANSIENT throttle (retry later — the backend exists) from a backend that is
#: genuinely unreachable/missing. ``"rate_limited"`` ⇒ the brief banner says
#: "rate-limited, retrying"; ``"unreachable"`` (the default) ⇒ "no backend".
SEARCH_REASON_RATE_LIMITED = "rate_limited"
SEARCH_REASON_UNREACHABLE = "unreachable"


class SearchError(Exception):
    """Raised when a search backend cannot satisfy a request.

    Carries a TYPED :attr:`reason` so the caller can tell a transient throttle
    (``"rate_limited"`` — the backend is up, just throttling; the honest brief
    note becomes "rate-limited, retrying") apart from a backend that is missing
    or unreachable (``"unreachable"`` — the default; the brief stays honestly
    "structured data only / no backend"). The human ``str(exc)`` message is
    unchanged; ``reason`` is the machine-readable discriminator layered on top.
    """

    def __init__(self, message: str, *, reason: str = SEARCH_REASON_UNREACHABLE) -> None:
        super().__init__(message)
        self.reason = reason


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


def result_limit(options: dict | None) -> int:
    """The caller's result cap: ``maxResults`` (or ``numResults``, the key the
    ``web_search`` tool sends) when it is a positive integer, else
    :data:`DEFAULT_CITATION_LIMIT`. Every backend caps results AND citations
    with this one rule."""
    opts = options or {}
    try:
        limit = int(opts.get("maxResults", opts.get("numResults")))
    except (TypeError, ValueError):
        return DEFAULT_CITATION_LIMIT
    return limit if limit > 0 else DEFAULT_CITATION_LIMIT


def normalize_results_to_citations(
    results: list[SearchResult], *, limit: int = DEFAULT_CITATION_LIMIT
) -> list[Citation]:
    """Promote the top-N ``results`` to ``{url, title, excerpt}`` citations.

    The excerpt is the result's snippet (the inline-quotable span); a
    backend that supplies no snippet still yields a citation with an empty
    excerpt so the source is never silently dropped.
    """
    return [
        Citation(
            url=result.url,
            title=result.title,
            excerpt=result.snippet or "",
            domain=bare_host(result.url),
            published_at=result.published_at,
        )
        for result in results[: max(limit, 0)]
    ]


__all__ = [
    "Citation",
    "DEFAULT_CITATION_LIMIT",
    "SEARCH_REASON_RATE_LIMITED",
    "SEARCH_REASON_UNREACHABLE",
    "SearchBackend",
    "SearchError",
    "SearchResponse",
    "SearchResult",
    "bare_host",
    "normalize_results_to_citations",
    "result_limit",
]
