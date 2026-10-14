import asyncio
from fastmcp import Client
async def main():
    for port in (52153, 52154):
        try:
            async with Client(f"http://127.0.0.1:{port}/mcp/") as c:
                tools = await c.list_tools()
                leaks=[(t.name,p) for t in tools for p in (t.inputSchema or {}).get("properties",{}) if any(s in p.lower() for s in ("key","secret","token","password","credential"))]
                print(port, "tools", len(tools), "secret-shaped params:", leaks)
        except Exception as e: print(port, "ERR", type(e).__name__, str(e)[:120])
asyncio.run(main())
