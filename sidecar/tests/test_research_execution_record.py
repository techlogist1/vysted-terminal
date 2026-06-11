"""ResearchExecution record matrix (R10 — E2 regression armor).

The execution record is minted at the research tool boundary and stamped from
the loop that RAN; the auto-publish derives the brief's mode/depth from it and
ONLY it. This file pins the full matrix the brief names:

  (composer-options, model-arg escalation, options-threaded invoke [the same
  path a resumed run re-enters], persona) × (normal/deep/ultra)
  → ``execution.loop`` + auto-publish mode/depth correct;
  payload without execution → NO auto-publish;
  disambiguation result → the chooser publish.

Every engine seam is faked at the module the handler lazily imports — no
network, no LLM. The fakes stamp ``execution_loop`` exactly as Team RESOLVE's
contract requires (fast/iter/heavy/research-model on every engine return).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

import config
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent, LLMUsage
from services import agent_runtime, agent_tools
from services.agent_tools.research import _research


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Engine fakes — each stamps execution_loop per the Team RESOLVE contract
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_engines(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Fake all three engine seams; returns the call-recording dict."""
    calls: dict[str, Any] = {}

    async def _fake_gather_fast(query: str, *, region: str, tool_call: Any, on_step: Any = None):
        calls["fast"] = {"query": query, "region": region}
        return {
            "ok": True,
            "query": query,
            "symbol": "NVDA",
            "execution_loop": "fast",
            "structured": {"price": {"ok": True}},
            "web": {"available": True, "citations": [{"url": "https://x", "title": "t"}]},
        }

    async def _fake_run_deep_brief(
        query: str,
        *,
        depth: str = "deep",
        rounds: Any = None,
        wall_seconds: Any = None,
        backend: Any = None,
        api_key: Any = None,
    ):
        calls["deep"] = {"query": query, "depth": depth}
        loop = "heavy" if depth == "ultra" else "iter"
        return {
            "ok": True,
            "query": query,
            "symbol": "NVDA",
            "markdown": "## Brief\nBody [1].",
            "sources": [{"url": "https://x", "title": "t"}],
            "execution_loop": loop,
            "mode": "heavy" if loop == "heavy" else "deep",
            "backend": "native",
        }

    async def _fake_run_research_model_brief(
        query: str, *, depth: str = "normal", api_key: Any = None, model: Any = None
    ):
        calls["tier_b"] = {"query": query, "depth": depth}
        return {
            "ok": True,
            "query": query,
            "symbol": "",
            "markdown": "## Hosted brief",
            "sources": [],
            "execution_loop": "research-model",
            "mode": "fast" if depth == "normal" else "deep",
            "backend": "research-model:test/model",
        }

    monkeypatch.setattr("services.research.fast.gather_fast", _fake_gather_fast)
    monkeypatch.setattr("services.agent_tools.deep_research.run_deep_brief", _fake_run_deep_brief)
    monkeypatch.setattr(
        "services.agent_tools.deep_research.run_research_model_brief",
        _fake_run_research_model_brief,
    )
    return calls


@pytest.fixture(autouse=True)
def _clean_depth_ctx() -> Any:
    yield
    config.set_request_research_depth(None)


class _StubToolCall:
    def __init__(self, tool_call_id: str = "tc-1") -> None:
        self.tool_call_id = tool_call_id


def _publish(out: dict[str, Any]) -> Any:
    return agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(out))


# ---------------------------------------------------------------------------
# Row 1 — composer-options (the slider floor) × normal/deep/ultra
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slider", "loop", "mode", "depth"),
    [
        ("normal", "fast", "fast", "quick"),
        ("deep", "iter", "deep", "deep"),
        ("ultra", "heavy", "deep", "heavy"),
    ],
)
def test_composer_slider_floor_drives_loop_and_publish(
    fake_engines: dict[str, Any], slider: str, loop: str, mode: str, depth: str
) -> None:
    config.set_request_research_depth(slider)
    out = _run(_research({"query": "nvidia"}))
    assert out["ok"] is True
    assert out["execution"]["loop"] == loop
    assert out["execution"]["requested_depth"] == slider
    assert out["execution"]["degraded_reason"] is None  # engine stamped its loop
    event = _publish(out)
    assert event is not None
    assert event.input["mode"] == mode
    assert event.input["depth"] == depth
    assert event.input["execution"] == out["execution"]


