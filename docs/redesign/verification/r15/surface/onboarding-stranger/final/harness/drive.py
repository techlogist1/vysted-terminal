#!/usr/bin/env python3
"""final-drive-onboarding-stranger HTTP drive. writes = own :52846 (clean profile); reads may go to :52800."""
import json, sys, time, urllib.error, urllib.request
OUT = "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/surface/onboarding-stranger/final/http-log.jsonl"
HDR = {"X-Vysted-Region": "IN"}
def call(tag, method, path, body=None, port=52846, timeout=110, keep=1800):
    h = dict(HDR); data = None
    if body is not None:
        data = json.dumps(body).encode(); h["Content-Type"] = "application/json"
    req = urllib.request.Request(f"http://127.0.0.1:{port}" + path, data=data, method=method, headers=h)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, txt = r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        code, txt = ex.code, ex.read().decode("utf-8", "replace")
    except Exception as ex:
        code, txt = -1, f"{type(ex).__name__}: {ex}"
    row = {"tag": tag, "t": time.strftime("%H:%M:%S"), "port": port, "m": method, "path": path, "req": body,
           "status": code, "secs": round(time.time() - t0, 2), "bytes": len(txt), "body": txt[:keep]}
    open(OUT, "a").write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{tag:5} {port} {method:4} {code:4} {row['secs']:6}s {len(txt):7}B {path[:60]}  {txt[:220]!r}")
P = sys.argv[1]
if P == "boot":
    for i, p in enumerate(["/health", "/system/hardware", "/system/local-model-recommendation",
        "/system/ollama/status", "/llm/providers", "/workspace", "/agents", "/search/status",
        "/mcp/status", "/system/provider-health", "/portfolio/positions", "/system/region",
        "/screener/default-universe", "/safety/disclaimer-status", "/brokers"], 1):
        call(f"B{i:02d}", "GET", p, keep=2500)
elif P == "keys":
    K = "sk-or-v1-" + "0" * 40 + "notarealkey"
    call("K01", "POST", "/llm/keys/validate", {"provider": "ollama", "api_key": None})
    call("K02", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": K})
    call("K03", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": ""})
    call("K04", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": None})
    call("K05", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": K + " \n"})
    call("K06", "POST", "/llm/keys/validate", {"provider": "ollama", "api_key": None, "model": "qwen3:8b"})
    call("K07", "POST", "/llm/keys/validate", {"provider": "ollama", "api_key": None, "model": "llama3.1:70b-not-pulled-xyz"})
    call("K08", "POST", "/llm/keys/validate", {"provider": "openai", "api_key": "sk-proj-notarealkey000000000000000000"})
    call("K09", "POST", "/llm/keys/validate", {"provider": "ollama", "api_key": None, "model": "llama3.1:8b"})
    call("K10", "POST", "/llm/keys/validate", {"provider": "deepseek", "api_key": None})
elif P == "cockpit":
    call("C01", "GET", "/quotes?symbols=RELIANCE.NS,TCS.NS,HDFCBANK.NS,INFY.NS&asset_class=equity")
    call("C02", "GET", "/quotes/%5ENSEI?asset_class=equity")
    call("C03", "GET", "/history/%5ENSEI?timeframe=1d&asset_class=equity", keep=400)
    call("C04", "GET", "/news?limit=10&region=IN", keep=2500)
    call("C05", "GET", "/fundamentals/RELIANCE.NS", keep=1200)
    call("C06", "GET", "/resolve?q=zomato&region=IN")
    call("C07", "GET", "/resolve?q=ZOMATO&region=IN")
    call("C08", "GET", "/resolve/autocomplete?q=zomato&region=IN&limit=6")
    call("C09", "GET", "/quotes/ZOMATO.NS?asset_class=equity")
    call("C10", "GET", "/resolve?q=eternal&region=IN")
    call("C11", "GET", "/quotes/ETERNAL.NS?asset_class=equity")
elif P == "shared":
    for i, p in enumerate(["/health", "/system/region", "/system/local-model-recommendation"], 1):
        call(f"X{i:02d}", "GET", p, port=52800)
if P == "unreach":
    call("U01", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": "sk-or-v1-notarealkey", "base_url": "http://127.0.0.1:59997/api/v1"})
    call("U02", "POST", "/llm/keys/validate", {"provider": "ollama", "api_key": None, "base_url": "http://127.0.0.1:59997", "model": "qwen3:8b"})
    call("U03", "POST", "/llm/keys/validate", {"provider": "openai", "api_key": "sk-notarealkey", "base_url": "http://127.0.0.1:59997/v1"})
    call("U04", "POST", "/llm/keys/validate", {"provider": "openrouter", "api_key": "x", "extra": 1})
    call("U05", "POST", "/llm/keys/validate", {"provider": "notaprovider", "api_key": "x"})
