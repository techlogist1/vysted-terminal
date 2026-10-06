import asyncio, sys
sys.path.insert(0, ".")
from services.agent_runtime import _dispatch_tool_with_progress, LLMToolUseEvent

finished = {"v": False}

async def slow_tool(*a, **kw):
    await asyncio.sleep(0.4)
    finished["v"] = True
    return "done"

async def main():
    tc = LLMToolUseEvent(tool_call_id="t1", name="slow_tool", input={})
    local_tools = {"slow_tool": slow_tool}
    gen = _dispatch_tool_with_progress(tc, local_tools)
    task = asyncio.create_task(gen.__anext__())
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await gen.aclose()
    print("right after aclose(): tool finished =", finished["v"])
    await asyncio.sleep(0.6)
    print("0.6s later: tool finished =", finished["v"])

asyncio.run(main())
