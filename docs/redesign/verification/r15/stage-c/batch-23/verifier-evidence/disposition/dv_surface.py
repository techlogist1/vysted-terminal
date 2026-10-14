"""Tool surface sent to the provider per phrasing on the shipping head (cwd=<tree>/sidecar), agent mode."""
import asyncio, sys
sys.path.insert(0, "."); sys.path.insert(0, sys.argv[1])
import pytest
from services import agent_runtime
from models.llm import LLMDoneEvent, LLMUsage
from dv_prompts import MISS, KEEP, OVER, L38, L37
class Cap:
    tool_ids = None
    async def stream_chat(self, messages, model, api_key=None, **kw):
        Cap.tool_ids = kw.get("tool_ids"); yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
async def main():
    for name, group in (("MISS", MISS), ("KEEP", KEEP), ("OVER", OVER), ("L38", L38), ("L37", L37)):
        for tag, p in group:
            mp = pytest.MonkeyPatch(); agent_runtime.reload(); Cap.tool_ids = None
            mp.setattr(agent_runtime, "get_provider", lambda *_a, **_k: Cap())
            async for _ in agent_runtime.invoke_agent(agent_id="copilot", prompt=p, api_key="k", provider="ollama", autonomy="ask", mode="agent"): pass
            mp.undo(); t = set(Cap.tool_ids or [])
            print(f"{name:4} {tag:28} n_tools={len(t):2} writes={sorted(x for x in t if x.startswith('portfolio_'))} price={'price_data' in t} | {p}")
asyncio.run(main())
