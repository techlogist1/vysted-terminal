import asyncio, os, shutil, tempfile
from datetime import date, timedelta
from services import option_chain as oc, nse_bhavcopy, data_cache
ROWS=[{"x":1}]
async def scenario(name, today, cached_days, results):
    calls=[]
    async def fake(day):
        calls.append(day.isoformat()); return results.get(day, ("missing", None))
    oc._fetch_fo_day=fake
    nse_bhavcopy._ist_today=lambda: today
    for d in cached_days: await data_cache.set(oc._cache_key(d), {"rows": ROWS})
    out=[]
    for i in range(3):
        r=await oc.fetch_latest_fo()
        out.append(r.trade_date.isoformat() if r else None)
    print(name, "served", out, "network calls", calls)
async def main():
    # Literal: Fri 2026-09-25 today; Thu 09-24 cached; today's probe fails transiently x3
    fri=date(2026,9,25); thu=date(2026,9,24); wed=date(2026,9,23)
    await scenario("literal(today failed, thu cached)", fri, [thu], {fri:("failed",None)})
    # Fresh A: today 404, thu cached
    os.environ  # noqa
    await scenario("fresh(today 404, thu cached)", date(2026,9,25), [], {date(2026,9,25):("missing",None)})
    # Fresh B: Monday 09-28 today 404, Fri 09-25 uncached fetch fails, Thu 09-24 cached
    mon=date(2026,9,28)
    await scenario("fresh(mon 404, fri FAILED, thu cached)", mon, [], {mon:("missing",None), fri:("failed",None)})
asyncio.run(main())
