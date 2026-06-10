"""Web-search backends — the common interface + registry (Pass B / Pillar C).

The agent calls :meth:`SearchBackend.search` through this seam; concrete
backends (SearXNG JSON, the keyless engine rotation, the bare DDG floor) are
selected at call time by :func:`resolve`. See :mod:`services.search.base` for
the wire contract and :mod:`services.search.registry` for backend selection.
"""

from __future__ import annotations

from .base import (
    Citation,
    SearchBackend,
    SearchError,
    SearchResponse,
    SearchResult,
    locale_domains,
    normalize_results_to_citations,
)
from .registry import KNOWN_BACKENDS, resolve

__all__ = [
    "KNOWN_BACKENDS",
    "Citation",
    "SearchBackend",
    "SearchError",
    "SearchResponse",
    "SearchResult",
    "locale_domains",
    "normalize_results_to_citations",
    "resolve",
]
