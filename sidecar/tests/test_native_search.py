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
    PROVIDER_LEVEL_NATIVE_SEARCH,
    SUPPORTS_NATIVE_SEARCH,
    anthropic_web_search_tool,
    normalize_anthropic,
    normalize_gemini,
    normalize_openai,
    normalize_xai,
    openrouter_web_search_tool,
)
from services.llm.openai import OpenAIProvider

# ---------------------------------------------------------------------------
# SUPPORTS_NATIVE_SEARCH
# ---------------------------------------------------------------------------


def test_supports_native_search_set() -> None:
    # Four native-search providers plus OpenRouter (WS5), whose native search
    # is gated PER-MODEL by the runtime, not by mere membership. xAI retired
    # Live Search (410, R15-LEAD-008), so it has no native rung.
    assert SUPPORTS_NATIVE_SEARCH == {
        "anthropic",
        "openai",
        "gemini",
        "groq",
        "openrouter",
    }
    # DeepSeek + Ollama explicitly excluded (no native search at all).
    assert "deepseek" not in SUPPORTS_NATIVE_SEARCH
    assert "ollama" not in SUPPORTS_NATIVE_SEARCH


def test_provider_level_native_search_excludes_openrouter() -> None:
    # OpenRouter is a broker: native search is per-MODEL, so it is NOT in the
    # provider-level set. Gemini and Groq are per-model too (R15-AGENT-005).
    assert PROVIDER_LEVEL_NATIVE_SEARCH == {"anthropic"}
    # OpenAI is per-MODEL too (chat-completions search is *-search-preview only).
    assert "openai" not in PROVIDER_LEVEL_NATIVE_SEARCH
    assert "openrouter" not in PROVIDER_LEVEL_NATIVE_SEARCH


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
async def test_openai_injects_web_search_options(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _patch_openai(monkeypatch)
    provider = OpenAIProvider(provider_id="openai")
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="gpt-4o-search-preview",
            api_key="sk-test",
            web_search=True,
        )
    )
    last_kwargs = state["last"].chat.completions.last_kwargs
    # Chat-completions takes the ``web_search_options`` param, never a tools entry.
    assert last_kwargs["web_search_options"] == {}
    assert {"type": "web_search"} not in last_kwargs.get("tools", [])
    assert "web_search" not in last_kwargs
    assert "search_parameters" not in last_kwargs.get("extra_body", {})


@pytest.mark.asyncio
async def test_openai_web_search_noops_on_non_search_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression: a ``{"type": "web_search"}`` tools entry 400s on every model
    # but the *-search-preview ones ("Supported values are: 'function' and
    # 'custom'"), so a normal model must send neither the tool nor the param.
    state = _patch_openai(monkeypatch)
    provider = OpenAIProvider(provider_id="openai")
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="gpt-5.6-luna",
            api_key="sk-test",
            web_search=True,
        )
    )
    last_kwargs = state["last"].chat.completions.last_kwargs
    assert "web_search_options" not in last_kwargs
    assert {"type": "web_search"} not in last_kwargs.get("tools", [])
    assert "web_search" not in last_kwargs


@pytest.mark.asyncio
async def test_xai_sends_no_search_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    # R15-LEAD-008: xAI answers ``search_parameters`` (Live Search) with 410, so
    # even a stray web_search=True must not put it on the request.
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
    assert "search_parameters" not in last_kwargs.get("extra_body", {})
    assert "search_parameters" not in last_kwargs
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
    # DeepSeek still gets no web-search tool; extra_body may be absent entirely
    # (no OpenRouter provider routing for deepseek).
    assert "extra_body" not in last_kwargs
    # No leaked kwargs either.
    assert "web_search" not in last_kwargs
    assert "web_search_max_uses" not in last_kwargs


def test_openrouter_web_search_tool_shape() -> None:
    # WS5: OpenRouter rides its own tool type so the upstream model's native
    # server-side search fires (citations come back as OpenAI url_citation
    # annotations → normalize_openai handles them unchanged).
    assert openrouter_web_search_tool() == {"type": "openrouter:web_search"}


