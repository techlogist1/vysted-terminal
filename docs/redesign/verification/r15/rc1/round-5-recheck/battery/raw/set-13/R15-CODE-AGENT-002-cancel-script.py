import asyncio, sys
sys.path.insert(0, ".")
from services import mcp_client

async def main():
    c = mcp_client.McpClient("t", transport="http", endpoint="http://x/mcp")

    class _StubSession:
        async def call_tool(self, name, args):
            await asyncio.sleep(10)

    c._session = _StubSession()
    c._generation = 1

    task = asyncio.create_task(c.call_tool("t", {}))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
        print("no exception (BUG)")
    except asyncio.CancelledError:
        print("genuine outer cancellation propagated as CancelledError (correct)")
    except mcp_client.ProviderError as e:
        print(f"BUG: outer cancellation swallowed into ProviderError: {e}")

asyncio.run(main())
