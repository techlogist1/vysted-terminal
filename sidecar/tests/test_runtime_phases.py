"""Direct tests of invoke_agent's phases, no provider involved (R15-CODE-AGENT-009)."""

from __future__ import annotations

import contextvars
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

import config
from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMResearchStepEvent,
    LLMToolUseEvent,
    LLMUsage,
)
from services import agent_runtime as rt


def _setup(**overrides: Any) -> rt._RunSetup:
    fields: dict[str, Any] = {
        "provider_id": "ollama",
        "model": "qwen2.5:7b",
        "adapter": None,
        "tool_ids": ["price_data", "open_panel"],
        "read_only": False,
        "local_tools": {},
        "messages": [LLMMessage(role="user", content="hi")],
        "window": None,
        "opts": {},
        "notices": [],
    }
    return rt._RunSetup(**(fields | overrides))


async def _events(*events: Any) -> AsyncIterator[Any]:
    for event in events:
        yield event


async def _drain(gen: AsyncIterator[Any]) -> list[Any]:
    return [event async for event in gen]


def test_prepare_run_pops_every_runtime_option_and_publishes_it_task_local() -> None:
    spec = rt.get_agent("copilot")
    assert spec is not None
    options = {
        "history": [],
        "modelWebSearch": " NONE ",
        "deepResearchBackend": " Perplexity ",
        "research_depth": "",
        "depth": "Ultra",
        "temperature": 0.2,
        "unknown_knob": 1,
    }

    def prepare() -> tuple[rt._RunSetup, tuple[Any, ...]]:
        run = rt._prepare_run(spec, "hi", None, "k", "ollama", "m1", options, "delegate", None)
        published = (
            config.get_request_model_web_search(),
            config.get_deep_research_backend(),
            config.get_request_research_depth(),
            config.get_llm_creds(),
        )
        return run, published

    run, published = contextvars.copy_context().run(prepare)

    assert run.opts == {"temperature": 0.2}
    assert published == ("none", "perplexity", "ultra", ("ollama", "m1", "k"))
    assert (run.provider_id, run.model) == ("ollama", "m1")
    assert run.window  # Ollama runs in a bounded window
    assert run.tool_ids[-1] == rt.ASK_USER_TOOL  # Delegate mode can always pause
    assert run.notices == []
    assert "history" in options  # the caller's dict is never mutated


def test_open_round_caps_the_last_round_and_spends_down_native_search() -> None:
    run = _setup(opts={"web_search": True, "web_search_max_uses": rt._WEB_SEARCH_CAP})
    turn = rt._TurnState(native_searches=2)

    rnd = rt._open_round(run, turn)
    assert not rnd.capped
    assert run.opts["web_search_max_uses"] == rt._WEB_SEARCH_CAP - 2

    turn.rounds, turn.native_searches = rt._MAX_TOOL_ROUNDS, rt._WEB_SEARCH_CAP
    rnd = rt._open_round(run, turn)
    assert rnd.capped
    assert run.messages[-1].content == rt._CAPPED_ROUND_NOTE
    assert "web_search" not in run.opts and "web_search_max_uses" not in run.opts


@pytest.mark.asyncio
async def test_consume_round_collects_tool_calls_and_swallows_the_mid_run_done() -> None:
    turn = rt._TurnState(last_research_execution={"mode": "FAST"})
    rnd = rt._Round(capped=False)
    call = LLMToolUseEvent(tool_call_id="", name="publish_brief", input={"markdown": "m"})
    stream = _events(LLMDeltaEvent(text="Looking."), call, LLMDoneEvent(usage=LLMUsage()))

    out = await _drain(rt._consume_round(stream, _setup(), turn, rnd, None, None))

    assert out == [LLMDeltaEvent(text="Looking."), call]
    assert not rnd.ended
    assert rnd.pending_tools == [call]
    assert call.tool_call_id.startswith("call_")  # never the provider's id
    assert call.input["execution"] == {"mode": "FAST"}
    assert turn.publish_brief_calls == [call.tool_call_id]
    assert turn.turn_text


