#!/usr/bin/env python3
"""L2-rot HTTP drive of MY sidecar (:52226). usage: drive.py <profile-tag>
Appends one row per request to ../http-log.jsonl (profile-tagged)."""
import json, sys, time, urllib.error, urllib.request
BASE = "http://127.0.0.1:52226"
OUT = "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/lifecycle/L2-rot/http-log.jsonl"
TAG = sys.argv[1]

def call(tag, method, path, body=None, timeout=180, keep=900):
    h = {"X-Vysted-Region": "IN"}
    data = None
    if body is not None:
        data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, txt = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        code, txt = ex.code, ex.read().decode("utf-8", "replace")
    except Exception as ex:  # noqa: BLE001
        code, txt = -1, f"{type(ex).__name__}: {ex}"
    row = {"profile": TAG, "tag": tag, "t": time.strftime("%H:%M:%S"), "m": method, "path": path,
           "req": body, "status": code, "secs": round(time.time() - t0, 2), "bytes": len(txt), "body": txt[:keep]}
    with open(OUT, "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{TAG}:{tag:4} {method:4} {code:4} {row['secs']:7}s {len(txt):7}B {path[:60]}  {txt[:260]!r}", flush=True)
    return code, txt

call("H1", "GET", "/health")
call("Q1", "GET", "/quotes/RELIANCE.NS?asset_class=equity")
call("Q2", "GET", "/quotes?symbols=TCS.NS,INFY.NS,SUZLON.NS&asset_class=equity", keep=1500)
call("Y1", "GET", "/history/RELIANCE.NS?timeframe=1d&range=3mo&asset_class=equity", keep=400)
call("Y2", "GET", "/history/SUZLON.NS?timeframe=1d&range=1y&asset_class=equity", keep=400)
call("D1", "GET", "/disclosures/announcements?symbol=RELIANCE&exchange=NSE&limit=3", keep=600)
call("D2", "GET", "/disclosures/results?symbol=RELIANCE", keep=600)
call("D3", "GET", "/disclosures/shareholding?symbol=RELIANCE", keep=600)
call("R1", "GET", "/resolve?q=zomato&region=IN", keep=400)
call("P1", "GET", "/system/provider-health")
call("H2", "GET", "/health")
