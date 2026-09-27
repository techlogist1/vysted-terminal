import asyncio, os, tempfile
from datetime import date
from pathlib import Path
os.environ["VYSTED_DATA_DIR"] = tempfile.mkdtemp()
from services import option_chain as oc, nse_bhavcopy, data_cache
TUE = date(2026, 9, 22); MON = date(2026, 9, 21); FRI = date(2026, 9, 18)
calls = []
async def scenario(name, plan, seed_days, n=3):
    data_cache.reset_for_tests(Path(tempfile.mkdtemp()) / "c.db")
    calls.clear()
    async def fake(day):
        calls.append(day.isoformat()); return plan.get(day, ("missing", None))
    oc._fetch_fo_day = fake
    nse_bhavcopy._ist_today = lambda: TUE
    for d in seed_days:
        await data_cache.set(oc._cache_key(d), {"rows": {"NIFTY": [["2026-09-29", 25000, "call", 1, 0, 1, 1, 1, 25000]]}})
    res = []
    for _ in range(n):
        r = await oc.fetch_latest_fo()
        res.append(r.trade_date.isoformat() if r else None)
    print(f"{name}: seeded={[d.isoformat() for d in seed_days]} results={res} network_calls={calls}")
async def main():
    await scenario("A (entry case) TUE=failed", {TUE: ("failed", None)}, [MON])
    await scenario("B TUE=404", {TUE: ("missing", None)}, [MON])
    await scenario("C fresh: TUE=404, MON=failed", {TUE: ("missing", None), MON: ("failed", None)}, [FRI])
    await scenario("D fresh: TUE=failed, MON uncached", {TUE: ("failed", None)}, [FRI])
asyncio.run(main())
