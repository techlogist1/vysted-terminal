#!/usr/bin/env python3
"""L2-rot probe E: ONLY the UDiFF primary path moves (404); the legacy sec_bhavdata_full
fallback is still live. Does _fetch_day ever try the fallback? Real network, own scratch
data dir, source untouched. usage: sidecar/.venv/bin/python fallback_skip.py <scratch-dir>"""
import asyncio, os, sys
os.environ["VYSTED_DATA_DIR"] = sys.argv[1]; os.makedirs(sys.argv[1], exist_ok=True)
SIDECAR = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar"
sys.path.insert(0, SIDECAR); os.chdir(SIDECAR)
import logging
logging.basicConfig(level=logging.INFO, format="LOG %(levelname)s %(name)s: %(message)s")
for n in ("httpx", "httpcore"): logging.getLogger(n).setLevel(logging.WARNING)
from datetime import date
from services import nse_bhavcopy, data_cache
calls = []
orig = nse_bhavcopy._throttled_get
async def counting(url):
    r = await orig(url); calls.append((url.split("/")[-1][:48], r.status_code)); return r
nse_bhavcopy._throttled_get = counting
async def main():
    good = nse_bhavcopy._UDIFF_URL
    nse_bhavcopy._UDIFF_URL = good.replace("/content/cm/", "/content/cm-v0-retired/")
    st, rows = await nse_bhavcopy._fetch_day(date(2026, 9, 22))
    print("E1 _fetch_day(2026-09-22) primary moved, fallback live:", st, None if rows is None else len(rows), calls[:]); calls.clear()
    r = await nse_bhavcopy._throttled_get(nse_bhavcopy._SEC_FULL_URL.format(dmy="22092026"))
    print("E2 direct GET of the fallback URL:", r.status_code, len(r.content), "bytes;",
          "rows parsed:", len(nse_bhavcopy.parse_bhavcopy(nse_bhavcopy._decode_body(r.content))))
    res = await nse_bhavcopy.fetch_latest()
    print("E3 fetch_latest primary moved:", None if res is None else (str(res.trade_date), len(res.rows)), calls[:])
    conn = data_cache._get_conn()
    print("E4 markers:", conn.execute("SELECT key, value FROM cache WHERE key LIKE 'nse_bhavcopy:%' ORDER BY key").fetchall())
    await nse_bhavcopy.aclose()
asyncio.run(main())
