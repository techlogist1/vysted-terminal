import asyncio
from services import corporate_disclosures as cd
from services.agent_tools import disclosure_tools as dt
calls = []
def fake(name):
    def f(bare, limit):
        calls.append((name, bare, limit)); return [], cd._covered_window([], limit, None, cd._today_ist(), False)
    return f
cd._fetch_nse_announcements = fake("NSE"); cd._fetch_bse_announcements = fake("BSE")
async def main():
    tool = dt._corporate_announcements
    async def step(label, coro):
        n = len(calls); r = await coro; print(f"{label}: +{len(calls)-n} network lane calls", r.get("ok") if isinstance(r, dict) else type(r).__name__)
    await step("research gather_floor  INFY limit=50", tool({"symbol": "INFY", "limit": 50}))
    await step("research researcher    INFY limit=50", tool({"symbol": "INFY", "limit": 50}))
    await step("panel route            INFY limit=50", cd.get_announcements_cached("INFY", None, 50))
    await step("fresh: deep.py default INFY (limit 20)", tool({"symbol": "INFY"}))
    await step("fresh: FAST INFY limit=20", tool({"symbol": "INFY", "limit": 20}))
    await step("fresh: INFY.NS limit=50", tool({"symbol": "INFY.NS", "limit": 50}))
    await step("fresh: transcripts tool (MAX 200)", cd.get_announcements_cached("INFY", None, cd.MAX_LIMIT))
asyncio.run(main())
