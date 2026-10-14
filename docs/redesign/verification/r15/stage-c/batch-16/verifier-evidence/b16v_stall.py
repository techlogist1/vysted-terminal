import asyncio, os, sys, time, socket, threading, tempfile
sys.path.insert(0, ".")
# a black-hole proxy: accepts, never answers
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(50); port = srv.getsockname()[1]
held = []
threading.Thread(target=lambda: [held.append(srv.accept()) for _ in iter(int, 1)], daemon=True).start()
os.environ["HTTPS_PROXY"] = os.environ["HTTP_PROXY"] = f"http://127.0.0.1:{port}"
os.environ["VYSTED_DATA_DIR"] = tempfile.mkdtemp()
from services import adr_ratio, sec_filings_provider
calls = 0
orig = adr_ratio._fetch
async def counted(s):
    global calls; calls += 1; return await orig(s)
adr_ratio._fetch = counted
async def main():
    for sym in ("TSM", "TSM", "BABA"):
        t = time.monotonic(); r = await adr_ratio.lookup(sym)
        print(sym, "->", r, f"{time.monotonic()-t:.2f}s", "fetch calls:", calls, flush=True)
asyncio.run(main())
