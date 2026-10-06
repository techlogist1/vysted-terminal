#!/usr/bin/env python3
"""Keyless stranger first-run drive on MY clean sidecar (:52223). Appends to http-log.jsonl.
usage: drive.py <pass-name>   (passes defined below; each row tagged)"""
import json, sys, time, urllib.error, urllib.request
PORT = 52223
BASE = f"http://127.0.0.1:{PORT}"
OUT = "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/surface/onboarding-stranger/http-log.jsonl"
HDR = {"X-Vysted-Region": "IN"}

def call(tag, method, path, body=None, timeout=150, keep=1500, headers=None):
    h = dict(HDR); h.update(headers or {})
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
    row = {"tag": tag, "t": time.strftime("%H:%M:%S"), "m": method, "path": path, "req": body,
           "status": code, "secs": round(time.time() - t0, 2), "bytes": len(txt), "body": txt[:keep]}
    with open(OUT, "a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{tag:5} {method:4} {code:4} {row['secs']:7}s {len(txt):7}B {path[:70]}  {txt[:150]!r}")
    return code, txt

P = sys.argv[1]
if P == "boot":
    for i, p in enumerate(["/health", "/system/hardware", "/system/local-model-recommendation",
        "/system/ollama/status", "/llm/providers", "/safety/disclaimer-status", "/workspace",
        "/agents", "/search/status", "/search/searxng/status", "/mcp/status", "/openbb-mcp/status",
        "/sec/status", "/system/provider-health", "/portfolio/positions", "/brokers"], 1):
        call(f"B{i:02d}", "GET", p, keep=2500)
elif P == "cockpit":
    call("C01", "GET", "/quotes?symbols=SPY,QQQ,NVDA,AAPL&asset_class=equity")
    call("C02", "GET", "/crypto/ticker?exchange=binance&symbol=BTC/USDT")
    call("C03", "GET", "/history/SPY?timeframe=1d&asset_class=equity", keep=400)
    call("C04", "GET", "/fundamentals/SPY")
    call("C05", "GET", "/news?limit=10&region=IN", keep=2500)
    call("C06", "GET", "/quotes/RELIANCE.NS?asset_class=equity")
    call("C07", "GET", "/history/RELIANCE.NS?timeframe=1d&asset_class=equity", keep=400)
    call("C08", "GET", "/fundamentals/RELIANCE.NS", keep=2500)
    call("C09", "GET", "/resolve?q=zomato&region=IN")
    call("C10", "GET", "/resolve/autocomplete?q=zomato&region=IN&limit=6")
elif P == "keys":
    # what the onboarding CloudStep + composer preflight POST (no real key anywhere)
    call("K01", "POST", "/llm/keys/validate", {"provider": "ollama", "api_key": None})
    call("K02", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": "sk-or-v1-notarealkey000000000000"})
    call("K03", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": ""})
    call("K04", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": None})
    call("K05", "GET", "/llm/providers/ollama/models")
    call("K06", "GET", "/llm/providers/openrouter/models", keep=600)
else:
    print("unknown pass"); sys.exit(2)
