"""L1-stranger HTTP drive: GET/POST against MY sidecar (:52225) only, append http-log.jsonl."""
import json, sys, time, urllib.request, urllib.error
BASE = "http://127.0.0.1:52225"
LOG = __file__.rsplit("/harness/", 1)[0] + "/http-log.jsonl"
def call(tag, method, path, body=None, timeout=90, keep=1200):
    t = time.time()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:
        status, raw = None, repr(e).encode()
    el = round(time.time() - t, 2)
    txt = raw.decode(errors="replace")
    rec = {"tag": tag, "method": method, "path": path, "body": body, "status": status, "elapsed_s": el,
           "bytes": len(raw), "at": time.strftime("%H:%M:%S"), "resp": txt[:keep]}
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"{tag} {method} {path} -> {status} {el}s {len(raw)}B | {txt[:220]}")
    return status, txt
if __name__ == "__main__":
    for spec in sys.argv[1:]:
        tag, method, path = spec.split(" ", 2)
        call(tag, method, path)
