"""Tests for the OpenRouter live model catalog fetcher.

No real network call: every request is served by an ``httpx.MockTransport``
injected by monkeypatching the module's ``httpx.AsyncClient`` factory. The
handler asserts the exact endpoint + params + auth header the fetcher issues and
returns canned model rows that exercise the tool-capability marking, the
tool-first sort, the pricing formatter, and the 401→public fallback.
"""

from __future__ import annotations

import httpx
import pytest

from services.llm import openrouter_catalog

_FULL = [
    {
        "id": "z/no-tools",
        "name": "Z No Tools",
        "context_length": 8000,
        "supported_parameters": ["temperature"],
        "pricing": {"prompt": "0.000001", "completion": "0.000002"},
    },
    {
        "id": "a/with-tools",
        "name": "A With Tools",
        # Native server-side web search + structured outputs + reasoning all
        # advertised → web_search == "native" and both metadata flags True.
        "context_length": 128000,
        "supported_parameters": [
            "tools",
            "tool_choice",
            "web_search_options",
            "structured_outputs",
            "reasoning",
        ],
        "pricing": {"prompt": "0", "completion": "0"},
    },
    {
        "id": "m/mid-tools",
        "name": "M Mid",
        # No native search param, but OpenRouter prices a web plugin for it →
        # web_search == "plugin". No structured/reasoning params → both False.
        "context_length": 32000,
        "supported_parameters": ["tools"],
        "pricing": {
            "prompt": "0.0000005",
            "completion": "0.0000015",
            "web_search": "0.004",
        },
    },
]
_TOOL_SUBSET = [row for row in _FULL if "tools" in row["supported_parameters"]]


