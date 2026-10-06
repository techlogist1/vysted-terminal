import asyncio, time, sys
from services.budget_guard import BudgetGuard
from services.research import deep
from services.research.models import ResearchBrief
from services.research.verify import cross_check
async def tool_call(name, args):
    await asyncio.sleep(0.01)
    return {"ok": True, "results": [{"url": f"https://www.site{i}news.com/x", "title": "t", "snippet": "revenue 100 crore"} for i in range(3)]}
def mk(extract_s, verdict_s):
    async def llm(messages):
        sysmsg = messages[0]["content"]
        if sysmsg.startswith("List the most important NUMERIC"):
            await asyncio.sleep(extract_s)
            return "\n".join(f"Revenue was {i}00 crore in FY26" for i in range(1,6))
        await asyncio.sleep(verdict_s)
        return "AGREE"
    return llm
async def run(label, extract_s, verdict_s, wall, cap):
    tok = deep.LLM_CALL_TIMEOUT.set(cap)
    b = ResearchBrief(query="q", symbol="SMR", mode="ultra", markdown="Revenue 100 crore; margin 12%")
    g = BudgetGuard(max_steps=6, max_wall_seconds=wall)
    t = time.monotonic()
    out = await cross_check(b, tool_call=tool_call, llm_call=mk(extract_s, verdict_s), budget=g)
    el = time.monotonic() - t
    cc = out.structured.get("cross_check", {})
    print(f"{label}: wall={wall}s elapsed={el:.2f}s claims={len(cc.get('claims',[]))} verdicts={[c['verdict'] for c in cc.get('claims',[])]}")
    deep.LLM_CALL_TIMEOUT.reset(tok)
async def main():
    await run("A literal: 5 slow verdicts (3s each), fast extract", 0.0, 3.0, 2.0, 60)
    await run("B fresh: slow extract (5s), fast verdicts", 5.0, 0.0, 0.5, 60)
    await run("C fresh: slow extract 4s + slow verdicts 3s", 4.0, 3.0, 2.0, 150)
asyncio.run(main())
