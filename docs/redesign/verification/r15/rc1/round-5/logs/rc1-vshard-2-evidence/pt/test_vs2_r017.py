import asyncio, json, os
from typing import Any
import pytest
from services import agent_tools
from services.agent_tools import deep_research
from services.budget_guard import BudgetGuard
from services.research import iter as iter_research
from services.research.depth import PROFILES
from services.research.models import ResearchBrief
from tests.test_research_iter import FakeLLM
from tests.test_research_iter import _kse_floor_tool_factory

OUT = {}

async def _llm(msgs):
    return await FakeLLM(reflect="complete")(msgs)

def _go(depth):
    try:
        r = asyncio.run(deep_research._run_loop(profile=PROFILES[depth], query="research KSE", llm_call=FakeLLM(reflect="complete"), budget=BudgetGuard(max_steps=12)))
        return {k: r.get(k) for k in ("ok", "execution_loop", "degraded_reason")} if isinstance(r, dict) else {"brief": type(r).__name__}
    except Exception as e:
        return {"ESCAPED": f"{type(e).__name__}: {e}"}

@pytest.mark.parametrize("where", ["snapshot_structured", "resolve_target"])
def test_real_loop_raise_parity(monkeypatch, where):
    monkeypatch.setattr(agent_tools, "invoke_tool", _kse_floor_tool_factory())
    async def boom(*a, **k):
        raise ValueError(f"{where} exploded")
    monkeypatch.setattr(iter_research, where, boom)
    OUT[where] = {"deep": _go("deep"), "ultra": _go("ultra")}
    d, u = OUT[where]["deep"], OUT[where]["ultra"]
    json.dump(OUT, open(os.environ["R017_OUT"], "w"), indent=1)
    assert "ESCAPED" not in d and "ESCAPED" not in u
    assert d["ok"] is False and u["ok"] is False

def test_cross_check_raise_probe(monkeypatch):
    monkeypatch.setattr(agent_tools, "invoke_tool", _kse_floor_tool_factory())
    import services.research.verify as verify
    async def boom(*a, **k):
        raise ValueError("cross_check exploded")
    monkeypatch.setattr(verify, "cross_check", boom)
    OUT["cross_check_ultra"] = _go("ultra")
    json.dump(OUT, open(os.environ["R017_OUT"], "w"), indent=1)
