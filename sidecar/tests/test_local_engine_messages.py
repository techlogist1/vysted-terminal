"""Provider ``local`` sends at most one system turn, and it is first.

Qwen 3.5's GGUF chat template (and Llama/Gemma/Mistral's) raises "System message
must be at the beginning." on any other system turn, so llama-server 500s every
agent request. Every other provider still sends the runtime's list unchanged.
The wire is faked with an httpx transport under the real OpenAI SDK.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx
import openai
import pytest

from models.llm import LLMMessage
from services.llm import LOCAL_NOTE_PREFIX, OpenAIProvider, get_provider
from services.llm import openai as openai_adapter
from services.local_models import engine

_DONE = (
    'data: {"id":"c","object":"chat.completion.chunk","created":0,"model":"m",'
    '"choices":[{"index":0,"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\n'
    "data: [DONE]\n\n"
)

TOOL_CALL = {"id": "call_1", "name": "get_quote", "input": {"symbol": "AAPL"}}

RUN = [
    LLMMessage(role="system", content="You are Vysted."),
    LLMMessage(role="system", content="Session preamble."),
    LLMMessage(role="system", content="Earlier tools: get_quote."),
    LLMMessage(role="user", content="What is Apple's price?"),
    LLMMessage(role="assistant", content="", metadata={"tool_calls": [TOOL_CALL]}),
    LLMMessage(
        role="tool", content='{"price": 1}', tool_call_id="call_1", metadata={"name": "get_quote"}
    ),
    LLMMessage(role="system", content="Tool rounds are capped; answer now."),
]


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """Every request body the SDK puts on the wire, engine 'up'."""
    bodies: list[dict[str, Any]] = []
    real = openai.AsyncOpenAI

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, text=_DONE, headers={"content-type": "text/event-stream"})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        openai_adapter.openai,
        "AsyncOpenAI",
        lambda **kw: real(http_client=httpx.AsyncClient(transport=transport), **kw),
    )
    engine.set_engine(51234, "qwen3.5-4b")
    yield bodies
    engine.set_engine(None, None)


async def _messages(provider: Any, msgs: list[LLMMessage], sent: list[dict[str, Any]]) -> Any:
    _ = [e async for e in provider.stream_chat(messages=msgs, model="m", api_key="k")]
    return sent[-1]["messages"]


@pytest.mark.asyncio
async def test_local_merges_leading_systems_and_labels_a_mid_run_note(
    sent: list[dict[str, Any]],
) -> None:
    out = await _messages(get_provider("local"), RUN, sent)
    assert [m["role"] for m in out] == ["system", "user", "assistant", "tool", "user"]
    assert out[0]["content"] == "You are Vysted.\n\nSession preamble.\n\nEarlier tools: get_quote."
    assert out[4]["content"] == LOCAL_NOTE_PREFIX + "Tool rounds are capped; answer now."
    # Tool-call and tool-result turns ride through untouched.
    assert out[2]["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_quote", "arguments": '{"symbol": "AAPL"}'},
        }
    ]
    assert out[3] == {"role": "tool", "tool_call_id": "call_1", "content": '{"price": 1}'}


@pytest.mark.asyncio
async def test_local_leaves_a_list_with_no_system_turn_unchanged(
    sent: list[dict[str, Any]],
) -> None:
    msgs = [m for m in RUN if m.role != "system"]
    local = await _messages(get_provider("local"), msgs, sent)
    hosted = await _messages(OpenAIProvider(), msgs, sent)
    assert local == hosted


@pytest.mark.asyncio
async def test_other_providers_still_send_every_system_turn_in_place(
    sent: list[dict[str, Any]],
) -> None:
    out = await _messages(OpenAIProvider(), RUN, sent)
    assert [m["role"] for m in out] == [
        "system",
        "system",
        "system",
        "user",
        "assistant",
        "tool",
        "system",
    ]
    assert out[6]["content"] == "Tool rounds are capped; answer now."
