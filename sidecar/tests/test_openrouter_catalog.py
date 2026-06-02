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
        "context_length": 128000,
        "supported_parameters": ["tools", "tool_choice"],
        "pricing": {"prompt": "0", "completion": "0"},
    },
    {
        "id": "m/mid-tools",
        "name": "M Mid",
        "context_length": 32000,
        "supported_parameters": ["tools"],
        "pricing": {"prompt": "0.0000005", "completion": "0.0000015"},
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
