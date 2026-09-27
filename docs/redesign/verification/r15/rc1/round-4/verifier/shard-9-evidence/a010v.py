import asyncio, os, socket, threading, time
bh = socket.socket(); bh.bind(("127.0.0.1", 0)); bh.listen(64)
held = []
def _acc():
    while True:
        c, _ = bh.accept(); held.append(c)  # accept, never answer
threading.Thread(target=_acc, daemon=True).start()
port = bh.getsockname()[1]
for k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY"):
    os.environ[k] = f"http://127.0.0.1:{port}"
os.environ.pop("NO_PROXY", None); os.environ.pop("no_proxy", None)
from services.agent_tools.resolve_symbol import _resolve_symbol
from services import symbol_resolver
async def ticker(stop, gaps):
    last = time.monotonic()
    while not stop.is_set():
        await asyncio.sleep(0.01); now = time.monotonic(); gaps.append(now - last); last = now
async def main():
    # warm the masters first so only the live leg is timed
    t = time.monotonic(); await symbol_resolver.resolve_async("infosys", "IN"); print("warm masters", round(time.monotonic()-t,2))
    for q, reg in (("zzqx vericheck unfound co", "US"), ("qqzv bramblewick holdings plc", "IN")):
        symbol_resolver._live_cache.clear(); symbol_resolver._live_cooldown_until = 0.0
        stop = asyncio.Event(); gaps = []
        tk = asyncio.create_task(ticker(stop, gaps))
        t0 = time.monotonic()
        side = asyncio.create_task(asyncio.to_thread(time.sleep, 0.01)); 
        r = await _resolve_symbol({"query": q, "region": reg})
        dt = time.monotonic() - t0
        await side
        stop.set(); await tk
        print(repr(q), reg, "wall_s", round(dt, 2), "max_gap_ms", round(max(gaps)*1000), "result", r.get("ok"), r.get("status"))
asyncio.run(main())
