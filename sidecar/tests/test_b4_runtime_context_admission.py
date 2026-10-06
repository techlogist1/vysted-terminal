"""R15-AGENT-008: nothing bounded what entered the model's context.

The copilot sent all ~50 tool schemas every round, tool results went in whole
and were re-sent every later round, and nothing counted any of it against the
local lane's 16,384-token window (Ollama silently drops the prompt's head past
it). A window-bound lane now gets a cue-driven tool subset, capped results and
oldest-first elision; a hosted lane (no window) keeps the full set.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent
from services import agent_runtime
from services.llm.base import LLMProvider
from services.llm.ollama import DEFAULT_NUM_CTX, OllamaProvider

_BIG = json.dumps({"ok": True, "rows": ["x" * 200] * 200})  # ~41 KB


class _Recording:
    """Round 1 issues ``calls``; round 2 answers. Records each round's prompt."""

    def __init__(self, calls: list[LLMToolUseEvent]) -> None:
        self.calls = calls
        self.rounds: list[dict[str, Any]] = []

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        tool_ids = kwargs["tool_ids"]
        self.rounds.append(
            {
                "estimate": agent_runtime._estimate_tokens(messages, tool_ids),
                "tool_ids": list(tool_ids),
                "tool_messages": [m.content for m in messages if m.role == "tool"],
            }
        )
        if len(self.rounds) == 1:
            for call in self.calls:
                yield call
            yield LLMDoneEvent()
            return
        yield LLMDeltaEvent(text="done")
        yield LLMDoneEvent()

    async def validate_key(self, api_key: str | None = None) -> bool:
        return True


class _OllamaLane(_Recording, OllamaProvider):
    pass


class _HostedLane(_Recording, LLMProvider):
    pass


async def _drive(
    monkeypatch: pytest.MonkeyPatch,
    provider: _Recording,
    provider_id: str,
    prompt: str,
    results: dict[str, str],
) -> list[Any]:
    async def _dispatch(tool_call: Any, local_tools: Any = None) -> AsyncIterator[Any]:
        yield agent_runtime._ToolDone(results[tool_call.name])

    agent_runtime.reload()
    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _dispatch)
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    return [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot", prompt=prompt, provider=provider_id, api_key="k", mode="edit"
        )
    ]


def _two_calls(*names: str) -> list[LLMToolUseEvent]:
    return [LLMToolUseEvent(tool_call_id=f"c{i}", name=n, input={}) for i, n in enumerate(names)]


@pytest.mark.asyncio
async def test_ollama_turn_fits_num_ctx_with_a_cued_tool_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane = _OllamaLane(_two_calls("screener_run", "fundamentals"))
    await _drive(
        monkeypatch,
        lane,
        "ollama",
        "screen nse-all for P/E under 15",
        {"screener_run": _BIG, "fundamentals": _BIG},
    )
    assert len(lane.rounds) == 2
    assert all(r["estimate"] < DEFAULT_NUM_CTX for r in lane.rounds), lane.rounds
    assert "screener_run" in lane.rounds[0]["tool_ids"]
    assert "price_option" not in lane.rounds[0]["tool_ids"]


@pytest.mark.asyncio
async def test_hosted_turn_sends_every_tool_and_elides_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lane = _HostedLane(_two_calls("screener_run", "fundamentals"))
    await _drive(
        monkeypatch,
        lane,
        "deepseek",
        "screen nse-all for P/E under 15",
        {"screener_run": _BIG, "fundamentals": _BIG},
    )
    spec = agent_runtime.get_agent("copilot")
    assert spec is not None
    assert lane.rounds[0]["tool_ids"] == list(spec.tools)
    assert lane.rounds[1]["tool_messages"] == [_BIG, _BIG]


@pytest.mark.asyncio
async def test_ollama_caps_a_large_result_but_the_raw_path_keeps_it_whole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A class case the fix was not written against: a 40 KB announcements
    payload reaches the local model capped with the marker, while the research
    auto-publish still renders from the untouched raw result."""
    markdown = "## Brief\n" + "Order book grew. " * 2500  # ~42 KB
    from services.agent_tools.research import brief_for

    bundle = {"ok": True, "query": "reliance", "markdown": markdown, "execution": {"run_id": "r1"}}
    # The research tool attaches its brief (C6); the runtime publishes it.
    research = json.dumps({**bundle, "brief": brief_for(bundle)})
    lane = _OllamaLane(_two_calls("corporate_announcements", "research"))
    events = await _drive(
        monkeypatch,
        lane,
        "ollama",
        "latest corporate announcements for RELIANCE",
        {"corporate_announcements": _BIG, "research": research},
    )
    announcements = lane.rounds[1]["tool_messages"][0]
    assert "chars elided — call again with a narrower query or a smaller limit]" in announcements
    assert len(announcements) < len(_BIG) // 2
    publish = next(e for e in events if getattr(e, "name", None) == "publish_brief")
    assert publish.input["markdown"] == markdown


def test_oldest_tool_results_are_elided_first_and_the_latest_round_kept() -> None:
    def _calls(i: int) -> LLMMessage:
        return LLMMessage(
            role="assistant",
            content="",
            metadata={"tool_calls": [{"id": f"c{i}", "name": "news", "input": {}}]},
        )

    old, latest = "o" * 40_000, "n" * 20_000
    prompt = "u" * 4_000
    messages = [
        LLMMessage(role="system", content="s"),
        LLMMessage(role="user", content=prompt),
        _calls(1),
        LLMMessage(role="tool", content=old, tool_call_id="c1"),
        _calls(2),
        LLMMessage(role="tool", content=latest, tool_call_id="c2"),
    ]
    agent_runtime._fit_to_window(messages, ["news"], DEFAULT_NUM_CTX)
    assert messages[3].content == agent_runtime._ELIDED_RESULT
    assert messages[5].content == latest
    assert messages[1].content == prompt