@pytest.mark.asyncio
async def test_openrouter_injects_web_search_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _patch_openai(monkeypatch)
    # OpenRouter rides OpenAIProvider with provider_id="openrouter".
    provider = OpenAIProvider(base_url="https://openrouter.ai/api/v1", provider_id="openrouter")
    await _drain(
        provider.stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="anthropic/claude-opus-4-8",
            api_key="sk-test",
            web_search=True,
        )
    )
    last_kwargs = state["last"].chat.completions.last_kwargs
    # The OpenRouter-specific tool type rides the SAME tools array, NOT a
    # search_parameters block (that is xAI's shape).
    assert {"type": "openrouter:web_search"} in last_kwargs["tools"]
    assert "search_parameters" not in last_kwargs.get("extra_body", {})
    # The kwarg must be consumed, never forwarded to the SDK.
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


# ---------------------------------------------------------------------------
# R9 Track A interface — detection + the cross-verify invocation channel
# ---------------------------------------------------------------------------


def test_native_search_available_is_the_one_detection_truth() -> None:
    from services.llm.native_search import native_search_available

    # The provider-level provider always qualifies, hint or not.
    assert native_search_available("anthropic") is True
    assert native_search_available("anthropic", "none") is True
    # xAI retired Live Search (R15-LEAD-008): no native rung on any model.
    assert native_search_available("xai", None, "grok-4") is False
    # OpenAI is per-model: only the *-search-preview models take web_search_options.
    assert native_search_available("openai", None, "gpt-4o-search-preview") is True
    assert native_search_available("openai", None, "gpt-4.1-mini") is False
    # OpenRouter is per-model: only the "native" capability rides.
    assert native_search_available("openrouter", "native") is True
    assert native_search_available("openrouter", "NATIVE ") is True
    assert native_search_available("openrouter", "plugin") is False
    assert native_search_available("openrouter", None) is False
    # No native rung at all.
    assert native_search_available("deepseek", "native") is False
    assert native_search_available("ollama") is False


def test_runtime_gate_delegates_to_the_same_truth() -> None:
    # The agent runtime's injection gate and this interface must be ONE
    # function — Team B's cross-verify and the loop can never disagree.
    from services import agent_runtime
    from services.llm.native_search import native_search_available

    for prov, hint in (("anthropic", None), ("openrouter", "native"), ("openrouter", "plugin")):
        assert agent_runtime._native_search_enabled(prov, hint) == native_search_available(
            prov, hint
        )


async def _request_carries_native_search(
    monkeypatch: pytest.MonkeyPatch, provider_id: str, model: str
) -> bool:
    """Drive the real adapter as an agent round (function tools + web_search)
    and report whether the captured request carries a native-search param."""
    from services.llm import get_provider

    anth = _patch_anthropic(monkeypatch)
    oai = _patch_openai(monkeypatch)
    gem = _patch_gemini(monkeypatch)
    await _drain(
        get_provider(provider_id).stream_chat(  # type: ignore[arg-type]
            messages=[LLMMessage(role="user", content="latest news on RELIANCE")],
            model=model,
            api_key="sk-test",
            tool_ids=["price_data"],
            web_search=True,
        )
    )
    if provider_id == "anthropic":
        tools = anth.messages.last_kwargs["tools"]  # type: ignore[index]
        return any(t.get("type") == ANTHROPIC_WEB_SEARCH_TYPE for t in tools)
    if provider_id == "gemini":
        return {"google_search": {}} in gem.aio.models.last_call["config"]["tools"]  # type: ignore[index]
    if provider_id == "groq":
        # Compound searches server-side on its own; the model id is the switch.
        return "compound" in model
    sent = oai["last"].chat.completions.last_kwargs
    return (
        "web_search_options" in sent
        or "search_parameters" in sent.get("extra_body", {})
        or {"type": "openrouter:web_search"} in sent.get("tools", [])
    )


