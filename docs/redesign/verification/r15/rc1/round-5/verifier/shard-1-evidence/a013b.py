import asyncio
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMUsage
from services import agent_runtime, run_manager
import tests.test_run_manager as T
class P:
    async def stream_chat(self, messages, model, api_key=None, **kw):
        for i in range(30):
            yield LLMDeltaEvent(text=f"[p{i:02d}] " + "margin and valuation commentary " * 3)
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=10, output_tokens=10))
agent_runtime.reload(); run_manager.reset_for_tests()
agent_runtime.get_provider = lambda *a, **k: P()
async def main():
    from routers import runs as R
    rid = run_manager.launch_run(agent_id="copilot", prompt="long single-round answer", api_key="sk")
    row = await T._await_terminal(rid)
    w = R.get_run(rid)
    a = w["answer"]
    print("status", row.status, "answer len", len(a), "has p00", "[p00]" in a, "has p29", "[p29]" in a, "ends", repr(a[-40:]))
    lst = R.list_runs() if hasattr(R, "list_runs") else None
    print("list digest lens", [len(str(x.get("digest") or "")) for x in (lst if isinstance(lst, list) else (lst or {}).get("runs", []))][:3])
asyncio.run(main())