# ---------------------------------------------------------------------------
# Row 2 — model-arg escalation (and the floor never demotes)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arg", "loop", "depth"),
    [("normal", "fast", "quick"), ("deep", "iter", "deep"), ("ultra", "heavy", "heavy")],
)
def test_model_arg_escalates_above_a_normal_slider(
    fake_engines: dict[str, Any], arg: str, loop: str, depth: str
) -> None:
    config.set_request_research_depth("normal")
    out = _run(_research({"query": "nvidia", "depth": arg}))
    assert out["execution"]["loop"] == loop
    assert out["execution"]["requested_depth"] == arg
    event = _publish(out)
    assert event is not None
    assert event.input["depth"] == depth


def test_model_arg_never_demotes_the_slider_floor(fake_engines: dict[str, Any]) -> None:
    """The R7 floor rule survives: a model-passed 'normal' cannot demote the
    user's deep slider — the record reports the EFFECTIVE depth."""
    config.set_request_research_depth("deep")
    out = _run(_research({"query": "nvidia", "depth": "normal"}))
    assert out["execution"]["requested_depth"] == "deep"
    assert out["execution"]["loop"] == "iter"


# ---------------------------------------------------------------------------
# Row 3 — Tier B (research-model lane) maps per requested stop
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stop", "mode", "depth"),
    [("normal", "fast", "quick"), ("deep", "deep", "deep"), ("ultra", "deep", "heavy")],
)
def test_tier_b_research_model_maps_per_requested_stop(
    fake_engines: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    stop: str,
    mode: str,
    depth: str,
) -> None:
    token = config.set_request_research_search_tier("tier_b")
    try:
        out = _run(_research({"query": "nvidia", "depth": stop}))
    finally:
        config.reset_request_research_search_tier(token)
    assert out["execution"]["loop"] == "research-model"
    assert out["execution"]["requested_depth"] == stop
    assert fake_engines["tier_b"]["depth"] == stop
    event = _publish(out)
    assert event is not None
    assert event.input["mode"] == mode
    assert event.input["depth"] == depth


# ---------------------------------------------------------------------------
# Degradation honesty + legacy payloads
# ---------------------------------------------------------------------------


def test_degraded_deep_run_states_why(monkeypatch: pytest.MonkeyPatch) -> None:
    """Requested deep but the fast loop ran → degraded_reason MUST say why,
    carrying the payload's note when present (never silent)."""

    async def _degraded(query: str, **_kwargs: Any):
        return {
            "ok": True,
            "query": query,
            "markdown": "x",
            "execution_loop": "fast",
            "note": "deep loop unavailable: no model configured",
        }

    monkeypatch.setattr("services.agent_tools.deep_research.run_deep_brief", _degraded)
    out = _run(_research({"query": "nvidia", "depth": "deep"}))
    reason = out["execution"]["degraded_reason"]
    assert reason is not None
    assert "requested deep" in reason
    assert "no model configured" in reason


def test_legacy_payload_without_execution_loop_derives_with_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An engine return WITHOUT execution_loop (pre-RESOLVE shape) derives the
    loop from its legacy mode and says so — inference is never silent."""

    async def _legacy(query: str, **_kwargs: Any):
        return {"ok": True, "query": query, "markdown": "x", "mode": "deep"}

    monkeypatch.setattr("services.agent_tools.deep_research.run_deep_brief", _legacy)
    out = _run(_research({"query": "nvidia", "depth": "deep"}))
    assert out["execution"]["loop"] == "iter"
    assert out["execution"]["degraded_reason"] == "legacy engine payload"


def test_payload_without_execution_never_auto_publishes() -> None:
    bare = {"ok": True, "query": "x", "markdown": "body", "mode": "deep"}
    assert _publish(bare) is None


def test_disambiguation_result_publishes_the_chooser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The full composition: engine returns needs_disambiguation → the handler
    stamps the record → the auto-publish is the chooser, nothing else."""

    async def _ambiguous(query: str, *, region: str, tool_call: Any, on_step: Any = None):
        return {
            "ok": True,
            "needs_disambiguation": True,
            "query": query,
            "execution_loop": "fast",
            "candidates": [
                {"symbol": "TCS", "name": "Tata Consultancy", "exchange": "NSE", "score": 0.6},
            ],
            "message": "Which Tata did you mean?",
        }

    monkeypatch.setattr("services.research.fast.gather_fast", _ambiguous)
    out = _run(_research({"query": "tata"}))
    assert out["execution"]["run_id"]
    event = _publish(out)
    assert event is not None
    assert set(event.input) == {"query", "disambiguation", "execution"}
    assert event.input["disambiguation"]["candidates"][0]["symbol"] == "TCS"


