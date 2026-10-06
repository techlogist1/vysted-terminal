import sys, asyncio, time; sys.path.insert(0, sys.argv[1])
from services.llm import openai as oa, oneshot
from models.llm import LLMToolUseEvent, LLMUsage, LLMDoneEvent, LLMDeltaEvent
calls=[0]
class Hang:
    async def stream_chat(self, **k):
        calls[0]+=1
        await asyncio.sleep(3600); yield None
class Slowok:
    async def stream_chat(self, **k):
        calls[0]+=1
        yield LLMDeltaEvent(text='{"nope": 1}')
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=100, output_tokens=7), finish_reason="stop")
async def run(adapter, provider):
    calls[0]=0
    oneshot.get_provider = lambda p: adapter
    oa._REPAIR_TIMEOUT_S = 0.5
    p = oa.OpenAIProvider(provider_id=provider)
    evs=[LLMToolUseEvent(tool_call_id=f"c{i}", name="price_data", input={"sym": "X"}) for i in range(5)]
    repairs=[]
    t=time.monotonic()
    out = await p._resolve_tool_events(evs, [], model="m", api_key="k", repairs=repairs)
    return calls[0], round(time.monotonic()-t,2), [list(o.input)[0] for o in out], repairs
import inspect
print("OpenAIProvider init sig:", inspect.signature(oa.OpenAIProvider.__init__))
for name, ad, prov in [("hang/openai", Hang(), "openai"), ("hang/openrouter", Hang(), "openrouter"), ("invalid-reply/openrouter", Slowok(), "openrouter")]:
    print(name, asyncio.run(run(ad, prov)))
print("cap", oa._MAX_REPAIRS_PER_ROUND)
