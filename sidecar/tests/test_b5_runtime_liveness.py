"""Batch 5 (W3): the agent loop's waits are bounded and visibly alive.

R15-AGENT-025: a provider that accepted the request and never streamed left the
chat on a silent spinner for up to 600 s (no client timeout, no heartbeat), and
the planner pre-pass awaited an untimed completion before the first frame.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent
from services import agent_runtime
from services.llm import oneshot
from services.llm.base import IDLE_TIMEOUT_S, LOCAL_IDLE_TIMEOUT_S
from services.llm.ollama import OllamaProvider
from services.llm.openai import OpenAIProvider


class _Hangs:
    """A provider that accepts the request and never sends anything."""

    async def stream_chat(self, messages: Any, model: str, api_key: Any = None, **kwargs: Any):
        await asyncio.sleep(3600)
        yield LLMDoneEvent()  # pragma: no cover — never reached


class _Answers:
    async def stream_chat(self, messages: Any, model: str, api_key: Any = None, **kwargs: Any):
        yield LLMDeltaEvent(text="RELIANCE closed at Rs 1,412.")
        yield LLMDoneEvent(finish_reason="stop")


@pytest.fixture
def _fast_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_runtime, "_HEARTBEAT_SECONDS", 0.01)
    monkeypatch.setattr(agent_runtime, "IDLE_TIMEOUT_S", 0.05)


@pytest.mark.usefixtures("_fast_clock")
@pytest.mark.asyncio
async def test_a_hanging_provider_gets_heartbeats_then_an_error_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_runtime.reload()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: _Hangs())
    started = time.monotonic()
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="price of RELIANCE?",
            provider="openai",
            api_key="k",
            mode="ask",
        )
    ]
    assert time.monotonic() - started < 2
    kinds = [e.kind for e in events]
    assert kinds[0] == "heartbeat"
    assert [e.code for e in events if e.kind == "error"] == ["provider_idle"]
    assert kinds[-1] == "done"


@pytest.mark.usefixtures("_fast_clock")
@pytest.mark.asyncio
async def test_a_quiet_tool_is_kept_alive_by_heartbeats() -> None:
    async def slow_tool(_args: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.05)
        return {"ok": True}

    call = LLMToolUseEvent(tool_call_id="t-1", name="slow_tool", input={})
    items = [
        item
        async for item in agent_runtime._dispatch_tool_with_progress(call, {"slow_tool": slow_tool})
    ]
    assert getattr(items[0], "kind", None) == "heartbeat"
    assert isinstance(items[-1], agent_runtime._ToolDone)


@pytest.mark.asyncio
async def test_a_hung_planner_times_out_and_the_turn_proceeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_runtime.reload()
    monkeypatch.setattr(agent_runtime, "_PLANNER_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: _Answers())
    monkeypatch.setattr(oneshot, "get_provider", lambda *_a, **_k: _Hangs())
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="open a chart of AAPL and add NVDA to my watchlist",
            provider="openai",
            model="gpt-4.1-mini",
            api_key="k",
            mode="agent",
        )
    ]
    kinds = [e.kind for e in events]
    assert "agent_plan" not in kinds
    assert kinds[-2:] == ["delta", "done"]


def test_adapter_clients_carry_an_explicit_idle_timeout() -> None:
    # The SDK default read timeout is 600 s (OpenAI) or none at all (Ollama).
    assert OpenAIProvider()._client("sk").timeout.read == IDLE_TIMEOUT_S
    ollama_client = OllamaProvider()._client()._client
    assert ollama_client.timeout.read == LOCAL_IDLE_TIMEOUT_S
