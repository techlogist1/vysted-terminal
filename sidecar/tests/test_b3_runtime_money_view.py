"""R15-AGENT-001: the model reads research money only as scaled displays.

The research tool message carried ``fundamentals.market_cap = 2895037857792.0``
next to its ``"₹289,504 cr"`` display; llama3.1:8b read the float and said
"Rs 2,895,037 cr" (10x). The model-facing view replaces money scalars with the
semantics display; the auto-published brief keeps the raw bundle.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent, LLMUsage
from services import agent_runtime
from services.research.semantics import derive_semantics, display_value
from services.search.scrub import GUARD_CLOSE, GUARD_OPEN


def _research_payload(symbol: str, price: float, fund: dict[str, Any]) -> dict[str, Any]:
    structured: dict[str, Any] = {
        "price": {"ok": True, "provider": "nse_direct", "data": {"symbol": symbol, "price": price}},
        "fundamentals": {"ok": True, "provider": "yfinance", "data": {"symbol": symbol, **fund}},
    }
    structured["derived"] = derive_semantics(structured, "IN", symbol=symbol)
    return {
        "ok": True,
        "query": f"research {symbol}",
        "symbol": symbol,
        "structured": structured,
        "execution": {"run_id": "run-1", "loop": "fast", "requested_depth": "normal"},
    }


_BEL = _research_payload(
    "BEL",
    396.0,
    {
        "currency": "INR",
        "market_cap": 2895037857792.0,
        "shares_outstanding": 7309575000.0,
        "pe_ratio": 52.1,
    },
)

_KPIT = _research_payload(
    "KPITTECH",
    529.05,
    {
        "currency": "INR",
        "market_cap": 144021815296.0,
        "revenue_ttm": 65911640064.0,
        "net_income_ttm": 5826180096.0,
        "shares_outstanding": 272227219.0,
        "pe_ratio": 24.88476,
    },
)


class _ResearchThenAnswerProvider:
    def __init__(self) -> None:
        self.round_messages: list[list[LLMMessage]] = []

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **_: Any
    ) -> AsyncIterator[Any]:
        self.round_messages.append(list(messages))
        if len(self.round_messages) == 1:
            yield LLMToolUseEvent(tool_call_id="r-1", name="research", input={"query": "x"})
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
            return
        yield LLMDeltaEvent(text="ok")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))


async def _run(monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]) -> tuple[str, list[Any]]:
    agent_runtime.reload()
    provider = _ResearchThenAnswerProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)

    async def _fake_dispatch(_call: Any, _local: Any = None) -> AsyncIterator[Any]:
        yield agent_runtime._ToolDone(json.dumps(payload))

    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _fake_dispatch)
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot", prompt="research it", api_key="k", mode="edit"
        )
    ]
    tool_msg = next(m for m in provider.round_messages[1] if m.role == "tool")
    # Research text is third-party, so the message is fenced (R15-AGENT-021);
    # the JSON body sits inside the guard after its "Source:" line.
    body = tool_msg.content.split(GUARD_OPEN, 1)[1].split(GUARD_CLOSE, 1)[0]
    return body.strip().split("\n", 1)[1], events


@pytest.mark.asyncio
async def test_bel_market_cap_reaches_the_model_only_as_its_crore_display(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content, _ = await _run(monkeypatch, _BEL)
    assert "2895037857792" not in content
    assert display_value(2895037857792.0, "currency", "INR") in content
    assert "₹289,504 cr" in content
    # Non-money numbers are kept as numbers.
    assert json.loads(content)["structured"]["fundamentals"]["data"]["pe_ratio"] == 52.1


@pytest.mark.asyncio
async def test_kpit_statement_sizes_reach_the_model_only_as_displays(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content, _ = await _run(monkeypatch, _KPIT)
    for raw in ("144021815296", "65911640064", "5826180096"):
        assert raw not in content
    data = json.loads(content)["structured"]["fundamentals"]["data"]
    assert data["revenue_ttm"] == display_value(65911640064.0, "currency", "INR")
    assert data["net_income_ttm"] == display_value(5826180096.0, "currency", "INR")


@pytest.mark.asyncio
async def test_auto_publish_keeps_the_raw_market_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    _, events = await _run(monkeypatch, _BEL)
    brief = next(e for e in events if isinstance(e, LLMToolUseEvent) and e.name == "publish_brief")
    raw = brief.input["structured"]["fundamentals"]["data"]["market_cap"]
    assert raw == 2895037857792.0
