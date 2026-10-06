"""R15-AGENT-003: at the tool-round cap, announced tool calls == dispatched ones.

The capped round's tool_use was yielded (the UI staged it, AUTO could apply a
host action) but never dispatched, and the turn could end with no text.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMMessage,
    LLMToolUseEvent,
    LLMUsage,
)
from services import agent_runtime


class _ToolForeverProvider:
    """Emits one tool call per round, forever, and never any text."""

    def __init__(self, final_round_tool: str = "price_data") -> None:
        self._final_round_tool = final_round_tool
        self.round_messages: list[list[LLMMessage]] = []

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **_: Any
    ) -> AsyncIterator[Any]:
        self.round_messages.append(list(messages))
        n = len(self.round_messages)
        name = self._final_round_tool if n > agent_runtime._MAX_TOOL_ROUNDS else "price_data"
        yield LLMToolUseEvent(tool_call_id=f"tc{n}", name=name, input={"symbol": "TCS.NS"})
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))


async def _run(
    monkeypatch: pytest.MonkeyPatch, provider: _ToolForeverProvider, autonomy: str | None
) -> tuple[list[Any], list[str]]:
    agent_runtime.reload()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    dispatched: list[str] = []

    async def _fake_dispatch(call: Any, _local: Any = None) -> AsyncIterator[Any]:
        dispatched.append(call.tool_call_id)
        yield agent_runtime._ToolDone('{"ok": true}')

    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _fake_dispatch)
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot", prompt="x", api_key="k", mode="edit", autonomy=autonomy
        )
    ]
    return events, dispatched


@pytest.mark.asyncio
async def test_yielded_tool_calls_equal_dispatched_and_turn_ends_in_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _ToolForeverProvider()
    events, dispatched = await _run(monkeypatch, provider, autonomy=None)
    yielded = [e.tool_call_id for e in events if isinstance(e, LLMToolUseEvent)]
    assert yielded == dispatched
    assert len(dispatched) == agent_runtime._MAX_TOOL_ROUNDS
    assert isinstance(events[-1], LLMDoneEvent)
    assert isinstance(events[-2], LLMDeltaEvent) and events[-2].text.strip()
    # The capped round was told to answer now, with the tools still offered.
    capped_messages = provider.round_messages[-1]
    assert capped_messages[-1].role == "system"
    assert "do not call any more tools" in capped_messages[-1].content


@pytest.mark.asyncio
async def test_capped_round_host_action_is_never_yielded_under_auto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _ToolForeverProvider(final_round_tool="write_note")
    events, dispatched = await _run(monkeypatch, provider, autonomy="auto")
    names = [e.name for e in events if isinstance(e, LLMToolUseEvent)]
    assert "write_note" not in names
    assert len(names) == len(dispatched) == agent_runtime._MAX_TOOL_ROUNDS
