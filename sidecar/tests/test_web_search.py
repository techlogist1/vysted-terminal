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


def test_honest_message_when_even_ddg_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    # Defensive path: if EVERY backend (including the ddg floor) fails to resolve,
    # the handler still returns an honest message rather than a fabricated source.
    token = config._search_tier_ctx.set("byok-exa")
    try:
        monkeypatch.setattr(registry, "resolve", lambda *a, **k: None)
        out = _run(_web_search({"query": "nvidia earnings"}))
    finally:
        config._search_tier_ctx.reset(token)
    assert out["ok"] is False
    assert "Exa" in out["message"] or "SearXNG" in out["message"]
    assert "search" in out["message"].lower()


def test_ddg_is_the_keyless_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry

    # byok-exa tier with no key: exa/searxng resolve to None, so the keyless
    # DuckDuckGo floor serves the query — web search is never dark out of the box.
    def _resolve(active_id, **_kw):  # noqa: ANN001, ANN003
        return _FakeBackend("ddg") if active_id == "ddg" else None

    token = config._search_tier_ctx.set("byok-exa")
    try:
        monkeypatch.setattr(registry, "resolve", _resolve)
        out = _run(_web_search({"query": "nvidia earnings"}))
    finally:
        config._search_tier_ctx.reset(token)
    assert out["ok"] is True
    assert out["backend"] == "ddg"
    assert out["results"][0]["url"] == "https://x.com/a"


def test_local_searxng_tier_autodetects_when_no_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import registry, searxng

    detected: dict[str, object] = {}

    async def _fake_detect(base=None, *, client=None):  # noqa: ANN001, ANN202
        detected["called"] = True
        return "http://localhost:8888"

    monkeypatch.setattr(searxng, "detect_searxng", _fake_detect)

    captured: dict[str, object] = {}

    def _resolve(active_id, *, exa_key=None, searxng_url=None, region=None):  # noqa: ANN001
        captured["searxng_url"] = searxng_url
        return _FakeBackend("searxng") if active_id == "searxng" else None

    monkeypatch.setattr(registry, "resolve", _resolve)
    token = config._search_tier_ctx.set("local-searxng")
    try:
        out = _run(_web_search({"query": "x"}))
    finally:
        config._search_tier_ctx.reset(token)
    assert detected.get("called") is True
    assert captured["searxng_url"] == "http://localhost:8888"  # autodetected URL flows through
    assert out["ok"] is True and out["backend"] == "searxng"


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
    # WS3: a plain SearchError (no typed reason) defaults to "unreachable" so the
    # brief reports an honest no-backend miss rather than a transient throttle.
    assert out["reason"] == "unreachable"


def test_search_error_forwards_typed_rate_limit_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS3: a SearchError tagged ``reason="rate_limited"`` (a transient throttle)
    is surfaced on the failed dict so the brief shows "rate-limited, retrying"
    instead of the false "no backend configured" banner."""
    from services.search import registry
    from services.search.base import SEARCH_REASON_RATE_LIMITED

    class _Throttled:
        backend = "ddg"

        async def search(self, query, *, options=None):  # noqa: ANN001, ANN201
            raise SearchError(
                "keyless web search is rate-limiting right now — retry shortly",
                reason=SEARCH_REASON_RATE_LIMITED,
            )

    token = config._search_tier_ctx.set("byok-exa")
    try:
        monkeypatch.setattr(registry, "resolve", lambda *a, **k: _Throttled())
        out = _run(_web_search({"query": "x"}))
    finally:
        config._search_tier_ctx.reset(token)
    assert out["ok"] is False
    assert out["reason"] == "rate_limited"


def test_web_search_in_catalog_and_registered() -> None:
    import services.agent_tools as agent_tools
    from services.agent_tools import catalog, registry_v0_6_0

    assert "web_search" in catalog.CAPABILITY_CATALOG
    cap = catalog.CAPABILITY_CATALOG["web_search"]
    assert cap.read_only is True and cap.domain == "research"
    registry_v0_6_0.register_v0_6_0_tools()
    assert "web_search" in agent_tools.registered_tools()
