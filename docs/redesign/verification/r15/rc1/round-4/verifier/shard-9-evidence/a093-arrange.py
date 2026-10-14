import asyncio
from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage
from services import agent_runtime
class P:
    n=0
    async def stream_chat(self, messages, model, api_key=None, **kw):
        P.n+=1
        if P.n==1:
            yield LLMToolUseEvent(tool_call_id="", name="arrange_layout", input={"pattern":"custom","panels":["chart","news"]})
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
        else:
            yield LLMDeltaEvent(text="done"); yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
async def main():
    agent_runtime.reload()
    agent_runtime.get_provider = lambda *_a, **_k: P()
    try:
        async for ev in agent_runtime.invoke_agent(agent_id="copilot", prompt="Lay out a custom desk with the chart and news panels", api_key="k", provider="ollama", mode="agent", autonomy="auto"):
            print(type(ev).__name__, str(getattr(ev,'model_dump',lambda:ev)())[:220])
    except Exception as x:
        print("INVOKE RAISED", type(x).__name__, x)
asyncio.run(main())
