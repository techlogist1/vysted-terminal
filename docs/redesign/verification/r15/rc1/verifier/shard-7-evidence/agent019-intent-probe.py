import asyncio, sys
from typing import Any
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMUsage
from services import agent_runtime, planner
class Cap:
    tool_ids=None
    async def stream_chat(self, messages, model, api_key=None, **kw):
        self.tool_ids=list(kw["tool_ids"]); yield LLMDeltaEvent(text="ok"); yield LLMDoneEvent(usage=LLMUsage(input_tokens=1,output_tokens=1))
async def ids(prompt):
    agent_runtime.reload(); p=Cap(); agent_runtime.get_provider=lambda *a,**k:p
    async for _ in agent_runtime.invoke_agent(agent_id="copilot",prompt=prompt,api_key="k",provider="ollama",mode="agent"): pass
    return set(p.tool_ids)
CASES=[
 ("Can you log 10 TCS at 3400 in my portfolio?","portfolio_add_position"),
 ("Can you record that I hold 20 ITC at 410?","portfolio_add_position"),
 ("Write a note on Cochin Shipyard: valuation looks stretched at ~54x trailing P/E; revisit after Q2 results.","write_note"),
 ("Delete TCS from my portfolio","portfolio_delete_position"),
 # fresh
 ("Could you drop WIPRO from my portfolio?","portfolio_delete_position"),
 ("Please get rid of my HDFC Bank holding","portfolio_delete_position"),
 ("I picked up 50 shares of ITC at 420 today","portfolio_add_position"),
 ("Can you mark that I purchased 5 BEL at 280?","portfolio_add_position"),
 ("I own 100 SBIN at 800 - please track that","portfolio_add_position"),
 ("Would you make a note that L&T margins are improving?","write_note"),
 ("Could you filter for PSU banks with P/E under 10?","write_screener_filters"),
 ("Can you save this layout as morning desk?","save_layout"),
 ("I exited my ITC position, can you take it out of my portfolio?","portfolio_delete_position"),
 ("Can you bump my INFY quantity to 30?","portfolio_update_position"),
 ("Show me stocks with ROE above 20% and debt to equity below 0.5","write_screener_filters"),
 ("Add HAL to my notes: order book 1.9 lakh crore","write_note"),
 ("what is P/E?",None),
 ("How is my portfolio doing?",None),
]
async def main():
    for pr,need in CASES:
        t=await ids(pr); intent=planner.classify_intent(pr)
        w=sorted(t & {"write_note","write_screener_filters","save_screen","save_layout","portfolio_add_position","portfolio_update_position","portfolio_delete_position"})
        ok = (need in t) if need else (not w)
        print(("PASS" if ok else "FAIL"), repr(pr)[:62].ljust(64), "need",need,"| intent",getattr(intent,'intent',intent),"| writes",w)
asyncio.run(main())
