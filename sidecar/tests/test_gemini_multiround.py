"""Gemini multi-round tool use (FR-024 / SC-005) — regression lock.

CURRENT_STATE §4 documented the break: Gemini pairs a ``functionResponse`` to
its ``functionCall`` by tool *name* (not call id), but the runtime appended
tool-result messages carrying only ``tool_call_id`` and no name — so every
Gemini ``function_response`` serialised ``name=""`` and the second round broke.

Two layers lock the fix:
  1. the runtime now threads the tool NAME onto the tool-result message
     (``metadata={"name": ...}``);
  2. the Gemini adapter reads that name into the ``function_response`` part.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMMessage,
    LLMToolUseEvent,
)
from services import agent_runtime
from services.llm.base import LLMProvider, LLMStreamEvent
from services.llm.gemini import _split_system_and_contents


class _RecordingProvider(LLMProvider):
    """Round 1: emit a real-catalog tool_use. Round 2: answer."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        self.calls.append({"messages": list(messages), "kwargs": dict(kwargs)})
        if len(self.calls) == 1:
            yield LLMToolUseEvent(tool_call_id="tc1", name="get_terminal_state", input={})
            yield LLMDoneEvent()
        else:
            yield LLMDeltaEvent(text="done")
            yield LLMDoneEvent()

    async def validate_key(self, api_key: str | None = None) -> bool:
        return True


async def _drain(agen: AsyncIterator[LLMStreamEvent]) -> None:
    async for _ in agen:
        pass


def test_runtime_threads_tool_name_onto_tool_result(monkeypatch) -> None:
    """The runtime must carry the tool name on the role='tool' message."""
    agent_runtime.reload()
    fake = _RecordingProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda _pid, base_url=None: fake)

    asyncio.run(_drain(agent_runtime.invoke_agent("copilot", "hi", api_key="x")))

    # The SECOND provider call carries the tool-result message; it must name the
    # tool so a name-keyed provider (Gemini) can pair the response.
    second = fake.calls[1]["messages"]
    tool_msgs = [m for m in second if m.role == "tool"]
    assert tool_msgs, "expected a tool-result message on the second round"
    assert all(m.metadata and m.metadata.get("name") for m in tool_msgs), (
        "tool-result message is missing the tool name (breaks Gemini multi-round)"
    )
    assert tool_msgs[0].metadata["name"] == "get_terminal_state"


def test_gemini_function_response_is_keyed_by_name() -> None:
    """The adapter must serialise the function_response name from metadata."""
    messages = [
        LLMMessage(role="user", content="is this cheap?"),
        LLMMessage(
            role="assistant",
            content="",
            metadata={
                "tool_calls": [{"id": "tc1", "name": "price_data", "input": {"symbol": "AAPL"}}]
            },
        ),
        LLMMessage(
            role="tool",
            content='{"ok": true}',
            tool_call_id="tc1",
            metadata={"name": "price_data"},
        ),
    ]
    _system, contents = _split_system_and_contents(messages)

    responses = [
        part["function_response"]
        for content in contents
        for part in content["parts"]
        if "function_response" in part
    ]
    assert responses, "expected a function_response part"
    assert responses[0]["name"] == "price_data", "function_response not keyed by tool name"

    calls = [
        part["function_call"]
        for content in contents
        for part in content["parts"]
        if "function_call" in part
    ]
    assert calls and calls[0]["name"] == "price_data", "function_call not keyed by tool name"


def test_gemini_empty_name_when_metadata_absent_documents_old_bug() -> None:
    """Without the name in metadata the adapter falls back to '' — the old break."""
    messages = [
        LLMMessage(role="tool", content='{"ok": true}', tool_call_id="tc1"),
    ]
    _system, contents = _split_system_and_contents(messages)
    fr = contents[0]["parts"][0]["function_response"]
    assert fr["name"] == ""  # exactly the bug the runtime fix avoids by populating metadata


# ---------------------------------------------------------------------------
# R15-AGENT-006: Gemini 3 thought signatures survive a multi-round tool turn
# ---------------------------------------------------------------------------


class _Obj:
    def __init__(self, **kw: Any) -> None:
        self.__dict__.update(kw)


def _call_part(name: str, signature: bytes | None) -> _Obj:
    return _Obj(
        text=None, function_call=_Obj(name=name, id=None, args={}), thought_signature=signature
    )


def _response(*parts: _Obj) -> _Obj:
    content = _Obj(parts=list(parts))
    return _Obj(candidates=[_Obj(content=content, finish_reason=None)], usage_metadata=None)


def _drive_gemini(monkeypatch, round_one: list[_Obj]) -> list[dict[str, Any]]:
    """Run the copilot on the real Gemini adapter against a fake SDK stream;
    return the ``contents`` the adapter sent on each round."""
    from google import genai

    rounds = [[_response(*round_one)], [_response(_Obj(text="done", function_call=None))]]
    sent: list[dict[str, Any]] = []

    async def _stream(items: list[Any]) -> AsyncIterator[Any]:
        for item in items:
            yield item

    class _Models:
        async def generate_content_stream(self, **kwargs: Any) -> AsyncIterator[Any]:
            sent.append(kwargs)
            return _stream(rounds[len(sent) - 1])

    class _Client:
        def __init__(self, **_: Any) -> None:
            self.aio = _Obj(models=_Models())

    monkeypatch.setattr(genai, "Client", _Client)
    agent_runtime.reload()
    asyncio.run(
        _drain(
            agent_runtime.invoke_agent(
                "copilot", "hi", provider="gemini", model="gemini-3-pro-preview", api_key="x"
            )
        )
    )
    assert len(sent) == 2
    return sent[1]["contents"]


def _model_call_parts(contents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        part
        for content in contents
        if content["role"] == "model"
        for part in content["parts"]
        if "function_call" in part
    ]


def test_thought_signature_rides_back_on_its_function_call(monkeypatch) -> None:
    from google.genai import types

    contents = _drive_gemini(monkeypatch, [_call_part("get_terminal_state", b"sig")])
    parts = _model_call_parts(contents)
    assert len(parts) == 1
    assert parts[0]["thought_signature"] == b"sig"
    for content in contents:
        types.Content.model_validate(content)  # the SDK accepts the replayed turn


def test_only_the_signed_call_carries_a_signature(monkeypatch) -> None:
    contents = _drive_gemini(
        monkeypatch,
        [_call_part("get_terminal_state", b"sig-a"), _call_part("get_portfolio", None)],
    )
    parts = _model_call_parts(contents)
    assert [p["function_call"]["name"] for p in parts] == ["get_terminal_state", "get_portfolio"]
    assert parts[0]["thought_signature"] == b"sig-a"
    assert "thought_signature" not in parts[1]


def test_provider_meta_never_rides_the_sse_wire() -> None:
    event = LLMToolUseEvent(tool_call_id="t", name="n", provider_meta={"thought_signature": "c2ln"})
    assert "provider_meta" not in event.model_dump()
    assert "provider_meta" not in event.model_dump_json()
