"""R15-RESEARCH-005: a synthesis that never comes back is stated, not misattributed.

On the local lane every distill/synthesis call hit the fixed 60 s cap, the
structured floor shipped with "web coverage is thin" although web sources were
captured, raw floats reached the body, and no degraded reason was recorded.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import config
from services import agent_tools
from services.agent_tools import deep_research
from services.llm import oneshot
from services.research import deep
from services.research import iter as iter_research
from services.research.depth import PROFILES
from services.search import extract

_THIN = "Web coverage for this name is thin"


async def _india_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "resolve_symbol":
        return {
            "ok": True,
            "resolved": {
                "symbol": "CGPOWER",
                "name": "CG Power and Industrial Solutions",
                "exchange": "NSE",
                "region": "IN",
                "asset_class": "equity",
                "confidence": 0.98,
            },
        }
    if name == "web_search":
        return {
            "ok": True,
            "citations": [
                {
                    "url": "https://news.example.in/cg-power-order-book",
                    "title": "CG Power and Industrial Solutions order book grows",
                    "excerpt": "CG Power order book rose on railway demand",
                    "source": "news.example.in",
                }
            ],
        }
    if name == "corporate_announcements":
        return {"ok": True, "announcements": []}
    return {"ok": True, "provider": "test"}


async def _snapshot(tool_call: Any, symbol: str, **_: Any) -> dict[str, Any]:
    """The price + fundamentals legs as ``snapshot_structured`` shapes them (offline)."""
    return {
        "price": {
            "ok": True,
            "provider": "yfinance",
            "data": {"price": 896.1, "change_percent": -1.527472527472525, "currency": "INR"},
        },
        "fundamentals": {
            "ok": True,
            "provider": "yfinance",
            "data": {"currency": "INR", "market_cap": 1411777036288.0, "pe_ratio": 113.143936},
        },
    }


@pytest.fixture
def local_run(monkeypatch: pytest.MonkeyPatch):
    """A DEEP run on the local lane whose every model call outlives the cap."""

    async def _no_visit(url: str, **_: Any) -> str | None:
        return None

    seen: dict[str, Any] = {}

    async def _slow_model(provider, model, api_key, messages, *, timeout=None):  # noqa: ANN001
        seen["timeout"] = timeout
        seen["loop_cap"] = deep.LLM_CALL_TIMEOUT.get(None)
        await asyncio.sleep(5)
        return "never", None

    monkeypatch.setattr(agent_tools, "invoke_tool", _india_tool)
    monkeypatch.setattr(iter_research, "snapshot_structured", _snapshot)
    monkeypatch.setattr(extract, "visit_for_research", _no_visit)
    monkeypatch.setattr(config, "get_step_sink", lambda: None)
    monkeypatch.setattr(oneshot, "complete_with_usage", _slow_model)
    monkeypatch.setattr(deep_research, "_LOCAL_LLM_CALL_TIMEOUT_SECS", 0.05)

    def _run() -> dict[str, Any]:
        token = config.set_request_llm_creds("ollama", "llama3.1:8b", None)
        try:
            out = asyncio.run(
                deep_research._run_native("CG Power outlook", PROFILES["deep"], 1, 60)
            )
        finally:
            config.reset_request_llm_creds(token)
        out["_seen"] = seen
        return out

    return _run


def test_synthesis_timeout_with_web_sources_is_stated_not_called_thin(local_run) -> None:
    out = local_run()
    assert out["ok"] is True
    assert any(s["url"].startswith("http") for s in out["sources"]), "web sources were captured"
    assert out["degraded_reason"] == deep.SYNTHESIS_TIMEOUT_REASON
    assert deep.SYNTHESIS_TIMEOUT_NOTE in (out["note"] or "")
    md = out["markdown"]
    assert _THIN not in md
    # Floor money in crore, the change as a rounded percent: never a raw float.
    assert "₹141,178 cr" in md
    assert "-1.53%" in md
    assert "1411777036288" not in md and "1.527472527472525" not in md


def test_local_lane_raises_the_per_call_cap_for_adapter_and_loop(local_run) -> None:
    """The adapter cap and the loop's universal cap move together on the local lane."""
    out = local_run()
    assert out["_seen"]["timeout"] == 0.05
    assert out["_seen"]["loop_cap"] == 0.05
    assert deep.LLM_CALL_TIMEOUT.get(None) is None  # reset after the run


def test_floor_with_zero_web_sources_still_says_thin_coverage() -> None:
    structured = {
        "price": {"ok": True, "provider": "bse", "data": {"price": 142.5, "currency": "INR"}},
    }
    thin = deep.build_structured_floor(
        query="KSE outlook", symbol="KSE", structured=structured, web_sources=0
    )
    assert thin is not None and _THIN in thin
    assert "₹142.50" in thin
    sourced = deep.build_structured_floor(
        query="KSE outlook", symbol="KSE", structured=structured, web_sources=4
    )
    assert sourced is not None and _THIN not in sourced
    assert "4 web source(s)" in sourced
