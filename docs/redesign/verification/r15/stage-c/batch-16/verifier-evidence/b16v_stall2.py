import asyncio, os, sys, time, socket, threading, tempfile
sys.path.insert(0, ".")
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(50); port = srv.getsockname()[1]
held = []
threading.Thread(target=lambda: [held.append(srv.accept()) for _ in iter(int, 1)], daemon=True).start()
# only SEC goes through the black hole; yahoo stays direct
os.environ["HTTPS_PROXY"] = f"http://127.0.0.1:{port}"
os.environ["NO_PROXY"] = "yahoo.com,.yahoo.com,query1.finance.yahoo.com,query2.finance.yahoo.com,fc.yahoo.com,guce.yahoo.com,127.0.0.1,localhost"
os.environ["VYSTED_DATA_DIR"] = tempfile.mkdtemp()
from services.agent_tools import fundamentals as f
async def main():
    for i in range(2):
        t = time.monotonic(); r = await f._fundamentals({"symbol": "TSM"})
        print("fundamentals TSM", i, "ok=", r.get("ok"), "ads_ratio" in r, r.get("error"), f"{time.monotonic()-t:.2f}s", flush=True)
    t = time.monotonic(); r = await f._financial_statements({"symbol": "TSM"})
    print("financial_statements TSM ok=", r.get("ok"), "ads_ratio" in r, str(r.get("error"))[:100], f"{time.monotonic()-t:.2f}s", flush=True)
asyncio.run(main())
