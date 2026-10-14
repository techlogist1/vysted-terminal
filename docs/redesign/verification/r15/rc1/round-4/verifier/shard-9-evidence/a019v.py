import asyncio, sys
sys.path.insert(0, "tests")
from test_b3_runtime_intent_gate import _CaptureProvider, _DATA_WRITES
from services import agent_runtime, planner
async def tools(prompt):
    agent_runtime.reload()
    p = _CaptureProvider()
    agent_runtime.get_provider = lambda *_a, **_k: p
    async for _ in agent_runtime.invoke_agent(agent_id="copilot", prompt=prompt, api_key="k", provider="ollama", mode="agent"):
        pass
    return set(p.tool_ids)
CASES = [
 # acceptance (entry)
 ("Would you scrap my ITC position?", "portfolio_delete_position"),
 ("Could you drop WIPRO from my portfolio?", "portfolio_delete_position"),
 ("Can you bump my INFY quantity to 30?", "portfolio_update_position"),
 ("Can you log 10 TCS at 3400 in my portfolio?", "portfolio_add_position"),
 # fresh, not in tests
 ("Is it possible to add 10 SBIN at 800 to my portfolio?", "portfolio_add_position"),
 ("Any chance you could get rid of my TCS position?", "portfolio_delete_position"),
 ("Mind noting that INFY cut its guidance?", "write_note"),
 ("Would it be possible to save this screen as defence picks?", "save_screen"),
 ("I sold all my WIPRO shares today.", "portfolio_delete_position"),
 ("Should you add 20 ITC at 410 to my portfolio?", "portfolio_add_position"),
 ("How about adding 15 HAL at 4200 to my portfolio?", "portfolio_add_position"),
 ("What if you noted that BEL order book is 75k cr?", "write_note"),
 ("Is there a way to filter the screener to P/E under 20?", "write_screener_filters"),
 ("Why not save my layout as morning desk?", "save_layout"),
 ("Kindly remove HDFC Bank from my portfolio", "portfolio_delete_position"),
 ("Record my purchase of 12 LT at 3600", "portfolio_add_position"),
]
CONTROLS = ["Is RELIANCE up today?", "How is my portfolio doing?", "what is P/E?", "Can you explain what a P/E ratio is?"]
async def main():
    for pr, need in CASES:
        t = await tools(pr)
        ic = planner.classify_intent(pr)
        print("KEEP" if need in t else "STRIP", "|", pr, "| need", need, "| intent", getattr(ic,"intent",ic), getattr(ic,"signals",None), "| n_tools", len(t))
    for pr in CONTROLS:
        t = await tools(pr)
        print("control", "STRIPS" if not (t & _DATA_WRITES) else "KEEPS "+str(t & _DATA_WRITES), "|", pr)
asyncio.run(main())
