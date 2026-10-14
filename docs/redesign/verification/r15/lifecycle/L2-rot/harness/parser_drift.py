#!/usr/bin/env python3
"""L2-rot in-process probes (no sidecar, own scratch data dir). Calls the REAL provider
functions; only the upstream answer is changed (monkeypatched constant / stubbed JSON).
usage: sidecar/.venv/bin/python parser_drift.py <scratch-data-dir>"""
import asyncio, json, os, sys
from datetime import date
os.environ["VYSTED_DATA_DIR"] = sys.argv[1]
os.makedirs(sys.argv[1], exist_ok=True)
SIDECAR = "/Users/lokavyasingh/Documents/dev/vysted-terminal/sidecar"
sys.path.insert(0, SIDECAR); os.chdir(SIDECAR)
import logging
logging.basicConfig(level=logging.INFO, format="LOG %(levelname)s %(name)s: %(message)s")
for noisy in ("httpx", "httpcore", "urllib3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
from services import nse_provider, nse_bhavcopy, nse_symbol_change, provider_registry, data_cache

def show(tag, obj):
    print(f"== {tag}: {obj}", flush=True)

# ---- A. historicalOR field drift (one real window fetched, then keys renamed) ----------
real = nse_provider._get_json(nse_provider._HISTORICAL_PATH,
                              {"symbol": "RELIANCE", "series": '["EQ"]', "from": "08-09-2026", "to": "22-09-2026"},
                              nse_provider._quote_referer("RELIANCE"))
rows = real.get("data", [])
show("A0 real historicalOR rows", len(rows))
show("A0 real row keys (sample)", sorted(k for k in rows[0].keys() if k.startswith("CH_"))[:14] if rows else None)
RENAME_OHLV = {"CH_OPENING_PRICE": "chOpen", "CH_TRADE_HIGH_PRICE": "chHigh",
               "CH_TRADE_LOW_PRICE": "chLow", "CH_TOT_TRADED_QTY": "chVolume"}
drift = {"data": [{RENAME_OHLV.get(k, k): v for k, v in r.items()} for r in rows]}
orig_get_json = nse_provider._get_json
nse_provider._get_json = lambda path, params, referer: drift  # upstream now answers the drifted shape
bars = nse_provider._rows_to_bars(drift["data"])
show("A1 _rows_to_bars on OHLV-renamed rows (last 2)", [b.model_dump(mode="json") for b in bars[-2:]] if bars else bars)
series = provider_registry.get_history("RELIANCE.NS", "1d", "1mo")
last = series.bars[-1]
show("A2 registry.get_history served", {"provider": series.provider, "n": len(series.bars),
     "last": last.model_dump(mode="json"),
     "flat_bars": sum(1 for b in series.bars if b.open == b.high == b.low == b.close),
     "zero_volume_bars": sum(1 for b in series.bars if not b.volume)})
q = nse_provider._quote_from_history("RELIANCE")
show("A3 _quote_from_history on drifted rows", q.model_dump(mode="json"))
RENAME_ALL = dict(RENAME_OHLV, CH_CLOSING_PRICE="chClose", CH_PREVIOUS_CLS_PRICE="chPrevClose")
drift_all = {"data": [{RENAME_ALL.get(k, k): v for k, v in r.items()} for r in rows]}
nse_provider._get_json = lambda path, params, referer: drift_all
try:
    nse_provider.get_history("RELIANCE.NS", "1d", "1mo")
    show("A4 close renamed -> nse_direct", "SERVED (unexpected)")
except Exception as exc:
    show("A4 close renamed -> nse_direct raises", f"{type(exc).__name__}: {exc}")
nse_provider._get_json = orig_get_json

# ---- B. bhavcopy header drift -----------------------------------------------------------
udiff_hdr = "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4"
row = "2026-09-22,2026-09-22,CM,NSE,STK,2885,INE002A01018,RELIANCE,EQ,,,,,RELIANCE INDUSTRIES LTD,1247.6,1251.9,1237.4,1240.4,1240.0,1247.4,,1240.4,,,10684376,1.3e10,300000,F1,1,,,,,"
show("B0 parse_bhavcopy UDiFF (today's header)", {k: v.close for k, v in nse_bhavcopy.parse_bhavcopy(udiff_hdr + "\n" + row).items()})
show("B1 parse_bhavcopy with TckrSymb->TckrSym (1 column renamed)",
     nse_bhavcopy.parse_bhavcopy(udiff_hdr.replace("TckrSymb", "TckrSym") + "\n" + row))
show("B2 parse_bhavcopy with ClsPric->ClsgPric", nse_bhavcopy.parse_bhavcopy(udiff_hdr.replace(",ClsPric,", ",ClsgPric,") + "\n" + row))

# ---- C. bhavcopy URL moved: 404 read as 'holiday', markers outlive the fix -------------
calls = []
orig_tget = nse_bhavcopy._throttled_get
async def counting_get(url):
    resp = await orig_tget(url)
    calls.append((url.split("/")[-1][:60], resp.status_code))
    return resp
nse_bhavcopy._throttled_get = counting_get

async def keys():
    conn = data_cache._get_conn()
    return [(k, v) for k, v in conn.execute("SELECT key, value FROM cache WHERE key LIKE 'nse_bhavcopy:%' ORDER BY key").fetchall()]

async def bhav_probe():
    good_udiff, good_sec = nse_bhavcopy._UDIFF_URL, nse_bhavcopy._SEC_FULL_URL
    nse_bhavcopy._UDIFF_URL = good_udiff.replace("/content/cm/", "/content/cm-v0-retired/")
    nse_bhavcopy._SEC_FULL_URL = good_sec.replace("/products/content/", "/products/content-v0-retired/")
    calls.clear()
    r = await nse_bhavcopy.fetch_latest()
    show("C1 fetch_latest with MOVED url", {"result": None if r is None else str(r.trade_date), "requests": calls[:]})
    show("C1 cache after (value per key)", [(k, v[:20]) for k, v in await keys()])
    nse_bhavcopy._UDIFF_URL, nse_bhavcopy._SEC_FULL_URL = good_udiff, good_sec   # the fix release
    calls.clear()
    r = await nse_bhavcopy.fetch_latest()
    show("C2 fetch_latest after URL FIXED (same cache)", {"result": None if r is None else str(r.trade_date), "requests": calls[:]})
    conn = data_cache._get_conn(); conn.execute("DELETE FROM cache WHERE key LIKE 'nse_bhavcopy:%'"); conn.commit()
    calls.clear()
    r = await nse_bhavcopy.fetch_latest()
    show("C3 control: fixed URL, clean cache", {"result": None if r is None else str(r.trade_date),
         "rows": 0 if r is None else len(r.rows), "requests": calls[:]})
    await nse_bhavcopy.aclose()

asyncio.run(bhav_probe())

# ---- D. symbolchange URL moved ---------------------------------------------------------
async def sc_probe():
    nse_symbol_change._URL = nse_symbol_change._URL.replace("symbolchange.csv", "symbolchange-v0-retired.csv")
    r = await nse_symbol_change.fetch_latest()
    show("D1 symbolchange MOVED, no cache", None if r is None else len(r))
    show("D1 lookup_current('ZOMATO')", nse_symbol_change.lookup_current("ZOMATO"))
asyncio.run(sc_probe())
