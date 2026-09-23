"""Batch 5 (W3): a truncated or empty answer is never finalised as success.

R15-AGENT-026: the three junk shapes the failure inducer drove (a cut socket, a
200 non-SSE body, empty ``choices``) reached the chat as a clean ``done``, and a
``length`` finish was carried but never acted on.
"""

from __future__ import annotations

from typing import Any

import openai
import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage
from services import agent_runtime
from services.llm.openai import OpenAIProvider


class _Script:
    """A provider that replays one scripted round."""

    def __init__(self, *events: Any) -> None:
        self._events = events

    async def stream_chat(self, messages: Any, model: str, api_key: Any = None, **kwargs: Any):
        for event in self._events:
            yield event


async def _drive(monkeypatch: pytest.MonkeyPatch, provider: Any) -> list[Any]:
    agent_runtime.reload()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    return [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot", prompt="What is the price of RELIANCE?", api_key="k", mode="ask"
        )
    ]


def _codes(events: list[Any]) -> list[str | None]:
    return [e.code for e in events if e.kind == "error"]


def _notices(events: list[Any]) -> list[str]:
    return [e.detail for e in events if e.kind == "research_step" and e.step_kind == "notice"]


class _Chunk:
    def __init__(self, text: str | None = None) -> None:
        delta = type("Delta", (), {"content": text, "tool_calls": None})()
        self.choices = (
            [type("Choice", (), {"delta": delta, "finish_reason": None})()] if text else []
        )
        self.usage = None


def _openai_replaying(monkeypatch: pytest.MonkeyPatch, chunks: list[_Chunk]) -> OpenAIProvider:
    async def _iter() -> Any:
        for chunk in chunks:
            yield chunk

    class _Completions:
        async def create(self, **_kwargs: Any) -> Any:
            return _iter()

    class _Client:
        def __init__(self, **_kwargs: Any) -> None:
            self.chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr(openai, "AsyncOpenAI", _Client)
    return OpenAIProvider()


@pytest.mark.asyncio
async def test_openai_stream_cut_mid_answer_is_not_a_clean_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _openai_replaying(monkeypatch, [_Chunk("RELIANCE closed at Rs 1,4")])
    raw = [
        e async for e in provider.stream_chat([LLMMessage(role="user", content="q")], model="junk")
    ]
    assert [e.kind for e in raw] == ["delta"]
    events = await _drive(monkeypatch, provider)
    assert _codes(events) == ["truncated"]
    assert events[-1].kind == "done"


@pytest.mark.parametrize(
    "chunks",
    [[], [_Chunk()]],
    ids=["non-sse-200-body", "empty-choices"],
)
@pytest.mark.asyncio
async def test_openai_zero_output_bodies_become_empty_response(
    monkeypatch: pytest.MonkeyPatch, chunks: list[_Chunk]
) -> None:
    events = await _drive(monkeypatch, _openai_replaying(monkeypatch, chunks))
    assert _codes(events) == ["empty_response"]


@pytest.mark.asyncio
async def test_a_finished_round_with_no_text_and_no_tool_is_an_empty_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = await _drive(monkeypatch, _Script(LLMDoneEvent(finish_reason="stop")))
    assert _codes(events) == ["empty_response"]


@pytest.mark.parametrize("reason", ["max_tokens", "length", "FinishReason.MAX_TOKENS"])
@pytest.mark.asyncio
async def test_length_finish_yields_a_truncation_notice(
    monkeypatch: pytest.MonkeyPatch, reason: str
) -> None:
    # max_tokens is Anthropic's; length (Ollama/Groq/OpenAI) and Gemini's enum
    # spelling are the cases the fix was not written against.
    events = await _drive(
        monkeypatch,
        _Script(LLMDeltaEvent(text="| FY24 | 1,2"), LLMDoneEvent(finish_reason=reason)),
    )
    assert _notices(events) == [agent_runtime._LENGTH_NOTICE]
    assert _codes(events) == []
    assert events[-1].kind == "done"
