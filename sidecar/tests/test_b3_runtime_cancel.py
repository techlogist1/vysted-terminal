"""R15-AGENT-002: closing the tool-progress stream cancels the in-flight tool.

Stop in the composer (or an SSE disconnect) ``aclose()``s the agent stream. The
tool ran as a detached ``asyncio`` task, so before the fix it kept running --
research, LLM and web calls spending the user's key for minutes.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

import config
from models.llm import LLMResearchStepEvent, LLMToolUseEvent
from services import agent_runtime


@pytest.mark.asyncio
async def test_aclose_cancels_the_running_tool_within_100ms() -> None:
    finished_sleep: list[bool] = []
    tool_task: list[asyncio.Task[Any]] = []

    async def slow_tool(_args: dict[str, Any]) -> dict[str, Any]:
        tool_task.append(asyncio.current_task())  # type: ignore[arg-type]
        sink = config.get_step_sink()
        assert sink is not None
        sink({"kind": "engine", "detail": "working"})
        await asyncio.sleep(5)
        finished_sleep.append(True)
        return {"ok": True}

    call = LLMToolUseEvent(tool_call_id="slow-1", name="slow_tool", input={})
    gen = agent_runtime._dispatch_tool_with_progress(call, {"slow_tool": slow_tool})
    first = await gen.__anext__()
    assert isinstance(first, LLMResearchStepEvent)

    started = time.monotonic()
    await gen.aclose()
    elapsed = time.monotonic() - started

    assert tool_task and tool_task[0].cancelled()
    assert elapsed < 0.1
    await asyncio.sleep(0.05)
    assert finished_sleep == []