@pytest.mark.asyncio
async def test_consume_round_halts_before_dispatch_when_the_budget_says_stop() -> None:
    rnd = rt._Round(capped=False)
    call = LLMToolUseEvent(tool_call_id="", name="price_data", input={"symbol": "AAPL"})
    done = LLMDoneEvent(usage=LLMUsage(input_tokens=10))
    seen: list[tuple[str, str]] = []

    def budget(_usage: LLMUsage, model: str, provider: str) -> bool:
        seen.append((model, provider))
        return False

    out = await _drain(
        rt._consume_round(_events(call, done), _setup(), rt._TurnState(), rnd, None, budget)
    )

    assert seen == [("qwen2.5:7b", "ollama")]
    assert [type(e) for e in out] == [LLMToolUseEvent, LLMResearchStepEvent, LLMDoneEvent]
    assert out[1].tool == rt.HALT_NOTICE_TOOL
    assert rnd.ended


@pytest.mark.asyncio
async def test_consume_round_drops_tool_calls_on_the_capped_round() -> None:
    rnd = rt._Round(capped=True)
    call = LLMToolUseEvent(tool_call_id="", name="price_data", input={"symbol": "AAPL"})

    out = await _drain(
        rt._consume_round(_events(call, LLMDoneEvent()), _setup(), rt._TurnState(), rnd, None, None)
    )

    assert rnd.pending_tools == []
    assert out[0] == LLMDeltaEvent(text=rt._CAPPED_ROUND_CLOSE)
    assert isinstance(out[-1], LLMDoneEvent)
    assert rnd.ended


@pytest.mark.asyncio
async def test_finish_turn_names_a_length_cut_and_an_empty_answer() -> None:
    run = _setup(window=8192)
    rnd = rt._Round(capped=False)
    done = LLMDoneEvent(finish_reason="length")

    out = await _drain(rt._finish_turn(done, run, rt._TurnState(), rnd, None))

    assert [type(e) for e in out] == [LLMResearchStepEvent, LLMErrorEvent, LLMDoneEvent]
    assert out[0].detail == rt._LENGTH_NOTICE
    assert out[1].code == "empty_response"
    assert out[2].context_window == 8192
    assert rnd.ended


@pytest.mark.asyncio
async def test_finish_turn_explains_a_content_filter_refusal() -> None:
    turn = rt._TurnState(turn_text=True)
    done = LLMDoneEvent(finish_reason="content_filter")

    out = await _drain(rt._finish_turn(done, _setup(), turn, rt._Round(capped=False), None))

    assert [type(e) for e in out] == [LLMErrorEvent, LLMDoneEvent]
    assert out[0].code == "content_filter"


@pytest.mark.asyncio
async def test_finish_unterminated_says_the_answer_was_cut_and_closes_the_stream() -> None:
    rnd = rt._Round(capped=False, streamed_text=True)

    out = await _drain(rt._finish_unterminated(_setup(), rt._TurnState(), rnd, None))

    assert [type(e) for e in out] == [LLMErrorEvent, LLMDoneEvent]
    assert out[0].code == "truncated"
    assert rnd.ended


@pytest.mark.asyncio
async def test_dispatch_round_answers_each_call_and_stops_searching_past_the_cap() -> None:
    async def read_notes(_args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "notes": "thesis"}

    run = _setup(model="deepseek-reasoner", local_tools={"read_notes": read_notes})
    turn = rt._TurnState(web_search_calls=rt._WEB_SEARCH_CAP)
    rnd = rt._Round(capped=False, reasoning_parts=["think ", "first"])
    search = LLMToolUseEvent(tool_call_id="call_s", name="web_search", input={"query": "q"})
    notes = LLMToolUseEvent(tool_call_id="call_n", name="read_notes", input={})
    rnd.pending_tools = [search, notes]
    results: list[tuple[str, str]] = []

    out = await _drain(
        rt._dispatch_round(
            run, turn, rnd, None, lambda call, result: results.append((call.name, result))
        )
    )

    assert out == []
    assistant, search_result, notes_result = run.messages[-3:]
    assert assistant.content == "think first"  # the reasoner's reasoning is echoed
    assert [c["id"] for c in assistant.metadata["tool_calls"]] == ["call_s", "call_n"]
    assert (search_result.tool_call_id, search_result.metadata) == (
        "call_s",
        {"name": "web_search"},
    )
    assert "web-search cap reached" in json.loads(results[0][1])["message"]
    assert notes_result.tool_call_id == "call_n"
    assert json.loads(results[1][1]) == {"ok": True, "notes": "thesis"}
    assert turn.web_search_calls == rt._WEB_SEARCH_CAP + 1