@pytest.mark.asyncio
async def test_every_registry_default_model_keeps_a_search_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R15-AGENT-005: when the gate says "native", the runtime drops the local
    # web_search tool, so the adapter's request must then carry native search;
    # otherwise web_search stays in tool_ids. Either way the agent can search.
    from services import agent_runtime, model_registry

    for provider_id in model_registry.provider_ids():
        model = model_registry.default_model_for(provider_id)
        if agent_runtime._native_search_enabled(provider_id, None, model):
            assert await _request_carries_native_search(monkeypatch, provider_id, model), (
                provider_id,
                model,
            )
    # The registry defaults that have no native search alongside function tools.
    assert agent_runtime._native_search_enabled("gemini", None, "gemini-2.5-pro") is False
    assert agent_runtime._native_search_enabled("groq", None, "llama-3.3-70b-versatile") is False


@pytest.mark.asyncio
async def test_gemini_3_and_groq_compound_ride_native_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import agent_runtime

    assert agent_runtime._native_search_enabled("gemini", None, "gemini-3-pro-preview") is True
    assert await _request_carries_native_search(monkeypatch, "gemini", "gemini-3-pro-preview")
    assert agent_runtime._native_search_enabled("gemini", None, "gemini-2.5-flash") is False
    assert agent_runtime._native_search_enabled("groq", None, "groq/compound-mini") is True
    assert agent_runtime._native_search_enabled("groq", None, "llama-3.1-8b-instant") is False


@pytest.mark.asyncio
async def test_native_search_oneshot_keeps_gemini_25_grounding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The cross-verify channel sends no function tools, so Gemini 2.5 still
    # grounds on google_search there.
    from services.llm.native_search import native_search_oneshot

    client = _patch_gemini(monkeypatch)
    out = await native_search_oneshot("gemini", "gemini-2.5-pro", "sk-test", "q")
    assert out["reason"] == "empty"  # the fake stream returns no text
    assert {"google_search": {}} in client.aio.models.last_call["config"]["tools"]  # type: ignore[index]


class _OneshotProvider:
    """Stub adapter for the invocation channel — records kwargs, streams text."""

    def __init__(self, parts: list[str] | None = None, error: bool = False) -> None:
        self.parts = parts if parts is not None else ["grounded ", "answer"]
        self.error = error
        self.captured: dict[str, Any] | None = None

    def stream_chat(self, *, messages, model, api_key=None, **kwargs):  # noqa: ANN001, ANN003, ANN201
        self.captured = {"messages": messages, "model": model, "api_key": api_key, **kwargs}

        async def _gen() -> AsyncIterator[Any]:
            if self.error:
                raise RuntimeError("adapter blew up")
            for part in self.parts:
                from models.llm import LLMDeltaEvent

                yield LLMDeltaEvent(text=part)
            from models.llm import LLMDoneEvent

            yield LLMDoneEvent()

        return _gen()


@pytest.mark.asyncio
async def test_native_search_oneshot_grounds_and_returns_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import services.llm as llm_pkg
    from services.llm.native_search import native_search_oneshot

    provider = _OneshotProvider()
    monkeypatch.setattr(llm_pkg, "get_provider", lambda *_a, **_k: provider)

    out = await native_search_oneshot("openai", "gpt-4o-search-preview", "sk-test", "nvda revenue?")
    assert out["ok"] is True
    assert out["text"] == "grounded answer"
    assert isinstance(out["citations"], list)
    # The adapter call MUST carry the native-search opt-in.
    assert provider.captured is not None
    assert provider.captured["web_search"] is True
    assert provider.captured["web_search_max_uses"] == 3


@pytest.mark.asyncio
async def test_native_search_oneshot_honest_on_unavailable_pair() -> None:
    from services.llm.native_search import native_search_oneshot

    out = await native_search_oneshot("deepseek", "deepseek-v4-flash", "sk", "q")
    assert out == {"ok": False, "reason": "unavailable", "text": "", "citations": []}
    out = await native_search_oneshot("openrouter", "some/model", "sk", "q")
    assert out["ok"] is False and out["reason"] == "unavailable"
    # OpenAI is per-model too: a non-search-preview model has no native rung.
    out = await native_search_oneshot("openai", "gpt-5.6-luna", "sk", "q")
    assert out["ok"] is False and out["reason"] == "unavailable"


