import asyncio, sys
sys.path.insert(0, ".")
import anyio, httpx
from services import mcp_client

async def main():
    for exc_cls, label in [
        (anyio.ClosedResourceError, "ClosedResourceError"),
        (anyio.BrokenResourceError, "BrokenResourceError"),
        (httpx.ReadError, "ReadError"),
    ]:
        c = mcp_client.McpClient("t", transport="http", endpoint="http://x/mcp")

        class _StubSession:
            async def call_tool(self, name, args):
                raise exc_cls("boom") if exc_cls is not httpx.ReadError else exc_cls("boom", request=httpx.Request("GET","http://x"))

        c._session = _StubSession()
        c._generation = 1
        try:
            await c.call_tool("t", {})
            print(label, "no exception raised (BUG)")
        except mcp_client.ProviderError as e:
            print(f"{label} -> ProviderError raised: {e}; session dropped? {c._session is None}")
        except Exception as e:
            print(f"{label} -> raw exception escaped (BUG): {type(e).__name__}: {e}; session dropped? {c._session is None}")

asyncio.run(main())
