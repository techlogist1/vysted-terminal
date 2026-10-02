"""LLM adapter-layer pins for the R15 lows (contract/typing/config threading)."""

from __future__ import annotations

import ast
import inspect
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import openai
import pytest

from models.llm import LLMMessage
from services.llm import get_provider
from services.llm.base import LLMProvider

_LLM_DIR = Path(__file__).resolve().parent.parent / "services" / "llm"


def test_stream_chat_abc_is_not_a_coroutine_function() -> None:
    """R15-CODE-PLATFORM-044: every adapter is an async generator and every
    caller does ``async for`` without ``await``, so the ABC must not declare a
    coroutine."""
    assert not inspect.iscoroutinefunction(LLMProvider.stream_chat)


def test_validate_key_has_no_reraise_only_clause() -> None:
    """R15-CODE-AGENT-030: ``except <ProviderError>: raise`` behaves exactly
    like no clause, so no adapter's validate_key may carry one."""
    offenders = []
    for path in sorted(_LLM_DIR.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not (isinstance(node, ast.AsyncFunctionDef) and node.name == "validate_key"):
                continue
            for handler in ast.walk(node):
                if (
                    isinstance(handler, ast.ExceptHandler)
                    and len(handler.body) == 1
                    and isinstance(handler.body[0], ast.Raise)
                    and handler.body[0].exc is None
                ):
                    offenders.append(f"{path.name}:{handler.lineno}")
    assert offenders == []


def test_get_provider_groq_gemini_honour_or_reject_base_url() -> None:
    """R15-CODE-AGENT-020: a base_url handed to get_provider reaches the SDK
    client for groq and gemini instead of being dropped; omitted, the vendor
    default stays."""
    groq_proxy = "https://groq.proxy.internal/openai/v1/"
    gemini_proxy = "https://gemini.proxy.internal/"
    groq_client = get_provider("groq", base_url=groq_proxy)._client("k")
    gemini_client = get_provider("gemini", base_url=gemini_proxy)._client("k")
    assert str(groq_client.base_url) == groq_proxy
    assert gemini_client._api_client._http_options.base_url == gemini_proxy
    assert str(get_provider("groq")._client("k").base_url).startswith("https://api.groq.com")
    default_gemini = get_provider("gemini")._client("k")._api_client._http_options.base_url
    assert default_gemini.startswith("https://generativelanguage.googleapis.com")


@pytest.mark.asyncio
async def test_openrouter_auto_surfaces_served_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-AGENT-075: with ``openrouter/auto`` the chunks name the model that
    answered; the round's usage carries it so the chat and the spend see it."""

    def chunk(**fields: Any) -> SimpleNamespace:
        return SimpleNamespace(model="anthropic/claude-3-opus", usage=None, **fields)

    delta = SimpleNamespace(content="42", tool_calls=None)
    chunks = [
        chunk(choices=[SimpleNamespace(delta=delta, finish_reason="stop")]),
        chunk(choices=[]),
    ]
    chunks[-1].usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20)

    async def create(**_: Any) -> AsyncIterator[Any]:
        async def stream() -> AsyncIterator[Any]:
            for c in chunks:
                yield c

        return stream()

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: client)
    events = [
        e
        async for e in get_provider("openrouter").stream_chat(
            messages=[LLMMessage(role="user", content="value TCS")],
            model="openrouter/auto",
            api_key="sk-or-test",
        )
    ]
    done = events[-1]
    assert done.kind == "done"
    assert done.usage.served_model == "anthropic/claude-3-opus"
    assert done.usage.input_tokens == 100
