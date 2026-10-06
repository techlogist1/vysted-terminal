"""batch-22 verifier: tool surface sent to the provider per phrasing (cwd=<tree>/sidecar)."""
import asyncio, sys
sys.path.insert(0, ".")
import pytest
from services import agent_runtime
from models.llm import LLMDoneEvent, LLMUsage
class Cap:
    tool_ids = None
    async def stream_chat(self, messages, model, api_key=None, **kw):
        Cap.tool_ids = kw.get("tool_ids"); yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
# (expect_no_tools, prompt)
P = [
 (True, "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my total proceeds."),
 (True, "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 (True, "Don’t use any tools. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
 (True, "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds."),
 # verifier-fresh positives
 (True, "Skip the tools for this one — I hold 12 HDFCBANK at ₹1,600; add 3 more at ₹1,650, what is my average?"),
 (True, "Avoid calling any functions. I bought 40 ITC at ₹415; what did I spend?"),
 (True, "Zero tool calls please: 7 INFY at ₹1,500 — total cost?"),
 (True, "Work it out without tool use: 9 WIPRO at ₹260 sold at ₹270, profit?"),
 (True, "Do NOT use external data. I own 20 SBIN at ₹800, what is my cost basis?"),
 (True, "Please don’t invoke any tool — record nothing, just tell me 5 × ₹3,100."),
 # false-positive controls (should keep tools)
 (False, "Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS"),
 (False, "Only use data from price_data for the above symbols: TCS.NS"),
 (False, "Why did you not use the tools? Get the TCS.NS price now."),
 (False, "Why did you not use the tools"),
 (False, "Don't forget to use the tools to get the latest TCS.NS price."),
 (False, "Do not answer without using the tools: what is TCS.NS trading at?"),
 (False, "Never guess, always call the tools: what is INFY.NS trading at"),
 (False, "Not sure which tool to use — what is TCS.NS trading at?"),
 (False, "Don't use web search, get TCS.NS price"),
 (False, "No tools except price_data for TCS.NS"),
 (False, "Add 10 TCS at 3,200 to my portfolio"),
 (False, "What tools do you have?"),
 (False, "Answer using the latest data, not just from memory: TCS.NS price"),
 (False, "I don't trust your memory, use the tools to fetch INFY.NS fundamentals"),
]
async def main():
    for exp, p in P:
        mp = pytest.MonkeyPatch(); agent_runtime.reload(); Cap.tool_ids = None
        mp.setattr(agent_runtime, "get_provider", lambda *_a, **_k: Cap())
        async for _ in agent_runtime.invoke_agent(agent_id="copilot", prompt=p, api_key="k", provider="ollama", autonomy="ask", mode="agent"): pass
        mp.undo(); t = set(Cap.tool_ids or [])
        got_none = len(t) == 0
        ok = "OK " if got_none == exp else "BAD"
        print(f"{ok} expect_no_tools={exp} n_tools={len(t)} writes={sorted(x for x in t if x.startswith('portfolio_'))[:3]} price={'price_data' in t} | {p}")
asyncio.run(main())