@pytest.mark.asyncio
async def test_native_search_oneshot_never_picks_xai() -> None:
    # R15-LEAD-008: the cross-verify channel must not route to xAI's retired
    # Live Search (410); it reports the pair unavailable instead.
    from services.llm.native_search import native_search_oneshot

    out = await native_search_oneshot("xai", "grok-4", "sk", "q")
    assert out == {"ok": False, "reason": "unavailable", "text": "", "citations": []}


@pytest.mark.asyncio
async def test_native_search_oneshot_openrouter_gated_per_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import services.llm as llm_pkg
    from services.llm.native_search import native_search_oneshot

    provider = _OneshotProvider()
    monkeypatch.setattr(llm_pkg, "get_provider", lambda *_a, **_k: provider)
    out = await native_search_oneshot(
        "openrouter", "perplexity/sonar", "sk", "q", model_web_search="native"
    )
    assert out["ok"] is True


@pytest.mark.asyncio
async def test_native_search_oneshot_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.llm as llm_pkg
    from services.llm.native_search import native_search_oneshot

    provider = _OneshotProvider(error=True)
    monkeypatch.setattr(llm_pkg, "get_provider", lambda *_a, **_k: provider)
    out = await native_search_oneshot("openai", "gpt-4o-search-preview", "sk", "q")
    assert out["ok"] is False and out["reason"] == "error"

    provider = _OneshotProvider(parts=[])
    monkeypatch.setattr(llm_pkg, "get_provider", lambda *_a, **_k: provider)
    out = await native_search_oneshot("openai", "gpt-4o-search-preview", "sk", "q")
    assert out["ok"] is False and out["reason"] == "empty"


# ---------------------------------------------------------------------------
# Native searches are counted, priced and capped per run (R15-AGENT-049)
# ---------------------------------------------------------------------------


def _chunk(*, delta: Any = None, finish: str | None = None, usage: Any = None) -> Any:
    from types import SimpleNamespace

    choices = [SimpleNamespace(delta=delta, finish_reason=finish)] if delta or finish else []
    return SimpleNamespace(choices=choices, usage=usage)


def _usage(searches: int | None = None) -> Any:
    from types import SimpleNamespace

    server = {"web_search_requests": searches} if searches is not None else None
    return SimpleNamespace(prompt_tokens=100, completion_tokens=10, server_tool_use=server)


async def _aiter(items: list[Any]) -> AsyncIterator[Any]:
    for item in items:
        yield item


class _ScriptedCompletions:
    """Each ``create`` call streams the next scripted round; records its kwargs."""

    def __init__(self, rounds: list[list[Any]]) -> None:
        self.rounds = rounds
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> AsyncIterator[Any]:
        self.calls.append(kwargs)
        return _aiter(self.rounds[len(self.calls) - 1])


def _tool_round(searches: int) -> list[Any]:
    from types import SimpleNamespace

    call = SimpleNamespace(
        index=0,
        id="c",
        function=SimpleNamespace(name="price_data", arguments='{"symbol": "SPY"}'),
    )
    return [
        _chunk(delta=SimpleNamespace(content=None, tool_calls=[call]), finish="tool_calls"),
        _chunk(usage=_usage(searches)),
    ]


def _answer_round() -> list[Any]:
    from types import SimpleNamespace

    return [
        _chunk(delta=SimpleNamespace(content="SPY is up."), finish="stop"),
        _chunk(usage=_usage(0)),
    ]


