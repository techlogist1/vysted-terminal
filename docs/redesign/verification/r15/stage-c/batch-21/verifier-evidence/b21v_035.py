"""batch-21 verifier: tool surface sent to the provider per no-tool phrasing (cwd=<tree>/sidecar)."""
import asyncio, sys
sys.path.insert(0, ".")
import pytest
from services import agent_runtime
from models.llm import LLMDoneEvent, LLMUsage
class Cap:
    tool_ids = None
    async def stream_chat(self, messages, model, api_key=None, **kw):
        Cap.tool_ids = kw.get("tool_ids"); yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
P = ["I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and my total proceeds.",
 "Please answer without using any tools: I own 30 ITC shares at ₹410 and will add 10 more at ₹420. What's my new average cost?",
 "No tools please. I bought 15 WIPRO shares at ₹250 and sold them at ₹262. What was my profit?",
 "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my total proceeds.",
 "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my proceeds.",
 "Don’t use any tools. I sold 5 TCS shares at ₹3,100 each; restate my proceeds.",
 "Add 10 TCS at 3,200 to my portfolio"]
async def main():
    for mode in ("agent", None):
        for p in P:
            mp = pytest.MonkeyPatch(); agent_runtime.reload(); Cap.tool_ids = None
            mp.setattr(agent_runtime, "get_provider", lambda *_a, **_k: Cap())
            kw = {"mode": mode} if mode else {}
            async for _ in agent_runtime.invoke_agent(agent_id="copilot", prompt=p, api_key="k", provider="ollama", autonomy="ask", **kw): pass
            mp.undo(); t = set(Cap.tool_ids or [])
            print(f"mode={mode} n_tools={len(t)} writes={sorted(x for x in t if x.startswith('portfolio_'))} | {p[:60]}")
asyncio.run(main())
