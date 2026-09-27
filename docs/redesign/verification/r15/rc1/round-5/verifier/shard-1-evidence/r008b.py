import asyncio, time, sys
from services import agent_tools
from services.agent_tools import web_search as _ws; _ws.register()
from services.search.ddg import DdgSearchBackend
from services.search.brave import BraveSearchBackend
from services.search.mojeek import MojeekSearchBackend
from services.search.base import SearchResponse, SearchResult
async def hang(self, query, *, options=None):
    await asyncio.sleep(60)
def ok(name):
    async def f(self, query, *, options=None):
        await asyncio.sleep(0.9)
        return SearchResponse(results=[SearchResult(url=f"https://www.{name}-news-{i}.com/dixon", title=f"Dixon Technologies Q2 news {i}", snippet="Dixon Technologies reported") for i in range(3)], citations=[], backend=name, query=query)
    return f
mode = sys.argv[1]
DdgSearchBackend.search = hang
if mode == "brave_ok":
    BraveSearchBackend.search = ok("brave")
else:
    BraveSearchBackend.search = hang
    MojeekSearchBackend.search = ok("mojeek")
async def main():
    t = time.monotonic()
    try:
        r = await asyncio.wait_for(agent_tools.invoke_tool("web_search", {"query": sys.argv[2]}), 25)
        rows = r.get("results") or []
        print(f"mode={mode} elapsed={time.monotonic()-t:.1f}s ok={r.get('ok')} backend={r.get('backend')} rows={len(rows)}")
    except asyncio.TimeoutError:
        print(f"mode={mode} TIMEOUT at 25s (tool cap)")
asyncio.run(main())
