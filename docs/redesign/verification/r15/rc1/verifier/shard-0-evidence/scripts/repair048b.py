import asyncio, sys, time
sys.path.insert(0, '.')
from services.llm import oneshot
from services.llm import openai as oa
from models.llm import LLMToolUseEvent

oa._REPAIR_TIMEOUT_S = 0.5  # scale the 30 s cap down for the probe
starts = []
class Hang:
    async def stream_chat(self, messages, model, api_key=None, **kw):
        starts.append(time.monotonic())
        await asyncio.sleep(3600)
        yield None
oneshot.get_provider = lambda p: Hang()

async def main():
    adapter = oa.OpenAIProvider()
    events = [LLMToolUseEvent(tool_call_id=f"c{i}", name="compare_symbols", input={"symbols": i}) for i in range(5)]
    repairs = []
    t = time.monotonic()
    out = await adapter._resolve_tool_events(events, [], model="gpt-4o-mini", api_key="x", repairs=repairs)
    print(f"hanging repairs: calls={len(starts)} ledger={repairs} elapsed={time.monotonic()-t:.2f}s (cap {oa._MAX_REPAIRS_PER_ROUND} x {oa._REPAIR_TIMEOUT_S}s) sentinels={sum(1 for e in out if oa.INVALID_ARGS_SENTINEL in e.input)}")
asyncio.run(main())
