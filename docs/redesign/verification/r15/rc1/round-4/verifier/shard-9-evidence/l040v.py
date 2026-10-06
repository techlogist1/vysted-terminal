import asyncio, sys, time, os
mode = sys.argv[1]
import yfinance as yf
class _S:
    def __init__(self, *a, **k): self.quotes = []
yf.Search = _S
from services import symbol_resolver as sr
Q = ["infosys", "tata steel", "reliance q4 results", "hdfc bank limited results", "wipro", "cochin shipyard",
     "bharat electronics", "adani ports", "larsen toubro", "itc hotels", "sun pharma", "maruti suzuki",
     "apple inc", "microsoft", "nvidia corp", "berkshire hathaway"]
async def main():
    t0 = time.monotonic()
    if mode == "literal":
        tasks = [asyncio.create_task(sr.resolve_async(q, "IN")) for q in Q[:12]]
    else:  # fresh: 16 mixed autocomplete+resolve across regions
        tasks = [asyncio.create_task(sr.autocomplete_async(q, "US" if i % 2 else "IN", 8)) for i, q in enumerate(Q)]
        tasks += [asyncio.create_task(sr.resolve_async(q, "US")) for q in Q[12:]]
    await asyncio.sleep(0.05)
    t = time.monotonic(); await asyncio.to_thread(time.sleep, 0); side = time.monotonic() - t
    await asyncio.gather(*tasks)
    print(mode, "n_tasks", len(tasks), "unrelated_to_thread_wait_s", round(side, 3), "all_done_s", round(time.monotonic() - t0, 2), "default_pool_max", min(32, (os.cpu_count() or 1) + 4))
asyncio.run(main())
