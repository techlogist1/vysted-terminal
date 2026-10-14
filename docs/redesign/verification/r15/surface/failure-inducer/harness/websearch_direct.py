"""Call the web_search tool handler in-process under an induced search env (no docker on PATH)."""
import asyncio, json, sys, time
sys.path.insert(0, ".")
import config
import os
QUERY = os.environ.get("WSQ", "Kaynes Technology India news")
from services import agent_tools
from services.agent_tools import web_search as _ws
_ws.register()

async def one(label, url):
    config.set_request_search(tier=None, searxng_url=url)
    t = time.time()
    try:
        r = await asyncio.wait_for(agent_tools.invoke_tool("web_search", {"query": QUERY, "num_results": 5, "category": "news"}), 120)
    except Exception as e:  # noqa: BLE001
        r = {"exc": f"{type(e).__name__}: {e}"}
    el = round(time.time() - t, 1)
    slim = {k: v for k, v in r.items() if k not in ("results", "citations")}
    slim["n_results"] = len(r.get("results") or [])
    print(json.dumps({"case": label, "secs": el, "result": slim})[:900], flush=True)

async def main():
    order = sys.argv[1:] or ["dead", "keyless"]
    q = {"dead": ("dead_custom_url_127.0.0.1:9", "http://127.0.0.1:9"), "keyless": ("no_custom_url_nodocker_keyless", None)}
    for i, k in enumerate(order):
        await one(f"{i}:{q[k][0]}", q[k][1])

asyncio.run(main())