def test_begin_step_announces_the_run(fake_engines: dict[str, Any]) -> None:
    """The boundary emits research:begin {run_id} depth={depth} query={query}
    BEFORE any engine work — the frontend keys in-flight state on it."""
    steps: list[Any] = []
    token = config.set_step_sink(steps.append)
    try:
        out = _run(_research({"query": "nvidia earnings", "depth": "deep"}))
    finally:
        config.reset_step_sink(token)
    assert steps, "no begin step emitted"
    begin = steps[0]
    assert begin.kind == "engine"
    assert begin.detail == (
        f"research:begin {out['execution']['run_id']} depth=deep query=nvidia earnings"
    )


# ---------------------------------------------------------------------------
# Rows 4+5 — the options-threaded invoke (the path a resumed run re-enters)
# and a PERSONA, end-to-end through the runtime's auto-publish
# ---------------------------------------------------------------------------


class _ResearchThenAnswerProvider:
    """Round 1 calls the research tool; round 2 streams the final text."""

    def __init__(self) -> None:
        self._round = 0

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        if self._round == 0:
            self._round += 1
            yield LLMToolUseEvent(tool_call_id="call-1", name="research", input={"query": "nvda"})
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="Brief is up.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2))


async def _invoke_collect(agent_id: str, monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    agent_runtime.reload()
    agent_tools.reset_for_tests()
    agent_tools.register_v0_5_0_tools()
    agent_tools.register_v0_6_0_tools()
    monkeypatch.setattr(
        agent_runtime, "get_provider", lambda *_a, **_k: _ResearchThenAnswerProvider()
    )
    events: list[Any] = []
    async for event in agent_runtime.invoke_agent(
        agent_id=agent_id,
        prompt="research nvda deeply",
        api_key="sk-test",
        mode="edit",
        options={"research_depth": "deep"},  # the composer/resume-rethreaded floor
    ):
        events.append(event)
    return events


def _auto_publish_from(events: list[Any]) -> Any:
    for event in events:
        if getattr(event, "kind", None) == "tool_use" and event.tool_call_id.endswith(
            "__autobrief"
        ):
            return event
    return None


@pytest.mark.asyncio
async def test_options_threaded_invoke_publishes_the_deep_truth(
    fake_engines: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """options.research_depth (the same channel a resumed run re-threads, R10
    §4) floors the run at deep — the auto-publish carries iter/deep/deep and
    the verbatim execution record, end-to-end through invoke_agent."""
    events = await _invoke_collect("copilot", monkeypatch)
    publish = _auto_publish_from(events)
    assert publish is not None
    assert publish.input["mode"] == "deep"
    assert publish.input["depth"] == "deep"
    assert publish.input["execution"]["loop"] == "iter"
    assert publish.input["execution"]["requested_depth"] == "deep"
    # The begin step rides the live research_step channel for the frontend.
    begin_steps = [
        e
        for e in events
        if getattr(e, "kind", None) == "research_step" and e.detail.startswith("research:begin ")
    ]
    assert len(begin_steps) == 1


@pytest.mark.asyncio
async def test_persona_invoke_publishes_the_same_execution_truth(
    fake_engines: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A PERSONA (graham) runs the same boundary: its research auto-publish
    carries the identical execution-derived mode/depth — capability and
    honesty parity with the copilot (E5 × E2)."""
    events = await _invoke_collect("graham", monkeypatch)
    publish = _auto_publish_from(events)
    assert publish is not None
    assert publish.input["mode"] == "deep"
    assert publish.input["depth"] == "deep"
    assert publish.input["execution"]["loop"] == "iter"
