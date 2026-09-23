import asyncio, sys, time
sys.path.insert(0, ".")
import config
from services.agent_tools import web_search as ws
from services import agent_tools
ws.register()
from services.search import keyless, searxng as sx, transport
from services import searxng_manager
T0 = time.time()
def wrap(obj, name, label):
    orig = getattr(obj, name)
    async def w(*a, **k):
        t = time.time()
        try:
            r = await orig(*a, **k)
            print(f"{time.time()-T0:6.1f}s {label} ok in {time.time()-t:.1f}s -> {type(r).__name__}", flush=True)
            return r
        except Exception as e:
            print(f"{time.time()-T0:6.1f}s {label} FAIL in {time.time()-t:.1f}s -> {type(e).__name__}: {str(e)[:140]}", flush=True)
            raise
    setattr(obj, name, w)
wrap(searxng_manager.manager, "ready_base_url_detected", "manager.ready_base_url_detected")
wrap(sx.SearxngSearchBackend, "search", "searxng.search") if False else None
orig_init = keyless.KeylessSearchBackend.__init__
def init(self, *a, **k):
    orig_init(self, *a, **k)
    for eid, eng in list(self._engines.items()):
        wrap(eng, "search", f"engine[{eid}].search")
keyless.KeylessSearchBackend.__init__ = init
wrap(keyless.KeylessSearchBackend, "_try_engine", "keyless._try_engine") if False else None
async def main():
    config.set_request_search(tier=None, searxng_url=None)
    t = time.time()
    r = await agent_tools.invoke_tool("web_search", {"query": sys.argv[1], "num_results": 5, "category": "news"})
    print(f"TOTAL {time.time()-t:.1f}s ok={r.get('ok')} backend={r.get('backend')} n={len(r.get('results') or [])}")
asyncio.run(main())
