"""R9 lead-integration seam pins (gates 2, 4, 5).

The fan-out left three cross-partition seams to the lead; these tests pin them:

1. The B4 dual-channel cross-verify wiring: ``_run_native`` builds a
   ``native_search`` callable from Track A's detection truth and threads it into
   the loop (→ ``verify.cross_check``); no native capability ⇒ ``None`` (the
   single-lane behavior stays byte-identical).
2. The gate-2 honesty chain: a keyless-floor retrieval ANYWHERE in a research
   run stamps the published brief ``backend="keyless-fallback"`` (web_search
   tool → run-scoped telemetry → engine payload), and the synthetic
   auto-publish forwards ``backend`` verbatim so the UI nudge can fire.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import config
from services import agent_runtime
from services.agent_tools import deep_research, web_search
from services.research.depth import PROFILES


class _StubToolCall:
    def __init__(self, tool_call_id: str = "tc-1") -> None:
        self.tool_call_id = tool_call_id


def _stub_brief() -> Any:
    class _Brief:
        def to_dict(self) -> dict[str, Any]:
            return {"query": "q", "symbol": "TEST", "markdown": "## x", "sources": []}

    return _Brief()


def test_run_native_threads_native_search_into_the_loop(monkeypatch) -> None:
    """tier_a + native-capable chat model ⇒ the loop receives a callable."""
    captured: dict[str, Any] = {}

    async def fake_run_loop(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return _stub_brief()

    monkeypatch.setattr(deep_research, "_run_loop", fake_run_loop)
    creds_token = config.set_request_llm_creds("openrouter", "x-ai/grok-4.3", "k")
    mws_token = config.set_request_model_web_search("native")
    try:
        out = asyncio.run(
            deep_research._run_native("q", PROFILES["deep"], rounds=1, wall=30)
        )
    finally:
        config.reset_request_llm_creds(creds_token)
        config._model_web_search_ctx.reset(mws_token)
    assert out["ok"] is True
    assert callable(captured.get("native_search")), (
        "B4 wiring: a native-capable model must thread a native_search callable "
        "into the loop (it was None — the cross-verify would stay dormant)"
    )


def test_run_native_keeps_single_lane_without_native_capability(monkeypatch) -> None:
    """No native search (e.g. deepseek) ⇒ native_search is None — byte-identical lane."""
    captured: dict[str, Any] = {}

    async def fake_run_loop(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return _stub_brief()

    monkeypatch.setattr(deep_research, "_run_loop", fake_run_loop)
    creds_token = config.set_request_llm_creds("deepseek", "deepseek-v4-flash", "k")
    try:
        out = asyncio.run(
            deep_research._run_native("q", PROFILES["deep"], rounds=1, wall=30)
        )
    finally:
        config.reset_request_llm_creds(creds_token)
    assert out["ok"] is True
    assert captured.get("native_search") is None


def test_keyless_floor_retrieval_stamps_the_published_brief(monkeypatch) -> None:
    """Gate 2: a floor-served search inside the run flips the brief's backend id."""

    async def fake_run_loop(**kwargs: Any) -> Any:
        # Simulate a researcher (child task) whose web_search served via the floor.
        telemetry = config.get_search_telemetry()
        assert telemetry is not None, "the engine must open telemetry before the loop"
        telemetry["keyless_fallback_searches"] = 3
        return _stub_brief()

    monkeypatch.setattr(deep_research, "_run_loop", fake_run_loop)
    creds_token = config.set_request_llm_creds("deepseek", "deepseek-v4-flash", "k")
    try:
        out = asyncio.run(
            deep_research._run_native("q", PROFILES["deep"], rounds=1, wall=30)
        )
    finally:
        config.reset_request_llm_creds(creds_token)
    assert out["backend"] == "keyless-fallback"


def test_searxng_served_run_keeps_native_backend(monkeypatch) -> None:
    """No floor hit ⇒ the engine id stays 'native' (no false nudge)."""

    async def fake_run_loop(**kwargs: Any) -> Any:
        return _stub_brief()

    monkeypatch.setattr(deep_research, "_run_loop", fake_run_loop)
    creds_token = config.set_request_llm_creds("deepseek", "deepseek-v4-flash", "k")
    try:
        out = asyncio.run(
            deep_research._run_native("q", PROFILES["deep"], rounds=1, wall=30)
        )
    finally:
        config.reset_request_llm_creds(creds_token)
    assert out["backend"] == "native"


def test_web_search_floor_records_run_telemetry(monkeypatch) -> None:
    """The web_search tool bumps the run's shared telemetry when the floor serves."""

    class _Backend:
        pass

    async def fake_resolve(region: str) -> Any:
        return _Backend(), web_search.KEYLESS_FALLBACK_BACKEND_ID

    async def fake_dispatch(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"ok": True, "results": [], "citations": []}

    monkeypatch.setattr(web_search, "_resolve_backend", fake_resolve)
    monkeypatch.setattr(web_search, "_dispatch", fake_dispatch)

    telemetry = config.begin_search_telemetry()
    out = asyncio.run(web_search._web_search({"query": "tcs results"}))
    assert out["backend"] == web_search.KEYLESS_FALLBACK_BACKEND_ID
    assert telemetry["keyless_fallback_searches"] == 1
    # And again — the counter accumulates across the run's searches.
    asyncio.run(web_search._web_search({"query": "tcs dividend"}))
    assert telemetry["keyless_fallback_searches"] == 2


def test_auto_publish_forwards_the_backend_id() -> None:
    """The synthetic publish_brief carries the engine's honest backend verbatim."""
    bundle = {
        "ok": True,
        "query": "TCS",
        "symbol": "TCS",
        "markdown": "## Brief\nText [1].",
        "sources": [{"url": "https://nseindia.com/x", "title": "t"}],
        "backend": "keyless-fallback",
    }
    event = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(bundle))
    assert event is not None
    assert event.input["backend"] == "keyless-fallback"

    bundle["backend"] = "research-model:perplexity/sonar"
    event2 = agent_runtime._auto_publish_event(_StubToolCall(), json.dumps(bundle))
    assert event2 is not None
    assert event2.input["backend"] == "research-model:perplexity/sonar"
