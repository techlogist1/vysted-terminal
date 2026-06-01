"""Pass B (B3) — the web_search agent tool + the agent-runtime native dispatch."""

from __future__ import annotations

import asyncio

import pytest

import config
from services.agent_tools.web_search import _web_search
from services.search.base import Citation, SearchError, SearchResponse, SearchResult


class _FakeBackend:
    def __init__(self, backend: str = "exa") -> None:
        self.backend = backend

    async def search(self, query: str, *, options=None) -> SearchResponse:  # noqa: ANN001
        return SearchResponse(
            results=[SearchResult(url="https://x.com/a", title="A", snippet="snip")],
            citations=[Citation(url="https://x.com/a", title="A", excerpt="snip")],
            backend=self.backend,
            query=query,
        )


def _run(coro):
    return asyncio.run(coro)


def test_missing_query_is_rejected() -> None:
    out = _run(_web_search({}))
    assert out["ok"] is False and "error" in out


def test_honest_fallback_when_no_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    # byok-exa tier but no key -> registry.resolve returns None -> honest message.
    token = config._search_tier_ctx.set("byok-exa")
    try:
        monkeypatch.setattr(registry, "resolve", lambda *a, **k: None)
        out = _run(_web_search({"query": "nvidia earnings"}))
    finally:
        config._search_tier_ctx.reset(token)
    assert out["ok"] is False
    assert "Exa" in out["message"] or "SearXNG" in out["message"]
    assert "search" in out["message"].lower()


def test_dispatch_returns_results_and_citations(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    token = config._search_tier_ctx.set("byok-exa")
    try:
        monkeypatch.setattr(registry, "resolve", lambda *a, **k: _FakeBackend("exa"))
        out = _run(_web_search({"query": "nvidia", "num_results": 3, "category": "financial"}))
    finally:
        config._search_tier_ctx.reset(token)
    assert out["ok"] is True
    assert out["backend"] == "exa"
    assert out["results"][0]["url"] == "https://x.com/a"
    assert out["citations"][0] == {"url": "https://x.com/a", "title": "A", "excerpt": "snip"}


def test_search_error_becomes_human_message(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    class _Boom:
        backend = "exa"

        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError("Exa rejected the key (401) — check your Exa API key.")

    token = config._search_tier_ctx.set("byok-exa")
    try:
        monkeypatch.setattr(registry, "resolve", lambda *a, **k: _Boom())
        out = _run(_web_search({"query": "x"}))
    finally:
        config._search_tier_ctx.reset(token)
    assert out["ok"] is False and "401" in out["message"]


def test_web_search_in_catalog_and_registered() -> None:
    import services.agent_tools as agent_tools
    from services.agent_tools import catalog, registry_v0_6_0

    assert "web_search" in catalog.CAPABILITY_CATALOG
    cap = catalog.CAPABILITY_CATALOG["web_search"]
    assert cap.read_only is True and cap.domain == "research"
    registry_v0_6_0.register_v0_6_0_tools()
    assert "web_search" in agent_tools.registered_tools()
