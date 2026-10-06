#!/usr/bin/env python3
"""settings-plugins HTTP driver: one JSON line per request to --out (request, status, secs, body excerpt).
  pn.py <tag> <METHOD> <path> [json-body|@file] [--port 52221] [--out FILE] [--full]"""
import argparse, json, time, http.client
ap = argparse.ArgumentParser()
ap.add_argument("tag"); ap.add_argument("method"); ap.add_argument("path"); ap.add_argument("body", nargs="?")
ap.add_argument("--port", type=int, default=52222)
ap.add_argument("--out", default="/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/surface/settings-plugins/http-log.jsonl")
ap.add_argument("--full", action="store_true"); ap.add_argument("--timeout", type=float, default=180)
a = ap.parse_args()
body = None
if a.body:
    body = open(a.body[1:]).read() if a.body.startswith("@") else a.body
c = http.client.HTTPConnection("127.0.0.1", a.port, timeout=a.timeout)
t0 = time.time()
try:
    c.request(a.method, a.path, body.encode() if body else None, {"Content-Type": "application/json"} if body else {})
    r = c.getresponse(); raw = r.read().decode(errors="replace"); st = r.status
except Exception as e:
    raw = f"{type(e).__name__}: {e}"; st = -1
rec = {"tag": a.tag, "m": a.method, "path": a.path, "req_len": len(body) if body else 0,
       "req": (body[:400] if body else None), "status": st, "secs": round(time.time() - t0, 3), "len": len(raw),
       "resp": raw if a.full else raw[:1200]}
open(a.out, "a").write(json.dumps(rec) + "\n")
print(json.dumps({k: rec[k] for k in ("tag", "status", "secs", "len")}), raw[:600])
