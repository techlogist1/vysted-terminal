import asyncio, os, sys, time, tempfile
sys.path.insert(0, ".")
os.environ["VYSTED_DATA_DIR"] = tempfile.mkdtemp()
from services import adr_ratio
async def main():
    for sym in ("SIFY", "WIT", "INFY", "IBN", "HDB", "BABA", "TSM"):
        t = time.monotonic()
        try: r = await asyncio.wait_for(adr_ratio._fetch(sym), 120)
        except Exception as e: r = repr(e)
        print(sym, f"{time.monotonic()-t:.2f}s", (r or {}).get("ordinary_shares_per_ads") if isinstance(r, dict) else r, flush=True)
    t = time.monotonic(); r = await adr_ratio.lookup("HDB"); print("lookup HDB (bounded)", f"{time.monotonic()-t:.2f}s", r and r.get("ordinary_shares_per_ads"), flush=True)
asyncio.run(main())
