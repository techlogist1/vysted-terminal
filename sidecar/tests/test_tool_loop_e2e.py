"""End-to-end test of the (Phase-10) live agentic tool loop.

Before Phase 10 the runtime loop existed but no adapter ever sent a ``tools=``
schema, so no model emitted a ``tool_use`` and the loop never ran. These tests
drive the loop with a scripted fake provider to prove, without a live API key:

1. tool definitions are SENT to the adapter (the keystone),
2. a model ``tool_use`` is dispatched and its result fed back,
3. the assistant tool-call turn is reconstructed before the tool result,
4. the terminal-context preamble + ``get_terminal_state`` surface live state,
   so the copilot answers grounded in what the user is looking at.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import config
from models.agent import AgentContextSnapshot
from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMMessage,
    LLMResearchStepEvent,
    LLMToolUseEvent,
)
from services import agent_runtime, agent_tools
from services.agent_tools.schemas import anthropic_tools, gemini_tools, openai_tools
from services.llm.base import LLMProvider, LLMStreamEvent


class _ScriptedProvider(LLMProvider):
    """Round 1: call get_terminal_state. Round 2: answer referencing the result."""

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
            # The runtime fed the tool result back; the "model" reads the
            # focused symbol from it and answers.
            yield LLMDeltaEvent(text="You're looking at AAPL — here's my read.")
            yield LLMDoneEvent()

    async def validate_key(self, api_key: str | None = None) -> bool:
        return True


async def _collect(agen: AsyncIterator[LLMStreamEvent]) -> list[LLMStreamEvent]:
    return [event async for event in agen]


def _snapshot() -> AgentContextSnapshot:
    return AgentContextSnapshot(
        focused_source="chart-1",
        by_source={
            "__terminal__": {
                "focusedSymbol": "AAPL",
                "charts": [
                    {
                        "panelId": "chart-1",
                        "symbol": "AAPL",
                        "timeframe": "1d",
                        "indicators": ["RSI"],
                    }
                ],
                "watchlist": {"symbols": ["AAPL", "MSFT"], "selected": "AAPL"},
                "portfolio": {"positionCount": 1, "totalValue": 1000},
                "openPanels": ["chart-1", "watchlist"],
                "capturedAt": 1,
            }
        },
        captured_at=1,
    )


def test_copilot_tool_loop_runs_end_to_end(monkeypatch) -> None:
    agent_runtime.reload()
    fake = _ScriptedProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda _pid, base_url=None: fake)

    events = asyncio.run(
        _collect(
            agent_runtime.invoke_agent(
                "copilot", "is this cheap?", context_snapshot=_snapshot(), api_key="x"
            )
        )
    )

    # (1) the loop actually fired: a tool_use was yielded.
    tool_uses = [e for e in events if isinstance(e, LLMToolUseEvent)]
    assert any(t.name == "get_terminal_state" for t in tool_uses)

    # (2) the final answer references the live focused symbol.
    text = "".join(e.text for e in events if isinstance(e, LLMDeltaEvent))
    assert "AAPL" in text

    # (3) the KEYSTONE: tools were SENT to the adapter on the first call,
    #     including the copilot's allow-list.
    first_kwargs = fake.calls[0]["kwargs"]
    assert "tool_ids" in first_kwargs
    assert "get_terminal_state" in first_kwargs["tool_ids"]

    # (4) the second call carries the reconstructed assistant tool-call turn
    #     followed by the tool RESULT containing the live terminal state.
    second = fake.calls[1]["messages"]
    assert any(
        m.role == "assistant" and m.metadata and m.metadata.get("tool_calls") for m in second
    )
    assert any(m.role == "tool" and "AAPL" in m.content for m in second)

    # (5) the context preamble rendered the deixis line with the focused symbol.
    assert any(m.role == "system" and "AAPL" in m.content for m in second)


class _ResearchProvider(LLMProvider):
    """Round 1: call a long research tool. Round 2: answer from its result."""

    def __init__(self) -> None:
        self.n = 0

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        self.n += 1
        if self.n == 1:
            yield LLMToolUseEvent(tool_call_id="tc1", name="research", input={"query": "x"})
            yield LLMDoneEvent()
        else:
            yield LLMDeltaEvent(text="here is the brief")
            yield LLMDoneEvent()

    async def validate_key(self, api_key: str | None = None) -> bool:
        return True


def test_research_steps_stream_live_during_a_tool_round(monkeypatch) -> None:
    """Track A: a tool that emits ResearchSteps via the runtime step-sink
    surfaces them as live ``research_step`` events INTERLEAVED into the stream —
    before the terminal ``done`` — so a long research round is no longer silent.
    """
    from services.research.models import ResearchStep

    agent_runtime.reload()

    async def _emitting_tool(args: dict[str, Any]) -> dict[str, Any]:
        # The runtime publishes a per-dispatch sink; the tool forwards its steps.
        sink = config.get_step_sink()
        assert sink is not None
        sink(ResearchStep("plan", "decomposed into 2 questions"))
        sink(ResearchStep("search", "searched the web", latency_ms=42))
        sink(ResearchStep("synthesize", "wrote the brief"))
        return {"ok": True, "summary": "fake brief"}

    # Override the real research tool for this round; reset restores it.
    agent_tools.register_tool("research", _emitting_tool)
    fake = _ResearchProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda _pid, base_url=None: fake)

    try:
        events = asyncio.run(
            _collect(agent_runtime.invoke_agent("copilot", "research x", api_key="x"))
        )
    finally:
        agent_tools.reset_for_tests()

    steps = [e for e in events if isinstance(e, LLMResearchStepEvent)]
    # (1) all three steps streamed, in order, with the right kinds + indices.
    assert [s.step_kind for s in steps] == ["plan", "search", "synthesize"]
    assert [s.index for s in steps] == [1, 2, 3]
    assert steps[1].latency_ms == 42
    # (2) each carries the originating tool + tool_call_id (UI grouping).
    assert all(s.tool == "research" and s.tool_call_id == "tc1" for s in steps)
    # (3) they interleave BEFORE the terminal done (not after the run finishes).
    kinds = [type(e).__name__ for e in events]
    assert kinds.index("LLMResearchStepEvent") < kinds.index("LLMDoneEvent")
    # (4) the tool result still fed back so the model could answer.
    text = "".join(e.text for e in events if isinstance(e, LLMDeltaEvent))
    assert "brief" in text


class _CapturingProvider(LLMProvider):
    """Answers immediately and records the kwargs (incl. the tool_ids) it was sent."""

    def __init__(self) -> None:
        self.kwargs: dict[str, Any] | None = None

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        self.kwargs = dict(kwargs)
        yield LLMDeltaEvent(text="ok")
        yield LLMDoneEvent()

    async def validate_key(self, api_key: str | None = None) -> bool:
        return True


def _tool_ids_for(monkeypatch, prompt: str) -> list[str]:
    agent_runtime.reload()
    fake = _CapturingProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda _pid, base_url=None: fake)
    asyncio.run(_collect(agent_runtime.invoke_agent("copilot", prompt, api_key="x", mode="agent")))
    assert fake.kwargs is not None
    return list(fake.kwargs.get("tool_ids") or [])


def test_agent_mode_infers_read_intent_and_gates_to_read_only(monkeypatch) -> None:
    """Track B + Decision 4: the collapsed 'agent' mode infers a READ intent and
    strips ORDER + write mutators server-side, but RETAINS a read-safe panel
    allow-list so a read question can still ground itself by pulling up the
    relevant chart/index. ``propose_order`` STAYS stripped on a read intent
    (§6.5 — the AI has no path to place an order); every retained panel action
    still rides the frontend diff/accept gate (auto-apply excludes orders)."""
    tids = _tool_ids_for(monkeypatch, "what is a P/E ratio?")
    # §6.5: an order can never survive a read intent, in any mode.
    assert "propose_order" not in tids
    # Decision 4: the read-safe panel actions are retained so the agent can ground
    # a read answer in the cockpit (e.g. "how's the market" -> set_chart_symbol SPY).
    for panel_action in ("set_chart_symbol", "open_panel", "add_to_watchlist"):
        assert panel_action in tids
    assert "price_data" in tids  # read tools survive


def test_agent_mode_infers_build_intent_and_keeps_host_actions(monkeypatch) -> None:
    """A build-leaning prompt keeps the host actions so the agent can drive the
    cockpit (every mutation still rides the diff/accept gate frontend-side)."""
    tids = _tool_ids_for(monkeypatch, "set up a research cockpit for NVDA")
    assert "set_chart_symbol" in tids
    assert "open_panel" in tids


def test_tool_schemas_serialize_for_every_provider_shape() -> None:
    agent_runtime.reload()
    spec = agent_runtime.get_agent("copilot")
    assert spec is not None
    a = anthropic_tools(spec.tools)
    o = openai_tools(spec.tools)
    g = gemini_tools(spec.tools)
    assert a and all("name" in t and "input_schema" in t for t in a)
    assert o and all(t["type"] == "function" and "parameters" in t["function"] for t in o)
    assert g and "function_declarations" in g[0]
    # the same tool appears in all three shapes
    names_a = {t["name"] for t in a}
    assert "get_terminal_state" in names_a
    # unknown ids are filtered out, never break serialization.
    assert anthropic_tools(["definitely_not_a_tool"]) == []
    assert gemini_tools([]) == []


def test_history_is_threaded_into_messages(monkeypatch) -> None:
    agent_runtime.reload()
    fake = _ScriptedProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda _pid, base_url=None: fake)
    history = [
        {"role": "user", "content": "earlier question"},
        {"role": "assistant", "content": "earlier answer"},
    ]
    asyncio.run(
        _collect(
            agent_runtime.invoke_agent(
                "copilot", "follow-up", api_key="x", options={"history": history}
            )
        )
    )
    first = fake.calls[0]["messages"]
    contents = [m.content for m in first]
    assert "earlier question" in contents
    assert "earlier answer" in contents
    # history must NOT be forwarded to the adapter as a raw kwarg.
    assert "history" not in fake.calls[0]["kwargs"]
