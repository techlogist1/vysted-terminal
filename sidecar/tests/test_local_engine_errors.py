"""Provider ``local`` (the bundled llama-server) fails in plain words (R16 W2).

The engine runs on this computer, so a refused or cut connection is the engine
stopping, never the user's network; and a turn with no engine says how to start
it. The wire is faked with an httpx transport under the real OpenAI SDK.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from models.llm import LLMDeltaEvent, LLMErrorEvent, LLMMessage, LLMThinkingEvent
from services.errors import humanize
from services.llm import LocalEngineNotRunning, get_provider
from services.llm import openai as openai_adapter
from services.local_models import engine

NOT_RUNNING = "The on-computer model isn't running. Start it from Settings → Models."
STOPPED = (
    "The on-computer model stopped while answering. It restarts on its own — "
    "send your question again in a few seconds."
)


def _chunk(delta: dict[str, Any], finish: str | None = None) -> bytes:
    body = {
        "id": "c",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "/Users/someone/models/m.gguf",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(body)}\n\n".encode()


class _Body(httpx.AsyncByteStream):
    """An SSE body that yields ``parts`` then, optionally, dies like a killed engine."""

    def __init__(self, parts: list[bytes], die: bool) -> None:
        self._parts = parts
        self._die = die

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for part in self._parts:
            yield part
        if self._die:
            raise httpx.RemoteProtocolError("peer closed connection without sending complete body")


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> Callable[[Callable[[httpx.Request], Any]], None]:
    """Route the adapter's SDK client through ``handler`` with the engine 'up'."""
    real = openai.AsyncOpenAI
    monkeypatch.setattr(openai_adapter, "_MAX_TRANSPORT_RETRIES", 0)
    engine.set_engine(51234, "qwen3.5-4b")

    def install(handler: Callable[[httpx.Request], Any]) -> None:
        transport = httpx.MockTransport(handler)
        monkeypatch.setattr(
            openai_adapter.openai,
            "AsyncOpenAI",
            lambda **kw: real(http_client=httpx.AsyncClient(transport=transport), **kw),
        )

    yield install
    engine.set_engine(None, None)


async def _turn() -> list[Any]:
    adapter = get_provider("local")
    msgs = [LLMMessage(role="user", content="How has Reliance done?")]
    return [e async for e in adapter.stream_chat(messages=msgs, model="qwen3.5-4b")]


def _sse(parts: list[bytes], die: bool = False) -> Callable[[httpx.Request], httpx.Response]:
    return lambda _req: httpx.Response(
        200, headers={"content-type": "text/event-stream"}, stream=_Body(parts, die)
    )


@pytest.mark.asyncio
async def test_no_engine_says_how_to_start_it() -> None:
    engine.set_engine(None, None)
    [event] = await _turn()
    assert isinstance(event, LLMErrorEvent)
    assert (event.message, event.code) == (NOT_RUNNING, "local_not_running")


@pytest.mark.asyncio
async def test_refused_connection_is_the_engine_stopping(wire: Any) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[Errno 61] Connection refused", request=request)

    wire(refuse)
    [event] = await _turn()
    assert isinstance(event, LLMErrorEvent)
    assert (event.message, event.code) == (STOPPED, "local_stopped")
    assert "network" not in event.message and "internet" not in (event.action or "")


@pytest.mark.asyncio
async def test_engine_dying_mid_answer_ends_the_turn_plainly(wire: Any) -> None:
    wire(_sse([_chunk({"role": "assistant", "content": "Reliance "})], die=True))
    events = await _turn()
    assert [e.text for e in events if isinstance(e, LLMDeltaEvent)] == ["Reliance "]
    assert isinstance(events[-1], LLMErrorEvent) and events[-1].message == STOPPED


@pytest.mark.asyncio
async def test_truncated_stream_without_finish_ends_the_turn_plainly(wire: Any) -> None:
    wire(_sse([_chunk({"role": "assistant", "content": "Reliance "})]))
    events = await _turn()
    assert isinstance(events[-1], LLMErrorEvent) and events[-1].message == STOPPED


@pytest.mark.asyncio
async def test_reasoning_never_leaks_and_file_path_is_not_the_served_model(wire: Any) -> None:
    wire(
        _sse(
            [
                _chunk({"role": "assistant", "reasoning_content": "Let me think."}),
                _chunk({"content": "Up 12%."}),
                _chunk({}, finish="stop"),
                b"data: [DONE]\n\n",
            ]
        )
    )
    events = await _turn()
    answer = "".join(e.text for e in events if isinstance(e, LLMDeltaEvent))
    assert answer == "Up 12%."
    assert any(isinstance(e, LLMThinkingEvent) for e in events)
    assert events[-1].kind == "done"


def test_context_overflow_reads_plainly() -> None:
    raw = "Error code: 400 - request (6030 tokens) exceeds the available context size (4096 tokens)"
    human = humanize("local", RuntimeError(raw))
    assert human.code == "context_overflow"
    assert human.message == "The conversation is too long for the on-computer model."


def test_ollama_keeps_its_own_messages() -> None:
    human = humanize("ollama", httpx.ConnectError("Connection refused"))
    assert human.code == "ollama_not_running"
    assert humanize("local", LocalEngineNotRunning()).code == "local_not_running"


def test_chat_route_without_engine_streams_the_plain_error(client: TestClient) -> None:
    engine.set_engine(None, None)
    with client.stream(
        "POST",
        "/llm/chat",
        json={
            "provider": "local",
            "model": "qwen3.5-4b",
            "messages": [{"role": "user", "content": "hi"}],
        },
    ) as response:
        body = b"".join(response.iter_bytes()).decode()
    frames = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
    assert frames[0]["kind"] == "error" and frames[0]["message"] == NOT_RUNNING
