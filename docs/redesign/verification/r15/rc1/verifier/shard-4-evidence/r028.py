import asyncio
from services.agent_tools import web_search as ws
from services.research import fast
from services import searxng_manager as sm
async def fake_dispatch(backend, query, n, cat, region):
    return {"ok": True, "query": query, "results": [{"url": "https://ex.com/a", "title": "A"}], "citations": []}
ws._dispatch = fake_dispatch
async def main():
    sm.manager.state = sm.STATE_DEGRADED
    sm.manager._hot_path_detected = True
    direct = await ws._web_search({"query": "Tata Elxsi outlook"})
    print("web_search tool ->", {k: direct.get(k) for k in ("ok", "backend", "reason")})
    async def safe(tool_call, name, args): return await ws._web_search(args)
    fast._safe_call = safe
    web = await fast._web_round(None, "Tata Elxsi outlook")
    print("fast._web_round ->", {k: web.get(k) for k in ("available", "backend", "reason")})
asyncio.run(main())
