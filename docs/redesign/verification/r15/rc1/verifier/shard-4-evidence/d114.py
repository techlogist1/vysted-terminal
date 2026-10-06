import asyncio, tempfile, os
from datetime import date
os.environ.setdefault("VYSTED_DATA_DIR", tempfile.mkdtemp())
from services import option_chain as oc, data_cache, nse_bhavcopy
async def run(today, script, cached, reset=True):
    if reset: from pathlib import Path; data_cache.reset_for_tests(Path(tempfile.mkdtemp())/'c.db')
    for d in cached:
        await data_cache.set(oc._cache_key(d), {"rows": {"NIFTY": [1]}})
    calls=[]
    async def fake(day):
        calls.append(day.isoformat()); return script.get(day, ("missing", None))
    oc._fetch_fo_day = fake
    nse_bhavcopy._ist_today = lambda: today
    r = await oc.fetch_latest_fo()
    return (r.trade_date.isoformat() if r else None), calls
async def main():
    # entry repro: today (Fri 2026-09-25) transport fails, Thu 09-24 cached
    print("A", await run(date(2026,9,25), {date(2026,9,25):("failed",None)}, [date(2026,9,24)]))
    # burst: second call should not re-probe
    print("A2", await run(date(2026,9,25), {date(2026,9,25):("failed",None)}, [], reset=False))
    # fresh variant: Thu 10-01, today 404, Wed 09-30 transport fail, Tue 09-29 cached
    print("B", await run(date(2026,10,1), {date(2026,10,1):("missing",None), date(2026,9,30):("failed",None)}, [date(2026,9,29)]))
asyncio.run(main())
