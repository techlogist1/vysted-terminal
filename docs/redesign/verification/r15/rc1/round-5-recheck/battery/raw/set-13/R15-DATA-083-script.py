import asyncio, sys
sys.path.insert(0, ".")
from services import openbb_mcp_provider as p

class _StubClient:
    def __init__(self):
        self.n = 0
    async def call_tool(self, name, args):
        self.n += 1
        print("STUB call_tool invoked, n=", self.n)
        if self.n == 1:
            return {"isError": False, "content": [{"type": "text", "text": "{\"results\": []}"}]}
        return {"isError": True, "content": [{"type": "text", "text": "upstream 500"}]}

_stub = _StubClient()

async def fake_get_client():
    print("fake_get_client called")
    return _stub

async def main():
    p._last_tool_call_ok = None
    p._last_error = None
    p._get_client = fake_get_client

    r1 = await p._call_tool("x", {})
    print("call1 result:", r1)
    s1 = await p.status()
    print("after ok call:", {k: s1[k] for k in ("lastToolCallOk", "lastError")})

    try:
        r2 = await p._call_tool("x", {})
        print("call2 result (no exception, BUG?):", r2)
    except Exception as e:
        print("call 2 raised:", type(e).__name__, e)
    s2 = await p.status()
    print("after isError call:", {k: s2[k] for k in ("lastToolCallOk", "lastError")})

asyncio.run(main())
