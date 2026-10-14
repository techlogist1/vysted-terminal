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
 (True, "Please answer from memory only: what's 12% of ₹5,000?"),
 (True, "No function calls. I bought 15 WIPRO at ₹250; total cost?"),
 (True, "Never use tools for this: add 5 TCS at ₹3,000 to my holdings."),
 (True, "Refrain from calling any tools and restate my 5 TCS at ₹3,100."),
 (True, "Do not run any lookups — just compute 8 × ₹1,200."),
 (True, "The tools must not be used here. I hold 10 INFY at ₹1,500; cost?"),
 (True, "Answer strictly from what I told you: I own 20 SBIN at ₹800, cost basis?"),
 (True, "DON'T USE TOOLS. Sell 5 ITC at ₹420 from my portfolio."),
 (True, "Without using functions, add 3 HDFCBANK at ₹1,650 to my holdings and tell me the total."),
 (True, "no tool calls — I sold 4 TCS at ₹3,200, what did I get?"),
 (False, "Could you use the tools to get HDFCBANK.NS price?"),
 (False, "Please use your tools and fetch WIPRO.NS's close."),
 (False, "I never said don't use tools — get RELIANCE.NS price."),
 (False, "Don't rely on memory; get TCS.NS price with the tools."),
 (False, "Don't use any tools other than price data: TCS.NS close?"),
 (False, "Don't search the web; what is SBIN.NS trading at?"),
 (False, "No need to avoid the tools this time: what is SBIN.NS at?"),
 (False, "Don't just use the tools blindly — check the TCS.NS price and explain the move."),
 (False, "Never call the tools twice for one symbol; get the INFY.NS price."),
 (False, "Don't call functions you don't need, just get me SBIN.NS's latest price."),
 (False, "No lookups needed for TCS, I know it; what is ITC.NS trading at?"),
 (False, "Never use the search tools, only the quote: INFY.NS price?"),
 (False, "Don't use the tools for arithmetic; get the TCS.NS price."),
 (False, "Don't use tools for the math, but do fetch the TCS.NS price."),
 (False, "Do not call the tools again for TCS, just get INFY.NS price."),
 (False, "What is TCS.NS at? Don't call the news tool."),
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