@pytest.mark.asyncio
async def test_openrouter_native_searches_are_capped_and_priced_per_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Class pin (the count was authored on the OpenAI provider): OpenRouter
    rounds reporting 3 + 3 native searches reach the run cap of 5, so the next
    round carries no native search, and the turn's spend prices the 6."""
    from types import SimpleNamespace

    from models.llm import LLMDoneEvent, LLMUsage
    from services import agent_runtime, budget_guard

    completions = _ScriptedCompletions([_tool_round(3), _tool_round(3), _answer_round()])
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: client)
    provider = OpenAIProvider(base_url="https://openrouter.ai/api/v1", provider_id="openrouter")
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)

    async def _dispatch(_call: Any, _local: Any = None) -> AsyncIterator[Any]:
        yield agent_runtime._ToolDone('{"ok": true, "price": 1}')

    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _dispatch)
    agent_runtime.reload()
    model = "anthropic/claude-opus-4-8"
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="what is SPY doing today",
            provider="openrouter",
            model=model,
            api_key="sk-test",
            mode="edit",
            options={"modelWebSearch": "native"},
        )
    ]

    native = [{"type": "openrouter:web_search"} in c.get("tools", []) for c in completions.calls]
    assert native == [True, True, False]
    assert all("web_search_max_uses" not in c for c in completions.calls)
    [done] = [e for e in events if isinstance(e, LLMDoneEvent)]
    rounds = [LLMUsage(input_tokens=100, output_tokens=10, web_search_requests=n) for n in (3, 3)]
    rounds.append(LLMUsage(input_tokens=100, output_tokens=10))
    expected = sum(budget_guard.spend_usd("openrouter", model, u) or 0.0 for u in rounds)
    assert done.spend_usd == pytest.approx(expected)
    assert expected > 330 / 1e6 * budget_guard.price_per_million("openrouter", model)


@pytest.mark.asyncio
async def test_an_openai_search_preview_round_counts_one_search(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenAI reports no search count; a search-preview request is one search."""
    from types import SimpleNamespace

    from models.llm import LLMDoneEvent

    completions = _ScriptedCompletions([_answer_round()])
    completions.rounds[0][1] = _chunk(usage=_usage(None))
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: client)
    events = [
        e
        async for e in OpenAIProvider(provider_id="openai").stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="gpt-4o-search-preview",
            api_key="sk-test",
            web_search=True,
        )
    ]
    [done] = [e for e in events if isinstance(e, LLMDoneEvent)]
    assert done.usage is not None and done.usage.web_search_requests == 1


@pytest.mark.asyncio
async def test_a_gemini_round_counts_its_grounded_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    from models.llm import LLMDoneEvent

    grounding = SimpleNamespace(web_search_queries=["spy news", "spy price", "spy news"])
    candidate = SimpleNamespace(content=None, grounding_metadata=grounding, finish_reason="STOP")
    client = _patch_gemini(monkeypatch)

    async def _stream(**kwargs: Any) -> AsyncIterator[Any]:
        client.aio.models.last_call = kwargs
        return _aiter([SimpleNamespace(candidates=[candidate], usage_metadata=None)])

    monkeypatch.setattr(client.aio.models, "generate_content_stream", _stream)
    events = [
        e
        async for e in GeminiProvider().stream_chat(
            messages=[LLMMessage(role="user", content="news")],
            model="gemini-3-pro",
            api_key="sk-test",
            web_search=True,
        )
    ]
    [done] = [e for e in events if isinstance(e, LLMDoneEvent)]
    assert done.usage is not None and done.usage.web_search_requests == 2


def test_anthropic_usage_reports_native_search_count() -> None:
    """R15-AGENT-049 review pin: Anthropic reports server-side searches on
    ``usage.server_tool_use``; the adapter must carry the count so the runtime
    prices and caps them like every other native-search provider."""
    from types import SimpleNamespace

    from services.llm.anthropic import _usage_from_final

    usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        server_tool_use=SimpleNamespace(web_search_requests=3),
    )
    assert _usage_from_final(SimpleNamespace(usage=usage)).web_search_requests == 3
    bare = SimpleNamespace(input_tokens=1, output_tokens=1)
    assert _usage_from_final(SimpleNamespace(usage=bare)).web_search_requests is None
