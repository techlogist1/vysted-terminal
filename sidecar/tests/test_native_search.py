"""Native server-side web search — normalizer + per-adapter injection tests.

Two concerns, no live API calls:

1. **Citation normalizers** (``normalize_anthropic`` / ``_openai`` / ``_gemini`` /
   ``_xai``) flatten each provider's distinct citation shape to the common
   ``{url, title, excerpt}`` record. Tested against representative fake payloads
   plus defensive (missing-field) cases.
2. **Adapter request injection** — with ``web_search=True`` each adapter must add
   its provider's native search affordance to the outgoing request; with the
   kwarg on an *unsupported* provider (DeepSeek via the OpenAI base_url path) it
   must no-op gracefully. Each SDK client is mocked so the request kwargs are
   captured without a network call.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import anthropic
import openai
import pytest
from google import genai

from models.llm import LLMMessage
from services.llm.anthropic import AnthropicProvider
from services.llm.gemini import GeminiProvider
from services.llm.native_search import (
    ANTHROPIC_WEB_SEARCH_TYPE,
    SUPPORTS_NATIVE_SEARCH,
    anthropic_web_search_tool,
    normalize_anthropic,
    normalize_gemini,
    normalize_openai,
    normalize_xai,
)
from services.llm.openai import OpenAIProvider

# ---------------------------------------------------------------------------
# SUPPORTS_NATIVE_SEARCH
# ---------------------------------------------------------------------------


def test_supports_native_search_set() -> None:
    assert SUPPORTS_NATIVE_SEARCH == {"anthropic", "openai", "gemini", "groq", "xai"}
    # DeepSeek + Ollama explicitly excluded (no native search).
    assert "deepseek" not in SUPPORTS_NATIVE_SEARCH
    assert "ollama" not in SUPPORTS_NATIVE_SEARCH


# ---------------------------------------------------------------------------
# Citation normalizers
# ---------------------------------------------------------------------------


def test_normalize_anthropic_text_block_citations() -> None:
    # Anthropic threads citations on a text block as ``url`` + ``title`` +
    # ``cited_text``.
    blocks = [
        {
            "type": "text",
            "citations": [
                {
                    "url": "https://example.com/a",
                    "title": "Alpha",
                    "cited_text": "alpha excerpt",
                },
                {
                    "url": "https://example.com/b",
                    "title": "Beta",
                    "cited_text": "beta excerpt",
                },
            ],
        }
    ]
    out = normalize_anthropic(blocks)
    assert out == [
        {"url": "https://example.com/a", "title": "Alpha", "excerpt": "alpha excerpt"},
        {"url": "https://example.com/b", "title": "Beta", "excerpt": "beta excerpt"},
    ]


def test_normalize_anthropic_flat_citation_objects() -> None:
    # Accepts a bare list of citation objects too (not wrapped in a text block).
    blocks = [{"url": "https://x.test", "title": "X", "cited_text": "e"}]
    assert normalize_anthropic(blocks) == [{"url": "https://x.test", "title": "X", "excerpt": "e"}]


def test_normalize_anthropic_skips_missing_url() -> None:
    blocks = [
        {"citations": [{"title": "no url", "cited_text": "x"}]},
        {"citations": [{"url": "https://ok.test", "title": "ok", "cited_text": "y"}]},
    ]
    out = normalize_anthropic(blocks)
    assert out == [{"url": "https://ok.test", "title": "ok", "excerpt": "y"}]


def test_normalize_anthropic_empty() -> None:
    assert normalize_anthropic(None) == []
    assert normalize_anthropic([]) == []


def test_normalize_openai_url_citation_annotations() -> None:
    annotations = [
        {
            "type": "url_citation",
            "url": "https://news.test/1",
            "title": "Headline",
            "snippet": "the excerpt",
        },
        # A non-citation annotation type is ignored.
        {"type": "file_citation", "url": "ignored"},
    ]
    out = normalize_openai(annotations)
    assert out == [{"url": "https://news.test/1", "title": "Headline", "excerpt": "the excerpt"}]


def test_normalize_openai_nested_url_citation() -> None:
    # Newer SDK shape nests fields under ``url_citation``.
    annotations = [
        {
            "type": "url_citation",
            "url_citation": {"url": "https://n.test", "title": "T"},
        }
    ]
    assert normalize_openai(annotations) == [{"url": "https://n.test", "title": "T", "excerpt": ""}]


def test_normalize_openai_skips_missing_url() -> None:
    annotations = [{"type": "url_citation", "title": "no url"}]
    assert normalize_openai(annotations) == []


def test_normalize_gemini_grounding_chunks_camelcase() -> None:
    grounding_metadata = {
        "groundingChunks": [
            {"web": {"uri": "https://g.test/1", "title": "G1"}},
            {"web": {"uri": "https://g.test/2", "title": "G2"}},
            {"retrievedContext": {"uri": "ignored"}},  # not a web chunk
        ]
    }
    out = normalize_gemini(grounding_metadata)
    assert out == [
        {"url": "https://g.test/1", "title": "G1", "excerpt": ""},
        {"url": "https://g.test/2", "title": "G2", "excerpt": ""},
    ]


def test_normalize_gemini_grounding_chunks_snake_case() -> None:
    # The SDK model exposes ``grounding_chunks`` (snake_case).
    grounding_metadata = {"grounding_chunks": [{"web": {"uri": "https://s.test", "title": "S"}}]}
    assert normalize_gemini(grounding_metadata) == [
        {"url": "https://s.test", "title": "S", "excerpt": ""}
    ]


def test_normalize_gemini_empty() -> None:
    assert normalize_gemini(None) == []
    assert normalize_gemini({}) == []
    assert normalize_gemini({"groundingChunks": [{"web": {}}]}) == []


def test_normalize_xai_citation_strings() -> None:
    # xAI historically returns a bare array of url strings.
    citations = ["https://x.test/a", "https://x.test/b"]
    out = normalize_xai(citations)
    assert out == [
        {"url": "https://x.test/a", "title": "", "excerpt": ""},
        {"url": "https://x.test/b", "title": "", "excerpt": ""},
    ]


def test_normalize_xai_citation_objects() -> None:
    citations = [{"url": "https://x.test/c", "title": "C", "snippet": "ex"}]
    assert normalize_xai(citations) == [{"url": "https://x.test/c", "title": "C", "excerpt": "ex"}]


def test_normalize_xai_empty_and_bad() -> None:
    assert normalize_xai(None) == []
    assert normalize_xai([]) == []
    assert normalize_xai([""]) == []  # empty string -> skipped


# ---------------------------------------------------------------------------
# anthropic_web_search_tool helper
# ---------------------------------------------------------------------------


def test_anthropic_web_search_tool_shape() -> None:
    tool = anthropic_web_search_tool(max_uses=3)
    assert tool == {
        "type": ANTHROPIC_WEB_SEARCH_TYPE,
        "name": "web_search",
        "max_uses": 3,
    }


# ---------------------------------------------------------------------------
# Adapter request injection — Anthropic
# ---------------------------------------------------------------------------


class _AnthFinal:
    stop_reason = "end_turn"
    usage = None


class _AnthStream:
    def __init__(self) -> None:
        self._events: list[Any] = []

    async def __aenter__(self) -> _AnthStream:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    def __aiter__(self) -> _AnthStream:
        self._iter = iter(self._events)
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def get_final_message(self) -> Any:
        return _AnthFinal()


class _AnthMessages:
    def __init__(self) -> None:
        self.last_kwargs: dict[str, Any] | None = None

    def stream(self, **kwargs: Any) -> _AnthStream:
        self.last_kwargs = kwargs
        return _AnthStream()


class _AnthClient:
    def __init__(self, **_: Any) -> None:
        self.messages = _AnthMessages()


def _patch_anthropic(monkeypatch: pytest.MonkeyPatch) -> _AnthClient:
    client = _AnthClient()
    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **_: client)
    return client


async def _drain(stream: AsyncIterator[Any]) -> list[Any]:
    return [event async for event in stream]


@pytest.mark.asyncio
async def test_anthropic_injects_web_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _patch_anthropic(monkeypatch)
    provider = AnthropicProvider()
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="claude-opus-4-8",
            api_key="sk-test",
            web_search=True,
            web_search_max_uses=2,
        )
    )
    tools = client.messages.last_kwargs["tools"]  # type: ignore[index]
    assert {
        "type": ANTHROPIC_WEB_SEARCH_TYPE,
        "name": "web_search",
        "max_uses": 2,
    } in tools
    # The kwarg must be consumed, never forwarded to the SDK.
    assert "web_search" not in client.messages.last_kwargs  # type: ignore[operator]
    assert "web_search_max_uses" not in client.messages.last_kwargs  # type: ignore[operator]


@pytest.mark.asyncio
async def test_anthropic_no_web_search_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _patch_anthropic(monkeypatch)
    provider = AnthropicProvider()
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="hi")],
            model="claude-opus-4-8",
            api_key="sk-test",
        )
    )
    assert "tools" not in client.messages.last_kwargs  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Adapter request injection — OpenAI / xAI / DeepSeek
# ---------------------------------------------------------------------------


async def _empty_iter() -> AsyncIterator[Any]:
    return
    yield  # pragma: no cover - makes this an async generator


class _OAICompletions:
    def __init__(self) -> None:
        self.last_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> AsyncIterator[Any]:
        self.last_kwargs = kwargs
        return _empty_iter()


class _OAIChat:
    def __init__(self) -> None:
        self.completions = _OAICompletions()


class _OAIClient:
    def __init__(self, **kwargs: Any) -> None:
        self.base_url = kwargs.get("base_url")
        self.chat = _OAIChat()


def _patch_openai(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"last": None}

    def factory(**kwargs: Any) -> _OAIClient:
        client = _OAIClient(**kwargs)
        state["last"] = client
        return client

    monkeypatch.setattr(openai, "AsyncOpenAI", factory)
    return state


@pytest.mark.asyncio
async def test_openai_injects_web_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _patch_openai(monkeypatch)
    provider = OpenAIProvider(provider_id="openai")
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="gpt-4.1-mini",
            api_key="sk-test",
            web_search=True,
        )
    )
    last_kwargs = state["last"].chat.completions.last_kwargs
    assert {"type": "web_search"} in last_kwargs["tools"]
    assert "web_search" not in last_kwargs
    assert "search_parameters" not in last_kwargs.get("extra_body", {})


@pytest.mark.asyncio
async def test_xai_injects_search_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _patch_openai(monkeypatch)
    # xAI rides OpenAIProvider with provider_id="xai" + the x.ai base_url.
    provider = OpenAIProvider(base_url="https://api.x.ai/v1", provider_id="xai")
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="grok-4",
            api_key="sk-test",
            web_search=True,
        )
    )
    last_kwargs = state["last"].chat.completions.last_kwargs
    # Live Search rides ``search_parameters`` in extra_body, NOT a tools entry.
    assert "search_parameters" in last_kwargs["extra_body"]
    assert last_kwargs["extra_body"]["search_parameters"]["mode"] == "auto"
    assert "tools" not in last_kwargs


@pytest.mark.asyncio
async def test_deepseek_web_search_noops(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _patch_openai(monkeypatch)
    # DeepSeek has no native search — web_search=True must no-op gracefully.
    provider = OpenAIProvider(base_url="https://api.deepseek.com", provider_id="deepseek")
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="deepseek-chat",
            api_key="sk-test",
            web_search=True,
        )
    )
    last_kwargs = state["last"].chat.completions.last_kwargs
    assert "tools" not in last_kwargs
    assert "extra_body" not in last_kwargs
    # No leaked kwargs either.
    assert "web_search" not in last_kwargs
    assert "web_search_max_uses" not in last_kwargs


# ---------------------------------------------------------------------------
# Adapter request injection — Gemini
# ---------------------------------------------------------------------------


class _GeminiAioModels:
    def __init__(self) -> None:
        self.last_call: dict[str, Any] | None = None

    async def generate_content_stream(self, **kwargs: Any) -> AsyncIterator[Any]:
        self.last_call = kwargs
        return _empty_iter()


class _GeminiAio:
    def __init__(self) -> None:
        self.models = _GeminiAioModels()


class _GeminiClient:
    def __init__(self, **_: Any) -> None:
        self.aio = _GeminiAio()


def _patch_gemini(monkeypatch: pytest.MonkeyPatch) -> _GeminiClient:
    client = _GeminiClient()
    monkeypatch.setattr(genai, "Client", lambda **_: client)
    return client


@pytest.mark.asyncio
async def test_gemini_injects_google_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _patch_gemini(monkeypatch)
    provider = GeminiProvider()
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="gemini-2.5-flash",
            api_key="sk-test",
            web_search=True,
        )
    )
    config = client.aio.models.last_call["config"]  # type: ignore[index]
    assert {"google_search": {}} in config["tools"]
    # web_search must not leak as a forwarded kwarg to the SDK.
    assert "web_search" not in client.aio.models.last_call  # type: ignore[operator]
    assert "web_search_max_uses" not in client.aio.models.last_call  # type: ignore[operator]


@pytest.mark.asyncio
async def test_gemini_no_search_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _patch_gemini(monkeypatch)
    provider = GeminiProvider()
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="hi")],
            model="gemini-2.5-flash",
            api_key="sk-test",
        )
    )
    config = client.aio.models.last_call["config"]  # type: ignore[index]
    # No system, no tools -> config is None.
    assert config is None or "tools" not in config
