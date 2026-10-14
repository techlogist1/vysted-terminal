"""Proof: one failed rename-master fetch marks the IST day refreshed -> no retry until tomorrow."""
import asyncio, sys, tempfile, os
sys.path.insert(0, "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar")
import httpx
os.environ.setdefault("VYSTED_DATA_DIR", tempfile.mkdtemp())
from services import nse_symbol_change as m, data_cache
calls = {"n": 0}
CSV = "GUJARAT ENERGY LIMITED,GUJGASLTD,GUJENERGY,01-JUL-2026\n"
def handler(req):
    calls["n"] += 1
    if calls["n"] == 1:
        raise httpx.ConnectTimeout("")          # the boot blip (str() is empty, as in the live log)
    return httpx.Response(200, text=CSV)
async def main():
    try:
        from pathlib import Path; data_cache.reset_for_tests(Path(tempfile.mkdtemp())/"c.db")
    except Exception as e:
        print("data_cache.configure n/a:", type(e).__name__)
    m.reset_for_tests(transport=httpx.MockTransport(handler))
    await m.schedule_refresh(); await asyncio.sleep(0.5)
    print("after boot refresh: attempts=%d refreshed_on=%s map_size=%d lookup(GUJGASLTD)=%s" % (calls["n"], m._refreshed_on, len(m._active_map), m.lookup_current("GUJGASLTD")))
    for i in range(3):  # three later /resolve calls the same day
        await m.schedule_refresh(); await asyncio.sleep(0.2)
    print("after 3 more schedule_refresh(): attempts=%d map_size=%d lookup(GUJGASLTD)=%s" % (calls["n"], len(m._active_map), m.lookup_current("GUJGASLTD")))
    m._refreshed_on = None  # what IST midnight does
    await m.schedule_refresh(); await asyncio.sleep(0.5)
    print("after the day rolls over: attempts=%d lookup(GUJGASLTD)=%s" % (calls["n"], m.lookup_current("GUJGASLTD")))
asyncio.run(main())
