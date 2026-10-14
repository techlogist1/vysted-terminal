import asyncio, sys, time
sys.path.insert(0, ".")
from services.research.models import ResearchBrief
from services.research.verify import cross_check
from services.budget_guard import BudgetGuard

CLAIMS = "\n".join(f"Revenue grew {i}% in Q{i}" for i in range(1, 6))  # 5 numeric claims

async def slow_llm_call(messages):
    # extraction call returns claims instantly; verdict calls are the slow ones
    sys_content = messages[0]["content"] if messages else ""
    if "NUMERIC claims" in sys_content:
        return CLAIMS
    await asyncio.sleep(60)  # a slow verdict turn
    return "VERDICT: confirmed\nDETAIL: matches"

async def fake_tool_call(name, args):
    return {"ok": True, "results": [
        {"url": "https://a.example.com/x", "title": "t", "snippet": "s"},
        {"url": "https://b.example.com/y", "title": "t2", "snippet": "s2"},
    ]}

async def main():
    brief = ResearchBrief(query="q", symbol="TEST", mode="deep", markdown="Revenue grew 5% in Q5")
    budget = BudgetGuard(max_wall_seconds=0.3)
    t0 = time.monotonic()
    result = await cross_check(
        brief, region="IN", tool_call=fake_tool_call, llm_call=slow_llm_call,
        budget=budget, min_domains=1,
    )
    dt = time.monotonic() - t0
    print(f"cross_check wall time: {dt:.2f}s (budget wall was 0.3s)")
    cc = result.structured.get("cross_check")
    print("structured.cross_check:", cc)
    print("PASS: returned within 1s of the 0.3s wall" if dt < 1.0 else "FAIL: exceeded 1s")

asyncio.run(main())
