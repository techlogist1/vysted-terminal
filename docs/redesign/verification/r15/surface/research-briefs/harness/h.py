#!/usr/bin/env python3
"""GET/POST/PUT/DELETE against my own sidecar; append req/resp excerpt to an http-log.jsonl."""
import sys, json, time, urllib.request, urllib.error
method, port, path = sys.argv[1], sys.argv[2], sys.argv[3]
body = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
logf = sys.argv[5] if len(sys.argv) > 5 else None
assert int(port) in (52217, 52218), "own ports only"
url = f"http://127.0.0.1:{port}{path}"
t = time.time()
req = urllib.request.Request(url, data=body.encode() if body else None, method=method, headers={"Content-Type": "application/json", "X-Vysted-Region": "IN"})
try:
    r = urllib.request.urlopen(req, timeout=180); st = r.status; txt = r.read().decode('utf-8', 'replace')
except urllib.error.HTTPError as e:
    st = e.code; txt = e.read().decode('utf-8', 'replace')
except Exception as e:
    st = -1; txt = f"{type(e).__name__}: {e}"
dt = round(time.time() - t, 2)
if logf:
    with open(logf, 'a') as fh:
        fh.write(json.dumps({"ts": time.strftime('%H:%M:%S'), "method": method, "path": path, "body": body, "status": st, "secs": dt, "bytes": len(txt), "resp": txt[:4000]}) + "\n")
print(f"HTTP {st} {dt}s {len(txt)}B"); print(txt[:int(sys.argv[6]) if len(sys.argv) > 6 else 3000])
