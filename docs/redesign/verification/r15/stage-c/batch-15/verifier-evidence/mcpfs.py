import asyncio, json
from fastmcp import Client
async def main():
    async with Client("http://127.0.0.1:52310/mcp/") as c:
        tools = {t.name: t for t in await c.list_tools()}
        print("fs schema props:", list(tools["financial_statements"].inputSchema.get("properties",{})))
        for sym in ("SIFY","AAPL"):
            r = await c.call_tool("financial_statements", {"symbol": sym, "statement":"income","period":"annual"}, raise_on_error=False)
            d = r.structured_content or json.loads(r.content[0].text)
            print(sym, "ok=",d.get("ok"), "keys=", list(d)[:5], "ads_ratio=", json.dumps(d.get("ads_ratio"))[:160], d.get("error"))
asyncio.run(main())
