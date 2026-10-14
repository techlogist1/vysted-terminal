import asyncio, json
from fastmcp import Client
async def main():
    async with Client("http://127.0.0.1:52602/mcp/") as c:
        tools = await c.list_tools()
        leaks = []
        for t in tools:
            props = (t.inputSchema or {}).get("properties", {})
            for p in props:
                if any(s in p.lower() for s in ("key", "secret", "token", "password", "credential")):
                    leaks.append((t.name, p))
        inv = next(t for t in tools if t.name == "invoke_agent")
        print("tools:", len(tools)); print("invoke_agent schema:", json.dumps(inv.inputSchema))
        print("secret-shaped params across ALL tools:", leaks)
asyncio.run(main())
