import asyncio, time, sys
from services import agent_tools
from services.agent_tools import web_search as _ws; _ws.register()
from services.search.ddg import DdgSearchBackend
from services.search.brave import BraveSearchBackend
async def hang(self, query, *, options=None):
    await asyncio.sleep(60)
mode = sys.argv[1]
if mode in ("ddg", "ddg+brave"):
    DdgSearchBackend.search = hang
if mode == "ddg+brave":
    BraveSearchBackend.search = hang
async def main():
    q = sys.argv[2]
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(agent_tools.invoke_tool("web_search", {"query": q}), 25)
        el = time.monotonic() - t
        rows = r.get("results") or r.get("citations") or []
        print(str(r)[:600]); print(f"mode={mode} elapsed={el:.1f}s ok={r.get('ok')} backend={r.get('backend')} rows={len(rows)} first={(rows[0].get('url') if rows else None)}")
    except asyncio.TimeoutError:
        print(f"mode={mode} TIMEOUT at 25s (tool cap)")
asyncio.run(main())
