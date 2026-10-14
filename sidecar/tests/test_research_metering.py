"""R15-RESEARCH-009 / R15-AGENT-012: research LLM usage reaches the run guard.

The native DEEP/ULTRA loop calls the model through ONE ``llm_call`` seam in
``deep_research._run_native``. That seam now uses
``oneshot.complete_with_usage`` and folds each call's usage into the run's
``BudgetGuard``, whose token/spend ceilings come from the depth profile. An
adapter that reports no usage leaves the brief's cost UNKNOWN (null), never 0.
"""

from __future__ import annotations

import asyncio
import dataclasses
from typing import Any

import pytest

import config
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMUsage
from services import agent_tools
from services.agent_tools import deep_research
from services.llm import oneshot
from services.research import iter as iter_research
from services.research.deep import BUDGET_STOP_NOTE
from services.research.depth import PROFILES
from services.search import extract


def _route(messages: list[dict[str, Any]]) -> str:
    """Answer each research stage by its system prompt (the iter loop's roles)."""
    system = str(messages[0].get("content", "")).lower()
    if "planning the next round" in system:
        return "Sub-question A\nSub-question B"
    if "extract the key finding" in system:
        return "NVDA revenue grew 20% [1]"
    if "evolving research report" in system:
        return "REPORT: revenue grew [1]"
    if "reflect on research coverage" in system:
        return "gaps remain"
    return "# Brief\nRevenue grew [1]."


async def _fake_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "resolve_symbol":
        return {
            "ok": True,
            "resolved": {
                "symbol": "NVDA",
                "name": "NVIDIA Corporation",
                "exchange": "NASDAQ",
                "region": "US",
                "asset_class": "equity",
                "confidence": 0.97,
            },
        }
    if name == "web_search":
        return {
            "ok": True,
            "citations": [
                {
                    "url": "https://ex.com/a",
                    "title": "NVIDIA quarterly results",
                    "excerpt": "NVDA revenue grew",
                    "source": "ex.com",
                }
            ],
        }
    return {"ok": True, "provider": "test"}


@pytest.fixture
def native_run(monkeypatch: pytest.MonkeyPatch):
    """Run ``_run_native`` offline with a stubbed model that may report usage."""

    async def _no_visit(url: str, **_: Any) -> extract.VisitResult:
        return extract.VisitResult(None)

    async def _snapshot(tool_call: Any, symbol: str, **_: Any) -> dict[str, Any]:
        return {"price": {"ok": True, "provider": "test", "data": {"price": 181.2}}}

    monkeypatch.setattr(agent_tools, "invoke_tool", _fake_tool)
    monkeypatch.setattr(iter_research, "snapshot_structured", _snapshot)
    monkeypatch.setattr(extract, "visit_for_research", _no_visit)
    monkeypatch.setattr(config, "get_step_sink", lambda: None)

    def _run(profile: Any, usage: LLMUsage | None) -> dict[str, Any]:
        calls: list[int] = []

        async def _fake_complete_with_usage(provider, model, api_key, messages, *, timeout=None):  # noqa: ANN001
            calls.append(1)
            return _route(messages), usage

        monkeypatch.setattr(oneshot, "complete_with_usage", _fake_complete_with_usage)
        token = config.set_request_llm_creds("openai", "gpt-4.1", "sk-test")
        try:
            out = asyncio.run(deep_research._run_native("research NVDA", profile, 3, 120))
        finally:
            config.reset_request_llm_creds(token)
        out["_llm_calls"] = len(calls)
        return out

    return _run


def test_complete_with_usage_returns_the_done_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """The adapter's ``done`` usage comes back beside the text; ``complete`` stays ``str``."""

    class _Adapter:
        async def stream_chat(self, **_: Any):
            yield LLMDeltaEvent(text="hel")
            yield LLMDeltaEvent(text="lo")
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=120, output_tokens=30))

    monkeypatch.setattr(oneshot, "get_provider", lambda _p, **_k: _Adapter())
    text, usage = asyncio.run(
        oneshot.complete_with_usage("openai", "gpt-4.1", "k", [{"role": "user", "content": "q"}])
    )
    assert text == "hello"
    assert usage is not None and usage.input_tokens == 120 and usage.output_tokens == 30
    plain = asyncio.run(
        oneshot.complete("openai", "gpt-4.1", "k", [{"role": "user", "content": "q"}])
    )
    assert plain == "hello"


def test_deep_run_with_reported_usage_has_a_nonzero_cost(native_run) -> None:
    out = native_run(PROFILES["deep"], LLMUsage(input_tokens=2000, output_tokens=500))
    assert out["ok"] is True
    assert out["_llm_calls"] > 0
    assert out["cost"]["tokens"] == 2500 * out["_llm_calls"]
    assert out["cost"]["spend_usd"] > 0


def test_tiny_spend_ceiling_breaches_and_forces_synthesis(native_run) -> None:
    """A spend ceiling from the depth profile takes the loop's abort→synthesize path."""
    profile = dataclasses.replace(PROFILES["deep"], max_spend_usd=0.0001)
    out = native_run(profile, LLMUsage(input_tokens=2000, output_tokens=500))
    assert out["ok"] is True
    assert out["markdown"].strip()
    assert any("spend ceiling" in s["detail"] for s in out["steps"]), [
        s["detail"] for s in out["steps"]
    ]
    # The user-facing note names a budget stop that covers spend, not "time" only.
    assert out["note"] == BUDGET_STOP_NOTE and "spend" in BUDGET_STOP_NOTE


def test_unmeasured_usage_reports_unknown_cost_not_zero(native_run) -> None:
    out = native_run(PROFILES["deep"], None)
    assert out["ok"] is True
    assert out["cost"]["tokens"] is None
    assert out["cost"]["spend_usd"] is None


def test_research_guard_takes_its_ceilings_from_the_depth_profile() -> None:
    for depth in ("deep", "ultra"):
        profile = PROFILES[depth]
        guard = deep_research._research_budget(profile, profile.rounds, profile.wall_seconds)
        assert guard.max_tokens == profile.max_tokens > 0
        assert guard.max_spend_usd == profile.max_spend_usd > 0