_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _install(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    def _factory(*_a, **_k):  # noqa: ANN002, ANN003 — drops timeout=, injects transport
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(openrouter_catalog.httpx, "AsyncClient", _factory)


@pytest.mark.asyncio
async def test_with_key_hits_user_scoped_and_marks_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_paths: list[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        assert request.headers.get("authorization") == "Bearer sk-test"
        tools_only = request.url.params.get("supported_parameters") == "tools"
        data = _TOOL_SUBSET if tools_only else _FULL
        return httpx.Response(200, json={"data": data})

    _install(monkeypatch, _handler)
    options = await openrouter_catalog.fetch_openrouter_catalog("sk-test", None)

    # The key routes to the user-scoped endpoint (BYOK-narrowed list).
    assert all(path.endswith("/models/user") for path in seen_paths)
    assert len(options) == 3
    # Tool-capable models sort first; within a group, alphabetical by label.
    assert [o.id for o in options] == ["a/with-tools", "m/mid-tools", "z/no-tools"]
    assert options[0].supports_tools is True
    assert options[-1].supports_tools is False
    # Pricing formatter: free vs per-1M.
    assert options[0].pricing == "free"
    assert options[-1].pricing == "$1.00 / $2.00 per 1M"
    assert options[-1].context_length == 8000


@pytest.mark.asyncio
async def test_without_key_uses_public_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_paths: list[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        assert "authorization" not in request.headers
        tools_only = request.url.params.get("supported_parameters") == "tools"
        return httpx.Response(200, json={"data": _TOOL_SUBSET if tools_only else _FULL})

    _install(monkeypatch, _handler)
    options = await openrouter_catalog.fetch_openrouter_catalog(None, None)

    assert all(path.endswith("/models") for path in seen_paths)
    assert all(not path.endswith("/models/user") for path in seen_paths)
    assert len(options) == 3


@pytest.mark.asyncio
async def test_user_scoped_401_falls_back_to_public(monkeypatch: pytest.MonkeyPatch) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models/user"):
            return httpx.Response(401, json={"error": "no access"})
        return httpx.Response(200, json={"data": _FULL})

    _install(monkeypatch, _handler)
    options = await openrouter_catalog.fetch_openrouter_catalog("sk-bad-for-user", None)
    # Falls back to the public catalog rather than returning nothing.
    assert len(options) == 3


@pytest.mark.asyncio
async def test_total_failure_returns_empty_for_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def _handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    _install(monkeypatch, _handler)
    options = await openrouter_catalog.fetch_openrouter_catalog(None, None)
    # Empty → the router serves the registry known_models fallback.
    assert options == []


@pytest.mark.asyncio
async def test_per_model_capability_flags_derived(monkeypatch: pytest.MonkeyPatch) -> None:
    # WS5: derive web_search (native/plugin/none) + structured-output + reasoning
    # flags per model from supported_parameters / pricing.
    def _handler(request: httpx.Request) -> httpx.Response:
        tools_only = request.url.params.get("supported_parameters") == "tools"
        return httpx.Response(200, json={"data": _TOOL_SUBSET if tools_only else _FULL})

    _install(monkeypatch, _handler)
    options = await openrouter_catalog.fetch_openrouter_catalog(None, None)
    by_id = {o.id: o for o in options}

    # web_search_options advertised → native; structured_outputs + reasoning True.
    native = by_id["a/with-tools"]
    assert native.web_search == "native"
    assert native.supports_structured_outputs is True
    assert native.supports_reasoning is True

    # No native search param but a priced web plugin → plugin; no structured/
    # reasoning params → both False.
    plugin = by_id["m/mid-tools"]
    assert plugin.web_search == "plugin"
    assert plugin.supports_structured_outputs is False
    assert plugin.supports_reasoning is False

    # Neither native param nor priced plugin → none.
    none_model = by_id["z/no-tools"]
    assert none_model.web_search == "none"
    assert none_model.supports_structured_outputs is False
    assert none_model.supports_reasoning is False


def test_derive_web_search_zero_priced_plugin_is_not_plugin() -> None:
    # A `web_search` price of the string "0" is truthy but is NOT a real billed
    # plugin — it must classify as "none", not "plugin" (parity with the numeric
    # _format_pricing parse). A native param still wins regardless of pricing.
    assert openrouter_catalog._derive_web_search(frozenset(), {"web_search": "0"}) == "none"
    assert openrouter_catalog._derive_web_search(frozenset(), {"web_search": 0}) == "none"
    assert openrouter_catalog._derive_web_search(frozenset(), {"web_search": "0.004"}) == "plugin"
    assert openrouter_catalog._derive_web_search(frozenset(), {}) == "none"
    # A bare `web_search` supported-parameters token (not just web_search_options)
    # is native — OpenRouter's param naming is inconsistent.
    assert openrouter_catalog._derive_web_search(frozenset({"web_search"}), {}) == "native"


@pytest.mark.asyncio
async def test_missing_supported_parameters_leaves_metadata_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A model with no supported_parameters array: metadata flags stay None
    # (unknown), but web_search still resolves ("none" without a priced plugin,
    # "plugin" when pricing carries a web_search row).
    rows = [
        {"id": "x/bare", "name": "Bare", "pricing": {"prompt": "0", "completion": "0"}},
        {
            "id": "y/bare-plugin",
            "name": "Bare Plugin",
            "pricing": {"prompt": "0", "completion": "0", "web_search": "0.004"},
        },
    ]

    def _handler(request: httpx.Request) -> httpx.Response:
        # Tool filter returns nothing so supports_tools also exercises the None path.
        tools_only = request.url.params.get("supported_parameters") == "tools"
        return httpx.Response(200, json={"data": [] if tools_only else rows})

    _install(monkeypatch, _handler)
    options = await openrouter_catalog.fetch_openrouter_catalog(None, None)
    by_id = {o.id: o for o in options}

    bare = by_id["x/bare"]
    assert bare.web_search == "none"
    assert bare.supports_structured_outputs is None
    assert bare.supports_reasoning is None
    assert by_id["y/bare-plugin"].web_search == "plugin"


@pytest.mark.asyncio
async def test_tool_filter_failure_falls_back_to_array_marking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        # The ?supported_parameters=tools call fails; the unfiltered call works.
        if request.url.params.get("supported_parameters") == "tools":
            return httpx.Response(500, json={"error": "filter down"})
        return httpx.Response(200, json={"data": _FULL})

    _install(monkeypatch, _handler)
    options = await openrouter_catalog.fetch_openrouter_catalog(None, None)
    by_id = {o.id: o for o in options}
    # Marking falls back to each model's supported_parameters array.
    assert by_id["a/with-tools"].supports_tools is True
    assert by_id["z/no-tools"].supports_tools is False
