import asyncio, sys, time
sys.path.insert(0, '.')
from services.llm import oneshot
from services.llm import openai as oa
from models.llm import LLMToolUseEvent
from models.llm import LLMUsage

calls = []
async def ok_garbage(provider, model, key, msgs, timeout=None):
    calls.append(timeout); return "not json", LLMUsage(input_tokens=100, output_tokens=5)
async def times_out(provider, model, key, msgs, timeout=None):
    calls.append(timeout); await asyncio.sleep(0.05); raise TimeoutError("repair timed out")

async def run(fn, label):
    calls.clear()
    oneshot.complete_with_usage = fn
    adapter = oa.OpenAIProvider() if hasattr(oa, "OpenAIProvider") else None
    events = [LLMToolUseEvent(tool_call_id=f"c{i}", name="compare_symbols", input={"symbols": i}) for i in range(5)]
    repairs = []
    t = time.monotonic()
    out = await adapter._resolve_tool_events(events, [], model="gpt-4o-mini", api_key="x", repairs=repairs)
    print(f"{label}: repair calls={len(calls)} timeouts={calls} ledger={len(repairs)} metered_tokens={sum((u.input_tokens+u.output_tokens) for u in repairs if u)} elapsed={time.monotonic()-t:.2f}s sentinels={sum(1 for e in out if oa.INVALID_ARGS_SENTINEL in e.input)}")
asyncio.run(run(ok_garbage, "literal (repairs answer garbage)"))
asyncio.run(run(times_out, "fresh (every repair times out)"))
