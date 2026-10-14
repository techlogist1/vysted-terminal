import asyncio, sys
sys.path.insert(0, ".")
import services.agent_runtime as ar

CANCELLED = {"v": False}

async def fake_dispatch_tool(tool_call, local_tools=None):
    try:
        await asyncio.sleep(5)
        return "{}"
    except asyncio.CancelledError:
        CANCELLED["v"] = True
        raise

ar._dispatch_tool = fake_dispatch_tool

async def main():
    gen = ar._dispatch_tool_with_progress(tool_call=type("T", (), {"name": "research", "id": "x", "input": {}})())
    # pull first item only, then aclose() (mimics client disconnect closing the SSE generator)
    it = gen.__aiter__()
    try:
        await asyncio.wait_for(it.__anext__(), timeout=1.0)
    except (asyncio.TimeoutError, StopAsyncIteration):
        pass
    await gen.aclose()
    await asyncio.sleep(0.2)
    print("tool task cancelled on aclose:", CANCELLED["v"])

asyncio.run(main())
