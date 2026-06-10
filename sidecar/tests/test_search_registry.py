"""Offline unit tests for the search-backend interface + registry (C.4 / FR-080).

No live backend is called — ``resolve`` returns ``None`` (the honest fallback
signal) whenever a backend lacks its key/URL, so these tests never touch the
network.
"""

from __future__ import annotations

from services.search import (
    Citation,
    SearchResponse,
    SearchResult,
    locale_domains,
    normalize_results_to_citations,
    resolve,
)
from services.search.base import SearchBackend, SearchError


def _result(n: int) -> SearchResult:
    return SearchResult(
        url=f"https://example.com/{n}",
        title=f"Result {n}",
        snippet=f"Snippet body {n}",
        published_at="2026-05-14",
        source="example.com",
    )


# --- Dataclass shapes -------------------------------------------------------


def test_search_result_shape() -> None:
    r = SearchResult(url="https://u", title="t", snippet="s")
    assert (r.url, r.title, r.snippet) == ("https://u", "t", "s")
    # Optional fields default to None.
    assert r.published_at is None
    assert r.source is None


def test_citation_shape() -> None:
    c = Citation(url="https://u", title="t", excerpt="e")
    assert (c.url, c.title, c.excerpt) == ("https://u", "t", "e")


def test_search_response_shape() -> None:
    results = [_result(1)]
    citations = normalize_results_to_citations(results)
    resp = SearchResponse(results=results, citations=citations, backend="exa", query="nvda")
    assert resp.backend == "exa"
    assert resp.query == "nvda"
    assert resp.results == results
    assert resp.citations == citations


def test_search_error_is_exception() -> None:
    assert issubclass(SearchError, Exception)


# --- Citation normalization -------------------------------------------------


def test_normalize_three_results_to_three_citations() -> None:
    results = [_result(1), _result(2), _result(3)]
    citations = normalize_results_to_citations(results)
    assert len(citations) == 3
    for src, cite in zip(results, citations, strict=True):
        assert isinstance(cite, Citation)
        assert cite.url == src.url
        assert cite.title == src.title
        assert cite.excerpt == src.snippet


def test_normalize_respects_limit() -> None:
    results = [_result(n) for n in range(10)]
    citations = normalize_results_to_citations(results, limit=3)
    assert len(citations) == 3
    assert [c.url for c in citations] == [results[i].url for i in range(3)]


def test_normalize_empty_snippet_yields_empty_excerpt() -> None:
    r = SearchResult(url="https://u", title="t", snippet="")
    [cite] = normalize_results_to_citations([r])
    assert cite.excerpt == ""
    assert cite.url == "https://u"


# --- Locale domain profiles -------------------------------------------------


def test_locale_domains_in_includes_nse() -> None:
    domains = locale_domains("IN")
    assert "nseindia.com" in domains
    assert "bseindia.com" in domains
    assert "sebi.gov.in" in domains


def test_locale_domains_us_includes_sec() -> None:
    domains = locale_domains("US")
    assert "sec.gov" in domains
    assert "finance.yahoo.com" in domains


def test_locale_domains_case_insensitive() -> None:
    assert locale_domains("in") == locale_domains("IN")


def test_locale_domains_unknown_falls_back_to_us() -> None:
    assert locale_domains("ZZ") == locale_domains("US")


# --- Registry resolution (offline) ------------------------------------------


def test_resolve_returns_none_without_searxng_url() -> None:
    assert resolve("searxng") is None
    assert resolve("searxng", searxng_url="") is None


def test_resolve_ddg_is_unconditional_keyless_floor() -> None:
    from services.search.ddg import DdgSearchBackend
    from services.search.registry import KNOWN_BACKENDS

    # The ddg floor needs no key/url — it ALWAYS resolves, so web search is never
    # dark on a fresh install.
    backend = resolve("ddg")
    assert isinstance(backend, DdgSearchBackend)
    assert "ddg" in KNOWN_BACKENDS


def test_resolve_keyless_is_unconditional_floor_tier() -> None:
    from services.search.keyless import KeylessSearchBackend
    from services.search.registry import KNOWN_BACKENDS

    # The multi-engine keyless rotation needs no key/url — it ALWAYS resolves
    # and is the web_search handler's invisible fallback (R9: stamped
    # ``keyless-fallback`` at the tool layer, never a user-facing tier).
    backend = resolve("keyless")
    assert isinstance(backend, KeylessSearchBackend)
    assert "keyless" in KNOWN_BACKENDS


def test_dead_r7_byok_backends_are_unresolvable() -> None:
    # R9 Track A kill: the BYOK hosted-scraper tier (OpenRouter web plugin) and
    # the Exa-direct lane are DELETED — the registry must treat their old ids as
    # unknown, never construct a paid scraper backend again.
    from services.search.registry import KNOWN_BACKENDS

    assert resolve("exa") is None
    assert resolve("hosted") is None
    assert "exa" not in KNOWN_BACKENDS
    assert "hosted" not in KNOWN_BACKENDS


def test_resolve_returns_none_for_unknown_backend() -> None:
    # Engine ids inside the keyless tier (brave/mojeek) are NOT registry-level
    # backends — the tier is selected as one unit ("keyless").
    assert resolve("brave", searxng_url="http://u") is None
    assert resolve("mojeek") is None


def test_resolve_returns_none_for_empty_active_id() -> None:
    assert resolve(None, searxng_url="http://u") is None
    assert resolve("", searxng_url="http://u") is None


def test_search_backend_protocol_is_runtime_checkable() -> None:
    # A plain object without an async ``search`` is not a SearchBackend.
    assert not isinstance(object(), SearchBackend)
