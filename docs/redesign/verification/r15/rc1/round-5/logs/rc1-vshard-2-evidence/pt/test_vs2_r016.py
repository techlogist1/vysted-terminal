import json, os
from typing import Any
from services.budget_guard import BudgetGuard
from services.research.iter import run_heavy_research, run_iter_research
from services.research.models import ResearchBrief
from tests.test_research_iter import FakeLLM, _run

FLOOR = [f"https://nsearchives.nseindia.com/corporate/PARAS_{i}.pdf" for i in range(3)]
WEB = "https://example-news.com/paras-order-win"

async def _tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "resolve_symbol":
        return {"ok": True, "status": "bound", "resolved": {"symbol": "PARAS.NS", "name": "Paras Defence and Space Technologies Ltd", "exchange": "NSE", "region": "IN", "asset_class": "equity", "confidence": 1.0, "isin": "INE045601015", "bse_code": "543367", "industry": None}}
    if name == "web_search":
        return {"ok": True, "citations": [{"url": WEB, "title": "Paras order win", "excerpt": "Paras Defence order", "source": "example-news.com"}], "results": []}
    if name == "price_data":
        return {"ok": True, "provider": "nse", "quote": {"symbol": "PARAS.NS", "price": 700.0}}
    if name == "corporate_announcements":
        return {"ok": True, "announcements": [
            {"ts": f"2026-0{7+i}-1{i}", "category": "Financial Results", "headline": f"Financial results Q{i+1}", "attachment_url": FLOOR[i], "exchange": "NSE"} for i in range(3)]}
    return {"ok": False, "error": f"stub: {name}"}

OUT = {}

def _urls(b):
    return [s.url for s in b.sources] if isinstance(b, ResearchBrief) else repr(b)[:300]

def test_ultra_three_angles_floor_rows_cited():
    b = _run(run_heavy_research("Paras Defence thesis", angles=3, region="IN", tool_call=_tool, llm_call=FakeLLM(reflect="complete"), budget=BudgetGuard(max_steps=30), min_web_domains=2))
    OUT["ultra_3_angles"] = _urls(b)
    assert all(u in _urls(b) for u in FLOOR)

def test_ultra_budget_starved_floor_rows_cited():
    b = _run(run_heavy_research("Paras Defence thesis", angles=2, region="IN", tool_call=_tool, llm_call=FakeLLM(reflect="complete"), budget=BudgetGuard(max_steps=1)))
    OUT["ultra_budget_1"] = _urls(b)
    assert all(u in _urls(b) for u in FLOOR)

def test_deep_parity():
    b = _run(run_iter_research("Paras Defence thesis", region="IN", tool_call=_tool, llm_call=FakeLLM(reflect="complete"), budget=BudgetGuard(max_steps=30)))
    OUT["deep"] = _urls(b)
    json.dump(OUT, open(os.environ["R016_OUT"], "w"), indent=1)
    assert all(u in _urls(b) for u in FLOOR)
