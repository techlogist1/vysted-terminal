"""R7 Track R (Component 3) — the t3 hosted tier (OpenRouter web-search server tool).

Offline: the HTTP layer is a stub client injected via the backend's ``client``
seam — no live OpenRouter call, ever. Covers the CURRENT server-tool request
shape (verified against the live docs 2026-06-10), engine defaults + pricing
estimates, annotation parsing, BYOK key hygiene, and the ``web_search`` tool's
R7 tier routing.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

import config
from services.search import hosted, registry
from services.search.base import SearchError
from services.search.hosted import (
    DEFAULT_ENGINE,
    DEFAULT_HOSTED_MODEL,
    HostedSearchBackend,
    estimate_search_cost_usd,
    normalize_engine,
    web_search_server_tool,
)


def _run(coro):
    return asyncio.run(coro)


# --- Server-tool request shape (live docs, 2026-06-10) ------------------------


def test_server_tool_is_the_current_type_not_the_deprecated_plugin() -> None:
    tool = web_search_server_tool()
    assert tool["type"] == "openrouter:web_search"
    # The deprecated plugins-array spelling never appears.
    assert "id" not in tool and "plugins" not in tool


def test_server_tool_defaults_to_firecrawl_free_tier() -> None:
    tool = web_search_server_tool()
    assert tool["parameters"]["engine"] == "firecrawl"
    assert DEFAULT_ENGINE == "firecrawl"


def test_server_tool_carries_and_clamps_max_results() -> None:
    tool = web_search_server_tool(engine="exa", max_results=8)
    assert tool["parameters"]["max_results"] == 8
    assert tool["parameters"]["max_total_results"] == 8
    # Docs bound: 1-25.
    assert web_search_server_tool(max_results=99)["parameters"]["max_results"] == 25
    assert web_search_server_tool(max_results=0)["parameters"]["max_results"] == 1


def test_server_tool_optional_domain_allowlist() -> None:
    tool = web_search_server_tool(allowed_domains=["sec.gov", " nseindia.com "])
    assert tool["parameters"]["allowed_domains"] == ["sec.gov", "nseindia.com"]
    assert "allowed_domains" not in web_search_server_tool()["parameters"]


def test_engine_normalization() -> None:
    assert normalize_engine("exa") == "exa"
    assert normalize_engine(" Firecrawl ") == "firecrawl"
    assert normalize_engine("parallel") == "parallel"
    # Unknown/empty floors to the free-credit default, never a paid surprise.
    assert normalize_engine("warpdrive") == "firecrawl"
    assert normalize_engine(None) == "firecrawl"


# --- Pricing estimates (documented rates, 2026-06-10) -------------------------


def test_firecrawl_costs_nothing_openrouter_side() -> None:
    assert estimate_search_cost_usd("firecrawl", 10) == 0.0


def test_exa_flat_rate_within_included_results() -> None:
    assert estimate_search_cost_usd("exa", 5) == 0.005
    assert estimate_search_cost_usd("exa", 10) == 0.005


def test_exa_per_extra_result_above_ten() -> None:
    assert estimate_search_cost_usd("exa", 15) == pytest.approx(0.010)
    assert estimate_search_cost_usd("parallel", 25) == pytest.approx(0.020)


def test_native_engine_price_is_honestly_unknown() -> None:
    # Provider pass-through — we never fabricate a number.
    assert estimate_search_cost_usd("native", 5) is None


def test_auto_engine_worst_cases_to_exa_pricing() -> None:
    assert estimate_search_cost_usd("auto", 5) == 0.005


# --- Backend behaviour ---------------------------------------------------------


class _StubResponse:
    def __init__(self, body: dict[str, Any], status: int = 200) -> None:
        self._body = body
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", hosted.OPENROUTER_CHAT_URL)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    def json(self) -> dict[str, Any]:
        return self._body


class _StubClient:
    """Captures the outbound request; returns a canned response."""

    def __init__(self, body: dict[str, Any], status: int = 200) -> None:
        self._body = body
        self._status = status
        self.captured: dict[str, Any] = {}

    async def post(self, url: str, *, json: dict, headers: dict, timeout: Any) -> _StubResponse:
        self.captured = {"url": url, "json": json, "headers": headers}
        return _StubResponse(self._body, self._status)


def _annotations_body() -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "content": "Findings...",
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url_citation": {
                                "url": "https://sec.gov/filing",
                                "title": "10-K",
                                "content": "Revenue grew 12%...",
                            },
                        },
                        # Flat shape + duplicate url (kept once) + non-citation noise.
                        {
                            "type": "url_citation",
                            "url": "https://reuters.com/story",
                            "title": "Reuters",
                            "snippet": "snip",
                        },
                        {
                            "type": "url_citation",
                            "url_citation": {"url": "https://sec.gov/filing", "title": "dupe"},
                        },
                        {"type": "other_annotation", "url": "https://ignored.example"},
                    ],
                }
            }
        ]
    }


def test_backend_requires_a_key() -> None:
    with pytest.raises(SearchError) as excinfo:
        HostedSearchBackend(api_key="  ")
    assert "OpenRouter" in str(excinfo.value)


def test_search_sends_current_tool_shape_and_bearer_key() -> None:
    client = _StubClient(_annotations_body())
    backend = HostedSearchBackend(api_key="sk-or-test", client=client)  # type: ignore[arg-type]
    _run(backend.search("nvidia earnings", options={"numResults": 4}))

    sent = client.captured["json"]
    assert sent["model"] == DEFAULT_HOSTED_MODEL
    assert sent["tools"] == [
        {
            "type": "openrouter:web_search",
            "parameters": {"engine": "firecrawl", "max_results": 4, "max_total_results": 4},
        }
    ]
    assert client.captured["headers"]["Authorization"] == "Bearer sk-or-test"
    assert "nvidia earnings" in sent["messages"][0]["content"]


def test_engine_and_model_overrides_ride_options() -> None:
    client = _StubClient(_annotations_body())
    backend = HostedSearchBackend(api_key="sk-or-test", engine="exa", client=client)  # type: ignore[arg-type]
    response = _run(
        backend.search("q", options={"engine": "parallel", "model": "openai/gpt-5-mini"})
    )
    sent = client.captured["json"]
    assert sent["tools"][0]["parameters"]["engine"] == "parallel"
    assert sent["model"] == "openai/gpt-5-mini"
    assert response.metadata is not None and response.metadata["engine"] == "parallel"


def test_annotations_map_to_results_and_citations_deduped() -> None:
    client = _StubClient(_annotations_body())
    backend = HostedSearchBackend(api_key="sk-or-test", client=client)  # type: ignore[arg-type]
    response = _run(backend.search("q"))

    urls = [r.url for r in response.results]
    assert urls == ["https://sec.gov/filing", "https://reuters.com/story"]
    # The server tool's excerpt field is ``content`` (live docs); flat ``snippet`` accepted.
    assert response.results[0].snippet == "Revenue grew 12%..."
    assert response.results[1].snippet == "snip"
    assert [c.url for c in response.citations] == urls
    assert response.backend == "hosted"


def test_metadata_carries_per_search_cost_estimate() -> None:
    client = _StubClient(_annotations_body())
    backend = HostedSearchBackend(api_key="sk-or-test", engine="exa", client=client)  # type: ignore[arg-type]
    response = _run(backend.search("q", options={"numResults": 15}))

    meta = response.metadata
    assert meta is not None
    assert meta["tier"] == "t3_hosted"
    assert meta["engine"] == "exa"
    assert meta["search_cost_estimate_usd"] == pytest.approx(0.010)
    assert meta["estimate"] is True
    assert "0.005" in meta["cost_basis"]


def test_firecrawl_metadata_names_the_free_credit_tier() -> None:
    client = _StubClient(_annotations_body())
    backend = HostedSearchBackend(api_key="sk-or-test", client=client)  # type: ignore[arg-type]
    response = _run(backend.search("q"))
    meta = response.metadata
    assert meta is not None and meta["search_cost_estimate_usd"] == 0.0
    assert "Firecrawl credits" in meta["cost_basis"]


@pytest.mark.parametrize(
    ("status", "needle"),
    [(401, "key"), (402, "credits"), (429, "rate limit"), (500, "unavailable")],
)
def test_http_errors_become_human_messages_without_the_key(status: int, needle: str) -> None:
    client = _StubClient({}, status=status)
    backend = HostedSearchBackend(api_key="sk-or-supersecret", client=client)  # type: ignore[arg-type]
    with pytest.raises(SearchError) as excinfo:
        _run(backend.search("q"))
    message = str(excinfo.value)
    assert needle in message
    assert "sk-or-supersecret" not in message


def test_no_annotations_yields_empty_results_not_fabricated_sources() -> None:
    client = _StubClient({"choices": [{"message": {"content": "no search happened"}}]})
    backend = HostedSearchBackend(api_key="sk-or-test", client=client)  # type: ignore[arg-type]
    response = _run(backend.search("q"))
    assert response.results == [] and response.citations == []


def test_empty_query_is_rejected() -> None:
    backend = HostedSearchBackend(api_key="sk-or-test")
    with pytest.raises(SearchError):
        _run(backend.search("   "))


# --- Registry wiring -----------------------------------------------------------


def test_registry_resolves_hosted_with_key_only() -> None:
    assert registry.resolve("hosted") is None
    backend = registry.resolve("hosted", openrouter_key="sk-or-test", engine="exa")
    assert backend is not None and backend.name == "hosted"


def test_registry_existing_backends_unaffected_by_new_kwargs() -> None:
    assert registry.resolve("exa", openrouter_key="sk-or-test") is None
    assert registry.resolve("keyless", openrouter_key="sk-or-test") is not None


# --- web_search tool routing (R7 tiers) -----------------------------------------


class _FakeBackend:
    def __init__(self, backend_id: str, metadata: dict | None = None) -> None:
        self.backend = backend_id
        self._metadata = metadata

    async def search(self, query: str, *, options=None):  # noqa: ANN001
        from services.search.base import Citation, SearchResponse, SearchResult

        return SearchResponse(
            results=[SearchResult(url="https://x.com/a", title="A", snippet="s")],
            citations=[Citation(url="https://x.com/a", title="A", excerpt="s")],
            backend=self.backend,
            query=query,
            metadata=self._metadata,
        )


def _route(monkeypatch: pytest.MonkeyPatch, tier: str, key: str | None = None) -> dict:
    from services.agent_tools.web_search import _web_search

    resolved: dict[str, Any] = {}

    def _resolve(active_id, **kw):  # noqa: ANN001, ANN003
        resolved["id"] = active_id
        resolved["kw"] = kw
        if active_id == "hosted" and not kw.get("openrouter_key"):
            return None
        return _FakeBackend(
            active_id, metadata={"tier": "t3_hosted"} if active_id == "hosted" else None
        )

    monkeypatch.setattr(registry, "resolve", _resolve)
    tier_token = config.set_request_research_search_tier(tier)
    key_token = config.set_request_openrouter_search_key(key)
    try:
        out = _run(_web_search({"query": "tata motors results"}))
    finally:
        config.reset_request_openrouter_search_key(key_token)
        config.reset_request_research_search_tier(tier_token)
    out["_resolved"] = resolved
    return out


def test_t3_hosted_routes_to_hosted_backend_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    out = _route(monkeypatch, "t3_hosted", key="sk-or-test")
    assert out["ok"] is True and out["backend"] == "hosted"
    assert out["_resolved"]["id"] == "hosted"
    assert out["_resolved"]["kw"]["openrouter_key"] == "sk-or-test"
    # The per-search cost annex rides the tool result.
    assert out["metadata"] == {"tier": "t3_hosted"}


def test_t3_without_key_fails_honestly_never_reroutes(monkeypatch: pytest.MonkeyPatch) -> None:
    out = _route(monkeypatch, "t3_hosted", key=None)
    assert out["ok"] is False
    assert "OpenRouter" in out["message"]
    # It never silently fell through to another backend.
    assert out["_resolved"] == {}


def test_t2_routes_to_searxng(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.search import searxng as searxng_mod

    async def _detect() -> str:
        return "http://127.0.0.1:8888"

    monkeypatch.setattr(searxng_mod, "detect_searxng", _detect)
    out = _route(monkeypatch, "t2_searxng")
    assert out["ok"] is True and out["backend"] == "searxng"
    assert out["_resolved"]["kw"]["searxng_url"] == "http://127.0.0.1:8888"


def test_t1_routes_to_keyless_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    out = _route(monkeypatch, "t1_local")
    assert out["ok"] is True and out["backend"] == "keyless"


def test_no_r7_selection_keeps_legacy_routing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Without an explicit R7 tier the legacy path serves (floors to keyless).
    from services.agent_tools.web_search import _web_search

    def _resolve(active_id, **kw):  # noqa: ANN001, ANN003
        return _FakeBackend("keyless") if active_id == "keyless" else None

    monkeypatch.setattr(registry, "resolve", _resolve)
    out = _run(_web_search({"query": "spy etf flows"}))
    assert out["ok"] is True and out["backend"] == "keyless"
    assert "metadata" not in out
