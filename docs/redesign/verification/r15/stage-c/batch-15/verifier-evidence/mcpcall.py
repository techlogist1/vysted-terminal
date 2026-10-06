import asyncio, json, sys
from fastmcp import Client
async def main():
    async with Client("http://127.0.0.1:52310/mcp/") as c:
        for sym in sys.argv[1:]:
            r = await c.call_tool("fundamentals", {"symbol": sym}, raise_on_error=False)
            d = r.structured_content or json.loads(r.content[0].text)
            f = d.get("fundamentals") or {}
            print(sym, "ok=",d.get("ok"), "keys=",list(d)[:4], "finCcy=", f.get("financialCurrency") or f.get("financial_currency"))
            print("   ads_ratio=", json.dumps(d.get("ads_ratio")))
asyncio.run(main())
