import asyncio, json, sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
async def main(tool, args, out):
    async with streamablehttp_client("http://127.0.0.1:52910/mcp/") as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            if tool == "LIST":
                t = await s.list_tools(); print([x.name for x in t.tools]); return
            res = await s.call_tool(tool, json.loads(args))
            data = res.structuredContent if res.structuredContent is not None else [c.text for c in res.content if hasattr(c, "text")]
            json.dump(data, open(out, "w"), indent=1, default=str)
            print("wrote", out, "isError", res.isError)
asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "{}", sys.argv[3] if len(sys.argv) > 3 else "/dev/null"))
